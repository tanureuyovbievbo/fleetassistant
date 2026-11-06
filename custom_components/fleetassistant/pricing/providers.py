"""Rate providers: flat, TOU block schedules, dynamic series (C-13).

v1 ships these three. Regional tariffs, export curves, event targets and
regulatory constraints arrive later as rule packs (D10) — never as core code.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any, Protocol, runtime_checkable

from .series import Point

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


class PriceProviderError(ValueError):
    """Raised when a provider definition is unusable."""


@runtime_checkable
class RateProvider(Protocol):
    name: str

    def price_at(self, ts: datetime) -> float:
        """Import price in site currency per kWh at ``ts``."""


@dataclass(frozen=True)
class FlatRate:
    currency_per_kwh: float
    name: str = "flat"

    def price_at(self, ts: datetime) -> float:  # noqa: ARG002 - constant by design
        return float(self.currency_per_kwh)


@dataclass(frozen=True)
class TouBlock:
    start: str
    end: str
    price: float
    days: tuple[str, ...] = WEEKDAYS
    label: str = ""

    def __post_init__(self) -> None:
        _parse_clock(self.start)
        _parse_clock(self.end)
        for day in self.days:
            if day not in WEEKDAYS:
                raise PriceProviderError(f"unknown day {day!r}")

    def contains(self, ts: datetime) -> bool:
        if ts.strftime("%a").lower()[:3] not in self.days:
            return False
        start = _parse_clock(self.start)
        end = _parse_clock(self.end)
        clock = ts.time().replace(tzinfo=None)
        if start <= end:
            return start <= clock < end
        # Overnight block, e.g. 21:00-06:00 (also matches the next morning).
        return clock >= start or clock < end


def _parse_clock(value: str) -> time:
    try:
        hours, minutes = value.split(":")
        parsed = time(int(hours), int(minutes))
    except (ValueError, AttributeError) as exc:
        raise PriceProviderError(f"invalid HH:MM clock value {value!r}") from exc
    if not (0 <= parsed.hour <= 23 and 0 <= parsed.minute <= 59):
        raise PriceProviderError(f"invalid HH:MM clock value {value!r}")
    return parsed


@dataclass(frozen=True)
class TouSchedule:
    """Block schedule. First matching block wins; ``fallback`` covers the rest."""

    blocks: tuple[TouBlock, ...]
    fallback: float
    name: str = "tou"

    def price_at(self, ts: datetime) -> float:
        for block in self.blocks:
            if block.contains(ts):
                return block.price
        return float(self.fallback)

    def describe(self) -> list[dict[str, Any]]:
        return [
            {"start": b.start, "end": b.end, "days": list(b.days), "price": b.price, "label": b.label}
            for b in self.blocks
        ]


@dataclass(frozen=True)
class DynamicSeries:
    """Price points from a feed (Nord Pool, Tibber, Octopus, EPEX, ...).

    Hold-last-value before the first point and after the last, so a partial
    horizon degrades predictably instead of silently dropping periods.
    """

    points: tuple[Point, ...]
    name: str = "dynamic"
    fallback: float = 0.0

    def __post_init__(self) -> None:
        if not self.points:
            raise PriceProviderError("dynamic provider needs at least one point")

    def price_at(self, ts: datetime) -> float:
        ordered = sorted(self.points)
        value = self.fallback
        for point in ordered:
            if point.ts <= ts:
                value = point.value
            else:
                break
        return value

    @property
    def coverage(self) -> tuple[datetime, datetime]:
        ordered = sorted(self.points)
        return ordered[0].ts, ordered[-1].ts


def provider_from_profile(definition: dict[str, Any]) -> RateProvider:
    """Build a provider from a profile ``pricing.provider`` block."""
    kind = definition.get("type")
    if kind == "flat":
        return FlatRate(float(definition["currency_per_kwh"]))
    if kind == "tou":
        blocks = tuple(
            TouBlock(
                start=b["start"],
                end=b["end"],
                price=float(b["price"]),
                days=tuple(b.get("days", WEEKDAYS)),
                label=b.get("label", ""),
            )
            for b in definition.get("blocks", [])
        )
        if not blocks:
            raise PriceProviderError("tou provider needs at least one block")
        return TouSchedule(blocks=blocks, fallback=float(definition.get("fallback", 0.0)))
    if kind == "dynamic":
        points = tuple(Point(ts=_require_ts(p["datetime"]), value=float(p["value"])) for p in definition.get("series", []))
        return DynamicSeries(points=points, fallback=float(definition.get("fallback", 0.0)))
    raise PriceProviderError(f"unsupported provider type {kind!r}")


def _require_ts(value: Any) -> datetime:
    if not isinstance(value, str):
        raise PriceProviderError("series point datetime must be a string")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass
class ExportValueCurve:
    """Simple export compensation model.

    A full NEM 3.0-style curve belongs in a rule pack (D10). This class only
    supports a fixed value plus an optional per-hour multiplier list so v1 can
    represent 'export is worth less at noon' without regional logic.
    """

    currency_per_kwh: float = 0.0
    hour_multipliers: Sequence[float] = field(default_factory=tuple)
    name: str = "export_flat"

    def value_at(self, ts: datetime) -> float:
        if not self.hour_multipliers:
            return float(self.currency_per_kwh)
        return float(self.currency_per_kwh) * float(self.hour_multipliers[ts.hour % len(self.hour_multipliers)])
