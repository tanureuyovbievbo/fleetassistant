"""Compile a site profile into a HAEO *network plan* (pure Python).

The network plan is the intermediate representation between the HAEO-agnostic
site profile and HAEO's config-flow entries. It is deliberately data-only so it
can be diffed, reviewed, and contract-tested before anything is applied.

Serializable so the HA runtime can persist it. Immutable so a diff cannot
mutate the plan it came from.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from . import contracts

HorizonMode = Literal["preset", "forecast_sensor"]

#: HAEO element type names per profile kind, read from HAEO v0.5.0.
#:
#: The names are source-verified (``haeo_bridge/contracts.py``); the *mapping
#: choice* for ``meter``/``thermostat``/``relay`` is not, so those kinds stay
#: ``None`` and block an apply (C-23, OQ-002). Do not fill them from memory.
DEFAULT_TYPE_MAP: dict[str, str | None] = dict(contracts.CANDIDATE_KIND_TO_TYPE)


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
    system_id: str
    name: str
    kind: str
    haeo_type: str | None
    params: dict[str, Any]
    inputs: dict[str, Any]

    @property
    def identity(self) -> str:
        """Stable key used for idempotent diffing (name, not HAEO entry id)."""
        return f"{self.system_id}:{self.name}"


@dataclass(frozen=True)
class ConnectionPlan:
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
                    "params": e.params,
                    "inputs": e.inputs,
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
                    params=dict(e.get("params", {})),
                    inputs=dict(e.get("inputs", {})),
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


#: Profile element fields that become HAEO *inputs* (runtime-writable constants).
#: HAEO creates an input entity per configured field (brief), so these can be
#: changed at runtime without reconfiguring the element. Key names UNVERIFIED.
_INPUT_FIELDS = ("capacity_kwh", "min_soc_pct", "max_soc_pct", "import_limit_kw", "export_limit_kw")


def compile_plan(profile: dict[str, Any], type_map: HaeoTypeMap | None = None) -> NetworkPlan:
    """Compile a validated profile into a network plan.

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
        for element in system["elements"]:
            params = {
                key: value
                for key, value in element.items()
                if key not in ("id", "kind", "name", "notes")
            }
            inputs = {key: params[key] for key in _INPUT_FIELDS if key in params}
            elements.append(
                ElementPlan(
                    system_id=system_id,
                    name=element["id"],
                    kind=element["kind"],
                    haeo_type=tm.lookup(element["kind"]),
                    params=params,
                    inputs=inputs,
                )
            )
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
