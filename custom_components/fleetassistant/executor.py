"""Plan execution + fail-safe (C-12, C-15).

The executor takes optimizer intent (setpoints) and pushes it through the safety
pipeline. Three rules are structural, not configurable:

* A plan older than its validity window is never executed.
* When the optimizer is unreachable, every capability is driven to its declared
  fail-safe value and non-performance is reported (never concealed).
* Every attempt, including fail-safe, lands in the audit log.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from .adapters.base import Command, WriteResult
from .adapters.safety import SafetyPipeline


@dataclass(frozen=True)
class Setpoint:
    element_id: str
    capability: str
    value: float


@dataclass(frozen=True)
class ExecutionPlan:
    plan_id: str
    created_at: datetime
    setpoints: tuple[Setpoint, ...]
    source: str = "haeo"
    valid_for: timedelta = timedelta(minutes=15)

    @property
    def expires_at(self) -> datetime:
        return self.created_at + self.valid_for


@dataclass
class ExecutionReport:
    plan_id: str
    results: list[WriteResult] = field(default_factory=list)
    fail_safe: bool = False
    stale: bool = False
    reason: str = ""

    @property
    def applied(self) -> int:
        return sum(1 for r in self.results if r.ok)

    @property
    def rejected(self) -> int:
        return sum(1 for r in self.results if r.status == "rejected")

    def as_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "fail_safe": self.fail_safe,
            "stale": self.stale,
            "applied": self.applied,
            "rejected": self.rejected,
            "reason": self.reason,
            "results": [
                {
                    "element_id": r.element_id,
                    "capability": r.capability,
                    "status": r.status,
                    "effective_value": r.effective_value,
                    "authority": r.authority,
                    "audit_id": r.audit_id,
                }
                for r in self.results
            ],
        }


class Executor:
    def __init__(self, safety: SafetyPipeline) -> None:
        self._safety = safety

    def apply(self, plan: ExecutionPlan, now: datetime | None = None) -> ExecutionReport:
        stamp = now or datetime.now(UTC)
        if stamp > plan.expires_at:
            report = self.fail_safe(plan.plan_id, now=stamp, reason="plan expired")
            report.stale = True
            return report
        report = ExecutionReport(plan_id=plan.plan_id)
        for setpoint in plan.setpoints:
            report.results.append(
                self._safety.submit(
                    Command(
                        element_id=setpoint.element_id,
                        capability=setpoint.capability,
                        value=setpoint.value,
                        requested_by="executor",
                        source=plan.source,
                    ),
                    now=stamp,
                )
            )
        return report

    def fail_safe(self, plan_id: str = "fail_safe", *, now: datetime | None = None, reason: str = "optimizer unreachable") -> ExecutionReport:
        stamp = now or datetime.now(UTC)
        report = ExecutionReport(plan_id=plan_id, fail_safe=True, reason=reason)
        for element_id, capabilities in self._safety.capabilities().items():
            for capability in capabilities.values():
                report.results.append(
                    self._safety.submit(
                        Command(
                            element_id=element_id,
                            capability=capability.name,
                            value=capability.fail_safe_value,
                            requested_by="executor",
                            reason=reason,
                            source="fail_safe",
                        ),
                        now=stamp,
                    )
                )
        return report


def dry_run(plan: ExecutionPlan) -> list[tuple[str, str, float]]:
    return [(s.element_id, s.capability, s.value) for s in plan.setpoints]


def summarise_report(reports: Iterable[ExecutionReport]) -> dict[str, int]:
    applied = rejected = fail_safes = 0
    for report in reports:
        applied += report.applied
        rejected += report.rejected
        fail_safes += 1 if report.fail_safe else 0
    return {"applied": applied, "rejected": rejected, "fail_safe_reports": fail_safes}
