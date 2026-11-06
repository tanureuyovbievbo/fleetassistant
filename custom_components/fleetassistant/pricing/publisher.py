"""Render a merged tariff into the state and attributes HAEO reads.

HAEO consumes a forecast sensor: a ``forecast`` attribute listing period
boundaries (``{"time": iso, "value": number}`` — F-016) plus the current value.
Everything else we attach (source, quality, divergences) is for humans, the
telemetry record and repairs; HAEO ignores unknown attributes, so provenance can
ride along without touching the value it optimises against.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..haeo_bridge import contracts
from .series import forecast_item
from .sources import MergedTariff


def current_price(merged: MergedTariff, now: datetime) -> float | None:
    """Hold-last: the newest period at or before ``now``, else the first period."""
    if not merged.points:
        return None
    earlier = [point for point in merged.points if point.ts <= now]
    if earlier:
        return earlier[-1].value
    return merged.points[0].value


def price_attributes(
    merged: MergedTariff,
    *,
    now: datetime | None = None,
    boundary_key: str = contracts.FORECAST_BOUNDARY_KEY,
    limit: int | None = None,
) -> dict[str, Any]:
    """Attributes for the published price sensor."""
    points = merged.points if limit is None else merged.points[:limit]
    forecast = [forecast_item(point.ts, point.value, boundary_key) for point in points]
    attributes: dict[str, Any] = {
        contracts.FORECAST_ATTRIBUTE: forecast,
        "forecast_format_verified": False,  # OQ-007: the price attribute name is unconfirmed
        "price_authority": merged.authority,
        "price_source": current_source(merged, now),
        "provenance": merged.provenance,
        "degraded_periods": len(merged.stale),
        "fallback_periods": len(merged.fallbacks),
        "missing_periods": len(merged.missing),
        "divergences": [
            {
                "period": item.ts.isoformat(),
                "cloud": item.cloud,
                "user": item.user,
                "applied": item.chosen,
                "chosen_source": item.source,
            }
            for item in merged.divergences[:10]
        ],
        "warning": " | ".join(merged.warnings) if merged.warnings else None,
    }
    return attributes


def current_source(merged: MergedTariff, now: datetime | None) -> str | None:
    """Name of the source that supplied the period in force."""
    if now is None or not merged.points:
        return merged.points[0].source if merged.points else None
    earlier = [point for point in merged.points if point.ts <= now]
    chosen = earlier[-1] if earlier else merged.points[0]
    return chosen.source
