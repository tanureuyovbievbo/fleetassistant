"""T-21: plan execution, staleness, and fail-safe behaviour (C-12, C-15)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.fleetassistant.adapters import ModbusStubAdapter, SafetyPipeline
from custom_components.fleetassistant.audit import AuditLog
from custom_components.fleetassistant.executor import ExecutionPlan, Executor, Setpoint

NOW = datetime(2026, 7, 1, 18, 0, tzinfo=UTC)


def _executor(tmp_path):
    adapter = ModbusStubAdapter()
    audit = AuditLog(tmp_path / "audit.jsonl")
    return Executor(SafetyPipeline({adapter.adapter_id: adapter}, audit, consent_granted=True)), adapter, audit


def test_plan_is_applied_to_the_device(tmp_path) -> None:
    executor, adapter, audit = _executor(tmp_path)
    plan = ExecutionPlan(
        plan_id="p1",
        created_at=NOW,
        setpoints=(Setpoint("modbus_stub", "set_battery_target", 80.0),),
    )
    report = executor.apply(plan, now=NOW + timedelta(minutes=1))
    assert report.applied == 1
    assert report.rejected == 0
    assert adapter.read_state()["values"]["set_battery_target"] == 80.0
    assert audit.verify()


def test_stale_plan_triggers_fail_safe_instead_of_execution(tmp_path) -> None:
    executor, adapter, audit = _executor(tmp_path)
    plan = ExecutionPlan(
        plan_id="p2",
        created_at=NOW,
        setpoints=(Setpoint("modbus_stub", "set_battery_target", 95.0),),
        valid_for=timedelta(minutes=15),
    )
    report = executor.apply(plan, now=NOW + timedelta(hours=2))
    assert report.stale is True
    assert report.fail_safe is True
    # fail-safe values, never the stale plan's value
    assert adapter.read_state()["values"]["set_battery_target"] == 50.0
    assert adapter.read_state()["values"]["set_export_limit"] == 0.0
    assert audit.verify()


def test_fail_safe_reports_non_performance(tmp_path) -> None:
    executor, _, audit = _executor(tmp_path)
    report = executor.fail_safe("p3", now=NOW, reason="optimizer unreachable")
    assert report.fail_safe and "unreachable" in report.reason
    payload = report.as_dict()
    assert payload["fail_safe"] is True
    assert payload["applied"] >= 1
    kinds = [record.kind for record in audit.records()]
    assert kinds.count("control.write") == len(report.results)


def test_fail_safe_is_idempotent_under_hysteresis(tmp_path) -> None:
    executor, adapter, _ = _executor(tmp_path)
    executor.fail_safe("p4", now=NOW)
    writes_after_first = len(adapter.write_log)
    second = executor.fail_safe("p4", now=NOW + timedelta(minutes=1))
    assert len(adapter.write_log) == writes_after_first
    assert all(result.status == "skipped" for result in second.results)
