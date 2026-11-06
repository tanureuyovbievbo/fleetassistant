"""Compile a site profile into a HAEO *network plan* (pure Python).

The network plan is the intermediate representation between the HAEO-agnostic
site profile and HAEO's config-flow entries. It is deliberately data-only so it
can be diffed, reviewed, and contract-tested before anything is applied.

Serializable so the HA runtime can persist it. Immutable so a diff cannot
mutate the plan it came from.

Topology note: HAEO does not have connection entries. Each connected element
carries ``connection = {"type": "connection_target", "value": "<junction name>"}``
(``core/schema/sections/common.py``), so this module synthesises one junction
element per system and points every connected element at it. The profile's
``connections`` list stays in the plan for readable review and for schema-level
integrity checks, but nothing is written for it: it is expressed through the
element fields.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from ..pricing.compiler import INPUT_NAMES, price_entity_id
from . import contracts, fields

HorizonMode = Literal["preset", "forecast_sensor"]

#: HAEO element type names per profile kind, read from HAEO v0.5.0.
#:
#: The names are source-verified (``haeo_bridge/contracts.py``); the *mapping
#: choice* for ``meter``/``thermostat``/``relay`` is not, so those kinds stay
#: ``None`` and block an apply (C-23, OQ-002). Do not fill them from memory.
DEFAULT_TYPE_MAP: dict[str, str | None] = dict(contracts.CANDIDATE_KIND_TO_TYPE)

#: Kinds HAEO models as a node in the power network, so they need a connection.
CONNECTED_KINDS = frozenset({"grid", "battery", "load", "solar", "ev_charger"})


@dataclass(frozen=True)
class HaeoTypeMap:
    """Maps profile element kinds to HAEO element type names."""

    types: dict[str, str | None] = field(default_factory=lambda: dict(DEFAULT_TYPE_MAP))
    verified: bool = False
    source: str = (
        f"SOURCE_VERIFIED names from haeo@{contracts.HAEO_SURFACE_VERSION}; "
        "LIVE_UNVERIFIED until tests/contract/haeo passes (OQ-002)"
    )

    def lookup(self, kind: str) -> str | None:
        return self.types.get(kind)

    @property
    def unresolved_kinds(self) -> frozenset[str]:
        return frozenset(kind for kind, haeo_type in self.types.items() if haeo_type is None)


@dataclass(frozen=True)
class HubPlan:
    system_id: str
    hub: str
    horizon_mode: HorizonMode
    preset_days: int | None = None
    forecast_entity: str | None = None
    relax_impossible_plans: bool = True

    @property
    def horizon_preset(self) -> str | None:
        """HAEO preset name for this hub's horizon, if it uses a preset."""
        if self.horizon_mode != "preset":
            return None
        return contracts.horizon_preset_for(self.preset_days)

    def config_data(self) -> dict[str, Any]:
        """Hub *creation* data as HAEO v0.5.0 stores it (sectioned).

        Read from ``flows/hub.py:HubConfigFlow._create_hub_entry``: the setup
        form only carries name and horizon, plus the advanced-mode flag. The
        plan's ``relax_impossible_plans`` is written afterwards through
        :meth:`options_data` because HAEO exposes it in the hub's options flow.
        """
        return {
            contracts.CONF_INTEGRATION_TYPE: contracts.INTEGRATION_TYPE_HUB,
            contracts.HUB_SECTION_COMMON: {
                contracts.CONF_NAME: self.hub,
                contracts.CONF_HORIZON: contracts.horizon_value(
                    self.horizon_mode, self.horizon_preset, self.forecast_entity
                ),
            },
            contracts.HUB_SECTION_ADVANCED: {
                contracts.CONF_DEBOUNCE_SECONDS: contracts.DEFAULT_DEBOUNCE_SECONDS,
                contracts.CONF_ADVANCED_MODE: False,
            },
        }

    def options_data(self) -> dict[str, Any]:
        """Hub *options* data this plan requires (advanced section only).

        ``relax_infeasible`` is HAEO's "Relax impossible plans". Its default is
        False and fleetassistant wants True on fleet sites (ADR-0009), so the
        bridge always writes it explicitly.
        """
        return {
            contracts.HUB_SECTION_ADVANCED: {
                contracts.CONF_RELAX_INFEASIBLE: self.relax_impossible_plans,
            }
        }

    def options(self) -> dict[str, Any]:
        """Flat view of the hub settings the bridge asks HAEO for.

        Kept for diffing: it is what the driver compares, not what HAEO stores.
        """
        return {
            "hub": self.hub,
            "horizon_mode": self.horizon_mode,
            "horizon_preset": self.horizon_preset,
            "horizon_forecast_entity": self.forecast_entity,
            "relax_infeasible": self.relax_impossible_plans,
        }


