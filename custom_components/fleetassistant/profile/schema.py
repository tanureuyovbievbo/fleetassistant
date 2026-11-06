"""Site profile schema (v1) — pure validation, no Home Assistant imports.

The profile is the source of truth for a site (C-10) and is deliberately
HAEO-agnostic: it names *what the site has and what may be controlled*, never
HAEO element types or flow fields. The bridge (haeo_bridge/) maps it.

Everything here is data validation only; no I/O.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

SCHEMA_VERSION = 1

Severity = Literal["error", "warning"]

DEPLOYMENT_PROFILES = ("cloud_primary", "gateway_primary")
AUTHORITY_BY_PROFILE = {"cloud_primary": "coarse", "gateway_primary": "full"}

ELEMENT_KINDS = (
    "grid",
    "solar",
    "battery",
    "load",
    "meter",
    "ev_charger",
    "thermostat",
    "relay",
)

#: Which control capabilities a given element kind may expose (C-09).
ALLOWED_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "grid": ("set_export_limit",),
    "battery": ("set_battery_target", "set_export_limit"),
    "ev_charger": ("set_charger_amps", "set_charging_schedule"),
    "thermostat": ("set_thermostat_setpoint",),
    "relay": ("shed_circuit",),
}

CAPABILITY_UNITS = {
    "set_export_limit": "kW",
    "set_battery_target": "%",
    "set_charger_amps": "A",
    "set_thermostat_setpoint": "F",
    "set_charging_schedule": "json",
    "shed_circuit": "bool",
}

BACKINGS = ("api", "local")
AUTHORITIES = ("coarse", "full")

SLUG_RE = re.compile(r"^[a-z][a-z0-9_]{1,62}$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")

_TOP_LEVEL_KEYS = {
    "schema_version",
    "site",
    "deployment",
    "consent",
    "systems",
    "controls",
    "pricing",
    "rule_packs",
}


@dataclass(frozen=True)
class Issue:
    """One validation finding. ``path`` is dotted and index-aware."""

    code: str
    path: str
    message: str
    severity: Severity = "error"

    @property
    def is_error(self) -> bool:
        return self.severity == "error"

    def __str__(self) -> str:  # pragma: no cover - convenience
        return f"[{self.code}] {self.path}: {self.message}"


class _Collector:
    def __init__(self) -> None:
        self.issues: list[Issue] = []

    def error(self, code: str, path: str, message: str) -> None:
        self.issues.append(Issue(code, path, message, "error"))

    def warn(self, code: str, path: str, message: str) -> None:
        self.issues.append(Issue(code, path, message, "warning"))

    # -- primitives ---------------------------------------------------------
    def mapping(self, path: str, value: Any, required: Iterable[str], optional: Iterable[str] = ()) -> bool:
        if not isinstance(value, dict):
            self.error("type", path, "must be a mapping")
            return False
        for key in required:
            if key not in value:
                self.error("required", f"{path}.{key}", "is required")
        allowed = set(required) | set(optional)
        for key in value:
            if key not in allowed:
                self.error("unknown_key", f"{path}.{key}", "is not part of schema v1")
        return True

    def number(self, path: str, value: Any, *, minimum: float | None = None, maximum: float | None = None) -> float | None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            self.error("type", path, "must be a number")
            return None
        if not math.isfinite(value):
            self.error("range", path, "must be finite")
            return None
        if minimum is not None and value < minimum:
            self.error("range", path, f"must be >= {minimum}")
        if maximum is not None and value > maximum:
            self.error("range", path, f"must be <= {maximum}")
        return float(value)

    def slug(self, path: str, value: Any) -> str | None:
        if not isinstance(value, str) or not SLUG_RE.match(value):
            self.error("slug", path, "must match ^[a-z][a-z0-9_]{1,62}$")
            return None
        return value

    def text(self, path: str, value: Any, *, max_len: int = 200) -> str | None:
        if not isinstance(value, str) or not value.strip():
            self.error("type", path, "must be a non-empty string")
            return None
        if len(value) > max_len:
            self.error("range", path, f"must be at most {max_len} characters")
            return None
        return value

    def choice(self, path: str, value: Any, options: Iterable[str]) -> str | None:
        options = tuple(options)
        if value not in options:
            self.error("choice", path, f"must be one of {', '.join(options)}")
            return None
        return str(value)

    def boolean(self, path: str, value: Any) -> bool | None:
        if not isinstance(value, bool):
            self.error("type", path, "must be true or false")
            return None
        return value


def validate_profile(profile: Any) -> list[Issue]:
    """Validate a site profile document. Returns issues (empty == valid)."""
    c = _Collector()
    if not isinstance(profile, dict):
        c.error("type", "$", "profile must be a mapping")
        return c.issues

    for key in profile:
        if key not in _TOP_LEVEL_KEYS:
            c.error("unknown_key", f"$.{key}", "is not part of schema v1")
        if isinstance(key, str) and key.lower().startswith("haeo"):
            c.error(
                "haeo_leak",
                f"$.{key}",
                "the profile is HAEO-agnostic; HAEO names belong in the bridge (C-10)",
            )

    version = profile.get("schema_version")
    if version != SCHEMA_VERSION:
        c.error("schema_version", "$.schema_version", f"must be {SCHEMA_VERSION}")

    _validate_site(c, profile.get("site"))
    deployment = _validate_deployment(c, profile.get("deployment"))
    consent = _validate_consent(c, profile.get("consent"))

    systems = profile.get("systems")
    element_kinds: dict[str, str] = {}
    if not isinstance(systems, list) or not systems:
        c.error("required", "$.systems", "must be a non-empty list")
        systems = []
    hub_names: set[str] = set()
    for index, system in enumerate(systems):
        kinds = _validate_system(c, f"$.systems[{index}]", system, hub_names)
        element_kinds.update(kinds)

    _validate_controls(c, profile.get("controls", []), element_kinds, deployment, consent)
    _validate_pricing(c, profile.get("pricing"))
    _validate_rule_packs(c, profile.get("rule_packs", []))
    return c.issues


def _validate_site(c: _Collector, site: Any) -> dict[str, Any] | None:
    if not c.mapping("$.site", site, ("id", "name"), ("timezone", "currency", "notes")):
        return None
    c.slug("$.site.id", site.get("id"))
    c.text("$.site.name", site.get("name"), max_len=80)
    if "currency" in site and (
        not isinstance(site["currency"], str) or not CURRENCY_RE.match(site["currency"])
    ):
        c.error("currency", "$.site.currency", "must be an ISO-4217 code such as USD")
    if "timezone" in site:
        c.text("$.site.timezone", site["timezone"], max_len=64)
    return site


def _validate_deployment(c: _Collector, deployment: Any) -> str | None:
    if not c.mapping(
        "$.deployment", deployment, ("profile",), ("fail_safe", "notes", "relax_impossible_plans")
    ):
        return None
    prof = c.choice("$.deployment.profile", deployment.get("profile"), DEPLOYMENT_PROFILES)
    if "relax_impossible_plans" in deployment:
        c.boolean("$.deployment.relax_impossible_plans", deployment["relax_impossible_plans"])
    if "fail_safe" in deployment:
        fs = deployment["fail_safe"]
        if c.mapping("$.deployment.fail_safe", fs, (), ("contactor", "local_automation", "max_hold_minutes")):
            if "contactor" in fs:
                c.boolean("$.deployment.fail_safe.contactor", fs["contactor"])
            if "local_automation" in fs:
                c.boolean("$.deployment.fail_safe.local_automation", fs["local_automation"])
            if "max_hold_minutes" in fs:
                c.number("$.deployment.fail_safe.max_hold_minutes", fs["max_hold_minutes"], minimum=1, maximum=1440)
    if prof == "gateway_primary":
        fs = deployment.get("fail_safe") or {}
        if not fs.get("contactor") and not fs.get("local_automation"):
            c.warn(
                "fail_safe_missing",
                "$.deployment.fail_safe",
                "gateway sites should declare a contactor or local automation fail-safe (C-15)",
            )
    return prof


def _validate_consent(c: _Collector, consent: Any) -> dict[str, Any] | None:
    if consent is None:
        return None
    if not c.mapping("$.consent", consent, ("granted",), ("granted_at", "scope", "subject")):
        return None
    c.boolean("$.consent.granted", consent.get("granted"))
    return consent


def _validate_system(c: _Collector, path: str, system: Any, hub_names: set[str]) -> dict[str, str]:
    if not c.mapping(path, system, ("id", "name", "haeo", "elements"), ("connections",)):
        return {}
    c.slug(f"{path}.id", system.get("id"))
    c.text(f"{path}.name", system.get("name"), max_len=80)

    haeo = system.get("haeo")
    if c.mapping(f"{path}.haeo", haeo, ("hub", "horizon"), ()):
        hub = c.text(f"{path}.haeo.hub", haeo.get("hub"), max_len=60)
        if hub is not None:
            if hub in hub_names:
                c.error("duplicate_hub", f"{path}.haeo.hub", "hub names must be unique per site")
            hub_names.add(hub)
        horizon = haeo.get("horizon")
        if c.mapping(f"{path}.haeo.horizon", horizon, ("mode",), ("preset_days", "forecast_entity")):
            mode = c.choice(f"{path}.haeo.horizon.mode", horizon.get("mode"), ("preset", "forecast_sensor"))
            if mode == "preset":
                days = c.number(f"{path}.haeo.horizon.preset_days", horizon.get("preset_days"), minimum=1, maximum=14)
                if days is not None and horizon.get("preset_days") not in (2, 3, 5, 7):
                    c.warn(
                        "preset_not_in_haeo_set",
                        f"{path}.haeo.horizon.preset_days",
                        "HAEO presets are reported as 2/3/5/7 days; values outside that set are UNVERIFIED (OQ-007)",
                    )
            elif mode == "forecast_sensor":
                c.text(f"{path}.haeo.horizon.forecast_entity", horizon.get("forecast_entity"), max_len=120)

    elements = system.get("elements")
    ids: set[str] = set()
    kinds: dict[str, str] = {}
    if not isinstance(elements, list) or not elements:
        c.error("required", f"{path}.elements", "must be a non-empty list")
        elements = []
    for index, element in enumerate(elements):
        element_path = f"{path}.elements[{index}]"
        element_id, kind = _validate_element(c, element_path, element)
        if element_id is not None:
            if element_id in ids:
                c.error("duplicate_id", f"{element_path}.id", f"duplicate element id {element_id!r}")
            ids.add(element_id)
            if kind is not None:
                kinds[element_id] = kind

    connections = system.get("connections", [])
    if not isinstance(connections, list):
        c.error("type", f"{path}.connections", "must be a list")
        connections = []
    for index, connection in enumerate(connections):
        cpath = f"{path}.connections[{index}]"
        if not c.mapping(cpath, connection, ("from", "to"), ("kind",)):
            continue
        for side in ("from", "to"):
            ref = connection.get(side)
            if not isinstance(ref, str) or ref not in ids:
                c.error("dangling_reference", f"{cpath}.{side}", f"unknown element {ref!r}")

    return kinds


def _validate_element(c: _Collector, path: str, element: Any) -> tuple[str | None, str | None]:
    if not isinstance(element, dict):
        c.error("type", path, "must be a mapping")
        return None, None
    kind = c.choice(f"{path}.kind", element.get("kind"), ELEMENT_KINDS)
    element_id = c.slug(f"{path}.id", element.get("id"))
    #: Keys an element may carry that HAEO stores as element fields. They are
    #: listed in ``haeo_bridge/fields.py`` as the profile side of each FieldSpec;
    #: a key HAEO has no field for stays here only if the site needs it
    #: (``degradation_cost``), and the bridge reports it instead of writing it.
    base_optional = {
        "name",
        "vendor",
        "model",
        "notes",
        "entity_id",
        "forecast_entity",
        "window_calendar",
        "initial_soc_pct",
        "max_charge_kw",
        "max_discharge_kw",
        "import_price_entity",
        "export_price_entity",
        "curtailment_allowed",
        "salvage_value",
        "charge_limit_cost",
        "charge_efficiency_pct",
        "discharge_efficiency_pct",
        "deficit_price",
        "overage_price",
        "connected_entity",
        "current_soc_entity",
    }
    required = ["id", "kind"]
    if kind == "battery":
        required += [
            "capacity_kwh",
            "max_charge_kw",
            "max_discharge_kw",
            "min_soc_pct",
            "max_soc_pct",
            "degradation_cost",
        ]
    elif kind in ("solar", "load"):
        required += ["peak_kw"] if kind == "solar" else ["forecast_entity"]
    elif kind == "grid":
        required += ["import_limit_kw", "export_limit_kw"]
    elif kind == "meter":
        required += ["topology"]
    elif kind == "ev_charger":
        # A charger is a deferrable load in HAEO: it needs the run-window
        # calendar that says when charging may happen (ADR-0016).
        required += ["max_amps", "phases", "window_calendar"]
    elif kind == "thermostat":
        required += ["min_setpoint_f", "max_setpoint_f"]
    elif kind == "relay":
        required += ["rated_kw"]

    if not c.mapping(path, element, required, base_optional):
        return element_id, kind

    if kind == "battery":
        cap = c.number(f"{path}.capacity_kwh", element.get("capacity_kwh"), minimum=0.1)
        c.number(f"{path}.max_charge_kw", element.get("max_charge_kw"), minimum=0.0)
        c.number(f"{path}.max_discharge_kw", element.get("max_discharge_kw"), minimum=0.0)
        lo = c.number(f"{path}.min_soc_pct", element.get("min_soc_pct"), minimum=0, maximum=100)
        hi = c.number(f"{path}.max_soc_pct", element.get("max_soc_pct"), minimum=0, maximum=100)
        if lo is not None and hi is not None and lo >= hi:
            c.error("range", f"{path}.min_soc_pct", "must be lower than max_soc_pct")
        _validate_degradation_cost(c, f"{path}.degradation_cost", element.get("degradation_cost"))
        # Round-trip efficiency as a percentage (0 is a dead battery, 100 is lossless).
        # HAEO stores it as a 0..1 ratio and multiplies (F-058), so the bridge divides.
        for key, label in (
            ("charge_efficiency_pct", "charge efficiency"),
            ("discharge_efficiency_pct", "discharge efficiency"),
        ):
            if key in element:
                value = c.number(f"{path}.{key}", element[key], minimum=1, maximum=100)
                if value is not None and value < 50:
                    c.warn(
                        "range",
                        f"{path}.{key}",
                        f"{label} below 50% is unusual: check whether the number is a percentage",
                    )
        if cap is None:
            pass
    elif kind == "solar":
        c.number(f"{path}.peak_kw", element.get("peak_kw"), minimum=0.1)
        if "forecast_entity" in element:
            c.text(f"{path}.forecast_entity", element["forecast_entity"], max_len=120)
    elif kind == "load":
        c.text(f"{path}.forecast_entity", element.get("forecast_entity"), max_len=120)
    elif kind == "grid":
        c.number(f"{path}.import_limit_kw", element.get("import_limit_kw"), minimum=0.0)
        c.number(f"{path}.export_limit_kw", element.get("export_limit_kw"), minimum=0.0)
    elif kind == "meter":
        c.choice(f"{path}.topology", element.get("topology"), ("whole_home", "sub_panel"))
    elif kind == "ev_charger":
        c.number(f"{path}.max_amps", element.get("max_amps"), minimum=1, maximum=80)
        phases = element.get("phases")
        if phases not in (1, 3):
            c.error("choice", f"{path}.phases", "must be 1 or 3")
    elif kind == "thermostat":
        lo = c.number(f"{path}.min_setpoint_f", element.get("min_setpoint_f"), minimum=40, maximum=90)
        hi = c.number(f"{path}.max_setpoint_f", element.get("max_setpoint_f"), minimum=40, maximum=95)
        if lo is not None and hi is not None and lo >= hi:
            c.error("range", f"{path}.min_setpoint_f", "must be lower than max_setpoint_f")
    elif kind == "relay":
        c.number(f"{path}.rated_kw", element.get("rated_kw"), minimum=0.0)

    for key in element:
        if isinstance(key, str) and key.lower().startswith("haeo"):
            c.error("haeo_leak", f"{path}.{key}", "HAEO names belong in the bridge, not the profile (C-10)")
    return element_id, kind


def _validate_degradation_cost(c: _Collector, path: str, value: Any) -> None:
    """C-14: a battery always carries a priced degradation term with provenance."""
    if not c.mapping(path, value, ("currency_per_kwh", "source"), ("notes",)):
        return
    c.number(f"{path}.currency_per_kwh", value.get("currency_per_kwh"), minimum=0.0001)
    c.text(f"{path}.source", value.get("source"), max_len=300)


def _validate_controls(
    c: _Collector,
    controls: Any,
    element_kinds: dict[str, str],
    deployment: str | None,
    consent: dict[str, Any] | None,
) -> None:
    if not isinstance(controls, list):
        c.error("type", "$.controls", "must be a list")
        return
    seen: set[str] = set()
    all_ids = set(element_kinds)
    for index, control in enumerate(controls):
        path = f"$.controls[{index}]"
        required = (
            "id",
            "element",
            "capability",
            "unit",
            "min",
            "max",
            "rate_limit_per_minute",
            "hysteresis",
            "consent_required",
            "backing",
            "fail_safe_value",
        )
        if not c.mapping(path, control, required, ("notes", "authority")):
            continue
        cid = c.slug(f"{path}.id", control.get("id"))
        if cid is not None:
            if cid in seen:
                c.error("duplicate_id", f"{path}.id", f"duplicate control id {cid!r}")
            seen.add(cid)
        element = control.get("element")
        if not isinstance(element, str) or element not in all_ids:
            c.error("dangling_reference", f"{path}.element", f"unknown element {element!r}")
        capability = c.choice(
            f"{path}.capability",
            control.get("capability"),
            sorted({cap for caps in ALLOWED_CAPABILITIES.values() for cap in caps}),
        )
        if isinstance(element, str) and capability in ("", None):
            pass
        elif isinstance(element, str) and capability:
            kind = element_kinds.get(element)
            if kind is not None and capability not in ALLOWED_CAPABILITIES.get(kind, ()):
                c.error("capability_not_allowed", f"{path}.capability", f"element kind {kind!r} cannot expose {capability}")
        unit = control.get("unit")
        if capability and unit is not None and CAPABILITY_UNITS.get(capability) != unit:
            c.error("unit", f"{path}.unit", f"{capability} uses unit {CAPABILITY_UNITS.get(capability)!r}")
        lo = c.number(f"{path}.min", control.get("min"))
        hi = c.number(f"{path}.max", control.get("max"))
        if lo is not None and hi is not None and lo >= hi:
            c.error("range", f"{path}.min", "must be lower than max")
        fs = c.number(f"{path}.fail_safe_value", control.get("fail_safe_value"))
        if fs is not None and lo is not None and hi is not None and not (lo <= fs <= hi):
            c.error("range", f"{path}.fail_safe_value", "must lie inside [min, max]")
        c.number(f"{path}.rate_limit_per_minute", control.get("rate_limit_per_minute"), minimum=1, maximum=600)
        c.number(f"{path}.hysteresis", control.get("hysteresis"), minimum=0)
        c.boolean(f"{path}.consent_required", control.get("consent_required"))
        backing = c.choice(f"{path}.backing", control.get("backing"), BACKINGS)
        authority = control.get("authority")
        if authority is None and deployment is not None:
            authority = AUTHORITY_BY_PROFILE[deployment]
        if authority is not None:
            authority = c.choice(f"{path}.authority", authority, AUTHORITIES)
        if deployment == "cloud_primary" and backing == "local":
            c.error("authority_mismatch", f"{path}.backing", "cloud-primary sites cannot use local-backed control (C-12)")
        if deployment == "cloud_primary" and authority == "full":
            c.error("authority_mismatch", f"{path}.authority", "cloud-primary sites are coarse authority only (C-12)")
        if deployment == "gateway_primary" and authority == "coarse":
            c.warn("authority_degraded", f"{path}.authority", "gateway sites normally have full authority (C-12)")
        if control.get("consent_required") is True and consent is not None and consent.get("granted") is not True:
            c.warn("consent_pending", f"{path}.consent_required", "consent not granted; control writes will be blocked (C-18)")


def _validate_pricing(c: _Collector, pricing: Any) -> None:
    if pricing is None:
        return
    if not c.mapping("$.pricing", pricing, ("provider",), ("notes",)):
        return
    provider = pricing.get("provider")
    if not c.mapping("$.pricing.provider", provider, ("type",), ("currency_per_kwh", "blocks", "fallback", "series")):
        return
    ptype = c.choice("$.pricing.provider.type", provider.get("type"), ("flat", "tou", "dynamic"))
    if ptype == "flat":
        c.number("$.pricing.provider.currency_per_kwh", provider.get("currency_per_kwh"), minimum=-1.0, maximum=10.0)
    elif ptype == "tou":
        blocks = provider.get("blocks")
        if not isinstance(blocks, list) or not blocks:
            c.error("required", "$.pricing.provider.blocks", "tou providers need at least one block")
        else:
            for index, block in enumerate(blocks):
                bpath = f"$.pricing.provider.blocks[{index}]"
                if not c.mapping(bpath, block, ("start", "end", "price"), ("days", "label")):
                    continue
                c.text(f"{bpath}.start", block.get("start"), max_len=5)
                c.text(f"{bpath}.end", block.get("end"), max_len=5)
                c.number(f"{bpath}.price", block.get("price"), minimum=-1.0, maximum=10.0)
    elif ptype == "dynamic":
        c.text("$.pricing.provider.series", provider.get("series"), max_len=120)


def _validate_rule_packs(c: _Collector, packs: Any) -> None:
    if not isinstance(packs, list):
        c.error("type", "$.rule_packs", "must be a list (empty is valid: v1 ships zero packs)")
        return
    for index, pack in enumerate(packs):
        path = f"$.rule_packs[{index}]"
        if not c.mapping(path, pack, ("id",), ("version", "source")):
            continue
        c.slug(f"{path}.id", pack.get("id"))


def is_valid(profile: Any) -> bool:
    return not any(issue.is_error for issue in validate_profile(profile))
