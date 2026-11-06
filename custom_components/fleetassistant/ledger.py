"""Per-site commitments ledger (C-16).

Program integrity is a data structure, not a policy memo: every kW committed to
a program is recorded here, and a new commitment that would push simultaneous
exposure past qualified capacity is rejected. That makes double counting
structurally impossible when rule packs arrive.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

Authority = Literal["coarse", "full"]


class LedgerError(ValueError):
    """Raised when a commitment is malformed or would over-commit the site."""


@dataclass(frozen=True)
class Commitment:
    commitment_id: str
    program_id: str
    start: datetime
    end: datetime
    kw: float
    authority: Authority
    tier: Literal["firm", "best_effort"] = "best_effort"
    #: The capability this commitment buys (``set_export_limit``, ``set_battery_target``).
    #: Two programs must never hold the same capability over the same window — that is
    #: the double-counting this ledger exists to prevent (C-16).
    capability: str = ""

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise LedgerError("commitment end must be after start")
        if self.kw <= 0:
            raise LedgerError("commitment kw must be positive")
        if self.tier == "firm" and self.authority != "full":
            raise LedgerError("firm commitments require full authority (C-12)")

    def overlap(self, other: Commitment) -> tuple[datetime, datetime] | None:
        start = max(self.start, other.start)
        end = min(self.end, other.end)
        return (start, end) if start < end else None


@dataclass
class CommitmentsLedger:
    """Sites can be over-committed across programs; that is what this prevents."""

    site_id: str
    qualified_capacity_kw: float
    commitments: list[Commitment] = field(default_factory=list)

    def add(self, commitment: Commitment) -> None:
        if any(c.commitment_id == commitment.commitment_id for c in self.commitments):
            raise LedgerError(f"commitment {commitment.commitment_id!r} already exists")
        window = self._peak_with(commitment)
        if window > self.qualified_capacity_kw + 1e-9:
            raise LedgerError(
                f"over-commitment: {window:.3f} kW simultaneous vs {self.qualified_capacity_kw:.3f} kW qualified"
            )
        self.commitments.append(commitment)

    def remove(self, commitment_id: str) -> Commitment:
        for index, commitment in enumerate(self.commitments):
            if commitment.commitment_id == commitment_id:
                return self.commitments.pop(index)
        raise LedgerError(f"unknown commitment {commitment_id!r}")

    def _peak_with(self, extra: Commitment) -> float:
        return max_exposure([*self.commitments, extra])

    def exposure(self, start: datetime, end: datetime) -> float:
        window = Commitment("window", "window", start, end, 1.0, "coarse")
        relevant = [c for c in self.commitments if c.overlap(window)]
        return max_exposure(relevant) if relevant else 0.0

    def committed_programs(self) -> set[str]:
        return {c.program_id for c in self.commitments}

    def conflicts(
        self,
        *,
        program_id: str,
        start: datetime,
        end: datetime,
        capability: str,
    ) -> list[Commitment]:
        """Commitments held by *another* program for the same capability and window.

        Empty means this program may dispatch that capability over that window.
        A non-empty result is a structural double-booking, not a judgment call:
        two programs paying for the same kilowatt is the failure mode C-16 names.
        """
        window = Commitment("window", "window", start, end, 1.0, "coarse", capability=capability)
        return [
            c
            for c in self.commitments
            if c.program_id != program_id
            and (not capability or c.capability == capability)
            and c.overlap(window) is not None
        ]

    def headroom(self, start: datetime, end: datetime) -> float:
        """Qualified capacity minus simultaneous exposure over the window."""
        return max(0.0, self.qualified_capacity_kw - self.exposure(start, end))

    def as_list(self) -> list[dict[str, object]]:
        return [
            {
                "commitment_id": c.commitment_id,
                "program_id": c.program_id,
                "start": c.start.astimezone(UTC).isoformat(),
                "end": c.end.astimezone(UTC).isoformat(),
                "kw": c.kw,
                "authority": c.authority,
                "tier": c.tier,
                "capability": c.capability,
            }
            for c in self.commitments
        ]


def max_exposure(commitments: Iterable[Commitment]) -> float:
    """Peak simultaneous kW across a set of commitments (sweep over boundaries)."""
    items = list(commitments)
    if not items:
        return 0.0
    points = sorted({c.start for c in items} | {c.end for c in items})
    peak = 0.0
    for point in points:
        total = sum(c.kw for c in items if c.start <= point < c.end)
        peak = max(peak, total)
    return peak
