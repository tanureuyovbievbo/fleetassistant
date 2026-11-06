"""Home Assistant runtime wiring for one site.

Kept separate from ``__init__.py`` so the package imports cleanly without Home
Assistant installed (tests) and so this file is the only place that raises
repair issues.
"""

from __future__ import annotations

import json
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .audit import AuditLog
from .const import DOMAIN, NAME
from .haeo_bridge.plan import compile_plan
from .haeo_bridge.prevalidate import prevalidate
from .profile.schema import Issue, validate_profile
from .site import SiteRuntime


def _merge_options(profile: dict[str, Any], options: dict[str, Any]) -> tuple[dict[str, Any], list[Issue]]:
    """Apply options-flow overrides to the stored profile."""
    merged = json.loads(json.dumps(profile))  # deep copy; profile is JSON-only
    issues: list[Issue] = []

    raw = options.get("profile_json")
    if isinstance(raw, str) and raw.strip():
        try:
            merged = json.loads(raw)
        except json.JSONDecodeError as exc:
            issues.append(Issue("invalid_json", "options.profile_json", f"profile JSON is invalid: {exc.msg}"))

    preset_days = options.get("preset_days")
    if isinstance(preset_days, int) and not isinstance(preset_days, bool):
        for system in merged.get("systems", []):
            horizon = system.get("haeo", {}).get("horizon")
            if isinstance(horizon, dict) and horizon.get("mode") == "preset":
                horizon["preset_days"] = preset_days

    relax = options.get("relax_impossible_plans")
    if isinstance(relax, bool):
        merged.setdefault("deployment", {})["relax_impossible_plans"] = relax

    return merged, issues


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    profile, option_issues = _merge_options(dict(entry.data.get("profile", {})), dict(entry.options))
    issues: list[Issue] = list(option_issues)
    issues.extend(validate_profile(profile))

    audit_path = hass.config.path("fleetassistant", f"audit_{entry.entry_id}.jsonl")
    audit = AuditLog(audit_path)

    if any(issue.is_error for issue in issues):
        _raise_issues(hass, entry, [i for i in issues if i.is_error][:10], prefix="profile")
        return False

    plan = compile_plan(profile)
    plan_issues = prevalidate(plan)
    issues.extend(plan_issues)
    if any(issue.is_error for issue in plan_issues):
        _raise_issues(hass, entry, [i for i in plan_issues if i.is_error][:10], prefix="plan")

    runtime = SiteRuntime(
        entry_id=entry.entry_id,
        profile=profile,
        plan=plan,
        audit=audit,
        issues=issues,
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime

    # A successful setup can still carry blocking plan issues (for example an
    # unverified HAEO type map): the site exists, but nothing is applied.
    if any(issue.is_error for issue in plan_issues):
        runtime.last_apply_status = "blocked"
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True


def _raise_issues(hass: HomeAssistant, entry: ConfigEntry, issues: list[Issue], *, prefix: str) -> None:
    for index, issue in enumerate(issues):
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"{entry.entry_id}_{prefix}_{index}",
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key="invalid_profile",
            translation_placeholders={
                "entry": NAME,
                "path": issue.path,
                "message": issue.message,
                "code": issue.code,
            },
        )
