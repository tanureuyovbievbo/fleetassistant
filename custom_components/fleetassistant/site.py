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
