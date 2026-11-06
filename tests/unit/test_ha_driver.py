"""Flow-driven HAEO driver: the bridge answers HAEO's own config flows.

The fake port models the parts of HAEO v0.5.0 we recorded from source: a single
config-flow step for the hub, an options flow per hub, and a subentry flow per
element. It is deliberately stricter than an in-memory store so the tests prove
we go *through* the flows instead of writing records.
"""

from __future__ import annotations

from typing import Any

import pytest

from custom_components.fleetassistant.haeo_bridge import contracts
from custom_components.fleetassistant.haeo_bridge.apply import apply_plan
from custom_components.fleetassistant.haeo_bridge.flows import (
    EntryRecord,
    FlowError,
    FlowHaeoDriver,
    SubentryRecord,
    interpret,
)
from custom_components.fleetassistant.haeo_bridge.plan import (
    ConnectionPlan,
    ElementPlan,
    HaeoTypeMap,
    HubPlan,
    NetworkPlan,
)


class FakeFlowPort:
    """Minimal HAEO-shaped flow manager."""

    def __init__(self, version: str | None = "0.5.0") -> None:
        self._version = version
        self.hub_entries: dict[str, EntryRecord] = {}
        self.hub_options: dict[str, dict[str, Any]] = {}
        self._flows: dict[str, dict[str, Any]] = {}
        self.subentries: dict[str, list[SubentryRecord]] = {}
        self.calls: list[str] = []
        self.require_fields = False

    # -- helpers ------------------------------------------------------------
    def _new_flow(self, kind: str, entry_id: str | None = None, subentry_type: str | None = None) -> str:
        flow_id = f"flow{len(self._flows) + 1}"
        self._flows[flow_id] = {"kind": kind, "entry_id": entry_id, "subentry_type": subentry_type}
        return flow_id

    def _entry_records(self) -> list[EntryRecord]:
        # Home Assistant reports creation data and options-flow data separately;
        # the port merges them (options win per section), so the fake does too.
        return [
            EntryRecord(
                entry_id=e.entry_id,
                title=e.title,
                options={**e.options, **self.hub_options.get(e.entry_id, {})},
                subentries=tuple(self.subentries[e.entry_id]),
            )
            for e in self.hub_entries.values()
        ]

    # -- port ---------------------------------------------------------------
    async def haeo_version(self) -> str | None:
        return self._version

    async def entries(self, domain: str) -> list[EntryRecord]:
        return self._entry_records()

    async def init_config_flow(self, handler: str) -> dict[str, Any]:
        self.calls.append(f"init_config_flow:{handler}")
        return {"type": "form", "flow_id": self._new_flow("config"), "step_id": "user", "data_schema": [{"name": "name"}]}

    async def configure(self, flow_id: str, user_input: dict[str, Any]) -> dict[str, Any]:
        self.calls.append("configure")
        common = user_input.get("common") or {}
        name = common.get("name")
        if not name or not common.get("horizon"):
            return {"type": "form", "flow_id": flow_id, "step_id": "user", "errors": {"base": "invalid_horizon"}}
        entry_id = f"haeo_{len(self.hub_entries) + 1}"
        self.hub_entries[entry_id] = EntryRecord(entry_id=entry_id, title=str(name), options=dict(user_input))
        self.hub_options[entry_id] = {}
        self.subentries[entry_id] = [
            SubentryRecord(subentry_id="sub_network", subentry_type=contracts.ELEMENT_TYPE_NETWORK, title="Network")
        ]
        return {"type": "create_entry", "flow_id": flow_id, "result": {"entry_id": entry_id, "title": name}}

    async def init_options_flow(self, entry_id: str) -> dict[str, Any]:
        self.calls.append(f"init_options_flow:{entry_id}")
        return {"type": "form", "flow_id": self._new_flow("options", entry_id), "step_id": "init"}

    async def configure_options(self, flow_id: str, user_input: dict[str, Any]) -> dict[str, Any]:
        self.calls.append("configure_options")
        entry_id = self._flows[flow_id]["entry_id"]
        self.hub_options[entry_id] = dict(user_input)
        return {"type": "create_entry", "result": {"entry_id": entry_id}}

    async def init_subentry_flow(
        self, entry_id: str, subentry_type: str, *, subentry_id: str | None = None
    ) -> dict[str, Any]:
        self.calls.append(f"init_subentry_flow:{entry_id}:{subentry_type}")
        if entry_id not in self.hub_entries:
            return {"type": "abort", "reason": "unknown_entry"}
        if not contracts.is_known_element_type(subentry_type):
            return {"type": "abort", "reason": "not_supported"}
        return {
            "type": "form",
            "flow_id": self._new_flow("subentry", entry_id, subentry_type),
            "step_id": subentry_type,
            "data_schema": [{"name": "name"}, {"name": "element_type"}],
        }

    async def configure_subentry(self, flow_id: str, user_input: dict[str, Any]) -> dict[str, Any]:
        self.calls.append("configure_subentry")
        flow = self._flows[flow_id]
        if self.require_fields and "max_power_source_target" not in user_input:
            # HAEO re-shows the element form when a declared field is missing.
            return {
                "type": "form",
                "flow_id": flow_id,
                "step_id": flow["subentry_type"],
                "errors": {"base": "invalid_schema"},
            }
        if "name" not in user_input:
            return {"type": "form", "flow_id": flow_id, "step_id": flow["subentry_type"]}
        entry_id = flow["entry_id"]
        subentry_id = user_input.get("subentry_id") or f"sub_{len(self.subentries[entry_id]) + 1}"
        self.subentries[entry_id].append(
            SubentryRecord(
                subentry_id=subentry_id,
                subentry_type=flow["subentry_type"],
                title=str(user_input["name"]),
                data={k: v for k, v in user_input.items() if k not in ("name", "element_type")},
            )
        )
        return {"type": "create_entry", "result": {"subentry_id": subentry_id}}

    async def remove_subentry(self, entry_id: str, subentry_id: str) -> None:
        self.calls.append(f"remove_subentry:{entry_id}:{subentry_id}")
        self.subentries[entry_id] = [s for s in self.subentries[entry_id] if s.subentry_id != subentry_id]


