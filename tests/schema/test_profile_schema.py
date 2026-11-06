"""T-01: the three worked examples validate; broken profiles fail loudly."""

from __future__ import annotations

import pytest
from helpers import deep_copy, example

from custom_components.fleetassistant.profile.schema import validate_profile

EXAMPLES = ("tesla_cloud_primary.yaml", "solark_gateway_primary.yaml", "multi_hub_adu.json")


@pytest.mark.parametrize("name", EXAMPLES)
def test_example_profiles_are_valid(name: str) -> None:
    profile = example(name)
    issues = validate_profile(profile)
    assert [str(i) for i in issues if i.is_error] == []


def test_cloud_primary_example_declares_no_local_control() -> None:
    profile = example("tesla_cloud_primary.yaml")
    assert all(c["backing"] == "api" for c in profile["controls"])
    assert all(c["authority"] == "coarse" for c in profile["controls"])


def test_multi_hub_example_has_one_hub_per_system() -> None:
    profile = example("multi_hub_adu.json")
    hubs = [s["haeo"]["hub"] for s in profile["systems"]]
    assert len(hubs) == 2
    assert len(set(hubs)) == 2


def _codes(profile: dict) -> set[str]:
    return {issue.code for issue in validate_profile(profile) if issue.is_error}


def test_dangling_connection_is_an_error() -> None:
    profile = deep_copy(example("multi_hub_adu.json"))
    profile["systems"][0]["connections"][0]["to"] = "does_not_exist"
    assert "dangling_reference" in _codes(profile)


def test_battery_without_degradation_cost_is_an_error() -> None:
    profile = deep_copy(example("tesla_cloud_primary.yaml"))
    del profile["systems"][0]["elements"][2]["degradation_cost"]
    assert "required" in _codes(profile)


def test_haeo_names_are_rejected_in_the_profile() -> None:
    profile = deep_copy(example("tesla_cloud_primary.yaml"))
    profile["systems"][0]["elements"][0]["haeo_type"] = "grid"
    assert "haeo_leak" in _codes(profile)


def test_cloud_primary_may_not_use_local_control() -> None:
    profile = deep_copy(example("tesla_cloud_primary.yaml"))
    profile["controls"][0]["backing"] = "local"
    assert "authority_mismatch" in _codes(profile)


def test_control_unit_must_match_capability() -> None:
    profile = deep_copy(example("solark_gateway_primary.yaml"))
    profile["controls"][0]["unit"] = "kWh"
    assert "unit" in _codes(profile)


def test_unknown_schema_version_is_rejected() -> None:
    profile = deep_copy(example("tesla_cloud_primary.yaml"))
    profile["schema_version"] = 99
    assert "schema_version" in _codes(profile)


def test_capability_must_be_allowed_for_element_kind() -> None:
    profile = deep_copy(example("solark_gateway_primary.yaml"))
    profile["controls"][0]["element"] = "hvac"  # thermostat cannot set export limit
    assert "capability_not_allowed" in _codes(profile)


def test_fail_safe_value_must_lie_inside_limits() -> None:
    profile = deep_copy(example("solark_gateway_primary.yaml"))
    profile["controls"][0]["fail_safe_value"] = 999
    assert "range" in _codes(profile)


def test_price_authority_must_be_a_known_value() -> None:
    profile = deep_copy(example("tesla_cloud_primary.yaml"))
    profile["pricing"]["authority"] = "cheapest"
    assert "choice" in _codes(profile)


def test_price_authority_accepts_every_documented_value() -> None:
    for authority in ("cloud", "user", "user_unless_stale"):
        profile = deep_copy(example("tesla_cloud_primary.yaml"))
        profile["pricing"]["authority"] = authority
        assert _codes(profile) == set(), authority


def test_a_declared_cloud_source_needs_a_provider_id() -> None:
    profile = deep_copy(example("tesla_cloud_primary.yaml"))
    profile["pricing"]["cloud"] = {"provider": "Not A Slug"}
    assert "slug" in _codes(profile)


def test_export_multipliers_must_cover_all_24_hours() -> None:
    profile = deep_copy(example("tesla_cloud_primary.yaml"))
    profile["pricing"]["export"] = {"currency_per_kwh": 0.05, "hour_multipliers": [1.0] * 12}
    assert "range" in _codes(profile)


def test_an_export_curve_is_accepted() -> None:
    profile = deep_copy(example("tesla_cloud_primary.yaml"))
    profile["pricing"]["export"] = {"currency_per_kwh": 0.05, "hour_multipliers": [1.0] * 24}
    assert _codes(profile) == set()
