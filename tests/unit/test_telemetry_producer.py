"""Telemetry producer: one envelope per quality class, commanded is not measured."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.fleetassistant.adapters.base import WriteResult
from custom_components.fleetassistant.dispatch import DispatchOutcome
from custom_components.fleetassistant.executor import ExecutionReport, Setpoint
from custom_components.fleetassistant.telemetry import DedupeRegistry, summarise, to_envelope, validate_envelope
from custom_components.fleetassistant.telemetry.producer import Sample, TelemetryProducer

NOW = datetime(2026, 11, 6, 18, 0, tzinfo=UTC)


def _producer(**kwargs) -> TelemetryProducer:
    return TelemetryProducer(site_id="site_a", deployment_profile="gateway_primary", **kwargs)


def test_every_envelope_the_producer_builds_is_valid():
    producer = _producer()
    producer.start(NOW - timedelta(minutes=5))
    producer.observe(Sample("grid.set_export_limit", 4.0, quality="estimated", source="optimizer"))
    producer.observe_readback({"grid": {"set_export_limit": 3.8}})

    payloads = producer.build(now=NOW)

    assert len(payloads) == 2
    for payload in payloads:
        assert validate_envelope(payload) == []


def test_measured_and_estimated_samples_never_share_an_envelope():
    producer = _producer()
    producer.start(NOW - timedelta(minutes=5))
    producer.observe(Sample("battery.soc", 55.0, quality="estimated"))
    producer.observe_readback({"battery": {"soc": 54.0}}, authority="full")

    payloads = producer.build(now=NOW)

    qualities = sorted(payload["quality"] for payload in payloads)
    assert qualities == ["estimated", "measured"]
    measured = next(p for p in payloads if p["quality"] == "measured")
    assert measured["metrics"] == {"battery.soc.readback": 54.0}
    assert measured["authority"] == "full"


def test_a_commanded_setpoint_is_estimated_until_the_device_confirms():
    producer = _producer()
    producer.start(NOW - timedelta(minutes=5))
    producer.observe_plan(
        plan_id="p1",
        created_at=NOW - timedelta(minutes=2),
        setpoints=[Setpoint("grid", "set_export_limit", 5.0)],
    )
    payload = producer.build(now=NOW)[0]
    assert payload["quality"] == "estimated"
    assert payload["metrics"]["grid.set_export_limit"] == 5.0
    assert payload["plan"]["plan_id"] == "p1"
    assert to_envelope(payload).is_firm() is False


def test_only_a_measured_full_authority_envelope_is_firm():
    producer = _producer()
    producer.start(NOW - timedelta(minutes=5))
    producer.observe_readback({"grid": {"set_export_limit": 3.0}}, authority="full")

    producer_coarse = _producer()
    producer_coarse.start(NOW - timedelta(minutes=5))
    producer_coarse.observe_readback({"grid": {"set_export_limit": 3.0}}, authority="coarse")

    assert to_envelope(producer.build(now=NOW)[0]).is_firm() is True
    assert to_envelope(producer_coarse.build(now=NOW)[0]).is_firm() is False


def test_a_rejected_setpoint_becomes_a_flag_not_a_zero_metric():
    report = ExecutionReport(
        plan_id="p1",
        results=[WriteResult(status="rejected", element_id="ev", capability="set_charger_amps", requested_value=32.0, effective_value=None, reason="consent_missing: not granted", audit_id=1, authority="full")],
    )
    producer = _producer()
    producer.start(NOW - timedelta(minutes=5))

    producer.observe_dispatch(DispatchOutcome(action="rejected", reason="all rejected", report=report), now=NOW)
    payload = producer.build(now=NOW)[0]

    assert "ev.set_charger_amps.effective" not in payload["metrics"]
    assert any(flag.startswith("rejected:ev.set_charger_amps") for flag in payload["flags"])
    assert payload["metrics"]["dispatch.applied"] == 0.0


def test_a_fail_safe_dispatch_is_flagged():
    report = ExecutionReport(plan_id="fail_safe", results=[], fail_safe=True)
    producer = _producer()
    producer.start(NOW - timedelta(minutes=5))
    producer.observe_dispatch(DispatchOutcome(action="failed_safe", reason="optimizer unreachable", report=report), now=NOW)
    assert "dispatch:fail_safe" in producer.build(now=NOW)[0]["flags"]


def test_sequence_numbers_increase_per_envelope_and_the_collector_accepts_them():
    producer = _producer()
    collector = DedupeRegistry()
    producer.start(NOW - timedelta(minutes=5))
    producer.observe(Sample("grid.p", 1.0, quality="estimated"))
    producer.observe_readback({"grid": {"p": 1.0}})

    payloads = producer.build(now=NOW)

    assert [payload["seq"] for payload in payloads] == [0, 1]
    assert all(collector.accept(payload) for payload in payloads)
    assert collector.watermark("site_a") == 1


def test_the_interval_starts_when_the_producer_started():
    producer = _producer()
    producer.start(NOW - timedelta(minutes=5))
    producer.observe_readback({"grid": {"p": 1.0}})
    payload = producer.build(now=NOW)[0]
    assert payload["interval"] == {"start": "2026-11-06T17:55:00Z", "end": "2026-11-06T18:00:00Z"}


def test_build_resets_the_accumulator_so_intervals_do_not_bleed():
    producer = _producer()
    producer.start(NOW - timedelta(minutes=5))
    producer.observe_readback({"grid": {"p": 1.0}})
    producer.build(now=NOW)

    producer.observe_readback({"grid": {"p": 2.0}})
    second = producer.build(now=NOW + timedelta(minutes=5))[0]

    assert second["metrics"] == {"grid.p.readback": 2.0}
    assert second["interval"]["start"] == "2026-11-06T18:00:00Z"


def test_an_empty_interval_builds_no_envelope():
    producer = _producer()
    producer.start(NOW - timedelta(minutes=5))
    assert producer.build(now=NOW) == []


def test_summarise_reports_firm_share_across_the_two_classes():
    producer = _producer()
    producer.start(NOW - timedelta(minutes=5))
    producer.observe(Sample("grid.p", 5.0, quality="estimated"))
    producer.observe_readback({"grid": {"p": 4.9}})
    summary = summarise(to_envelope(payload) for payload in producer.build(now=NOW))
    assert summary["intervals"] == 2
    assert summary["firm_intervals"] == 1
    assert summary["firm_share"] == pytest.approx(0.5)
