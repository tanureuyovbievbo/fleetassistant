"""T-16..T-19: safety pipeline gates, audit chain, and adapter interchangeability."""

from __future__ import annotations

import pytest

from custom_components.fleetassistant.adapters import (
    AdapterError,
    ApiStubAdapter,
    Command,
    ModbusStubAdapter,
    SafetyPipeline,
    TokenBucket,
)
from custom_components.fleetassistant.audit import AuditLog


@pytest.fixture
def frozen_clock():
    now = [0.0]

    def clock() -> float:
        return now[0]

    clock.now = now  # type: ignore[attr-defined]
    return clock


def _pipeline(adapter, tmp_path, *, consent: bool, clock=None) -> tuple[SafetyPipeline, AuditLog]:
    audit = AuditLog(tmp_path / "audit.jsonl")
    bucket = TokenBucket(clock=clock) if clock else TokenBucket()
    return SafetyPipeline({adapter.adapter_id: adapter}, audit, consent_granted=consent, bucket=bucket), audit


def test_consent_blocks_api_control(tmp_path) -> None:
    pipeline, audit = _pipeline(ApiStubAdapter(), tmp_path, consent=False)
    result = pipeline.submit(Command("api_stub", "set_export_limit", 2.0, "test"))
    assert result.status == "rejected"
    assert "consent_missing" in result.reason
    assert audit.records()[-1].kind == "control.rejected"


def test_value_is_clamped_to_capability_limits(tmp_path) -> None:
    pipeline, _ = _pipeline(ApiStubAdapter(), tmp_path, consent=True)
    result = pipeline.submit(Command("api_stub", "set_export_limit", 99.0, "test"))
    assert result.status == "clamped"
    assert result.effective_value == 5.0


def test_hysteresis_skips_tiny_changes(tmp_path) -> None:
    pipeline, _ = _pipeline(ModbusStubAdapter(), tmp_path, consent=False)
    first = pipeline.submit(Command("modbus_stub", "set_battery_target", 60.0, "test"))
    tiny = pipeline.submit(Command("modbus_stub", "set_battery_target", 60.05, "test"))
    big = pipeline.submit(Command("modbus_stub", "set_battery_target", 65.0, "test"))
    assert first.status == "applied"
    assert tiny.status == "skipped"
    assert big.status == "applied"


def test_rate_limit_drops_excess_commands(tmp_path, frozen_clock) -> None:
    pipeline, _ = _pipeline(ModbusStubAdapter(), tmp_path, consent=False, clock=frozen_clock)
    statuses = [
        pipeline.submit(Command("modbus_stub", "set_export_limit", value * 0.5, "test")).status
        for value in range(13)
    ]
    assert statuses[:12] == ["applied"] * 12
    assert statuses[12] == "rejected"


def test_invalid_values_are_rejected(tmp_path) -> None:
    pipeline, _ = _pipeline(ModbusStubAdapter(), tmp_path, consent=False)
    for bad in (float("nan"), float("inf"), True):
        result = pipeline.submit(Command("modbus_stub", "set_export_limit", bad, "test"))  # type: ignore[arg-type]
        assert result.status == "rejected"


def test_unknown_element_and_capability_are_rejected(tmp_path) -> None:
    pipeline, _ = _pipeline(ModbusStubAdapter(), tmp_path, consent=False)
    assert pipeline.submit(Command("ghost", "set_export_limit", 1.0, "test")).status == "rejected"
    assert pipeline.submit(Command("modbus_stub", "open_garage", 1.0, "test")).status == "rejected"


def test_adapter_failure_is_recorded_not_swallowed(tmp_path) -> None:
    adapter = ModbusStubAdapter()
    adapter.fail_next_write = True
    pipeline, audit = _pipeline(adapter, tmp_path, consent=False)
    result = pipeline.submit(Command("modbus_stub", "set_export_limit", 3.0, "test"))
    assert result.status == "rejected"
    assert "adapter_error" in result.reason
    assert audit.verify()


def test_audit_chain_detects_tampering(tmp_path) -> None:
    pipeline, audit = _pipeline(ModbusStubAdapter(), tmp_path, consent=False)
    for value in range(3):
        pipeline.submit(Command("modbus_stub", "set_export_limit", float(value), "test"))
    assert audit.verify()

    path = tmp_path / "audit.jsonl"
    text = path.read_text(encoding="utf-8").replace('"applied"', '"clamped"', 1)
    path.write_text(text, encoding="utf-8")
    assert AuditLog(path).verify() is False


def test_audit_survives_reload(tmp_path) -> None:
    pipeline, _ = _pipeline(ModbusStubAdapter(), tmp_path, consent=False)
    pipeline.submit(Command("modbus_stub", "set_export_limit", 1.0, "test"))
    reloaded = AuditLog(tmp_path / "audit.jsonl")
    assert len(reloaded) == 1
    assert reloaded.verify()


def test_unknown_capability_on_adapter_raises() -> None:
    with pytest.raises(AdapterError):
        ModbusStubAdapter().write("open_garage", 1.0)
