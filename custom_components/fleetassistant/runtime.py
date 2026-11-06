"""Home Assistant runtime wiring for one site.

Kept separate from ``__init__.py`` so the package imports cleanly without Home
Assistant installed (tests) and so this file is the only place that raises
repair issues.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util

from .adapters.ha_caller import service_caller
from .adapters.ha_services import build_ha_adapters
from .adapters.safety import SafetyPipeline
from .audit import AuditLog
from .const import (
    CONF_APPLY_HAEO_PLAN,
    CONF_DISPATCH_ENABLED,
    DEFAULT_DISPATCH_ENABLED,
    DISPATCH_INTERVAL_SECONDS,
    DOMAIN,
    NAME,
)
from .dispatch import Dispatcher, MappedPlanSource
from .executor import Executor
from .haeo_bridge import contracts
from .haeo_bridge.apply import ApplyReport, apply_plan
from .haeo_bridge.flows import FlowHaeoDriver
from .haeo_bridge.ha_port import HomeAssistantFlowPort
from .haeo_bridge.plan import compile_plan
from .haeo_bridge.prevalidate import prevalidate
from .pricing.compiler import price_entity_id, resolve_tariffs
from .profile.schema import Issue, validate_profile
from .references import EntitySnapshot, check_references, collect_references, repair_key
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

    runtime.tariffs = resolve_tariffs(profile, dict(entry.options))
    runtime.audit.append(
        "price.resolve",
        {
            name: {
                "authority": tariff.authority,
                "provenance": tariff.provenance,
                "degraded_periods": len(tariff.stale),
                "missing_periods": len(tariff.missing),
            }
            for name, tariff in runtime.tariffs.items()
        },
    )

    # A successful setup can still carry blocking plan issues (for example an
    # unverified HAEO type map): the site exists, but nothing is applied.
    if any(issue.is_error for issue in plan_issues):
        runtime.last_apply_status = "blocked"

    if runtime.tariffs:
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    _check_references(hass, entry, runtime)
    _watch_references(hass, entry, runtime)
    _publish_price_repairs(hass, entry, runtime)
    _build_adapters(hass, entry, runtime)
    _start_dispatch(hass, entry, runtime)

    if entry.options.get(CONF_APPLY_HAEO_PLAN):
        await _apply_profile(hass, entry, runtime)
    return True


_REFERENCE_CODES = frozenset({"entity_missing", "entity_unavailable", "entity_no_forecast", "calendar_domain_mismatch"})


def _published_price_ids(runtime: SiteRuntime) -> set[str]:
    """Entity ids this integration creates itself (ADR-0019)."""
    return {price_entity_id(runtime.site_id, name) for name in runtime.tariffs}


def _check_references(hass: HomeAssistant, entry: ConfigEntry, runtime: SiteRuntime) -> None:
    """Verify every entity the profile names, and repair the ones that are absent.

    A missing sensor does not fail setup: the site is otherwise usable, and the
    repair tells the user exactly which entity to create or fix. Re-checking on
    reload clears the repairs that no longer apply.
    """
    runtime.references = collect_references(runtime.profile, published=_published_price_ids(runtime))
    issues = check_references(
        runtime.references,
        lambda entity_id: _snapshot(hass, entity_id),
        min_forecast_points=contracts.FORECAST_MIN_BOUNDARIES,
    )
    runtime.issues.extend(issues)

    wanted = {repair_key(reference) for reference in runtime.references}
    for repair in set(runtime.reference_repairs) - wanted:
        ir.async_delete_issue(hass, DOMAIN, f"{entry.entry_id}_{repair}")
    runtime.reference_repairs = []

    by_key: dict[str, list[Issue]] = {}
    for issue in issues:
        reference = next((r for r in runtime.references if r.path == issue.path), None)
        if reference is None:
            continue
        by_key.setdefault(repair_key(reference), []).append(issue)

    for key in wanted:
        found = by_key.get(key)
        if not found:
            ir.async_delete_issue(hass, DOMAIN, f"{entry.entry_id}_{key}")
            continue
        first = found[0]
        runtime.reference_repairs.append(key)
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"{entry.entry_id}_{key}",
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR if first.is_error else ir.IssueSeverity.WARNING,
            translation_key="entity_reference",
            translation_placeholders={
                "entry": NAME,
                "code": first.code,
                "path": first.path,
                "message": first.message,
            },
        )


def _watch_references(hass: HomeAssistant, entry: ConfigEntry, runtime: SiteRuntime) -> None:
    """Re-check references when one of them changes (RL-24).

    The setup check runs once. A sensor that exists at setup and goes away ten
    minutes later would otherwise stay silent until a restart.
    """
    entity_ids = sorted({reference.entity_id for reference in runtime.references})
    if not entity_ids:
        return
    wanted = set(entity_ids)

    @callback
    def _on_state_change(event: Any) -> None:
        if event.data.get("entity_id") not in wanted:
            return
        runtime.issues = [issue for issue in runtime.issues if issue.code not in _REFERENCE_CODES]
        _check_references(hass, entry, runtime)

    runtime.references_unsub = async_track_state_change_event(hass, entity_ids, _on_state_change)


def _publish_price_repairs(hass: HomeAssistant, entry: ConfigEntry, runtime: SiteRuntime) -> None:
    """Two price sources disagreeing is a decision someone must make (RL-22)."""
    divergences = [(name, tariff) for name, tariff in runtime.tariffs.items() if tariff.divergences]
    if not divergences:
        ir.async_delete_issue(hass, DOMAIN, f"{entry.entry_id}_price_divergence")
        for name in runtime.tariffs:
            ir.async_delete_issue(hass, DOMAIN, f"{entry.entry_id}_price_degraded_{name}")
        return

    name, tariff = divergences[0]
    worst = max(tariff.divergences, key=lambda item: abs(item.delta))
    runtime.audit.append(
        "price.divergence",
        {
            "input": name,
            "authority": tariff.authority,
            "periods": len(tariff.divergences),
            "worst": {"at": worst.ts.isoformat(), "cloud": worst.cloud, "user": worst.user, "chosen": worst.chosen},
        },
    )
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{entry.entry_id}_price_divergence",
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="price_divergence",
        translation_placeholders={
            "entry": NAME,
            "input": name,
            "periods": str(len(tariff.divergences)),
            "authority": tariff.authority,
            "at": worst.ts.isoformat(),
            "cloud": f"{worst.cloud:.4f}",
            "user": f"{worst.user:.4f}",
            "chosen": f"{worst.chosen:.4f}",
        },
    )

    for other, other_tariff in runtime.tariffs.items():
        key = f"{entry.entry_id}_price_degraded_{other}"
        if other_tariff.stale or other_tariff.missing:
            ir.async_create_issue(
                hass,
                DOMAIN,
                key,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="price_degraded",
                translation_placeholders={
                    "entry": NAME,
                    "input": other,
                    "stale": str(len(other_tariff.stale)),
                    "missing": str(len(other_tariff.missing)),
                },
            )
        else:
            ir.async_delete_issue(hass, DOMAIN, key)


def _snapshot(hass: HomeAssistant, entity_id: str) -> EntitySnapshot | None:
    state = hass.states.get(entity_id)
    if state is None:
        return None
    forecast = state.attributes.get(contracts.FORECAST_ATTRIBUTE) or []
    points = len(forecast) if isinstance(forecast, (list, tuple)) else 0
    unit = state.attributes.get("unit_of_measurement")
    return EntitySnapshot(state=state.state, forecast_points=points, unit=unit)


def _consent_granted(profile: dict[str, Any]) -> bool:
    consent = profile.get("consent") or {}
    return isinstance(consent, dict) and consent.get("granted") is True


def _build_adapters(hass: HomeAssistant, entry: ConfigEntry, runtime: SiteRuntime) -> None:
    """Turn local-backed controls into adapters bound to their HA entities.

    No write happens here: adapters are constructed so the executor has somewhere
    to send a plan, and an unbound control becomes a repair instead of a crash.
    """
    runtime.adapters, issues = build_ha_adapters(
        runtime.profile,
        service_caller(hass),
        reader=lambda entity_id: _entity_state(hass, entity_id),
    )
    # The pipeline owns consent, clamping, rate limits and hysteresis — the
    # dispatcher never writes around it.
    runtime.safety = SafetyPipeline(runtime.adapters, runtime.audit, consent_granted=_consent_granted(runtime.profile))
    runtime.issues.extend(issues)
    for index, issue in enumerate(issues):
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"{entry.entry_id}_control_{index}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="control_unbound",
            translation_placeholders={"entry": NAME, "path": issue.path, "message": issue.message},
        )
    runtime.audit.append(
        "control.adapters",
        {
            "adapters": sorted(runtime.adapters),
            "unbound": [f"{i.path}: {i.message}" for i in issues],
        },
    )


def _entity_state(hass: HomeAssistant, entity_id: str) -> str | None:
    state = hass.states.get(entity_id)
    return None if state is None else state.state


def _plan_mapping(runtime: SiteRuntime) -> list[tuple[str, str, str]]:
    """(element, capability, plan entity) for every control that names one."""
    mapping: list[tuple[str, str, str]] = []
    for control in runtime.profile.get("controls") or []:
        if not isinstance(control, Mapping):
            continue
        plan_entity = control.get("plan_entity")
        if not isinstance(plan_entity, str) or not plan_entity:
            continue
        mapping.append((str(control.get("element")), str(control.get("capability")), plan_entity))
    return mapping


def _start_dispatch(hass: HomeAssistant, entry: ConfigEntry, runtime: SiteRuntime) -> None:
    """Run the dispatch loop on a timer, if the site asked for it.

    Off by default: a site that has not mapped any plan entity has nothing to
    dispatch, and a timer that fails safe every minute is worse than no timer. Even
    when enabled, the loop only acts on entities the installer named — HAEO's own
    entity ids are never guessed (ADR-0012).
    """
    if not entry.options.get(CONF_DISPATCH_ENABLED, DEFAULT_DISPATCH_ENABLED):
        return
    if runtime.safety is None or not runtime.adapters:
        runtime.audit.append("dispatch.disabled", {"reason": "no local adapters to drive"})
        return

    dispatcher = Dispatcher(Executor(runtime.safety), runtime.audit)
    source = MappedPlanSource(lambda entity_id: _entity_state(hass, entity_id), _plan_mapping(runtime))
    runtime.dispatcher = dispatcher
    runtime.dispatch_source = source

    async def _tick(now: Any) -> None:
        outcome = await hass.async_add_executor_job(dispatcher.tick, source, dt_util.utcnow())
        runtime.dispatch_state.record(outcome)
        if outcome.action == "failed_safe":
            ir.async_create_issue(
                hass,
                DOMAIN,
                f"{entry.entry_id}_fail_safe",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="dispatch_failed_safe",
                translation_placeholders={"entry": NAME, "reason": outcome.reason},
            )
        elif outcome.action == "applied":
            ir.async_delete_issue(hass, DOMAIN, f"{entry.entry_id}_fail_safe")

    runtime.dispatch_unsub = async_track_time_interval(
        hass, callback(_tick), timedelta(seconds=DISPATCH_INTERVAL_SECONDS)
    )
    runtime.audit.append(
        "dispatch.started",
        {"interval_seconds": DISPATCH_INTERVAL_SECONDS, "setpoints": len(_plan_mapping(runtime))},
    )


async def _apply_profile(hass: HomeAssistant, entry: ConfigEntry, runtime: SiteRuntime) -> None:
    """Provision HAEO from the compiled plan, outside the event loop.

    The bridge driver is synchronous and answers HAEO's flows one step at a time,
    so it runs in an executor thread while the port bridges each flow call back
    onto ``hass.loop`` (see ``haeo_bridge/ha_port.py``). Failures never break
    setup: the entry keeps working, the report is stored for diagnostics, the
    audit trail records the attempt, and a repair issue tells the user what HAEO
    asked for.
    """
    driver = FlowHaeoDriver(HomeAssistantFlowPort(hass))
    report: ApplyReport = await hass.async_add_executor_job(apply_plan, driver, runtime.plan)

    runtime.last_apply_status = report.status
    runtime.last_apply_report = report
    runtime.issues.extend(report.issues)
    runtime.audit.append(
        "haeo.apply",
        {
            "status": report.status,
            "haeo_version": report.haeo_version,
            "operations": [{"type": op.type, "name": op.name, "system_id": op.system_id} for op in report.operations],
            "issues": [{"code": i.code, "path": i.path, "message": i.message} for i in report.issues],
        },
    )

    if report.status in {"blocked", "partial"}:
        first = report.issues[0] if report.issues else None
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"{entry.entry_id}_haeo_apply",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="haeo_apply_incomplete",
            translation_placeholders={
                "entry": NAME,
                "status": report.status,
                "path": "" if first is None else first.path,
                "message": "" if first is None else first.message,
                "code": "" if first is None else first.code,
            },
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, f"{entry.entry_id}_haeo_apply")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if runtime is not None:
        for attribute in ("dispatch_unsub", "references_unsub"):
            unsub = getattr(runtime, attribute, None)
            if unsub is not None:
                unsub()
        dispatcher = getattr(runtime, "dispatcher", None)
        if dispatcher is not None:
            # Leaving devices at the optimizer's last instruction while we go away
            # is the one thing a fail-safe exists to prevent.
            await hass.async_add_executor_job(
                lambda: dispatcher.fail_safe_once(now=dt_util.utcnow(), reason="integration unloading")
            )
    unloaded = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded


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
