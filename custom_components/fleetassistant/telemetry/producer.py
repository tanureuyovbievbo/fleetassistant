"""Turn what the site did into telemetry envelopes (D07 producer).

The schema (``telemetry/__init__.py``) was the easy half. This is the half that
decides what a real site reports, and it exists to keep three promises honest:

* **One envelope, one quality.** The envelope carries a single ``quality`` and
  ``source``, so a producer that mixed a measured SOC with an estimated export
  limit into one payload would be lying by structure. Samples are therefore
  grouped by ``(quality, source, authority)`` and each group becomes its own
  envelope — an interval can produce two envelopes, and that is correct.
* **Commanded is not measured.** A setpoint we sent is ``estimated`` until the
  device confirms it. Read-back from the state machine is ``measured``. Only a
  ``measured`` interval at ``full`` authority can back a firm claim (C-12), and
  ``Envelope.is_firm()`` is the only place that decision lives.
* **Privacy by construction.** Metrics are a flat dict of numbers with names we
  choose. No entity ids, no device serials, no per-circuit detail leaves the box
  unless a metric name says so.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from ..const import TELEMETRY_SCHEMA_VERSION

#: Reporting cadence. Five minutes matches the shortest HAEO period the default
#: horizon uses (1-minute periods exist only in the first hours of a 5-day run),
#: and keeps a 600-entity site well under any sane bandwidth budget.
DEFAULT_INTERVAL = timedelta(minutes=5)


@dataclass(frozen=True)
class Sample:
    """One number, with the provenance the envelope cannot carry per metric."""

    metric: str
    value: float
    quality: str = "estimated"
    source: str = "gateway"
    authority: str = "full"

    def key(self) -> tuple[str, str, str]:
        return (self.quality, self.source, self.authority)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


@dataclass
class TelemetryProducer:
    """Accumulates samples for one interval and renders envelopes for it.

    Deliberately not a thread: the dispatch loop calls ``observe_*`` and
    ``build`` from the executor thread that already owns the dispatcher.
    """

    site_id: str
    deployment_profile: str
    interval: timedelta = DEFAULT_INTERVAL
    seq: int = 0
    samples: list[Sample] = field(default_factory=list)
    plan_record: dict[str, Any] | None = None
    flags: list[str] = field(default_factory=list)
    started_at: datetime | None = None

    def start(self, now: datetime) -> None:
        self.started_at = now
        self.samples.clear()
        self.plan_record = None
        self.flags.clear()

    def observe(self, sample: Sample) -> None:
        if self.started_at is None:
            self.started_at = datetime.now(UTC)
        self.samples.append(sample)

    def observe_plan(self, *, plan_id: str, created_at: datetime, setpoints: Iterable[Any]) -> None:
        """Record what the optimizer asked for, including why it may be undelivered."""
        items = list(setpoints)
        self.plan_record = {
            "plan_id": plan_id,
            "created_at": _iso(created_at),
            "setpoints": len(items),
            "capabilities": sorted({str(getattr(item, "capability", "")) for item in items}),
        }
        for item in items:
            capability = str(getattr(item, "capability", ""))
            element = str(getattr(item, "element_id", ""))
            value = getattr(item, "value", None)
            if not capability or not element or not isinstance(value, (int, float)):
                continue
            self.samples.append(
                Sample(f"{element}.{capability}", float(value), quality="estimated", source="optimizer")
            )

    def observe_dispatch(self, outcome: Any, *, now: datetime) -> None:
        """Record a dispatch outcome: what was written, what was refused, and why.

        A refused setpoint is reported as a *flag*, not as a zero metric — a
        rejection is information about the control path, and writing 0.0 would
        look like a measurement of no power.
        """
        report = getattr(outcome, "report", None)
        applied = 0 if report is None else int(getattr(report, "applied", 0))
        self.observe(Sample("dispatch.applied", float(applied), quality="estimated", source="gateway"))
        if report is None:
            self.flags.append(f"dispatch:{getattr(outcome, 'action', 'unknown')}")
            return
        for result in report.results:
            metric = f"{result.element_id}.{result.capability}.effective"
            if result.ok and isinstance(result.effective_value, (int, float)):
                self.samples.append(Sample(metric, float(result.effective_value), quality="estimated", source="gateway"))
            else:
                self.flags.append(f"rejected:{result.element_id}.{result.capability}:{result.reason}")
        if getattr(outcome, "action", "") == "failed_safe":
            self.flags.append("dispatch:fail_safe")

    def observe_readback(self, readback: Mapping[str, Mapping[str, float]], *, authority: str = "full") -> None:
        """Record what the devices actually report (measured, never estimated)."""
        for element_id, capabilities in readback.items():
            for capability, value in capabilities.items():
                if not isinstance(value, (int, float)):
                    continue
                self.samples.append(
                    Sample(f"{element_id}.{capability}.readback", float(value), quality="measured", source="gateway", authority=authority)
                )

    def build(self, *, now: datetime) -> list[dict[str, Any]]:
        """Render one envelope per (quality, source, authority) group, then reset."""
        if self.started_at is None:
            self.started_at = now - self.interval
        groups: dict[tuple[str, str, str], dict[str, float]] = {}
        for sample in self.samples:
            bucket = groups.setdefault(sample.key(), {})
            # Last writer wins per metric: a later read-back supersedes an earlier
            # one within the same interval, and grouping keeps qualities apart.
            bucket[sample.metric] = sample.value

        payloads: list[dict[str, Any]] = []
        for (quality, source, authority), metrics in sorted(groups.items()):
            payloads.append(
                {
                    "schema_version": TELEMETRY_SCHEMA_VERSION,
                    "site_id": self.site_id,
                    "deployment_profile": self.deployment_profile,
                    "seq": self.seq,
                    "captured_at": _iso(now),
                    "interval": {"start": _iso(self.started_at), "end": _iso(now)},
                    "authority": authority,
                    "quality": quality,
                    "source": source,
                    "metrics": metrics,
                    "plan": self.plan_record or {},
                    "flags": sorted(set(self.flags)),
                }
            )
            self.seq += 1
        self.samples.clear()
        self.plan_record = None
        self.flags.clear()
        self.started_at = now
        return payloads
