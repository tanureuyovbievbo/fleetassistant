"""Fleet allocation: merit order, fairness caps, simultaneity, feedback trim (D09)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fleet.allocation import (
    Allocated,
    Allocation,
    Allocator,
    SiteOffer,
    dispatch_delta,
    feedback_trim,
    simultaneity_factor,
    simultaneous_capacity,
)

T0 = datetime(2026, 11, 6, 18, 0, tzinfo=UTC)


def _offer(site_id: str, kw: float, cost: float, **kwargs) -> SiteOffer:
    return SiteOffer(site_id=site_id, capacity_kw=kw, marginal_cost=cost, **kwargs)


def test_merit_order_buys_the_cheapest_kilowatts_first():
    result = Allocator().allocate(10.0, [_offer("a", 8.0, 0.30), _offer("b", 8.0, 0.10)])

    assert result.by_site() == {"b": 8.0, "a": 2.0}
    assert result.clearing_cost == pytest.approx(0.30)
    assert result.full


def test_a_short_fleet_reports_the_shortfall_rather_than_pretending():
    result = Allocator().allocate(25.0, [_offer("a", 8.0, 0.10), _offer("b", 8.0, 0.20)])

    assert result.allocated_kw == pytest.approx(16.0)
    assert result.shortfall_kw == pytest.approx(9.0)
    assert result.full is False


def test_availability_and_opt_out_are_respected_and_explained():
    result = Allocator().allocate(
        5.0,
        [
            _offer("gone", 10.0, 0.01, available=False),
            _offer("declined", 10.0, 0.02, opted_out=True),
            _offer("willing", 10.0, 0.90),
        ],
    )

    reasons = {item.site_id: item.reason for item in result.rejected}
    assert reasons == {"gone": "unavailable", "declined": "opted_out"}
    assert result.by_site() == {"willing": 5.0}


def test_a_comfort_reserve_is_never_allocated_away():
    offer = _offer("home", 10.0, 0.10, reserve_kw=6.0)

    assert offer.offered_kw == pytest.approx(4.0)
    assert Allocator().allocate(10.0, [offer]).allocated_kw == pytest.approx(4.0)


def test_a_site_whose_whole_capacity_is_reserved_offers_nothing():
    offer = _offer("cold", 6.0, 0.10, reserve_kw=6.0)
    result = Allocator().allocate(5.0, [offer])
    assert result.rejected[0].reason == "comfort_floor"
    assert result.allocations == ()


def test_a_battery_life_cap_bounds_one_event_even_when_the_site_could_give_more():
    offer = _offer("battery", 20.0, 0.05, battery_life_cap_kw=3.0)
    assert offer.offered_kw == pytest.approx(3.0)


def test_a_share_cap_spreads_the_event_instead_of_hammering_the_cheapest_site():
    allocator = Allocator(share_cap=0.5)
    result = allocator.allocate(10.0, [_offer("cheap", 20.0, 0.05), _offer("pricey", 20.0, 0.20)])

    # 0.5 of each site's capacity: the cheap site takes 5 kW, the pricey one covers the rest.
    assert result.by_site() == {"cheap": 5.0, "pricey": 5.0}


def test_a_site_share_cap_overrides_the_fleet_default():
    allocator = Allocator(share_cap=0.9)
    result = allocator.allocate(10.0, [_offer("a", 10.0, 0.05, share_cap=0.3), _offer("b", 10.0, 0.10)])
    assert result.by_site()["a"] == pytest.approx(3.0)


def test_equal_costs_are_broken_by_site_id_so_runs_are_reproducible():
    first = Allocator().allocate(5.0, [_offer("b", 10.0, 0.10), _offer("a", 10.0, 0.10)])
    second = Allocator().allocate(5.0, [_offer("a", 10.0, 0.10), _offer("b", 10.0, 0.10)])
    assert first.allocations == second.allocations
    assert first.by_site() == {"a": 5.0}


def test_a_zero_target_allocates_nothing_and_clears_the_curve():
    result = Allocator().allocate(0.0, [_offer("a", 10.0, 0.10)])
    assert result.allocations == ()
    assert result.clearing_cost is None
    assert result.full


def test_a_negative_target_is_a_caller_bug():
    with pytest.raises(ValueError):
        Allocator().allocate(-1.0, [])


@pytest.mark.parametrize("kwargs", [{"battery_life_cap_kw": -1.0}, {"share_cap": 1.5}, {"reserve_kw": -2.0}])
def test_offers_reject_impossible_limits(kwargs):
    with pytest.raises(ValueError):
        _offer("a", 5.0, 0.1, **kwargs)


def test_simultaneity_discounts_nameplates_that_overlap_only_partly():
    windows = [(T0, T0 + timedelta(hours=4)), (T0 + timedelta(hours=2), T0 + timedelta(hours=6))]
    # Two of six hours are simultaneous.
    assert simultaneity_factor(windows) == pytest.approx(2 / 6)
    assert simultaneous_capacity([_offer("a", 10.0, 0.1), _offer("b", 10.0, 0.1)], windows) == pytest.approx(20.0 * 2 / 6)


def test_simultaneity_of_identical_windows_is_one():
    windows = [(T0, T0 + timedelta(hours=1)), (T0, T0 + timedelta(hours=1))]
    assert simultaneity_factor(windows) == pytest.approx(1.0)


def test_simultaneity_of_disjoint_windows_is_zero():
    windows = [(T0, T0 + timedelta(hours=1)), (T0 + timedelta(hours=2), T0 + timedelta(hours=3))]
    assert simultaneity_factor(windows) == pytest.approx(0.0)


def test_simultaneity_of_no_windows_is_zero():
    assert simultaneity_factor([]) == pytest.approx(0.0)


def test_dispatch_delta_sends_only_changes_above_hysteresis():
    result = Allocator().allocate(10.0, [_offer("a", 10.0, 0.1), _offer("c", 10.0, 0.2)])
    delta = dispatch_delta(result, {"a": 4.9, "c": 2.0}, hysteresis_kw=0.25)

    # "a" moves 5.1 kW, "c" moves from 2.0 to 0.0, and "b" was never allocated.
    assert delta == {"a": 10.0, "c": 0.0}


def test_a_site_that_stops_delivering_is_told_zero_not_silence():
    empty = Allocator().allocate(0.0, [_offer("a", 10.0, 0.1)])
    assert dispatch_delta(empty, {"a": 5.0}) == {"a": 0.0}


def test_feedback_trim_ignores_noise_inside_the_deadband():
    assert feedback_trim(measured_kw=99.9, target_kw=100.0) == 0.0


def test_feedback_trim_adds_a_bounded_fraction_of_the_shortfall():
    assert feedback_trim(measured_kw=80.0, target_kw=100.0, gain=0.5) == pytest.approx(10.0)


def test_feedback_trim_reduces_when_the_fleet_overshoots():
    assert feedback_trim(measured_kw=120.0, target_kw=100.0, gain=0.5) == pytest.approx(-20.0)


def test_allocation_serialises_for_an_api_response():
    result: Allocation = Allocator().allocate(3.0, [_offer("a", 5.0, 0.1)])
    payload = result.as_dict()
    assert payload["allocations"] == [{"site_id": "a", "kw": 3.0, "marginal_cost": 0.1}]
    assert payload["shortfall_kw"] == 0.0
    assert isinstance(result.allocations[0], Allocated)
