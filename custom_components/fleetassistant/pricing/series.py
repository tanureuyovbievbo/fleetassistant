"""Time series helpers for optimizer inputs (pure Python)."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

#: HAEO reads forecast-style sensors whose ``forecast`` attribute lists points
#: with a boundary time and a value. The boundary key is ``time`` at HAEO v0.5.0
#: (source-verified, ``core/data/forecast_times.py``); what a *price* or *load*
#: input sensor is expected to look like is still unconfirmed against a live
#: instance (OQ-007), so this flag stays False.
FORECAST_FORMAT_VERIFIED = False


def _contracts():
    """Import the HAEO contract lazily.

    ``haeo_bridge.plan`` imports this package, so a module-level import here
    would close an import cycle that only resolves by luck of import order.
    """
    from ..haeo_bridge import contracts

    return contracts


def forecast_item(ts: datetime, value: float, boundary_key: str | None = None) -> dict[str, str | float]:
    """Return one ``forecast`` attribute point.

    Home Assistant's own forecast convention names the boundary ``datetime``,
    while HAEO reads ``time``. The key is a parameter so a caller can publish to
    either consumer without a second code path.
    """
    contracts = _contracts()
    key = boundary_key or contracts.FORECAST_BOUNDARY_KEY
    return {key: ts.astimezone(UTC).isoformat(), contracts.FORECAST_VALUE_KEY: float(value)}


@dataclass(frozen=True, order=True)
class Point:
    ts: datetime
    value: float

    def __post_init__(self) -> None:
        if self.ts.tzinfo is None:
            raise ValueError("series points must be timezone-aware")

    def as_forecast_item(self, boundary_key: str | None = None) -> dict[str, str | float]:
        return forecast_item(self.ts, self.value, boundary_key)


def floor_to(ts: datetime, step_minutes: int) -> datetime:
    if step_minutes <= 0:
        raise ValueError("step_minutes must be positive")
    epoch = ts.astimezone(UTC).timestamp()
    floored = epoch - (epoch % (step_minutes * 60))
    return datetime.fromtimestamp(floored, tz=UTC)


def build_series(
    start: datetime,
    hours: float,
    step_minutes: int,
    value_at: Callable[[datetime], float],
) -> list[Point]:
    """Sample ``value_at`` on the step grid, starting at ``start``."""
    if hours <= 0:
        raise ValueError("hours must be positive")
    count = int(round(hours * 60 / step_minutes))
    return [
        Point(start + timedelta(minutes=step_minutes * i), float(value_at(start + timedelta(minutes=step_minutes * i))))
        for i in range(count + 1)
    ]


def resample_hold(points: Sequence[Point], start: datetime, end: datetime, step_minutes: int) -> list[Point]:
    """Step-hold resample: each output point takes the last known value."""
    if not points:
        return []
    ordered = sorted(points)
    out: list[Point] = []
    cursor = start
    index = 0
    last = ordered[0].value
    while cursor <= end:
        while index < len(ordered) and ordered[index].ts <= cursor:
            last = ordered[index].value
            index += 1
        out.append(Point(cursor, last))
        cursor += timedelta(minutes=step_minutes)
    return out


def to_forecast(points: Iterable[Point]) -> dict[str, object]:
    """Serialize points into the payload shape a forecast sensor attribute needs."""
    return {
        "forecast": [point.as_forecast_item() for point in points],
        "format_verified": FORECAST_FORMAT_VERIFIED,
        "count": len(list(points)) if not isinstance(points, (list, tuple)) else len(points),
    }


def flatten(points: Iterable[Point]) -> list[tuple[str, float]]:
    return [(p.ts.isoformat(), p.value) for p in points]
