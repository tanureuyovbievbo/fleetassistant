"""The dispatch loop: apply, expire, fail safe — once (step 4)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.fleetassistant.adapters.ha_services import (
    HaServiceAdapter,
    NumberBinding,
    capability_from_control,
)
from custom_components.fleetassistant.adapters.safety import SafetyPipeline
from custom_components.fleetassistant.audit import AuditLog
from custom_components.fleetassistant.dispatch import (
    Dispatcher,
    DispatchOutcome,
    DispatchState,
    MappedPlanSource,
    PlanSnapshot,
    StaticPlanSource,
)
from custom_components.fleetassistant.executor import Executor, Setpoint

NOW = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)


class Bus:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def __call__(self, domain: str, service: str, data: dict) -> None:
        self.calls.append((domain, service, dict(data)))

    def values(self) -> list[float]:
        return [call[2]["value"] for call in self.calls if "value" in call[2]]


def _control(**overrides):
    control = {
        "id": "export_limit",
        "element": "grid",
        "capability": "set_export_limit",
        "unit": "kW",
        "min": 0.0,
        "max": 12.0,
        "rate_limit_per_minute": 600,
        "hysteresis": 0.0,
        "consent_required": False,
        "backing": "local",
        "authority": "full",
        "fail_safe_value": 12.0,
        "entity_id": "number.export_limit",
    }
    control.update(overrides)
    return control


def _setup(*, consent: bool = True, **control_overrides):
    bus = Bus()
    control = _control(**control_overrides)
    capability = capability_from_control(control)
    adapter = HaServiceAdapter("grid", bus, {capability.name: capability}, {capability.name: NumberBinding("number.export_limit")})
    audit = AuditLog()
    safety = SafetyPipeline({"grid": adapter}, audit, consent_granted=consent)
    return bus, audit, Executor(safety), capability


def _plan(created_at: datetime, value: float = 5.0) -> PlanSnapshot:
    return PlanSnapshot("plan-1", created_at, (Setpoint("grid", "set_export_limit", value),))


def test_a_fresh_plan_reaches_the_device_and_is_audited():
    bus, audit, executor, _ = _setup()
    dispatcher = Dispatcher(executor, audit)

    outcome = dispatcher.tick(StaticPlanSource(_plan(NOW)), NOW)

    assert outcome.action == "applied"
    assert outcome.wrote
    assert bus.values() == [5.0]
    assert [record.kind for record in audit.records()] == ["control.write", "dispatch.apply"]


def test_a_stale_plan_is_discarded_and_the_site_fails_safe():
    bus, audit, executor, _ = _setup()
    dispatcher = Dispatcher(executor, audit)

    outcome = dispatcher.tick(StaticPlanSource(_plan(NOW - timedelta(minutes=20), value=1.0)), NOW)

    assert outcome.action == "failed_safe"
    assert "plan is 1200s old" in outcome.reason
    assert bus.values() == [12.0]


def test_a_plan_within_its_age_is_applied():
    bus, audit, executor, _ = _setup()
    outcome = Dispatcher(executor, audit).tick(StaticPlanSource(_plan(NOW - timedelta(minutes=14), value=3.0)), NOW)
    assert outcome.action == "applied"
    assert bus.values() == [3.0]


def test_within_the_grace_period_a_silent_optimizer_is_tolerated():
    bus, audit, executor, _ = _setup()
    dispatcher = Dispatcher(executor, audit)
    dispatcher.tick(StaticPlanSource(_plan(NOW, 6.0)), NOW)

    outcome = dispatcher.tick(StaticPlanSource(None), NOW + timedelta(minutes=5))

    assert outcome.action == "idle"
    assert "grace period" in outcome.reason
    assert bus.values() == [6.0]


def test_after_the_grace_period_silence_fails_safe_exactly_once():
    bus, audit, executor, _ = _setup()
    dispatcher = Dispatcher(executor, audit)
    dispatcher.tick(StaticPlanSource(_plan(NOW, 6.0)), NOW)

    first = dispatcher.tick(StaticPlanSource(None), NOW + timedelta(minutes=31))
    second = dispatcher.tick(StaticPlanSource(None), NOW + timedelta(minutes=32))

    assert first.action == "failed_safe"
    assert second.action == "idle"
    assert "already failed safe" in second.reason
    assert bus.values() == [6.0, 12.0]
    assert [record.kind for record in audit.records()].count("dispatch.fail_safe") == 1


def test_a_source_that_raises_is_an_outage_not_a_crash():
    bus, audit, executor, _ = _setup()
    dispatcher = Dispatcher(executor, audit)
    broken = StaticPlanSource(None, raises=RuntimeError("haeo is restarting"))

    outcome = dispatcher.tick(broken, NOW)

    assert outcome.action == "failed_safe"
    assert "haeo is restarting" in outcome.reason
    assert bus.values() == [12.0]


def test_a_new_plan_after_an_outage_clears_the_lockout():
    bus, audit, executor, _ = _setup()
    dispatcher = Dispatcher(executor, audit)
    dispatcher.tick(StaticPlanSource(None), NOW)
    assert dispatcher.failed_safe_at == NOW

    outcome = dispatcher.tick(StaticPlanSource(_plan(NOW, 4.0)), NOW + timedelta(minutes=1))

    assert outcome.action == "applied"
    assert dispatcher.failed_safe_at is None


def test_without_consent_the_plan_is_rejected_and_nothing_is_written():
    bus, audit, executor, _ = _setup(consent=False, consent_required=True)
    dispatcher = Dispatcher(executor, audit)

    outcome = dispatcher.tick(StaticPlanSource(_plan(NOW, 4.0)), NOW)

    assert outcome.action == "rejected"
    assert bus.calls == []
    assert "consent" in outcome.report.results[0].reason


def test_unload_can_force_the_fail_safe():
    bus, audit, executor, _ = _setup()
    dispatcher = Dispatcher(executor, audit)
    dispatcher.tick(StaticPlanSource(_plan(NOW, 6.0)), NOW)

    outcome = dispatcher.fail_safe_once(now=NOW + timedelta(seconds=30), reason="integration unloading")

    assert outcome.action == "failed_safe"
    assert bus.values() == [6.0, 12.0]


# --- the mapped source ------------------------------------------------------


def test_the_mapped_source_reads_each_controls_plan_entity():
    states = {"number.haeo_grid_export": "7.5"}
    source = MappedPlanSource(states.get, [("grid", "set_export_limit", "number.haeo_grid_export")])

    snapshot = source.snapshot(NOW)

    assert snapshot is not None
    assert snapshot.setpoints == (Setpoint("grid", "set_export_limit", 7.5),)
    assert snapshot.created_at == NOW


def test_the_mapped_source_skips_missing_and_unreadable_entities():
    states = {"number.a": "unavailable", "number.b": "3.0"}
    source = MappedPlanSource(states.get, [("grid", "set_export_limit", "number.a"), ("battery", "set_battery_target", "number.b")])

    snapshot = source.snapshot(NOW)

    assert snapshot is not None
    assert snapshot.setpoints == (Setpoint("battery", "set_battery_target", 3.0),)


def test_a_mapped_source_with_nothing_readable_is_an_outage():
    assert MappedPlanSource(lambda entity_id: None, [("grid", "set_export_limit", "number.gone")]).snapshot(NOW) is None


def test_a_zero_setpoint_is_a_real_instruction_not_a_missing_reading():
    source = MappedPlanSource({"number.export": "0"}.get, [("grid", "set_export_limit", "number.export")])
    snapshot = source.snapshot(NOW)
    assert snapshot is not None
    assert snapshot.setpoints[0].value == 0.0


def test_the_state_history_keeps_the_most_recent_outcomes_only():
    state = DispatchState()
    for index in range(12):
        state.record(DispatchOutcome(action="idle", reason=f"tick {index}"))
    assert [row["reason"] for row in state.as_dict()] == [f"tick {index}" for index in range(2, 12)]


@pytest.mark.parametrize("action", ["applied", "failed_safe", "idle", "rejected"])
def test_only_an_applied_outcome_that_wrote_reports_a_write(action: str):
    outcome = DispatchOutcome(action=action, reason="x")  # type: ignore[arg-type]
    assert not outcome.wrote
