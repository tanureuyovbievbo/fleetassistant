"""The dispatch loop: plan in, safe writes out, fail-safe when the plan stops (step 4).

Three things can go wrong between an optimizer and a device, and this module is
about all three:

1. **The plan is wrong.** A setpoint outside the envelope, or one the customer has
   not consented to. The safety pipeline handles that; the dispatcher must not
   bypass it to "make the plan work".
2. **The plan is late.** A plan computed for 15:00 is not a plan for 16:00. Past its
   age it is discarded and the site falls back to its fail-safe setpoints, because
   holding a stale setpoint is how a battery ends up empty at the evening peak.
3. **The plan never comes.** The optimizer is down, the network is down, HAEO is
   mid-restart. After a grace period the site falls back — once, loudly, audited —
   and then stays quiet instead of hammering a dead source every tick.

Deliberately pure: time is passed in, sources are injected, the executor is the
real one. That makes the awkward cases (the 15-minute-old plan, the source that
throws, the fail-safe that must not repeat) ordinary unit tests.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Literal, Protocol

from .audit import AuditLog
from .executor import ExecutionPlan, ExecutionReport, Executor, Setpoint
from .ledger import CommitmentsLedger

DispatchAction = Literal["applied", "failed_safe", "idle", "rejected"]

#: How old a plan may be before it is considered stale. Long enough to survive a
#: slow solver run, short enough that one missed cycle does not hold a setpoint
#: through a price change.
DEFAULT_MAX_PLAN_AGE = timedelta(minutes=15)

#: How long the optimizer may be silent before the site falls back. Longer than
#: the plan age on purpose: one missed plan is normal, ten minutes of silence is not.
DEFAULT_FAIL_SAFE_AFTER = timedelta(minutes=30)


@dataclass(frozen=True)
class PlanSnapshot:
    """One optimizer plan, as the dispatcher sees it."""

    plan_id: str
    created_at: datetime
    setpoints: tuple[Setpoint, ...]
    source: str = "haeo"

    def age(self, now: datetime) -> timedelta:
        return now - self.created_at

    def to_plan(self, *, valid_for: timedelta) -> ExecutionPlan:
        return ExecutionPlan(
            plan_id=self.plan_id,
            created_at=self.created_at,
            setpoints=self.setpoints,
            source=self.source,
            valid_for=valid_for,
        )


class PlanSource(Protocol):
    """Where a plan comes from. Implementations may read entities or a file."""

    def snapshot(self, now: datetime) -> PlanSnapshot | None:
        """Return the current plan, or ``None`` when there is not one."""
        ...


@dataclass
class StaticPlanSource:
    """A source with one plan — useful for tests and for replaying a capture."""

    plan: PlanSnapshot | None
    raises: Exception | None = None

    def snapshot(self, now: datetime) -> PlanSnapshot | None:
        if self.raises is not None:
            raise self.raises
        return self.plan


@dataclass
class MappedPlanSource:
    """Builds a plan from entities the installer mapped to each capability.

    HAEO's own entity names are not guessed (ADR-0012): each control names the
    entity that publishes its setpoint (``plan_entity``), and a control without one
    simply contributes no setpoint. A value that is not a number is skipped and
    reported, never coerced to zero — a zero export limit at noon is a real
    instruction, not a missing reading.
    """

    reader: Callable[[str], str | None]
    mapping: Sequence[tuple[str, str, str]]  # (element_id, capability, entity_id)
    plan_id: str = "mapped"
    source: str = "haeo"

    def snapshot(self, now: datetime) -> PlanSnapshot | None:
        setpoints: list[Setpoint] = []
        for element_id, capability, entity_id in self.mapping:
            raw = self.reader(entity_id)
            if raw is None:
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue
            setpoints.append(Setpoint(element_id, capability, value))
        if not setpoints:
            return None
        return PlanSnapshot(plan_id=f"{self.plan_id}:{int(now.timestamp())}", created_at=now, setpoints=tuple(setpoints))


@dataclass(frozen=True)
class DispatchOutcome:
    """What one tick did, and why."""

    action: DispatchAction
    reason: str
    plan_id: str = ""
    plan_age_seconds: float | None = None
    report: ExecutionReport | None = None

    @property
    def wrote(self) -> bool:
        return self.action == "applied" and self.report is not None and bool(self.report.applied)


@dataclass
class Dispatcher:
    """Applies plans, expires them, and fails safe exactly once per outage."""

    executor: Executor
    audit: AuditLog
    max_plan_age: timedelta = DEFAULT_MAX_PLAN_AGE
    fail_safe_after: timedelta = DEFAULT_FAIL_SAFE_AFTER
    valid_for: timedelta | None = None
    #: When set, a plan is refused if another program already holds the same
    #: capability over the plan's window (C-16). Dispatching a capability twice is
    #: how a site gets paid twice for one kilowatt, so it is a refusal, not a warning.
    ledger: CommitmentsLedger | None = None
    program_id: str = ""
    last_applied_at: datetime | None = None
    failed_safe_at: datetime | None = None
    ticks: int = 0

    def tick(self, source: PlanSource, now: datetime) -> DispatchOutcome:
        self.ticks += 1
        try:
            snapshot = source.snapshot(now)
        except Exception as err:  # noqa: BLE001 - a broken source is an outage, not a crash
            return self._outage(f"plan source failed: {err}", now)
        if snapshot is None:
            return self._outage("no plan available", now)

        age = snapshot.age(now)
        if age > self.max_plan_age:
            return self._outage(f"plan is {age.total_seconds():.0f}s old (max {self.max_plan_age.total_seconds():.0f}s)", now)

        window = self.valid_for or self.max_plan_age
        conflict = self._conflict(snapshot, now, window)
        if conflict is not None:
            self.audit.append(
                "dispatch.refused",
                {"plan_id": snapshot.plan_id, "reason": conflict, "program_id": self.program_id},
            )
            return DispatchOutcome(action="rejected", reason=conflict, plan_id=snapshot.plan_id, plan_age_seconds=age.total_seconds())

        plan = snapshot.to_plan(valid_for=window)
        report = self.executor.apply(plan, now)
        self.last_applied_at = now
        self.failed_safe_at = None
        outcome = DispatchOutcome(
            action="applied" if report.applied else "rejected",
            reason="plan applied" if report.applied else "every setpoint was rejected",
            plan_id=snapshot.plan_id,
            plan_age_seconds=age.total_seconds(),
            report=report,
        )
        self.audit.append(
            "dispatch.apply",
            {
                "plan_id": snapshot.plan_id,
                "plan_age_seconds": round(age.total_seconds(), 3),
                "action": outcome.action,
                "applied": [r.capability for r in report.results if r.ok],
                "rejected": [{"capability": r.capability, "reason": r.reason} for r in report.results if not r.ok],
            },
        )
        return outcome

    def _conflict(self, snapshot: PlanSnapshot, now: datetime, window: timedelta) -> str | None:
        if self.ledger is None or not self.program_id:
            return None
        capabilities = sorted({setpoint.capability for setpoint in snapshot.setpoints})
        for capability in capabilities:
            held = self.ledger.conflicts(
                program_id=self.program_id, start=now, end=now + window, capability=capability
            )
            if held:
                programs = ", ".join(sorted({commitment.program_id for commitment in held}))
                return f"double_booked: {capability} is already committed to {programs}"
        return None

    def fail_safe_once(self, *, now: datetime, reason: str) -> DispatchOutcome:
        """Force the fail-safe on demand (unload, manual action), at most once."""
        return self._outage(reason, now, force=True)

    def _outage(self, reason: str, now: datetime, *, force: bool = False) -> DispatchOutcome:
        silent_for = None if self.last_applied_at is None else now - self.last_applied_at
        due = force or silent_for is None or silent_for >= self.fail_safe_after
        if self.failed_safe_at is not None and not force:
            return DispatchOutcome(action="idle", reason=f"{reason}; already failed safe")
        if not due:
            seconds = 0.0 if silent_for is None else silent_for.total_seconds()
            return DispatchOutcome(
                action="idle",
                reason=f"{reason}; within the {self.fail_safe_after.total_seconds():.0f}s grace period",
                plan_age_seconds=seconds,
            )
        report = self.executor.fail_safe(now=now, reason=reason)
        self.failed_safe_at = now
        self.audit.append("dispatch.fail_safe", {"reason": reason, "setpoints": len(report.results)})
        return DispatchOutcome(action="failed_safe", reason=reason, report=report)


@dataclass
class DispatchState:
    """Diagnostics-friendly view of the loop's recent behaviour."""

    outcomes: list[DispatchOutcome] = field(default_factory=list)

    def record(self, outcome: DispatchOutcome, *, keep: int = 10) -> None:
        self.outcomes.append(outcome)
        del self.outcomes[:-keep]

    def as_dict(self) -> list[dict[str, Any]]:
        return [
            {
                "action": outcome.action,
                "reason": outcome.reason,
                "plan_id": outcome.plan_id,
                "plan_age_seconds": outcome.plan_age_seconds,
            }
            for outcome in self.outcomes
        ]
