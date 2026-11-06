"""The published price sensors: what HAEO reads, and what we say about it."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from helpers import example

from custom_components.fleetassistant.pricing.compiler import (
    INPUT_NAMES,
    price_authority,
    resolve_tariffs,
)
from custom_components.fleetassistant.pricing.publisher import (
    current_price,
    current_source,
    price_attributes,
)
from custom_components.fleetassistant.pricing.sources import QuotedPoint, SeriesResult, merge_tariffs
from custom_components.fleetassistant.site import default_profile

START = datetime(2026, 11, 6, 0, tzinfo=UTC)


def _merged(cloud_prices: list[float] | None = None, authority: str = "cloud"):
    user = SeriesResult(
        source="user_flat",
        quality="entered",
        points=tuple(
            QuotedPoint(ts=START + timedelta(hours=index), value=0.30, source="user_flat", quality="entered")
            for index in range(4)
        ),
    )
    cloud = None
    if cloud_prices is not None:
        cloud = SeriesResult(
            source="vendor",
            quality="quoted",
            points=tuple(
                QuotedPoint(ts=START + timedelta(hours=index), value=value, source="vendor", quality="quoted")
                for index, value in enumerate(cloud_prices)
            ),
            fetched_at=START,
            expires_at=START + timedelta(hours=6),
        )
    return merge_tariffs(site_id="home", cloud=cloud, user=user, authority=authority, now=START)


def test_forecast_attribute_is_the_haeo_shape() -> None:
    attributes = price_attributes(_merged([0.5, 0.5, 0.5, 0.5]), now=START)
    forecast = attributes["forecast"]
    assert isinstance(forecast, list) and len(forecast) == 4
    assert set(forecast[0]) == {"time", "value"}
    assert forecast[0]["value"] == 0.5
    assert attributes["forecast_format_verified"] is False  # OQ-007 still open


def test_provenance_and_divergence_travel_in_attributes() -> None:
    attributes = price_attributes(_merged([0.5, 0.5, 0.5, 0.5], authority="user"), now=START)
    assert attributes["price_authority"] == "user"
    assert attributes["price_source"] == "user_flat"
    assert attributes["provenance"] == {"user_flat": 4}
    divergences = attributes["divergences"]
    assert len(divergences) == 4
    assert divergences[0]["cloud"] == 0.5
    assert divergences[0]["applied"] == 0.3
    assert "disagree" in str(attributes["warning"])


def test_attributes_truncate_for_state_size() -> None:
    attributes = price_attributes(_merged(), limit=2)
    assert len(attributes["forecast"]) == 2


def test_current_price_holds_the_last_period() -> None:
    merged = _merged()
    assert current_price(merged, START + timedelta(minutes=30)) == 0.30
    assert current_price(merged, START + timedelta(hours=2, minutes=59)) == 0.30
    assert current_source(merged, START + timedelta(minutes=30)) == "user_flat"


def test_current_price_before_the_first_period_uses_the_first() -> None:
    merged = _merged()
    assert current_price(merged, START - timedelta(hours=1)) == 0.30
    assert current_source(merged, START - timedelta(hours=1)) == "user_flat"


def test_an_empty_series_has_no_price() -> None:
    merged = merge_tariffs(site_id="home", authority="user", now=START)
    assert current_price(merged, START) is None
    assert current_source(merged, START) is None


def test_default_profile_resolves_both_price_inputs() -> None:
    profile = default_profile("demo", "Demo", "gateway_primary")
    tariffs = resolve_tariffs(profile, {}, now=START)

    assert set(tariffs) == {INPUT_NAMES["import"], INPUT_NAMES["export"]}
    import_tariff = tariffs[INPUT_NAMES["import"]]
    assert import_tariff.authority == "user"
    assert import_tariff.points  # the flat provider always prices
    export_tariff = tariffs[INPUT_NAMES["export"]]
    assert export_tariff.value_at(START) == 0.0
    assert any("no export value" in warning for warning in export_tariff.warnings)


def test_authority_precedence_is_options_then_profile_then_deployment() -> None:
    cloud_profile = default_profile("demo", "Demo", "cloud_primary")
    assert price_authority(cloud_profile, {}) == "cloud"
    assert price_authority(cloud_profile, {"price_authority": "user"}) == "user"
    cloud_profile["pricing"]["authority"] = "user_unless_stale"
    assert price_authority(cloud_profile, {}) == "user_unless_stale"
    assert price_authority(cloud_profile, {"price_authority": "cloud"}) == "cloud"


def test_a_cloud_series_can_be_merged_into_the_published_prices() -> None:
    profile = default_profile("demo", "Demo", "cloud_primary")
    cloud = SeriesResult(
        source="vendor",
        quality="quoted",
        points=tuple(
            QuotedPoint(
                ts=START + timedelta(hours=index), value=0.42, source="vendor", quality="quoted"
            )
            for index in range(4)
        ),
        fetched_at=START,
        expires_at=START + timedelta(hours=6),
    )
    tariffs = resolve_tariffs(profile, {}, now=START, cloud=cloud)

    import_tariff = tariffs[INPUT_NAMES["import"]]
    assert import_tariff.provenance["vendor"] == 4
    assert import_tariff.points[0].value == 0.42
    assert import_tariff.points[0].source == "vendor"


def test_the_repo_example_publishes_prices_the_plan_references() -> None:
    profile = example("tesla_cloud_primary.yaml")
    tariffs = resolve_tariffs(profile, {}, now=START)
    import_tariff = tariffs[INPUT_NAMES["import"]]
    assert import_tariff.points
    assert import_tariff.authority in {"cloud", "user", "user_unless_stale"}
    assert import_tariff.degraded_share == 0.0
    assert import_tariff.points[0].value >= 0.0
