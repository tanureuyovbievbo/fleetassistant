"""Device packs: brand data that binds a capability to entities (ADR-0022).

A device pack never contains code. It declares, per capability, which entity an
existing Home Assistant integration exposes and what the safety envelope is. The
integration that owns the device stays the transport; the pack is the contract.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..profile.schema import CAPABILITY_UNITS, Issue

PACK_VERSION = 1
PACK_FILENAME = "pack.json"

#: Capabilities whose value a pack may bind. ``set_charging_schedule`` is absent on
#: purpose: no HA entity shape carries a schedule we could write safely.
BINDABLE_CAPABILITIES = frozenset(
    {"set_export_limit", "set_battery_target", "set_charger_amps", "set_thermostat_setpoint", "shed_circuit"}
)

#: A cloud integration can only ever be coarse (C-12): it polls a vendor API.
CLOUD_IOT_CLASSES = frozenset({"cloud_polling", "cloud_push"})

REQUIRED_BINDING_KEYS = (
    "entity_id",
    "unit",
    "min",
    "max",
    "rate_limit_per_minute",
    "hysteresis",
    "consent_required",
    "backing",
    "authority",
    "fail_safe_value",
)


@dataclass(frozen=True)
class Binding:
    """One capability bound to one entity, with its safety envelope."""

    capability: str
    entity_id: str
    unit: str
    min: float
    max: float
    rate_limit_per_minute: int
    hysteresis: float
    consent_required: bool
    backing: str
    authority: str
    fail_safe_value: float
    value_key: str = "value"
    scale: float = 1.0
    notes: str = ""

    def as_control(self, *, element_id: str, control_id: str | None = None) -> dict[str, Any]:
        """Render a control block a site profile can carry."""
        return {
            "id": control_id or f"{element_id}_{self.capability}",
            "element": element_id,
            "capability": self.capability,
            "unit": self.unit,
            "min": self.min,
            "max": self.max,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "hysteresis": self.hysteresis,
            "consent_required": self.consent_required,
            "backing": self.backing,
            "authority": self.authority,
            "fail_safe_value": self.fail_safe_value,
            "entity_id": self.entity_id,
            "scale": self.scale,
        }


@dataclass(frozen=True)
class DevicePack:
    """A brand's declared control surface."""

    brand_id: str
    display_name: str
    integration_domain: str
    iot_class: str
    bindings: dict[str, Binding]
    models: tuple[str, ...] = ()
    verified: bool = False
    sources: tuple[dict[str, str], ...] = ()
    licence_note: str = ""
    tos_note: str = ""
    notes: str = ""

    @property
    def is_cloud(self) -> bool:
        return self.iot_class in CLOUD_IOT_CLASSES

    def binding_for(self, capability: str) -> Binding | None:
        return self.bindings.get(capability)

    def capabilities(self) -> tuple[str, ...]:
        return tuple(sorted(self.bindings))


@dataclass
class PackLoadResult:
    pack: DevicePack | None
    issues: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.pack is not None and not any(issue.is_error for issue in self.issues)


def validate_pack(data: Any, *, path: str = "pack") -> list[Issue]:
    """Check a pack document. Data-only packs are cheap to audit, so be strict."""
    issues: list[Issue] = []
    if not isinstance(data, dict):
        return [Issue("type", path, "a device pack must be a mapping", "error")]

    for key in ("pack_version", "brand_id", "display_name", "integration", "bindings"):
        if key not in data:
            issues.append(Issue("required", f"{path}.{key}", f"missing required key '{key}'", "error"))
    if data.get("pack_version") not in (None, PACK_VERSION):
        issues.append(
            Issue("pack_version", f"{path}.pack_version", f"unsupported pack version {data.get('pack_version')!r}", "error")
        )
    if not isinstance(data.get("brand_id"), str) or not str(data.get("brand_id", "")).strip():
        issues.append(Issue("brand_id", f"{path}.brand_id", "brand_id must be a non-empty string", "error"))

    integration = data.get("integration") or {}
    if not isinstance(integration, dict):
        issues.append(Issue("type", f"{path}.integration", "integration must be a mapping", "error"))
        integration = {}
    domain = integration.get("domain")
    if not isinstance(domain, str) or not domain:
        issues.append(Issue("required", f"{path}.integration.domain", "the HA integration domain is required", "error"))
    iot_class = integration.get("iot_class")
    if iot_class not in CLOUD_IOT_CLASSES | {"local_polling", "local_push", "assumed_state"}:
        issues.append(
            Issue("choice", f"{path}.integration.iot_class", f"unknown iot_class {iot_class!r}", "error")
        )

    if data.get("verified") is not True:
        issues.append(
            Issue(
                "pack_unverified",
                f"{path}.verified",
                "pack is not verified against a live instance: it may bind entities that do not exist "
                "(OQ-023) and must not enter a dispatch-eligible fleet yet",
                "warning",
            )
        )
    sources = data.get("sources")
    if not sources:
        issues.append(
            Issue(
                "pack_unsourced",
                f"{path}.sources",
                "no sources: a pack's entity ids, limits and ToS note need a URL and a date (C-22)",
                "error",
            )
        )

    for index, source in enumerate(data.get("sources") or ()):
        if not isinstance(source, dict) or not source.get("url"):
            issues.append(
                Issue(
                    "source_unverified",
                    f"{path}.sources[{index}]",
                    "source has no fetched URL: the pack cannot claim this entity or limit yet (C-22)",
                    "warning",
                )
            )

    bindings = data.get("bindings")
    if not isinstance(bindings, dict) or not bindings:
        issues.append(Issue("required", f"{path}.bindings", "a pack needs at least one binding", "error"))
        return issues

    for capability, binding in bindings.items():
        bp = f"{path}.bindings.{capability}"
        if capability not in BINDABLE_CAPABILITIES:
            issues.append(Issue("capability_unknown", bp, f"unknown capability {capability!r}", "error"))
            continue
        if not isinstance(binding, dict):
            issues.append(Issue("type", bp, "a binding must be a mapping", "error"))
            continue
        for key in REQUIRED_BINDING_KEYS:
            if key not in binding:
                issues.append(Issue("required", f"{bp}.{key}", f"missing required key '{key}'", "error"))
        unit = binding.get("unit")
        if unit is not None and unit != CAPABILITY_UNITS[capability]:
            issues.append(
                Issue("unit", f"{bp}.unit", f"{capability} is {CAPABILITY_UNITS[capability]!r}, pack says {unit!r}", "error")
            )
        low, high = binding.get("min"), binding.get("max")
        if isinstance(low, int | float) and isinstance(high, int | float) and low > high:
            issues.append(Issue("range", bp, f"min {low} is above max {high}", "error"))
        fail_safe = binding.get("fail_safe_value")
        numeric = all(isinstance(value, int | float) for value in (fail_safe, low, high))
        if numeric and not low <= fail_safe <= high:  # type: ignore[operator]
            issues.append(Issue("range", f"{bp}.fail_safe_value", f"{fail_safe} is outside [{low}, {high}]", "error"))
        authority = binding.get("authority")
        backing = binding.get("backing")
        if authority not in (None, "coarse", "full"):
            issues.append(Issue("choice", f"{bp}.authority", f"unknown authority {authority!r}", "error"))
        if backing not in (None, "api", "local"):
            issues.append(Issue("choice", f"{bp}.backing", f"unknown backing {backing!r}", "error"))
        if iot_class in CLOUD_IOT_CLASSES and authority == "full":
            issues.append(
                Issue(
                    "authority_cloud",
                    f"{bp}.authority",
                    "a cloud integration cannot back a full-authority binding (C-12)",
                    "error",
                )
            )
        entity_id = binding.get("entity_id")
        if isinstance(entity_id, str) and "." not in entity_id:
            issues.append(Issue("entity_id", f"{bp}.entity_id", f"{entity_id!r} is not an entity id", "error"))
    return issues


