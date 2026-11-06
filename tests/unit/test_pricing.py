"""T-22..T-25: generic price/target model (C-13, C-14)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from helpers import example

from custom_components.fleetassistant.pricing import (
    DynamicSeries,
    FlatRate,
    Point,
    TargetOverlay,
    TouBlock,
    TouSchedule,
    compile_price_inputs,
    provider_from_profile,
)

START = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)


def _at(hour: int, minute: int = 0) -> datetime:
    return START + timedelta(hours=hour, minutes=minute)


def test_tou_block_wraps_overnight() -> None:
    block = TouBlock(start="21:00", end="06:00", price=0.2)
    assert block.contains(_at(23))
    assert block.contains(_at(5))
    assert not block.contains(_at(12))


def test_tou_weekday_restriction() -> None:
    # 2026-06-01 is a Monday.
    block = TouBlock(start="21:00", end="06:00", price=0.2, days=("mon",))
    assert block.contains(_at(23))
    assert not block.contains(_at(24 * 5))  # Saturday


def test_profile_provider_is_resolved_from_the_profile() -> None:
    provider = provider_from_profile(example("tesla_cloud_primary.yaml")["pricing"]["provider"])
    assert isinstance(provider, TouSchedule)
    assert provider.price_at(_at(17)) == 0.52
    assert provider.price_at(_at(12)) == 0.38


def test_dynamic_series_holds_last_value() -> None:
    series = DynamicSeries(points=(Point(_at(0), 0.1), Point(_at(1), 0.2)))
    assert series.price_at(_at(2)) == 0.2
    assert series.price_at(_at(0, 30)) == 0.1

    early = DynamicSeries(points=(Point(_at(3), 0.4),), fallback=0.05)
    assert early.price_at(_at(0)) == 0.05


def test_flat_rate_is_constant() -> None:
    assert FlatRate(0.31).price_at(_at(7)) == 0.31


def test_overlay_adjusts_only_inside_its_window() -> None:
    profile = example("solark_gateway_primary.yaml")
    overlay = TargetOverlay("event", _at(17), _at(19), price_delta_per_kwh=1.5)
    inputs = compile_price_inputs(profile, horizon_start=START, horizon_hours=24, step_minutes=60, overlays=[overlay])
    items = inputs.entities["price_import"]["forecast"]
    by_time = {item["time"]: item["value"] for item in items}
    assert by_time[_at(17).isoformat()] == 0.31 + 1.5
    assert by_time[_at(20).isoformat()] == 0.31
    assert inputs.targets[0]["label"] == "event"


def test_compile_works_with_zero_rule_packs() -> None:
    profile = example("tesla_cloud_primary.yaml")
    assert profile["rule_packs"] == []
    inputs = compile_price_inputs(profile, horizon_start=START, horizon_hours=48, step_minutes=60)
    assert inputs.metadata["rule_packs"] == []
    assert len(inputs.entities["price_import"]["forecast"]) == 49
    assert inputs.warnings  # export value is absent in v1: reported, not silent


def test_degradation_term_is_required_and_present() -> None:
    inputs = compile_price_inputs(example("tesla_cloud_primary.yaml"), horizon_start=START, horizon_hours=2)
    assert len(inputs.degradation) == 1
    assert inputs.degradation[0]["element"] == "powerwall"
    assert inputs.degradation[0]["currency_per_kwh"] == 0.04
    assert inputs.degradation[0]["required"] is True
    assert inputs.degradation[0]["representation_verified"] is False


def test_zero_degradation_cost_is_flagged() -> None:
    profile = example("multi_hub_adu.json")
    profile["systems"][0]["elements"][2]["degradation_cost"]["currency_per_kwh"] = 0.0
    inputs = compile_price_inputs(profile, horizon_start=START, horizon_hours=2)
    assert any("C-14" in warning for warning in inputs.warnings)


def test_unverified_formats_are_declared_not_hidden() -> None:
    inputs = compile_price_inputs(example("solark_gateway_primary.yaml"), horizon_start=START, horizon_hours=1)
    assert inputs.metadata["input_names_verified"] is False
    assert inputs.entities["price_import"]["format_verified"] is False
