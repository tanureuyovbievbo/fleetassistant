"""Dual-source tariffs: precedence, staleness, provenance (ADR-0019)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from custom_components.fleetassistant.pricing.providers import FlatRate
from custom_components.fleetassistant.pricing.sources import (
    CloudTariffSource,
    QuotedPoint,
    SeriesResult,
    merge_tariffs,
    series_from_provider,
)

START = datetime(2026, 11, 6, 0, tzinfo=UTC)


def _user(price: float = 0.30, hours: float = 3.0, name: str = "user_flat") -> SeriesResult:
    return series_from_provider(
        FlatRate(price, name=name), start=START, end=START + timedelta(hours=hours), step_minutes=60
    )


def _cloud(
    values: list[float],
    *,
    hours_offset: int = 0,
    expires_at: datetime | None = None,
    quality: str = "quoted",
) -> SeriesResult:
    points = tuple(
        QuotedPoint(ts=START + timedelta(hours=hours_offset + index), value=value, source="vendor", quality=quality)
        for index, value in enumerate(values)
    )
    return SeriesResult(
        source="vendor",
        quality=quality,
        points=points,
        fetched_at=START,
        expires_at=expires_at,
    )


def test_a_user_schedule_is_always_fresh() -> None:
    assert _user().is_fresh(START + timedelta(days=365)) is True


def test_cloud_authority_wins_where_it_has_a_price() -> None:
    merged = merge_tariffs(
        site_id="home",
        cloud=_cloud([0.50, 0.55]),
        user=_user(0.30),
        authority="cloud",
        now=START,
    )
    assert [point.source for point in merged.points] == ["vendor", "vendor", "user_flat", "user_flat"]
    assert merged.provenance == {"vendor": 2, "user_flat": 2}
    assert len(merged.fallbacks) == 2


def test_user_authority_wins_and_cloud_fills_the_gaps() -> None:
    merged = merge_tariffs(
        site_id="home",
        cloud=_cloud([0.50], hours_offset=3),
        user=_user(0.30, hours=2),  # prices hours 0..2 only
        authority="user",
        now=START,
    )
    assert merged.points[-1].source == "vendor"
    assert merged.points[0].source == "user_flat"
    assert merged.fallbacks == (START + timedelta(hours=3),)


def test_a_stale_cloud_loses_to_a_fresh_user_schedule() -> None:
    merged = merge_tariffs(
        site_id="home",
        cloud=_cloud([0.10, 0.10, 0.10, 0.10], expires_at=START - timedelta(minutes=1)),
        user=_user(0.30),
        authority="cloud",
        now=START,
    )
    assert {point.source for point in merged.points} == {"user_flat"}
    assert merged.stale == ()
    assert any("fell back" in warning for warning in merged.warnings)


def test_a_stale_cloud_is_still_used_when_nothing_else_prices_the_period() -> None:
    merged = merge_tariffs(
        site_id="home",
        cloud=_cloud([0.10, 0.10], expires_at=START - timedelta(hours=1)),
        user=None,
        authority="cloud",
        now=START,
    )
    assert [point.quality for point in merged.points] == ["stale", "stale"]
    assert len(merged.stale) == 2
    assert merged.degraded_share == 1.0
    assert any("stale cloud quote" in warning for warning in merged.warnings)


def test_divergence_is_recorded_with_the_applied_source() -> None:
    merged = merge_tariffs(
        site_id="home",
        cloud=_cloud([0.50, 0.50, 0.50, 0.50]),
        user=_user(0.30),
        authority="user",
        now=START,
    )
    assert len(merged.divergences) == 4
    first = merged.divergences[0]
    assert first.cloud == 0.50
    assert first.user == 0.30
    assert first.chosen == 0.30
    assert first.source == "user_flat"
    assert pytest.approx(first.delta) == 0.20
    assert any("disagree" in warning for warning in merged.warnings)


def test_rounding_inside_the_tolerance_is_not_a_divergence() -> None:
    merged = merge_tariffs(
        site_id="home",
        cloud=_cloud([0.3001, 0.3001, 0.3001, 0.3001]),
        user=_user(0.30),
        authority="cloud",
        now=START,
    )
    assert merged.divergences == ()


def test_an_unknown_authority_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown price authority"):
        merge_tariffs(site_id="home", user=_user(), authority="cheapest")


def test_no_prices_is_a_loud_warning_not_an_empty_plan() -> None:
    merged = merge_tariffs(site_id="home", cloud=None, user=None, authority="user", now=START)
    assert merged.points == ()
    assert merged.degraded_share == 1.0
    assert any("C-23" in warning for warning in merged.warnings)


def test_missing_periods_are_counted() -> None:
    merged = merge_tariffs(
        site_id="home",
        cloud=_cloud([0.4], hours_offset=10),
        user=_user(0.30),
        authority="user",
        now=START,
    )
    assert merged.missing == ()
    assert merged.points[-1].ts == START + timedelta(hours=10)


def test_cloud_source_caches_within_its_ttl() -> None:
    calls: list[tuple[datetime, datetime]] = []

    async def fetcher(start: datetime, end: datetime) -> list[tuple[datetime, float]]:
        calls.append((start, end))
        return [(START + timedelta(hours=index), 0.40) for index in range(4)]

    source = CloudTariffSource(name="vendor", fetcher=fetcher, ttl=timedelta(hours=6))
    window = {"start": START, "end": START + timedelta(hours=3)}

    first = asyncio.run(source.async_resolve(now=START, **window))
    again = asyncio.run(source.async_resolve(now=START + timedelta(hours=1), **window))
    later = asyncio.run(source.async_resolve(now=START + timedelta(hours=7), **window))

    assert first is not None and again is not None and later is not None
    assert len(calls) == 2  # the TTL lapsed once
    assert source.requests == 2  # quota accounting for C-22
    assert later.quality == "quoted"


def test_a_lapsed_cache_is_viewed_as_stale() -> None:
    source = CloudTariffSource(name="vendor", ttl=timedelta(hours=1))
    source.cache = _cloud([0.40, 0.40], expires_at=START + timedelta(hours=1))

    fresh = source.stale_view(now=START)
    lapsed = source.stale_view(now=START + timedelta(hours=2))

    assert fresh is not None and fresh.quality == "quoted"
    assert lapsed is not None and lapsed.quality == "stale"
    assert [point.quality for point in lapsed.points] == ["stale", "stale"]


def test_a_cloud_source_without_a_fetcher_returns_its_cache() -> None:
    source = CloudTariffSource(name="vendor")
    assert asyncio.run(source.async_resolve(start=START, end=START, now=START)) is None

    source.cache = _cloud([0.40, 0.40])
    resolved = asyncio.run(source.async_resolve(start=START, end=START, now=START))
    assert resolved is not None and resolved.quality == "quoted"
