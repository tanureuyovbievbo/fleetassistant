"""The commitments guard in the dispatch path (C-16, ADR-0023).

The ledger already refuses an over-commitment at insert time. This suite covers the
other half: a dispatch that would *deliver* a capability another program already
holds must be refused before any device is touched, and the refusal must be as
visible as a write.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.fleetassistant.adapters.ha_services import (
    HaServiceAdapter,
    NumberBinding,
    capability_from_control,
)
from custom_components.fleetassistant.adapters.safety import SafetyPipeline
from custom_components.fleetassistant.audit import AuditLog
from custom_components.fleetassistant.dispatch import Dispatcher, PlanSnapshot, StaticPlanSource
from custom_components.fleetassistant.executor import Executor, Setpoint
from custom_components.fleetassistant.ledger import Commitment, CommitmentsLedger

NOW = datetime(2026, 11, 6, 18, 0, tzinfo=UTC)


class Bus:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def __call__(self, domain: str, service: str, data: dict) -> None:
        self.calls.append((domain, service, dict(data)))

    def values(self) -> list[float]:
        return [call[2]["value"] for call in self.calls if "value" in call[2]]


def _setup():
    bus = Bus()
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
    capability = capability_from_control(control)
    adapter = HaServiceAdapter(
        "grid", bus, {capability.name: capability}, {capability.name: NumberBinding("number.export_limit")}
    )
    audit = AuditLog()
    return bus, audit, Executor(SafetyPipeline({"grid": adapter}, audit, consent_granted=True))


def _plan(value: float = 4.0) -> PlanSnapshot:
    return PlanSnapshot("p1", NOW, (Setpoint("grid", "set_export_limit", value),))


def _ledger_with_elrp(**kwargs) -> CommitmentsLedger:
    ledger = CommitmentsLedger("site_a", 10.0)
    ledger.add(
        Commitment(
            "c1",
            "elrp",
            NOW,
            NOW + timedelta(hours=1),
            4.0,
            "full",
            capability="set_export_limit",
            **kwargs,
        )
    )
    return ledger


def test_dispatch_refuses_a_plan_another_program_already_holds():
    bus, audit, executor = _setup()
    dispatcher = Dispatcher(executor, audit, ledger=_ledger_with_elrp(), program_id="vpp")

    outcome = dispatcher.tick(StaticPlanSource(_plan()), NOW)

    assert outcome.action == "rejected"
    assert "double_booked" in outcome.reason and "elrp" in outcome.reason
    assert bus.calls == []
    assert [record.kind for record in audit.records()] == ["dispatch.refused"]


def test_the_program_that_holds_the_commitment_may_dispatch_it():
    bus, audit, executor = _setup()
    dispatcher = Dispatcher(executor, audit, ledger=_ledger_with_elrp(), program_id="elrp")

    outcome = dispatcher.tick(StaticPlanSource(_plan()), NOW)

    assert outcome.action == "applied"
    assert bus.values() == [4.0]


def test_a_window_that_does_not_overlap_is_not_a_conflict():
    bus, audit, executor = _setup()
    ledger = CommitmentsLedger("site_a", 10.0)
    ledger.add(
        Commitment(
            "c1",
            "elrp",
            NOW + timedelta(hours=2),
            NOW + timedelta(hours=3),
            4.0,
            "full",
            capability="set_export_limit",
        )
    )

    outcome = Dispatcher(executor, audit, ledger=ledger, program_id="vpp").tick(StaticPlanSource(_plan()), NOW)

    assert outcome.action == "applied"


def test_without_a_ledger_nothing_is_blocked():
    bus, audit, executor = _setup()
    outcome = Dispatcher(executor, audit).tick(StaticPlanSource(_plan()), NOW)
    assert outcome.action == "applied"
    assert bus.values() == [4.0]


def test_a_refused_dispatch_does_not_write_the_fail_safe_either():
    bus, audit, executor = _setup()
    dispatcher = Dispatcher(executor, audit, ledger=_ledger_with_elrp(), program_id="vpp")

    dispatcher.tick(StaticPlanSource(_plan()), NOW)
    dispatcher.tick(StaticPlanSource(_plan()), NOW + timedelta(minutes=1))

    # Two refusals, two audit records, zero device traffic: a double-booking is a
    # planning fault, not a safety event, so the fail-safe stays out of it.
    assert bus.calls == []
    assert [record.kind for record in audit.records()] == ["dispatch.refused", "dispatch.refused"]
