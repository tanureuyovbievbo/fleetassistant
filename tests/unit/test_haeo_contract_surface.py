"""The recorded HAEO surface must stay consistent with the profile schema.

These are *offline* checks: they do not talk to HAEO. They fail when a code
change would silently turn a modelling decision into a guess, which is what
C-23 and ADR-0012 exist to prevent.

Facts asserted here were read from ``hass-energy/haeo@v0.5.0``; see
``custom_components/fleetassistant/haeo_bridge/contracts.py`` for the anchors.
"""

from __future__ import annotations

from helpers import example

from custom_components.fleetassistant.const import SUPPORTED_HAEO_VERSIONS
from custom_components.fleetassistant.haeo_bridge import contracts
from custom_components.fleetassistant.haeo_bridge.plan import DEFAULT_TYPE_MAP, HaeoTypeMap, HubPlan, compile_plan
from custom_components.fleetassistant.haeo_bridge.prevalidate import prevalidate
from custom_components.fleetassistant.profile.schema import ELEMENT_KINDS


def test_surface_version_is_pinned_and_supported() -> None:
    assert contracts.HAEO_SURFACE_VERSION in SUPPORTED_HAEO_VERSIONS
    assert len(contracts.HAEO_SURFACE_COMMIT) == 40


def test_surface_is_not_live_verified_yet() -> None:
    # Flipping this is the whole point of the live contract workflow.
    assert contracts.HAEO_SURFACE_LIVE_VERIFIED is False


def test_every_profile_kind_has_a_type_or_a_recorded_gap() -> None:
    assert set(DEFAULT_TYPE_MAP) == set(ELEMENT_KINDS)
    assert not contracts.CANDIDATE_KIND_TO_TYPE.keys() - set(ELEMENT_KINDS)


def test_mapped_types_exist_in_haeo() -> None:
    for kind, haeo_type in contracts.CANDIDATE_KIND_TO_TYPE.items():
        if haeo_type is not None:
            assert contracts.is_known_element_type(haeo_type), kind


def test_unresolved_kinds_are_exactly_the_ones_without_an_element() -> None:
    assert {"meter", "thermostat", "relay"} == contracts.UNRESOLVED_KINDS
    for kind in contracts.UNRESOLVED_KINDS:
        assert contracts.CANDIDATE_KIND_TO_TYPE[kind] is None


def test_haeo_has_no_element_named_after_the_unresolved_kinds() -> None:
    for kind in contracts.UNRESOLVED_KINDS:
        assert kind not in contracts.ELEMENT_TYPES


def test_hub_creation_data_is_sectioned_with_a_tagged_horizon() -> None:
    hub = HubPlan(system_id="s", hub="solark_house", horizon_mode="preset", preset_days=5)
    data = hub.config_data()
    assert data[contracts.CONF_INTEGRATION_TYPE] == contracts.INTEGRATION_TYPE_HUB
    assert data[contracts.HUB_SECTION_COMMON][contracts.CONF_NAME] == "solark_house"
    assert data[contracts.HUB_SECTION_COMMON][contracts.CONF_HORIZON] == {contracts.HORIZON_VALUE_KEY: "5_days"}
    assert data[contracts.HUB_SECTION_ADVANCED][contracts.CONF_DEBOUNCE_SECONDS] == 2
    assert data[contracts.HUB_SECTION_ADVANCED][contracts.CONF_ADVANCED_MODE] is False


def test_forecast_sensor_horizon_is_a_tagged_entity_list() -> None:
    hub = HubPlan(
        system_id="s",
        hub="h",
        horizon_mode="forecast_sensor",
        forecast_entity="sensor.openderms_horizon",
    )
    horizon = hub.config_data()[contracts.HUB_SECTION_COMMON][contracts.CONF_HORIZON]
    assert horizon == {contracts.HORIZON_ENTITY_KEY: ["sensor.openderms_horizon"]}


def test_relax_infeasible_is_written_explicitly_even_though_haeo_defaults_off() -> None:
    assert contracts.HAEO_DEFAULT_RELAX_INFEASIBLE is False
    hub = HubPlan(system_id="s", hub="h", horizon_mode="preset", preset_days=5)
    assert hub.options_data()[contracts.HUB_SECTION_ADVANCED][contracts.CONF_RELAX_INFEASIBLE] is True


def test_unsupported_preset_days_are_rejected_by_prevalidate() -> None:
    profile = example("solark_gateway_primary.yaml")
    profile["systems"][0]["haeo"]["horizon"] = {"mode": "preset", "preset_days": 4}
    plan = compile_plan(profile, HaeoTypeMap(verified=True))
    codes = {issue.code for issue in prevalidate(plan)}
    assert "horizon_preset_unsupported" in codes


def test_preset_names_round_trip() -> None:
    for preset, days in contracts.HORIZON_PRESETS.items():
        assert contracts.horizon_preset_for(days) == preset
        assert contracts.preset_days(preset) == days
    assert contracts.horizon_preset_for(4) is None
