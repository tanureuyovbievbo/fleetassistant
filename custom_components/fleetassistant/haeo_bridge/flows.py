"""Drive HAEO's config flows through a small port.

Why a port: the Home Assistant flow managers are async APIs on ``hass``, and
HAEO's flows are UI flows (HAEO has no YAML config). Everything we need is
"start a flow, answer it, read what came back", so the mechanism is factored
behind :class:`FlowPort` and can be exercised without Home Assistant.

The Home Assistant implementation of the port is ``home_assistant_port`` in
:mod:`.ha_port`; it uses ``hass.config_entries.flow``,
``hass.config_entries.options`` and ``hass.config_entries.subentries``, which are
the same managers the REST endpoints and the UI use (see FACTS F-031..F-038).

Two rules this module enforces:

* We answer a flow and let HAEO validate and normalise the input. We never
  write a config entry or subentry directly, and we never touch HAEO storage
  (C-05, C-06).
* A flow that comes back with a form we cannot answer is a *stop*, not a retry
  loop: :class:`FlowError` names the step and the fields that are still missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from ..profile.schema import Issue
from . import contracts
from .apply import DriverError
from .plan import ElementPlan, NetworkPlan

FlowKind = Literal["form", "create_entry", "abort", "external_step", "progress", "unknown"]


@dataclass(frozen=True)
class SubentryRecord:
    """One HAEO element/connection subentry as Home Assistant reports it."""

    subentry_id: str
    subentry_type: str
    title: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EntryRecord:
    """One HAEO hub config entry as Home Assistant reports it."""

    entry_id: str
    title: str
    options: dict[str, Any] = field(default_factory=dict)
    subentries: tuple[SubentryRecord, ...] = ()

    def subentries_of_type(self, subentry_type: str) -> tuple[SubentryRecord, ...]:
        return tuple(s for s in self.subentries if s.subentry_type == subentry_type)


@dataclass(frozen=True)
class FlowStep:
    """A normalised flow result."""

    flow_id: str
    step_id: str | None
    kind: FlowKind
    fields: tuple[str, ...] = ()
    errors: dict[str, str] = field(default_factory=dict)
    entry: EntryRecord | None = None

    @property
    def missing_fields(self) -> tuple[str, ...]:
        return self.fields if self.kind == "form" else ()


class FlowError(DriverError):
    """A flow did not reach a conclusion we can use."""

    def __init__(self, step: FlowStep, detail: str = "") -> None:
        self.step = step
        where = f"step {step.step_id!r}" if step.step_id else "flow"
        parts = [f"HAEO {where} ended as {step.kind}"]
        if step.errors:
            parts.append("errors: " + ", ".join(f"{k}={v}" for k, v in sorted(step.errors.items())))
        if step.kind == "form" and step.fields:
            parts.append("still asking for: " + ", ".join(step.fields))
        if detail:
            parts.append(detail)
        # A form that came back with validation errors is a rejection; a plain
        # form is just a step we have no answer for (missing recorded fields).
        rejected = step.kind != "form" or bool(step.errors)
        super().__init__(
            "; ".join(parts),
            code="haeo_flow_rejected" if rejected else "haeo_flow_incomplete",
            path=step.step_id or "",
        )


class BridgeUnverified(DriverError):
    """Refused because a required HAEO field name is not recorded yet."""

    def __init__(self, what: str, code: str = "haeo_fields_unverified") -> None:
        super().__init__(f"{what}: HAEO field names are not recorded yet (OQ-017)", code=code)


class FlowPort(Protocol):
    """The slice of Home Assistant's flow managers the bridge needs."""

    async def haeo_version(self) -> str | None: ...

    async def entries(self, domain: str) -> list[EntryRecord]: ...

    async def init_config_flow(self, handler: str) -> dict[str, Any]: ...

    async def configure(self, flow_id: str, user_input: dict[str, Any]) -> dict[str, Any]: ...

    async def init_options_flow(self, entry_id: str) -> dict[str, Any]: ...

    async def configure_options(self, flow_id: str, user_input: dict[str, Any]) -> dict[str, Any]: ...

    async def init_subentry_flow(
        self,
        entry_id: str,
        subentry_type: str,
        *,
        subentry_id: str | None = None,
    ) -> dict[str, Any]: ...

    async def configure_subentry(self, flow_id: str, user_input: dict[str, Any]) -> dict[str, Any]: ...

    async def remove_subentry(self, entry_id: str, subentry_id: str) -> None: ...