def _plan() -> NetworkPlan:
    hub = HubPlan(system_id="main", hub="fleetassistant_main", horizon_mode="preset", preset_days=5)
    elements = [
        ElementPlan(system_id="main", name="Grid", kind="grid", haeo_type="grid", params={}, inputs={}),
        ElementPlan(
            system_id="main",
            name="Battery",
            kind="battery",
            haeo_type="battery",
            params={"degradation_cost": {"currency_per_kwh": 0.04}},
            inputs={"capacity_kwh": 27.0},
        ),
    ]
    return NetworkPlan(
        site_id="site1",
        deployment_profile="gateway_primary",
        authority="full",
        hubs=[hub],
        elements=elements,
        connections=[],
        type_map=HaeoTypeMap(types=dict(contracts.CANDIDATE_KIND_TO_TYPE), verified=True),
    )


def _with_elements(plan: NetworkPlan, elements: list[ElementPlan]) -> NetworkPlan:
    return NetworkPlan(
        site_id=plan.site_id,
        deployment_profile=plan.deployment_profile,
        authority=plan.authority,
        hubs=list(plan.hubs),
        elements=list(elements),
        connections=list(plan.connections),
        type_map=plan.type_map,
    )


def _connection() -> ConnectionPlan:
    return ConnectionPlan(system_id="main", source="Grid", target="Battery")


def test_create_hub_answers_the_hub_flow_with_sectioned_data() -> None:
    port = FakeFlowPort()
    driver = FlowHaeoDriver(port)
    report = apply_plan(driver, _plan())

    assert report.status == "applied"
    created = next(iter(port.hub_entries.values()))
    assert created.title == "fleetassistant_main"
    assert created.options["common"]["horizon"] == {"value": "5_days"}
    assert created.options["advanced"]["debounce_seconds"] == contracts.DEFAULT_DEBOUNCE_SECONDS
    assert [s.title for s in port.subentries[created.entry_id]] == ["Network", "Grid", "Battery"]


def test_second_apply_is_a_noop() -> None:
    port = FakeFlowPort()
    driver = FlowHaeoDriver(port)

    assert apply_plan(driver, _plan()).status == "applied"
    port.calls.clear()
    second = apply_plan(driver, _plan())

    assert second.status == "noop"
    assert second.operations == []
    assert "configure_subentry" not in port.calls


def test_flow_that_reports_errors_becomes_a_repair_issue() -> None:
    port = FakeFlowPort()
    port.require_fields = True
    report = apply_plan(FlowHaeoDriver(port), _plan())

    assert report.status == "partial"
    codes = {issue.code for issue in report.issues}
    assert "haeo_flow_rejected" in codes
    assert report.error is not None and "invalid_schema" in report.error


def test_flow_that_asks_for_more_fields_names_them() -> None:
    step = interpret(
        {
            "type": "form",
            "flow_id": "f1",
            "step_id": "grid",
            "data_schema": [{"name": "max_power_source_target"}],
        }
    )
    with pytest.raises(FlowError) as caught:
        raise FlowError(step)

    assert caught.value
    assert caught.value.code == "haeo_flow_incomplete"
    assert "max_power_source_target" in str(caught.value)


def test_connections_block_before_any_flow_starts() -> None:
    port = FakeFlowPort()
    plan = _plan()
    maybe = _with_elements(plan, plan.elements)
    object.__setattr__(maybe, "connections", [_connection()])

    report = apply_plan(FlowHaeoDriver(port), maybe)

    assert report.status == "blocked"
    assert {issue.code for issue in report.issues} == {"haeo_connection_fields_unverified"}
    assert port.calls == []


def test_relax_flag_change_drives_the_options_flow() -> None:
    port = FakeFlowPort()
    driver = FlowHaeoDriver(port)
    apply_plan(driver, _plan())

    stricter = _plan()
    stricter.hubs[0] = HubPlan(
        system_id="main", hub="fleetassistant_main", horizon_mode="preset", preset_days=5, relax_impossible_plans=False
    )
    report = apply_plan(driver, stricter)

    assert report.status == "applied"
    assert [op.type for op in report.operations] == ["update_hub"]
    assert port.hub_options[next(iter(port.hub_options))]["advanced"]["relax_infeasible"] is False


def test_unknown_element_type_is_refused_by_preflight() -> None:
    port = FakeFlowPort()
    plan = _with_elements(
        _plan(),
        [ElementPlan(system_id="main", name="Meter", kind="meter", haeo_type="meter_bogus", params={}, inputs={}), _plan().elements[1]],
    )

    report = apply_plan(FlowHaeoDriver(port), plan)

    assert report.status == "blocked"
    assert {issue.code for issue in report.issues} == {"haeo_type_unknown"}
    assert port.calls == []


def test_removed_element_is_deleted_through_the_subentry_manager() -> None:
    port = FakeFlowPort()
    driver = FlowHaeoDriver(port)
    apply_plan(driver, _plan())

    smaller = _with_elements(_plan(), _plan().elements[:1])
    report = apply_plan(driver, smaller)

    assert [op.type for op in report.operations] == ["remove_element"]
    assert any(call.startswith("remove_subentry:") for call in port.calls)