@dataclass(frozen=True)
class ElementPlan:
    """One HAEO element: what we write, and what we could not fill."""

    system_id: str
    name: str
    kind: str
    haeo_type: str | None
    sections: dict[str, dict[str, Any]] = field(default_factory=dict)
    connection: str | None = None
    missing_fields: tuple[tuple[str, str], ...] = ()
    ignored_keys: tuple[str, ...] = ()
    #: Profile keys HAEO has no field for but the site still needs (degradation
    #: cost, vendor identity). Kept for checks and diagnostics, never written.
    profile_extras: dict[str, Any] = field(default_factory=dict)
    #: Payload keys stored next to the sections rather than inside one (a
    #: ``policy`` element keeps its ``rules`` list here).
    flat: dict[str, Any] = field(default_factory=dict)

    @property
    def identity(self) -> str:
        """Stable key used for idempotent diffing (name, not HAEO entry id)."""
        return f"{self.system_id}:{self.name}"

    def payload(self) -> dict[str, Any]:
        """Element data as HAEO stores it (requires a resolved ``haeo_type``)."""
        if self.haeo_type is None:
            raise ValueError(f"element {self.name!r} has no HAEO type (OQ-002)")
        return fields.element_payload(self.name, self.haeo_type, self.sections, self.connection, self.flat)


@dataclass(frozen=True)
class ConnectionPlan:
    """A profile-declared link. Kept for review and integrity checks only."""

    system_id: str
    source: str
    target: str
    kind: str = "power"

    @property
    def identity(self) -> str:
        return f"{self.system_id}:{self.source}->{self.target}"


