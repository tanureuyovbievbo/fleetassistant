"""HAEO element fields: what each element type stores, and how we fill it.

Read from ``hass-energy/haeo`` v0.5.0 ``core/schema/elements/*.py`` and
``core/schema/sections/*.py`` on 2026-11-06. Three facts shape this module:

1. **Every element config is sectioned.** ``grid`` stores
   ``pricing``/``power_limits``; ``battery`` stores
   ``storage``/``limits``/``power_limits``/``pricing``/``efficiency``/``advanced``;
   ``load`` and ``solar`` store ``forecast``/``curtailment``; ``ev`` stores
   ``vehicle``/``charging``/``trip``/``public_charging``/``efficiency``/``advanced``.
2. **Every value is a tagged schema value**, not a bare number:
   ``{"type": "constant", "value": 12.0}`` or ``{"type": "entity", "value": ["sensor.x"]}``.
3. **Connectivity is a field, not an entry.** ``ConnectedCommonConfig`` requires
   ``connection`` = ``{"type": "connection_target", "value": "<element name>"}``,
   so topology is expressed by pointing each element at a junction (switchboard).

Names and shapes here are source-verified; that a live instance accepts our
payloads is not (``ELEMENT_FIELDS_LIVE_VERIFIED`` stays False, ADR-0012), so the
bridge refuses to apply until the live contract matrix passes.

Nothing here imports Home Assistant.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from . import contracts

ValueKind = Literal["entity", "constant", "none", "ratio"]

SOURCE_ELEMENTS = "haeo@0.5.0 core/schema/elements/"
SOURCE_SECTIONS = "haeo@0.5.0 core/schema/sections/"

#: Section name holding an element's own power limits (grid, battery).
SECTION_POWER_LIMITS = "power_limits"
SECTION_PRICING = "pricing"
SECTION_STORAGE = "storage"
SECTION_LIMITS = "limits"
SECTION_EFFICIENCY = "efficiency"
SECTION_ADVANCED = "advanced"
SECTION_FORECAST = "forecast"
SECTION_CURTAILMENT = "curtailment"
SECTION_VEHICLE = "vehicle"
SECTION_CHARGING = "charging"
SECTION_PUBLIC_CHARGING = "public_charging"
SECTION_SCHEDULE = "schedule"
SECTION_POWER = "power"

#: Field name HAEO requires on every connected element (``sections/common.py``).
CONNECTION_FIELD = "connection"
#: Tagged-value type for a connection target (``core/schema/connection_target.py``).
CONNECTION_TARGET_TYPE = "connection_target"
#: Element type used as the shared node elements connect to (``element_type.py``).
JUNCTION_TYPE = "junction"
#: Symbolic connection target: HAEO's own switchboard junction, whose title HAEO
#: takes from a translated string (F-062) and which therefore cannot be written
#: into a plan. The driver resolves it from the hub's subentries at apply time
#: (ADR-0025).
HUB_SWITCHBOARD = "hub_switchboard"


def is_switchboard(connection: str | None) -> bool:
    """True when ``connection`` is the symbolic switchboard target."""
    return connection == HUB_SWITCHBOARD


@dataclass(frozen=True)
class FieldSpec:
    """One HAEO element field and where its value comes from."""

    section: str
    field: str
    kind: ValueKind
    #: Profile key that fills it. ``None`` means we always write ``default``.
    profile_key: str | None = None
    required: bool = False
    default: Any = None
    unit: str = ""
    source: str = ""


def _f(  # noqa: PLR0913 - a field table row is inherently wide
    section: str,
    field: str,
    kind: ValueKind,
    profile_key: str | None = None,
    *,
    required: bool = False,
    default: Any = None,
    unit: str = "",
    source: str = "",
) -> FieldSpec:
    return FieldSpec(
        section=section,
        field=field,
        kind=kind,
        profile_key=profile_key,
        required=required,
        default=default,
        unit=unit,
        source=source,
    )


GRID_FIELDS = (
    _f(SECTION_PRICING, "price_source_target", "entity", "import_price_entity", required=True, unit="currency/kWh", source=SOURCE_ELEMENTS + "grid.py"),
    _f(SECTION_PRICING, "price_target_source", "entity", "export_price_entity", required=True, unit="currency/kWh", source=SOURCE_ELEMENTS + "grid.py"),
    _f(SECTION_POWER_LIMITS, "max_power_source_target", "constant", "import_limit_kw", unit="kW", source=SOURCE_ELEMENTS + "grid.py"),
    _f(SECTION_POWER_LIMITS, "max_power_target_source", "constant", "export_limit_kw", unit="kW", source=SOURCE_ELEMENTS + "grid.py"),
)

BATTERY_FIELDS = (
    _f(SECTION_STORAGE, "capacity", "constant", "capacity_kwh", required=True, unit="kWh", source=SOURCE_ELEMENTS + "battery.py"),
    _f(SECTION_STORAGE, "initial_charge_percentage", "ratio", "initial_soc_pct", unit="%", source=SOURCE_ELEMENTS + "battery.py"),
    _f(SECTION_LIMITS, "min_charge_percentage", "ratio", "min_soc_pct", unit="%", source=SOURCE_ELEMENTS + "battery.py"),
    _f(SECTION_LIMITS, "max_charge_percentage", "ratio", "max_soc_pct", unit="%", source=SOURCE_ELEMENTS + "battery.py"),
    _f(SECTION_POWER_LIMITS, "max_power_target_source", "constant", "max_charge_kw", unit="kW", source=SOURCE_ELEMENTS + "battery.py"),
    _f(SECTION_POWER_LIMITS, "max_power_source_target", "constant", "max_discharge_kw", unit="kW", source=SOURCE_ELEMENTS + "battery.py"),
    # Efficiency is a 0..1 ratio: the segment computes ``output = input * efficiency``
    # (F-058) and OutputType.EFFICIENCY is documented as "ratio (0-1, displayed as %)"
    # (F-057). HAEO's own field default is 95.0 (F-059), which under that maths would
    # create energy, so this field is ALWAYS written — never omitted (OQ-021, HAEO bug).
    _f(SECTION_EFFICIENCY, "efficiency_source_target", "ratio", "charge_efficiency_pct", required=True, default=95.0, unit="%", source=SOURCE_SECTIONS + "efficiency.py"),
    _f(SECTION_EFFICIENCY, "efficiency_target_source", "ratio", "discharge_efficiency_pct", required=True, default=95.0, unit="%", source=SOURCE_SECTIONS + "efficiency.py"),
    _f(SECTION_PRICING, "salvage_value", "constant", "salvage_value", unit="currency/kWh", source=SOURCE_ELEMENTS + "battery.py"),
    # Required by BatteryAdvancedConfig with no default in the schema; HAEO's own
    # form default is 100.0 (a penalty rate, not a price). We write it explicitly.
    _f(SECTION_ADVANCED, "charge_limit_cost", "constant", "charge_limit_cost", required=True, default=100.0, unit="currency/kWh", source=SOURCE_ELEMENTS + "battery.py"),
)

LOAD_FIELDS = (
    _f(SECTION_FORECAST, "forecast", "entity", "forecast_entity", required=True, unit="kW", source=SOURCE_ELEMENTS + "load.py"),
    _f(SECTION_CURTAILMENT, "curtailment", "constant", "curtailment_allowed", default=False, unit="bool", source=SOURCE_ELEMENTS + "load.py"),
)

SOLAR_FIELDS = (
    _f(SECTION_FORECAST, "forecast", "entity", "forecast_entity", required=True, unit="kW", source=SOURCE_ELEMENTS + "solar.py"),
    _f(SECTION_CURTAILMENT, "curtailment", "constant", "curtailment_allowed", default=True, unit="bool", source=SOURCE_ELEMENTS + "solar.py"),
)

EV_FIELDS = (
    _f(SECTION_VEHICLE, "capacity", "constant", "capacity_kwh", required=True, unit="kWh", source=SOURCE_ELEMENTS + "ev.py"),
    _f(SECTION_VEHICLE, "energy_per_distance", "constant", "energy_per_distance", required=True, unit="kWh/km", source=SOURCE_ELEMENTS + "ev.py"),
    _f(SECTION_VEHICLE, "current_soc", "entity", "current_soc_entity", required=True, unit="%", source=SOURCE_ELEMENTS + "ev.py"),
    _f(SECTION_VEHICLE, "min_charge_percentage", "constant", "min_soc_pct", unit="%", source=SOURCE_ELEMENTS + "ev.py"),
    _f(SECTION_CHARGING, "max_charge_rate", "constant", "max_charge_kw", required=True, unit="kW", source=SOURCE_ELEMENTS + "ev.py"),
    _f(SECTION_CHARGING, "max_discharge_rate", "constant", "max_discharge_kw", unit="kW", source=SOURCE_ELEMENTS + "ev.py"),
    _f(SECTION_CHARGING, "connected", "entity", "connected_entity", required=True, unit="bool", source=SOURCE_ELEMENTS + "ev.py"),
    _f(SECTION_PUBLIC_CHARGING, "public_charging_price", "constant", "public_charging_price", default=0.6, unit="currency/kWh", source=SOURCE_ELEMENTS + "ev.py"),
    # Efficiency is a 0..1 ratio: the segment computes ``output = input * efficiency``
    # (F-058) and OutputType.EFFICIENCY is documented as "ratio (0-1, displayed as %)"
    # (F-057). HAEO's own field default is 95.0 (F-059), which under that maths would
    # create energy, so this field is ALWAYS written — never omitted (OQ-021, HAEO bug).
    _f(SECTION_EFFICIENCY, "efficiency_source_target", "ratio", "charge_efficiency_pct", required=True, default=95.0, unit="%", source=SOURCE_SECTIONS + "efficiency.py"),
    _f(SECTION_EFFICIENCY, "efficiency_target_source", "ratio", "discharge_efficiency_pct", required=True, default=95.0, unit="%", source=SOURCE_SECTIONS + "efficiency.py"),
    _f(SECTION_ADVANCED, "charge_limit_cost", "constant", "charge_limit_cost", required=True, default=100.0, unit="currency/kWh", source=SOURCE_ELEMENTS + "ev.py"),
)

#: HAEO's ``ev`` models a vehicle, so no profile kind maps to it (ADR-0016).
#: Kept as a recorded table for the day a gateway profile carries vehicle state.
EV_VEHICLE_FIELDS = EV_FIELDS

#: A controllable charger is a deferrable load: HAEO requires a run-window
#: calendar and pays a deficit/overage price for energy delivered outside the
#: window's requirement (``core/schema/elements/deferrable_load.py``).
DEFERRABLE_LOAD_FIELDS = (
    _f(SECTION_SCHEDULE, "window_calendar", "entity", "window_calendar", required=True, unit="calendar", source=SOURCE_ELEMENTS + "deferrable_load.py"),
    _f(SECTION_POWER, "max_power", "constant", "max_charge_kw", unit="kW", source=SOURCE_ELEMENTS + "deferrable_load.py"),
    _f(SECTION_PRICING, "deficit_price", "constant", "deficit_price", default=10.0, unit="currency/kWh", source=SOURCE_ELEMENTS + "deferrable_load.py"),
    _f(SECTION_PRICING, "overage_price", "constant", "overage_price", default=0.0, unit="currency/kWh", source=SOURCE_ELEMENTS + "deferrable_load.py"),
)

#: Per HAEO element type: the fields we fill (source-verified names only).
#: Keyed by HAEO type, not profile kind: the sections belong to the element, and
#: a kind that maps to ``junction`` (or to nothing) carries no fields at all.
ELEMENT_FIELDS: dict[str, tuple[FieldSpec, ...]] = {
    "grid": GRID_FIELDS,
    "battery": BATTERY_FIELDS,
    "load": LOAD_FIELDS,
    "solar": SOLAR_FIELDS,
    "deferrable_load": DEFERRABLE_LOAD_FIELDS,
}

#: Profile keys that describe the site, not the element. They must never reach
#: HAEO: its flows reject unknown fields, and vendor names are not model inputs.
PROFILE_ONLY_KEYS = frozenset(
    {
        "id",
        "kind",
        "name",
        "notes",
        "vendor",
        "model",
        "topology",
        "peak_kw",
        "degradation_cost",
        "forecast_entity",  # consumed by LOAD/SOLAR fields, not free-form
        "haeo_name",
    }
)

#: OQ-021 resolved from source: efficiency is a 0..1 ratio (the segment computes
#: ``output = input * efficiency``, F-058) and HAEO's own default of 95.0 is wrong
#: under that maths. The field is therefore always written, and a live run confirms
#: only that HAEO stores what we send.
ELEMENT_FIELDS_LIVE_VERIFIED = False
ELEMENT_FIELDS_SOURCE = (
    f"SOURCE_VERIFIED field table from haeo@{contracts.HAEO_SURFACE_VERSION} "
    "core/schema/elements/*.py; LIVE_UNVERIFIED until tests/contract/haeo passes (OQ-017)"
)


def tag_value(kind: ValueKind, value: Any) -> dict[str, Any]:
    """Wrap a raw value the way HAEO stores it."""
    if kind == "entity":
        if isinstance(value, str):
            value = [value]
        return {"type": "entity", "value": list(value)}
    if kind == "none":
        return {"type": "none", "value": None}
    if kind == "ratio":
        # HAEO's `*_percentage` fields are 0..1 ratios: the battery adapter
        # multiplies them by capacity directly. A 20 in a profile means 20 %, so
        # it must reach HAEO as 0.2 (F-053) — sending 20 would mean 2000 %.
        return {"type": "constant", "value": float(value) / 100.0}
    return {"type": "constant", "value": value}


def connection_target(name: str) -> dict[str, Any]:
    """Tagged connection target pointing an element at a junction by name."""
    return {"type": CONNECTION_TARGET_TYPE, "value": name}


@dataclass(frozen=True)
class CompiledFields:
    """Sections for one element, plus what we could not fill."""

    sections: dict[str, dict[str, Any]] = field(default_factory=dict)
    missing: tuple[tuple[str, str], ...] = ()
    ignored: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"sections": self.sections, "missing": [list(m) for m in self.missing], "ignored": list(self.ignored)}


def compile_element_fields(element: dict[str, Any], haeo_type: str | None) -> CompiledFields:
    """Build HAEO sections for one profile element of HAEO type ``haeo_type``.

    Returns the sections, the ``(section, field)`` pairs that are required but
    have no source in the profile, and the profile keys we dropped (reported,
    never silently forwarded).
    """
    specs = ELEMENT_FIELDS.get(haeo_type or "", ())
    sections: dict[str, dict[str, Any]] = {}
    missing: list[tuple[str, str]] = []
    for spec in specs:
        value = None
        if spec.profile_key is not None and spec.profile_key in element:
            value = element[spec.profile_key]
        elif spec.default is not None:
            value = spec.default
        if value is None:
            if spec.required:
                missing.append((spec.section, spec.field))
            continue
        sections.setdefault(spec.section, {})[spec.field] = tag_value(spec.kind, value)
    consumed = {spec.profile_key for spec in specs if spec.profile_key}
    ignored = tuple(sorted(key for key in element if key not in consumed and key not in PROFILE_ONLY_KEYS))
    return CompiledFields(sections=sections, missing=tuple(missing), ignored=ignored)


def element_payload(
    name: str,
    haeo_type: str,
    sections: dict[str, dict[str, Any]],
    connection: str | None,
    flat: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Element data as HAEO's subentry flow/subentry stores it.

    ``sections`` become nested objects; ``flat`` keys are stored at the top level
    (a ``policy`` element keeps its ``rules`` list there, next to ``name``).
    """
    payload: dict[str, Any] = {
        contracts.CONF_NAME: name,
        contracts.CONF_ELEMENT_TYPE: haeo_type,
    }
    if connection is not None:
        payload[CONNECTION_FIELD] = connection_target(connection)
    for section, values in sections.items():
        payload[section] = dict(values)
    for key, value in (flat or {}).items():
        payload[key] = value
    return payload