def _kind(result: dict[str, Any]) -> FlowKind:
    raw = result.get("type")
    value = getattr(raw, "value", raw)
    if value in ("form", "create_entry", "abort", "external_step", "progress"):
        return value  # type: ignore[return-value]
    return "unknown"


def _schema_keys(schema: Any) -> tuple[str, ...]:
    """Extract field names from a serialised or live voluptuous schema."""
    keys: list[str] = []
    if isinstance(schema, list):
        for item in schema:
            if not isinstance(item, dict):
                continue
            if "name" in item and isinstance(item["name"], str):
                keys.append(item["name"])
            keys.extend(_schema_keys(item.get("schema")))
        return tuple(keys)
    mapping = getattr(schema, "schema", schema if isinstance(schema, dict) else None)
    if isinstance(mapping, dict):
        for key in mapping:
            name = getattr(key, "schema", key)
            if isinstance(name, str):
                keys.append(name)
            keys.extend(_schema_keys(mapping[key]))
    return tuple(keys)


def interpret(result: dict[str, Any]) -> FlowStep:
    """Turn a raw flow result (in-process or REST shape) into a FlowStep."""
    kind = _kind(result)
    entry: EntryRecord | None = None
    created = result.get("result")
    if kind == "create_entry" and isinstance(created, dict):
        entry = EntryRecord(entry_id=str(created.get("entry_id", "")), title=str(created.get("title", "")))
    return FlowStep(
        flow_id=str(result.get("flow_id", "")),
        step_id=result.get("step_id"),
        kind=kind,
        fields=_schema_keys(result.get("data_schema")) if kind == "form" else (),
        errors={k: str(v) for k, v in (result.get("errors") or {}).items()},
        entry=entry,
    )


