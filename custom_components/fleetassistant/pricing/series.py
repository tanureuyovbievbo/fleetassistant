"""Time series helpers for optimizer inputs (pure Python)."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

#: HAEO reads forecast-style sensors whose ``forecast`` attribute lists points
#: with a boundary time and a value (brief). The exact key names and the
#: attribute shape are UNVERIFIED until the e04 spike (OQ-007). Kept in one
#: place so the spike changes one function.
FORECAST_FORMAT_VERIFIED = False


@dataclass(frozen=True, order=True)
class Point:
    ts: datetime
    value: float

    def __post_init__(self) -> None:
        if self.ts.tzinfo is None:
            raise ValueError("series points must be timezone-aware")

    def as_forecast_item(self) -> dict[str, str | float]:
        return {"datetime": self.ts.astimezone(UTC).isoformat(), "value": self.value}


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
