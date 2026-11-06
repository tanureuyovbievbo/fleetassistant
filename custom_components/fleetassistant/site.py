"""Site runtime container: profile, compiled plan, audit log, issues."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .audit import AuditLog
from .haeo_bridge.plan import NetworkPlan
from .profile.schema import Issue


@dataclass
class SiteRuntime:
    """In-memory state for one config entry (one site, one tenant, one HA)."""

    entry_id: str
    profile: dict[str, Any]
    plan: NetworkPlan
    audit: AuditLog
    issues: list[Issue] = field(default_factory=list)
    last_apply_status: str = "not_applied"
    last_apply_report: Any = None
    #: Merged tariffs keyed by price input name (``price_import``/``price_export``),
    #: published as forecast sensors for HAEO to read (ADR-0019).
    tariffs: dict[str, Any] = field(default_factory=dict)
    #: Every entity the profile depends on (sensors, calendars), checked at setup.
    references: tuple[Any, ...] = ()
    #: One adapter per local-backed control element, keyed by element id.
    adapters: dict[str, Any] = field(default_factory=dict)
    #: Repairs raised for entity references, so they can be cleared on reload.
    reference_repairs: list[str] = field(default_factory=list)

    @property
    def site_id(self) -> str:
        return str(self.profile["site"]["id"])

    @property
    def blocking(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.is_error]

    def as_diagnostics(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "site_id": self.site_id,
            "deployment_profile": self.profile["deployment"]["profile"],
            "schema_version": self.profile.get("schema_version"),
            "last_apply_status": self.last_apply_status,
            "last_apply_operations": [] if self.last_apply_report is None else [
                {"type": op.type, "name": op.name} for op in self.last_apply_report.operations
            ],
            "last_apply_issues": [] if self.last_apply_report is None else [
                {"code": i.code, "path": i.path, "message": i.message} for i in self.last_apply_report.issues
            ],
            "price_authority": {name: tariff.authority for name, tariff in self.tariffs.items()},
            "price_provenance": {name: tariff.provenance for name, tariff in self.tariffs.items()},
            "price_warnings": [w for tariff in self.tariffs.values() for w in tariff.warnings],
            "references": [
                {"entity_id": r.entity_id, "requirement": r.requirement, "path": r.path} for r in self.references
            ],
            "control_adapters": {
                element: {
                    "adapter_id": adapter.adapter_id,
                    "backing": adapter.backing,
                    "capabilities": sorted(adapter.capabilities()),
                    "last_written": dict(adapter.read_state()),
                }
                for element, adapter in self.adapters.items()
            },
            "audit_records": len(self.audit),
            "audit_chain_valid": self.audit.verify(),
            "issues": [
                {"code": i.code, "path": i.path, "message": i.message, "severity": i.severity} for i in self.issues
            ],
            "plan": self.plan.as_dict(),
        }


def default_profile(site_id: str, name: str, deployment_profile: str) -> dict[str, Any]:
    """A minimal, valid profile for a fresh config entry.

    Placeholder entity ids are intentional: the options flow and the profile
    file are where real values arrive. Setup still succeeds so the user sees a
    working entry plus a repair issue telling them what to fill in — better than
    a failed setup with no explanation.
    """
    return {
        "schema_version": 1,
        "site": {"id": site_id, "name": name, "currency": "USD"},
        "deployment": {
            "profile": deployment_profile,
            "notes": "created by the fleetassistant config flow; edit through profile or options flow",
        },
        "consent": {"granted": False, "scope": "none"},
        "systems": [
            {
                "id": "main",
                "name": name,
                "haeo": {"hub": f"{site_id}_main", "horizon": {"mode": "preset", "preset_days": 5}},
                "elements": [
                    {"id": "grid", "kind": "grid", "import_limit_kw": 0.0, "export_limit_kw": 0.0},
                    {"id": "house", "kind": "load", "forecast_entity": "sensor.replace_me_load_forecast"},
                ],
                "connections": [{"from": "grid", "to": "house"}],
            }
        ],
        "controls": [],
        "pricing": {"provider": {"type": "flat", "currency_per_kwh": 0.0}},
        "rule_packs": [],
    }