class FlowHaeoDriver:
    """``HaeoDriver`` implementation that answers HAEO's flows.

    Synchronous on the outside because :func:`apply.apply_plan` is synchronous
    and testable; the port is awaited on a private event loop, so the port
    implementation may be async (Home Assistant) or a plain fake.
    """

    def __init__(self, port: FlowPort, *, advanced_options: bool = False) -> None:
        self._port = port
        self._advanced_options = advanced_options
        self.log: list[str] = []

    # -- preflight ----------------------------------------------------------
    def preflight(self, plan: NetworkPlan) -> list[Issue]:
        """Refuse plans that would need field names we have not recorded."""
        issues: list[Issue] = []
        if plan.connections and contracts.CONNECTION_FIELDS_UNRESOLVED:
            issues.append(
                Issue(
                    "haeo_connection_fields_unverified",
                    "connections",
                    "HAEO connection fields (source/target keys) are not recorded yet; "
                    "applying would create a network without links (OQ-017)",
                )
            )
        for element in plan.elements:
            if element.haeo_type is None:
                issues.append(
                    Issue(
                        "haeo_kind_unmapped",
                        f"{element.system_id}.{element.name}",
                        f"profile kind {element.kind!r} has no recorded HAEO element (ADR-0013)",
                    )
                )
            elif not contracts.is_known_element_type(element.haeo_type):
                issues.append(
                    Issue(
                        "haeo_type_unknown",
                        f"{element.system_id}.{element.name}",
                        f"HAEO {contracts.HAEO_SURFACE_VERSION} has no element type {element.haeo_type!r}",
                    )
                )
        return issues

    # -- HaeoDriver ---------------------------------------------------------
    def haeo_version(self) -> str | None:
        return self._await(self._port.haeo_version())

    def list_hubs(self) -> dict[str, dict[str, Any]]:
        return {record.title: {"options": _hub_options_from(record), "entry_id": record.entry_id} for record in self._entries()}

    def create_hub(self, name: str, options: dict[str, Any]) -> None:
        hub = _hub_plan(options, name)
        self._drive_config_flow(hub.config_data())
        # HAEO's setup form does not carry every setting (``relax_infeasible``
        # lives in the options flow and defaults to False), so settle the hub now
        # instead of leaving a "changed" hub for the next apply to discover.
        if _hub_options_from(self._entry(name)) != hub.options():
            self.update_hub(name, options)

    def update_hub(self, name: str, options: dict[str, Any]) -> None:
        record = self._entry(name)
        hub = _hub_plan(options, name)
        step = interpret(self._await(self._port.init_options_flow(record.entry_id)))
        if step.kind == "create_entry":
            return
        if step.kind != "form":
            raise FlowError(step, f"options flow for hub {name!r}")
        final = interpret(self._await(self._port.configure_options(step.flow_id, hub.options_data())))
        if final.kind != "create_entry":
            raise FlowError(final, f"options flow for hub {name!r}")

    def remove_hub(self, name: str) -> None:
        record = self._entry(name)
        for subentry in record.subentries:
            self._await(self._port.remove_subentry(record.entry_id, subentry.subentry_id))
        self.log.append(f"remove_hub:{name}")

    def list_elements(self, hub: str) -> dict[str, dict[str, Any]]:
        record = self._entry(hub)
        return {
            subentry.title: {
                "payload": {"type": subentry.subentry_type, "data": _normalise_element_data(subentry.data)}
            }
            for subentry in record.subentries
            if subentry.subentry_type not in contracts.NON_ELEMENT_SUBENTRY_TYPES
        }

    def create_element(self, hub: str, element: ElementPlan) -> None:
        record = self._entry(hub)
        haeo_type = self._require_type(element)
        data = {"name": element.name, "element_type": haeo_type, **element.params, **element.inputs}
        self._drive_subentry_flow(record.entry_id, haeo_type, data)

    def update_element(self, hub: str, name: str, element: ElementPlan) -> None:
        record = self._entry(hub)
        subentry = self._subentry(record, name)
        haeo_type = self._require_type(element)
        data = {"name": element.name, "element_type": haeo_type, **element.params, **element.inputs}
        self._drive_subentry_flow(
            record.entry_id,
            subentry.subentry_type,
            data,
            subentry_id=subentry.subentry_id,
        )

    def remove_element(self, hub: str, name: str) -> None:
        record = self._entry(hub)
        subentry = self._subentry(record, name)
        self._await(self._port.remove_subentry(record.entry_id, subentry.subentry_id))

    def list_connections(self, hub: str) -> set[tuple[str, str]]:
        # Connection subentry field names are unrecorded (OQ-017), so a plan with
        # connections never reaches this: ``preflight`` blocks it first.
        raise BridgeUnverified("reading HAEO connections", code="haeo_connection_fields_unverified")

    def create_connection(self, hub: str, source: str, target: str) -> None:
        raise BridgeUnverified("creating a HAEO connection", code="haeo_connection_fields_unverified")

    def remove_connection(self, hub: str, source: str, target: str) -> None:
        raise BridgeUnverified("removing a HAEO connection", code="haeo_connection_fields_unverified")

    # -- internals ----------------------------------------------------------
    def _await(self, awaitable: Any) -> Any:
        import asyncio

        return asyncio.run(awaitable)

    def _entries(self) -> list[EntryRecord]:
        return self._await(self._port.entries(contracts.HAEO_DOMAIN))

    def _entry(self, name: str) -> EntryRecord:
        for record in self._entries():
            if record.title == name:
                return record
        raise DriverError(f"HAEO hub {name!r} does not exist", code="haeo_hub_missing")

    def _subentry(self, record: EntryRecord, name: str) -> SubentryRecord:
        for subentry in record.subentries:
            if subentry.title == name and subentry.subentry_type not in contracts.NON_ELEMENT_SUBENTRY_TYPES:
                return subentry
        raise DriverError(f"HAEO element {name!r} does not exist", code="haeo_element_missing")

    def _require_type(self, element: ElementPlan) -> str:
        if element.haeo_type is None:
            raise BridgeUnverified(f"element {element.name!r} kind {element.kind!r}", code="haeo_kind_unmapped")
        if not contracts.is_known_element_type(element.haeo_type):
            raise DriverError(
                f"HAEO {contracts.HAEO_SURFACE_VERSION} has no element type {element.haeo_type!r}",
                code="haeo_type_unknown",
            )
        return element.haeo_type

    def _drive_config_flow(self, data: dict[str, Any]) -> EntryRecord:
        step = interpret(self._await(self._port.init_config_flow(contracts.HAEO_DOMAIN)))
        if step.kind == "create_entry":
            self.log.append("create_hub:single_step")
            return step.entry or EntryRecord(entry_id="", title="")
        if step.kind != "form":
            raise FlowError(step, "hub config flow")
        final = interpret(self._await(self._port.configure(step.flow_id, data)))
        if final.kind != "create_entry":
            raise FlowError(final, "hub config flow")
        self.log.append(f"create_hub:{data.get('common', {}).get('name')}")
        return final.entry or EntryRecord(entry_id="", title="")

    def _drive_subentry_flow(
        self,
        entry_id: str,
        subentry_type: str,
        data: dict[str, Any],
        *,
        subentry_id: str | None = None,
    ) -> EntryRecord | None:
        step = interpret(
            self._await(
                self._port.init_subentry_flow(entry_id, subentry_type, subentry_id=subentry_id)
            )
        )
        if step.kind == "create_entry":
            return step.entry
        if step.kind != "form":
            raise FlowError(step, f"{subentry_type} subentry flow")
        final = interpret(self._await(self._port.configure_subentry(step.flow_id, data)))
        if final.kind != "create_entry":
            raise FlowError(final, f"{subentry_type} subentry flow")
        self.log.append(f"subentry:{subentry_type}:{data.get('name')}")
        return final.entry


