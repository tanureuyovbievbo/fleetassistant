"""Generic target/incentive overlay (C-13).

A target overlay is deliberately region-free: a time window, an optional price
delta, an optional kW target, and a label. California event programs (ELRP,
DRIP, BatteryVPP) become rule packs that emit these overlays — the core never
learns what a program is.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .series import Point


@dataclass(frozen=True)
class TargetOverlay:
    label: str
    start: datetime
    end: datetime
    price_delta_per_kwh: float = 0.0
    target_kw: float | None = None
    element: str | None = None
    provenance: str = "site"

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError("overlay end must be after start")

    def covers(self, ts: datetime) -> bool:
        return self.start <= ts < self.end

    def adjust(self, point: Point) -> Point:
        if self.covers(point.ts):
            return Point(point.ts, point.value + self.price_delta_per_kwh)
        return point


def apply_overlays(points: list[Point], overlays: list[TargetOverlay]) -> list[Point]:
    if not overlays:
        return list(points)
    adjusted: list[Point] = []
    for point in points:
        value = point.value
        for overlay in overlays:
            if overlay.covers(point.ts):
                value += overlay.price_delta_per_kwh
        adjusted.append(Point(point.ts, value))
    return adjusted


def overlay_windows(overlays: list[TargetOverlay]) -> list[dict[str, object]]:
    """Machine-readable windows handed to HAEO as incentive constraints."""
    return [
        {
            "label": o.label,
            "start": o.start.isoformat(),
            "end": o.end.isoformat(),
            "target_kw": o.target_kw,
            "element": o.element,
            "provenance": o.provenance,
        }
        for o in overlays
    ]
