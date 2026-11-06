"""Fleet allocation: from per-site marginal costs to one aggregate dispatch (D09).

The site optimizer (HAEO) already knows what an extra kilowatt costs at each site
right now — that is what its shadow prices are. The fleet layer's job is the other
direction: given an aggregate target and a set of sites with different costs,
availability, comfort floors and battery-life caps, decide how many kilowatts each
site delivers.

Two traps this module refuses:

* **Simultaneity.** Site A's 10 kW and site B's 10 kW are not 20 kW of firm
  capacity unless their availability windows overlap and they are not the same
  physical feeder. ``simultaneous_capacity`` multiplies by a declared
  ``simultaneity_factor`` and sweeps windows rather than summing nameplates.
* **Fairness by accident.** Sorting by marginal cost alone sends every event to the
  cheapest site until it hits its cap, which is efficient and politically fatal
  (one household cycling its battery 4× per day). ``Allocator`` supports a
  per-site share cap and a round-robin fallback among equal-cost sites.

Deliberately dependency-free (C-08): the merit-order stack is a sort plus a loop,
not an LP. A real LP would be better at coupled constraints (shared feeder limits,
ramp coupling); when that is needed it is a new ADR with a solver dependency, not a
quiet import.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

RejectReason = Literal["unavailable", "opted_out", "comfort_floor", "battery_cap", "share_cap", "no_capacity"]


@dataclass(frozen=True)
class SiteOffer:
    """What one site can offer right now, and at what cost.

    All power values are kW; ``marginal_cost`` is currency per kWh, taken from the
    site's own shadow price so the fleet never has to model the site's physics.
    """

    site_id: str
    capacity_kw: float
    marginal_cost: float
    available: bool = True
    opted_out: bool = False
    #: Power the site must retain for its own comfort/safety load. Subtracted from
    #: ``capacity_kw`` before allocation, never allocated away.
    reserve_kw: float = 0.0
    #: Battery-life cap: maximum kW this site may deliver for *this* event, which may
    #: be lower than its instantaneous capability.
    battery_life_cap_kw: float | None = None
    #: Share of the aggregate this site may take (0..1). ``None`` means uncapped.
    share_cap: float | None = None

    def __post_init__(self) -> None:
        if self.capacity_kw < 0:
            raise ValueError(f"{self.site_id}: capacity_kw must be >= 0")
        if self.reserve_kw < 0:
            raise ValueError(f"{self.site_id}: reserve_kw must be >= 0")
        if self.battery_life_cap_kw is not None and self.battery_life_cap_kw < 0:
            raise ValueError(f"{self.site_id}: battery_life_cap_kw must be >= 0")
        if self.share_cap is not None and not 0.0 <= self.share_cap <= 1.0:
            raise ValueError(f"{self.site_id}: share_cap must be within 0..1")

    @property
    def offered_kw(self) -> float:
        """Usable kW after reserve and the battery-life cap."""
        usable = max(0.0, self.capacity_kw - self.reserve_kw)
        if self.battery_life_cap_kw is not None:
            usable = min(usable, self.battery_life_cap_kw)
        return usable

    def ineligible(self) -> RejectReason | None:
        if not self.available:
            return "unavailable"
        if self.opted_out:
            return "opted_out"
        if self.offered_kw <= 0:
            return "comfort_floor"
        return None


@dataclass(frozen=True)
class Allocated:
    site_id: str
    kw: float
    marginal_cost: float


@dataclass(frozen=True)
class Rejected:
    site_id: str
    reason: RejectReason
    detail: str = ""


@dataclass(frozen=True)
class Allocation:
    """The result of one allocation pass."""

    target_kw: float
    allocations: tuple[Allocated, ...]
    rejected: tuple[Rejected, ...] = ()
    #: Where the target sits on the fleet's marginal-cost curve (the cost of the
    #: last kilowatt actually bought). ``None`` when nothing was allocated.
    clearing_cost: float | None = None

    @property
    def allocated_kw(self) -> float:
        return sum(item.kw for item in self.allocations)

    @property
    def shortfall_kw(self) -> float:
        return max(0.0, self.target_kw - self.allocated_kw)

    @property
    def full(self) -> bool:
        return self.shortfall_kw <= 1e-9

    def by_site(self) -> dict[str, float]:
        return {item.site_id: item.kw for item in self.allocations}

    def as_dict(self) -> dict[str, object]:
        return {
            "target_kw": round(self.target_kw, 6),
            "allocated_kw": round(self.allocated_kw, 6),
            "shortfall_kw": round(self.shortfall_kw, 6),
            "clearing_cost": self.clearing_cost,
            "allocations": [
                {"site_id": item.site_id, "kw": round(item.kw, 6), "marginal_cost": item.marginal_cost}
                for item in self.allocations
            ],
            "rejected": [{"site_id": item.site_id, "reason": item.reason, "detail": item.detail} for item in self.rejected],
        }


@dataclass
class Allocator:
    """Merit-order allocation with fairness caps.

    ``share_cap`` applies to sites that do not declare their own; the second pass
    hands out any remaining target to capped sites in cost order, so a cap slows a
    site down instead of freezing the event.
    """

    share_cap: float | None = None
    #: Tolerance for floating-point comparisons when a cap lands exactly on a target.
    epsilon: float = 1e-9
    log: list[str] = field(default_factory=list)

    def allocate(self, target_kw: float, offers: Sequence[SiteOffer]) -> Allocation:
        if target_kw < 0:
            raise ValueError("target_kw must be >= 0")

        eligible: list[SiteOffer] = []
        rejected: list[Rejected] = []
        for offer in offers:
            reason = offer.ineligible()
            if reason is not None:
                rejected.append(Rejected(offer.site_id, reason, f"offered {offer.offered_kw:.3f} kW"))
            else:
                eligible.append(offer)

        eligible.sort(key=lambda offer: (offer.marginal_cost, offer.site_id))
        caps = {offer.site_id: self._cap_for(offer, target_kw) for offer in eligible}
        awarded: dict[str, float] = {offer.site_id: 0.0 for offer in eligible}
        remaining = target_kw

        # Pass 1: merit order, up to each site's effective cap.
        for offer in eligible:
            if remaining <= self.epsilon:
                break
            room = min(offer.offered_kw, caps[offer.site_id]) - awarded[offer.site_id]
            take = min(room, remaining)
            if take <= self.epsilon:
                continue
            awarded[offer.site_id] += take
            remaining -= take

        # Pass 2: fairness caps bound strict merit order, so a site that hit its cap
        # while cheaper sites were exhausted may take the remainder if it can.
        if remaining > self.epsilon:
            for offer in eligible:
                if remaining <= self.epsilon:
                    break
                room = offer.offered_kw - awarded[offer.site_id]
                take = min(room, remaining)
                if take <= self.epsilon:
                    continue
                awarded[offer.site_id] += take
                remaining -= take

        allocations = tuple(
            Allocated(offer.site_id, awarded[offer.site_id], offer.marginal_cost)
            for offer in eligible
            if awarded[offer.site_id] > self.epsilon
        )
        clearing = max((item.marginal_cost for item in allocations), default=None)
        self.log.append(
            f"target={target_kw:.3f}kW allocated={sum(a.kw for a in allocations):.3f}kW sites={len(allocations)}"
        )
        return Allocation(target_kw=target_kw, allocations=allocations, rejected=tuple(rejected), clearing_cost=clearing)

    def _cap_for(self, offer: SiteOffer, target_kw: float) -> float:
        cap = offer.share_cap if offer.share_cap is not None else self.share_cap
        if cap is None:
            return float("inf")
        # A share cap is a share of the *target*, not of the site's nameplate: capping
        # a share of capacity leaves a big site holding the same share of a small event,
        # which is the opposite of spreading it.
        return cap * max(0.0, target_kw)


def simultaneity_factor(windows: Sequence[tuple[datetime, datetime]]) -> float:
    """Share of the union of availability windows covered by every window.

    A site available 08:00–12:00 and another 10:00–14:00 overlap for two of six
    hours; treating their nameplates as simultaneous capacity would overstate the
    fleet by 3×. Returns 0.0 for an empty set.
    """
    if not windows:
        return 0.0
    union_start = min(start for start, _ in windows)
    union_end = max(end for _, end in windows)
    if union_end <= union_start:
        return 0.0
    boundaries = sorted({start for start, _ in windows} | {end for _, end in windows})
    covered = 0.0
    for left, right in zip(boundaries, boundaries[1:], strict=False):
        if right <= left:
            continue
        if all(start <= left and end >= right for start, end in windows):
            covered += (right - left).total_seconds()
    return covered / (union_end - union_start).total_seconds()


def simultaneous_capacity(offers: Sequence[SiteOffer], windows: Sequence[tuple[datetime, datetime]]) -> float:
    """Nameplate capacity discounted by the fraction of time it is truly simultaneous."""
    return sum(offer.offered_kw for offer in offers) * simultaneity_factor(windows)


def dispatch_delta(
    allocation: Allocation,
    previous: dict[str, float],
    *,
    hysteresis_kw: float = 0.25,
) -> dict[str, float]:
    """Only tell a site what actually changed.

    Sending a site its unchanged setpoint every event cycle wastes a write, trips
    rate limits, and makes the audit log unreadable. Values that moved less than
    ``hysteresis_kw`` are omitted; sites that were delivering and are now zero are
    sent an explicit ``0.0`` so the site never keeps delivering on a dropped message.
    """
    delta: dict[str, float] = {}
    for site_id, kw in allocation.by_site().items():
        before = previous.get(site_id, 0.0)
        if abs(kw - before) >= hysteresis_kw:
            delta[site_id] = kw
    for site_id, before in previous.items():
        if before > 0 and site_id not in allocation.by_site():
            delta[site_id] = 0.0
    return delta


def feedback_trim(
    measured_kw: float,
    target_kw: float,
    *,
    gain: float = 0.5,
    deadband_kw: float = 0.2,
) -> float:
    """Proportional trim for the aggregate error (sites under-deliver in reality).

    Returns the *extra* kW to request next pass. Bounded by design: a single pass
    may not add more than the error it saw, or a noisy meter oscillates the fleet.
    """
    error = target_kw - measured_kw
    if abs(error) < deadband_kw:
        return 0.0
    return error * gain if error > 0 else error


def window_start(now: datetime) -> datetime:
    """Normalise to UTC so window math never compares naive and aware stamps."""
    return now.astimezone(UTC)