def pack_from_dict(data: dict[str, Any]) -> DevicePack:
    """Build a pack from an already-validated document."""
    integration = data.get("integration") or {}
    bindings: dict[str, Binding] = {}
    for capability, raw in (data.get("bindings") or {}).items():
        bindings[capability] = Binding(
            capability=capability,
            entity_id=str(raw.get("entity_id", "")),
            unit=str(raw.get("unit", CAPABILITY_UNITS.get(capability, ""))),
            min=float(raw.get("min", 0.0)),
            max=float(raw.get("max", 0.0)),
            rate_limit_per_minute=int(raw.get("rate_limit_per_minute", 6)),
            hysteresis=float(raw.get("hysteresis", 0.0)),
            consent_required=bool(raw.get("consent_required", True)),
            backing=str(raw.get("backing", "local")),
            authority=str(raw.get("authority", "full")),
            fail_safe_value=float(raw.get("fail_safe_value", 0.0)),
            value_key=str(raw.get("value_key", "value")),
            scale=float(raw.get("scale", 1.0)),
            notes=str(raw.get("notes", "")),
        )
    licence = data.get("licence") or {}
    return DevicePack(
        brand_id=str(data["brand_id"]),
        display_name=str(data.get("display_name", data["brand_id"])),
        integration_domain=str(integration.get("domain", "")),
        iot_class=str(integration.get("iot_class", "")),
        bindings=bindings,
        models=tuple(str(model) for model in data.get("models") or ()),
        verified=data.get("verified") is True,
        sources=tuple(dict(source) for source in data.get("sources") or ()),
        licence_note=str(licence.get("integration_licence", "")),
        tos_note=str(licence.get("tos_note", "")),
        notes=str(data.get("notes", "")),
    )


def load_pack(path: Path | str) -> PackLoadResult:
    """Load and validate ``pack.json``; a file with errors yields ``pack=None``."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return PackLoadResult(None, [Issue("missing_file", str(path), "pack file not found", "error")])
    except json.JSONDecodeError as err:
        return PackLoadResult(None, [Issue("invalid_json", str(path), str(err), "error")])

    issues = validate_pack(data, path=str(path))
    if any(issue.is_error for issue in issues):
        return PackLoadResult(None, issues)
    return PackLoadResult(pack_from_dict(data), issues)


def load_packs(root: Path | str) -> tuple[dict[str, DevicePack], list[Issue]]:
    """Load every ``<brand>/pack.json`` under ``root``."""
    packs: dict[str, DevicePack] = {}
    issues: list[Issue] = []
    root = Path(root)
    if not root.is_dir():
        return packs, [Issue("missing_dir", str(root), "device pack directory not found", "warning")]
    for candidate in sorted(root.glob(f"*/{PACK_FILENAME}")):
        result = load_pack(candidate)
        issues.extend(result.issues)
        if result.pack is not None:
            if result.pack.brand_id in packs:
                issues.append(
                    Issue("duplicate_pack", str(candidate), f"duplicate brand_id {result.pack.brand_id!r}", "error")
                )
                continue
            packs[result.pack.brand_id] = result.pack
    return packs, issues


def controls_from_pack(pack: DevicePack, *, element_id: str, capabilities: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    """Render a pack as control blocks for one element."""
    wanted = capabilities or pack.capabilities()
    controls: list[dict[str, Any]] = []
    for capability in wanted:
        binding = pack.binding_for(capability)
        if binding is None:
            raise KeyError(f"{pack.brand_id} declares no {capability!r} binding")
        controls.append(binding.as_control(element_id=element_id))
    return controls