@dataclass(frozen=True)
class NetworkPlan:
    site_id: str
    deployment_profile: str
    authority: str
    hubs: tuple[HubPlan, ...]
    elements: tuple[ElementPlan, ...]
    connections: tuple[ConnectionPlan, ...]
    type_map: HaeoTypeMap
    source_schema_version: int = 1
    generated_by: str = "fleetassistant"

    def elements_of(self, system_id: str) -> tuple[ElementPlan, ...]:
        return tuple(element for element in self.elements if element.system_id == system_id)

    # -- serialization ------------------------------------------------------
    def as_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id,
            "deployment_profile": self.deployment_profile,
            "authority": self.authority,
            "source_schema_version": self.source_schema_version,
            "generated_by": self.generated_by,
            "type_map": {
                "types": dict(self.type_map.types),
                "verified": self.type_map.verified,
                "source": self.type_map.source,
            },
            "hubs": [
                {
                    "system_id": h.system_id,
                    "hub": h.hub,
                    "horizon_mode": h.horizon_mode,
                    "preset_days": h.preset_days,
                    "forecast_entity": h.forecast_entity,
                    "relax_impossible_plans": h.relax_impossible_plans,
                }
                for h in self.hubs
            ],
            "elements": [
                {
                    "system_id": e.system_id,
                    "name": e.name,
                    "kind": e.kind,
                    "haeo_type": e.haeo_type,
                    "sections": e.sections,
                    "connection": e.connection,
                    "missing_fields": [list(m) for m in e.missing_fields],
                    "ignored_keys": list(e.ignored_keys),
                    "profile_extras": e.profile_extras,
                }
                for e in self.elements
            ],
            "connections": [
                {"system_id": c.system_id, "source": c.source, "target": c.target, "kind": c.kind}
                for c in self.connections
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NetworkPlan:
        tm = data.get("type_map", {})
        return cls(
            site_id=data["site_id"],
            deployment_profile=data["deployment_profile"],
            authority=data["authority"],
            source_schema_version=data.get("source_schema_version", 1),
            generated_by=data.get("generated_by", "fleetassistant"),
            type_map=HaeoTypeMap(
                types=dict(tm.get("types", DEFAULT_TYPE_MAP)),
                verified=bool(tm.get("verified", False)),
                source=tm.get("source", "UNVERIFIED"),
            ),
            hubs=tuple(
                HubPlan(
                    system_id=h["system_id"],
                    hub=h["hub"],
                    horizon_mode=h["horizon_mode"],
                    preset_days=h.get("preset_days"),
                    forecast_entity=h.get("forecast_entity"),
                    relax_impossible_plans=h.get("relax_impossible_plans", True),
                )
                for h in data.get("hubs", [])
            ),
            elements=tuple(
                ElementPlan(
                    system_id=e["system_id"],
                    name=e["name"],
                    kind=e["kind"],
                    haeo_type=e.get("haeo_type"),
                    sections={section: dict(values) for section, values in e.get("sections", {}).items()},
                    connection=e.get("connection"),
                    missing_fields=tuple(tuple(item) for item in e.get("missing_fields", [])),
                    ignored_keys=tuple(e.get("ignored_keys", [])),
                    profile_extras=dict(e.get("profile_extras", {})),
                )
                for e in data.get("elements", [])
            ),
            connections=tuple(
                ConnectionPlan(
                    system_id=c["system_id"],
                    source=c["source"],
                    target=c["target"],
                    kind=c.get("kind", "power"),
                )
                for c in data.get("connections", [])
            ),
        )


#: Profile element key -> the compiled price input that fills it.
PRICE_ENTITY_FIELDS = {
    "import_price_entity": INPUT_NAMES["import"],
    "export_price_entity": INPUT_NAMES["export"],
}


def _with_price_entities(
    element: dict[str, Any],
    site_id: str,
    overrides: Mapping[str, Mapping[str, str]] | None,
) -> dict[str, Any]:
    """Point a grid element at the price sensors we publish.

    A grid element cannot be created without directional prices, and the profile
    carries rate *providers*, not entity ids. So the compiler fills them with the
    ids of the forecast sensors the pricing compiler emits, unless the caller
    passes explicit ids (``price_entities``) for a site that already has them.
    """
    if element["kind"] != "grid":
        return element
    explicit = dict((overrides or {}).get(element["id"], {}))
    filled = dict(element)
    for key, input_name in PRICE_ENTITY_FIELDS.items():
        filled.setdefault(key, explicit.get(key) or price_entity_id(site_id, input_name))
    return filled


def compile_plan(
    profile: dict[str, Any],
    type_map: HaeoTypeMap | None = None,
    *,
    price_entities: Mapping[str, Mapping[str, str]] | None = None,
) -> NetworkPlan:
    """Compile a validated profile into a network plan.

    ``price_entities`` overrides the price sensor ids per element id, for sites
    that already publish them (keys ``import_price_entity`` /
    ``export_price_entity``). Without it, grid elements point at the sensors the
    pricing compiler emits for this site.

    Raises ``ValueError`` if the profile is structurally unusable. It does not
    run schema validation — call ``profile.validate_profile`` first (the
    runtime does both).
    """
    tm = type_map or HaeoTypeMap()
    deployment = profile["deployment"]["profile"]
    authority = "coarse" if deployment == "cloud_primary" else "full"

    hubs: list[HubPlan] = []
    elements: list[ElementPlan] = []
    connections: list[ConnectionPlan] = []

    for system in profile["systems"]:
        system_id = system["id"]
        haeo = system["haeo"]
        horizon = haeo["horizon"]
        hubs.append(
            HubPlan(
                system_id=system_id,
                hub=haeo["hub"],
                horizon_mode=horizon["mode"],
                preset_days=horizon.get("preset_days"),
                forecast_entity=horizon.get("forecast_entity"),
                relax_impossible_plans=bool(profile.get("deployment", {}).get("relax_impossible_plans", True)),
            )
        )
        for raw_element in system["elements"]:
            element = _with_price_entities(raw_element, profile["site"]["id"], price_entities)
            kind = element["kind"]
            compiled = fields.compile_element_fields(element, tm.lookup(kind))
            elements.append(
                ElementPlan(
                    system_id=system_id,
                    name=element["id"],
                    kind=kind,
                    haeo_type=tm.lookup(kind),
                    sections=compiled.sections,
                    connection=fields.HUB_SWITCHBOARD if kind in CONNECTED_KINDS else None,
                    missing_fields=compiled.missing,
                    ignored_keys=compiled.ignored,
                    profile_extras={
                        key: value
                        for key, value in element.items()
                        if key in fields.PROFILE_ONLY_KEYS and key not in ("id", "kind", "name", "notes", "haeo_name")
                    },
                )
            )
        elements.extend(_degradation_policies(elements, system_id))
        for connection in system.get("connections", []):
            connections.append(
                ConnectionPlan(
                    system_id=system_id,
                    source=connection["from"],
                    target=connection["to"],
                    kind=connection.get("kind", "power"),
                )
            )

    return NetworkPlan(
        site_id=profile["site"]["id"],
        deployment_profile=deployment,
        authority=authority,
        hubs=tuple(hubs),
        elements=tuple(elements),
        connections=tuple(connections),
        type_map=tm,
    )


def _degradation_policies(elements: Sequence[ElementPlan], system_id: str) -> list[ElementPlan]:
    """Price each battery's discharge wear as a ``policy`` rule (ADR-0017).

    HAEO's battery has no degradation field. Its policy compiler places a rule's
    price on the sink-side minimum cut of the flow from ``source`` to ``target``;
    for a single source with a wildcard target that cut collapses to the source's
    own outbound edges — i.e. exactly the battery's discharge (F-056). Worse
    numbers make the optimizer prefer other sources.

    Deliberate gaps, reviewed again at docs/verification/REVIEW_LATER.md:

    - RL-01: only *discharge* wear is priced. Charging-side wear is unpriced, so an
      arbitrage plan can cycle the battery without paying for the wear it causes.
    - RL-02: the price is a constant snapshot. A cost that varies with temperature
      or SOC needs a per-period entity, not a constant.
    - RL-03: the wildcard target is exact for one battery per system. With two
      batteries, both rules cover the same flow and each battery pays the other's
      discharge cost.

    Changing any of these changes dispatch, so it is a decision (ADR-0017), never a
    quiet edit.
    """
    policies: list[ElementPlan] = []
    for element in elements:
        if element.system_id != system_id or element.haeo_type != "battery":
            continue
        cost = (element.profile_extras.get("degradation_cost") or {}).get("currency_per_kwh")
        if not cost or float(cost) <= 0:
            continue
        policies.append(
            ElementPlan(
                system_id=system_id,
                name=f"{element.name}_degradation",
                kind="policy",
                haeo_type=contracts.POLICY_TYPE,
                flat={
                    contracts.POLICY_RULES_FIELD: [
                        {
                            "name": f"{element.name} discharge wear",
                            "enabled": True,
                            "source": [element.name],
                            "target": [contracts.POLICY_WILDCARD],
                            "price": fields.tag_value("constant", float(cost)),
                        }
                    ]
                },
                profile_extras={
                    "degradation_cost": element.profile_extras["degradation_cost"],
                    "priced_element": element.name,
                },
            )
        )
    return policies


