"""Entity references a profile promises must exist (step 2).

The failure these tests prevent is quiet: a profile naming a sensor that was
never created loads cleanly, HAEO plans against ``unknown``, and the site looks
fine until someone reads the bill.
"""

from __future__ import annotations

import pytest
from helpers import example

from custom_components.fleetassistant.references import (
    EntitySnapshot,
    Reference,
    check_references,
    collect_references,
    repair_key,
)

EXAMPLES = "site_profiles/examples"


def _profile(name: str) -> dict:
    return example(name)


def test_references_come_from_elements_controls_and_the_horizon():
    profile = _profile("solark_gateway_primary.yaml")
    profile["site"]["haeo"] = {"horizon": {"mode": "forecast_sensor", "forecast_entity": "sensor.horizon"}}
    references = collect_references(profile)

    by_entity = {reference.entity_id: reference for reference in references}
    assert "sensor.house_load_forecast" in by_entity
    assert by_entity["sensor.house_load_forecast"].requirement == "forecast"
    assert by_entity["calendar.replace_me_ev_charging_window"].requirement == "calendar"
    assert by_entity["sensor.horizon"].requirement == "forecast"


def test_control_entities_are_collected_as_plain_entities():
    profile = _profile("solark_gateway_primary.yaml")
    profile["controls"][0]["entity_id"] = "number.solark_export_limit"
    references = {r.entity_id: r for r in collect_references(profile)}
    assert references["number.solark_export_limit"].requirement == "entity"
    assert references["number.solark_export_limit"].path == "$.controls[0].entity_id"


def test_published_price_sensors_are_not_reported_missing():
    profile = _profile("tesla_cloud_primary.yaml")
    published = {"sensor.fleetassistant_tesla_home_price_import"}
    references = collect_references(profile, published=published)
    assert all(reference.entity_id not in published for reference in references)


def test_an_absent_entity_is_an_error_naming_itself():
    references = [Reference("sensor.gone", "forecast", "$.systems[0].elements[1].forecast_entity", "load")]
    (issue,) = check_references(references, lambda entity_id: None)
    assert issue.code == "entity_missing"
    assert "sensor.gone" in issue.message
    assert issue.is_error


def test_an_unavailable_entity_warns_rather_than_blocks():
    references = [Reference("sensor.flaky", "forecast", "$.p", "load")]
    (issue,) = check_references(references, lambda entity_id: EntitySnapshot(state="unavailable", forecast_points=48))
    assert issue.code == "entity_unavailable"
    assert not issue.is_error


def test_a_forecast_with_one_point_cannot_drive_a_horizon():
    references = [Reference("sensor.thin", "forecast", "$.p", "load")]
    (issue,) = check_references(references, lambda entity_id: EntitySnapshot(state="3.2", forecast_points=1))
    assert issue.code == "entity_no_forecast"
    assert "need 2" in issue.message


def test_two_boundaries_are_enough():
    references = [Reference("sensor.thin", "forecast", "$.p", "load")]
    assert check_references(references, lambda entity_id: EntitySnapshot(state="3.2", forecast_points=2)) == []


def test_a_calendar_reference_must_be_a_calendar():
    references = [Reference("sensor.window", "calendar", "$.p", "ev")]
    (issue,) = check_references(references, lambda entity_id: EntitySnapshot(state="on"))
    assert issue.code == "calendar_domain_mismatch"


def test_a_plain_entity_needs_no_forecast():
    references = [Reference("number.export_limit", "entity", "$.p", "grid")]
    assert check_references(references, lambda entity_id: EntitySnapshot(state="5.0")) == []


def test_repair_keys_are_stable_and_unique_per_entity():
    a = Reference("sensor.load", "forecast", "$.a", "load")
    b = Reference("sensor.load", "entity", "$.b", "load")
    assert repair_key(a) == repair_key(b) == "reference_sensor_load"
    assert repair_key(Reference("calendar.w", "calendar", "$.c", "ev")) == "reference_calendar_w"


@pytest.mark.parametrize("name", ["tesla_cloud_primary.yaml", "solark_gateway_primary.yaml", "multi_hub_adu.json"])
def test_example_entity_ids_have_a_domain_and_an_object(name: str):
    for reference in collect_references(example(name)):
        domain, _, object_id = reference.entity_id.partition(".")
        assert domain and object_id, reference
        assert domain in {"sensor", "calendar", "number", "switch", "climate", "select", "input_number"}