def _hub_plan(options: dict[str, Any], name: str) -> Any:
    from .plan import HubPlan

    raw_preset = options.get("horizon_preset")
    days = raw_preset if isinstance(raw_preset, int) else contracts.preset_days(raw_preset)
    return HubPlan(
        system_id=str(options.get("system_id", name)),
        hub=name,
        horizon_mode=str(options.get("horizon_mode", "preset")),
        preset_days=days or 5,
        forecast_entity=options.get("horizon_forecast_entity"),
        relax_impossible_plans=bool(options.get("relax_infeasible", True)),
    )


def _hub_options_from(record: EntryRecord) -> dict[str, Any]:
    """Rebuild the flat diff view from what Home Assistant reports for a hub.

    HA reports the creation data as HAEO stored it (sectioned) merged with the
    options-flow data, so the tagged horizon value has to be unwrapped before it
    can be compared to :meth:`HubPlan.options`.
    """
    merged = dict(record.options)
    common = merged.get(contracts.HUB_SECTION_COMMON) or {}
    advanced = merged.get(contracts.HUB_SECTION_ADVANCED) or {}
    horizon = common.get(contracts.CONF_HORIZON) or {}
    value = horizon.get(contracts.HORIZON_VALUE_KEY)
    entity: str | None = None
    preset: str | None = None
    if isinstance(value, list):
        entity = str(value[0]) if value else None
    elif isinstance(value, str):
        preset = value
    return {
        "hub": record.title,
        "horizon_mode": "forecast_sensor" if entity else "preset",
        "horizon_preset": preset,
        "horizon_forecast_entity": entity,
        "relax_infeasible": bool(advanced.get(contracts.CONF_RELAX_INFEASIBLE, contracts.HAEO_DEFAULT_RELAX_INFEASIBLE)),
    }


def _normalise_element_data(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if key not in ("name", "element_type")}
