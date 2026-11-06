"""T-02..T-05: HAEO bridge plan, pre-validation, version pinning, idempotency."""

from __future__ import annotations

from dataclasses import replace

from helpers import deep_copy, example

from custom_components.fleetassistant.haeo_bridge.apply import (
    InMemoryHaeoDriver,
    apply_plan,
    check_version,
)
from custom_components.fleetassistant.haeo_bridge.contracts import CANDIDATE_KIND_TO_TYPE
from custom_components.fleetassistant.haeo_bridge.plan import (
    DEFAULT_TYPE_MAP,
    HaeoTypeMap,
    NetworkPlan,
    compile_plan,
)
from custom_components.fleetassistant.haeo_bridge.prevalidate import prevalidate
from custom_components.fleetassistant.profile.schema import validate_profile

#: Stand-in for a live-confirmed mapping: real HAEO element types where the
#: correspondence is unambiguous, a junction for the kinds still under decision
#: (a junction carries no fields, so it stands in without faking a model).
VERIFIED_MAP = HaeoTypeMap(
    types={kind: haeo_type or "junction" for kind, haeo_type in CANDIDATE_KIND_TO_TYPE.items()},
    verified=True,
)


def test_compile_plan_from_gateway_example() -> None:
    plan = compile_plan(example("solark_gateway_primary.yaml"))
    assert plan.site_id == "solark_adu_demo"
    assert plan.authority == "full"
    assert len(plan.hubs) == 1
    assert plan.hubs[0].relax_impossible_plans is True
    names = {e.name for e in plan.elements}
    assert {"main_bus", "grid", "battery", "ev", "hvac"} <= names
    assert len(plan.connections) == 6


def test_compile_plan_keeps_haoe_types_unverified_by_default() -> None:
    plan = compile_plan(example("tesla_cloud_primary.yaml"))
    assert plan.type_map.verified is False
    modelled = {e.kind: e.haeo_type for e in plan.elements}
    assert modelled["grid"] == "grid"
    assert modelled["battery"] == "battery"
    assert DEFAULT_TYPE_MAP["meter"] is None
    # A charger is a deferrable load, not HAEO's vehicle element (ADR-0016).
    assert DEFAULT_TYPE_MAP["ev_charger"] == "deferrable_load"


def test_prevalidate_blocks_unverified_types() -> None:
    plan = compile_plan(example("tesla_cloud_primary.yaml"))
    codes = {issue.code for issue in prevalidate(plan)}
    assert "haeo_type_unverified" in codes


def test_prevalidate_blocks_kinds_without_a_haoe_element() -> None:
    plan = compile_plan(example("solark_gateway_primary.yaml"))
    codes = {issue.code for issue in prevalidate(plan)}
    assert "haeo_kind_unmapped" in codes


def test_prevalidate_accepts_a_verified_type_map() -> None:
    plan = compile_plan(example("tesla_cloud_primary.yaml"), VERIFIED_MAP)
    assert prevalidate(plan) == []


def test_unverified_plan_is_blocked_and_nothing_is_applied() -> None:
    driver = InMemoryHaeoDriver()
    report = apply_plan(driver, compile_plan(example("tesla_cloud_primary.yaml")))
    assert report.status == "blocked"
    assert driver.calls == []
    assert any(issue.code == "haeo_type_unverified" for issue in report.issues)


def test_apply_creates_hub_and_elements() -> None:
    driver = InMemoryHaeoDriver()
    plan = compile_plan(example("solark_gateway_primary.yaml"), VERIFIED_MAP)
    report = apply_plan(driver, plan)
    assert report.status == "applied"
    assert "solark_house" in driver.hubs
    assert set(driver.elements["solark_house"]) == {e.name for e in plan.elements}
    assert len(report.operations) == 1 + len(plan.elements)


def test_every_connected_element_points_at_the_system_bus() -> None:
    plan = compile_plan(example("solark_gateway_primary.yaml"), VERIFIED_MAP)
    bus = "main_bus"
    connected = {"grid", "battery", "inverter", "house", "ev"}
    for element in plan.elements:
        if element.name in connected:
            assert element.connection == bus
        elif element.name != bus:
            assert element.connection is None
    grid = next(e for e in plan.elements if e.name == "grid")
    payload = grid.payload()
    assert payload["connection"] == {"type": "connection_target", "value": bus}
    assert payload["element_type"] == "grid"


def test_grid_prices_come_from_our_published_price_sensors() -> None:
    plan = compile_plan(example("tesla_cloud_primary.yaml"), VERIFIED_MAP)
    grid = next(e for e in plan.elements if e.name == "grid")
    pricing = grid.sections["pricing"]
    assert pricing["price_source_target"] == {
        "type": "entity",
        "value": ["sensor.fleetassistant_tesla_home_demo_price_import"],
    }
    assert pricing["price_target_source"]["value"] == ["sensor.fleetassistant_tesla_home_demo_price_export"]


def test_price_entities_can_be_overridden_per_site() -> None:
    plan = compile_plan(
        example("tesla_cloud_primary.yaml"),
        VERIFIED_MAP,
        price_entities={"grid": {"import_price_entity": "sensor.my_import"}},
    )
    grid = next(e for e in plan.elements if e.name == "grid")
    assert grid.sections["pricing"]["price_source_target"]["value"] == ["sensor.my_import"]
    assert grid.sections["pricing"]["price_target_source"]["value"][0].startswith("sensor.fleetassistant_")


def test_battery_fields_are_sectioned_and_tagged() -> None:
    plan = compile_plan(example("solark_gateway_primary.yaml"), VERIFIED_MAP)
    battery = next(e for e in plan.elements if e.name == "battery")
    assert battery.sections["storage"]["capacity"] == {"type": "constant", "value": 30.0}
    # HAEO's *_percentage fields are 0..1 ratios, so 10 % must leave as 0.1 (F-053).
    assert battery.sections["limits"]["min_charge_percentage"]["value"] == 0.1
    assert battery.sections["power_limits"]["max_power_target_source"]["value"] == 10.0
    # HAEO's own form default, written explicitly rather than left implicit.
    assert battery.sections["advanced"]["charge_limit_cost"]["value"] == 100.0
    assert battery.profile_extras["degradation_cost"]["currency_per_kwh"] == 0.03


def test_battery_efficiency_is_a_ratio_and_never_omitted() -> None:
    """HAEO computes ``output = input * efficiency`` and defaults the field to 95.0.

    Under that maths 95.0 would create energy, so we must always write the field
    (F-057..F-059, RL-19)."""
    profile = example("solark_gateway_primary.yaml")
    battery = next(e for e in profile["systems"][0]["elements"] if e["kind"] == "battery")
    battery["charge_efficiency_pct"] = 92.5

    element = next(e for e in compile_plan(profile, VERIFIED_MAP).elements if e.name == "battery")
    efficiency = element.sections["efficiency"]
    assert efficiency["efficiency_source_target"] == {"type": "constant", "value": 0.925}
    # 92.5 % is unconventional for the other direction too, so the schema warns but
    # still compiles; the discharge default stays a sane ratio, never 95.0.
    assert efficiency["efficiency_target_source"] == {"type": "constant", "value": 0.95}


def test_efficiency_outside_a_percentage_is_rejected() -> None:
    profile = example("solark_gateway_primary.yaml")
    battery = next(e for e in profile["systems"][0]["elements"] if e["kind"] == "battery")
    battery["charge_efficiency_pct"] = 0.925  # someone wrote the ratio, not the percentage

    issues = validate_profile(profile)
    assert any(issue.code == "range" and issue.path.endswith("charge_efficiency_pct") for issue in issues)


def test_reapplying_the_same_plan_is_a_noop() -> None:
    driver = InMemoryHaeoDriver()
    plan = compile_plan(example("solark_gateway_primary.yaml"), VERIFIED_MAP)
    apply_plan(driver, plan)
    calls_after_first = list(driver.calls)
    second = apply_plan(driver, plan)
    assert second.status == "noop"
    assert second.operations == []
    assert driver.calls == calls_after_first


def test_changed_element_is_updated_not_recreated() -> None:
    driver = InMemoryHaeoDriver()
    profile = example("solark_gateway_primary.yaml")
    apply_plan(driver, compile_plan(profile, VERIFIED_MAP))
    changed = deep_copy(profile)
    changed["systems"][0]["elements"][3]["capacity_kwh"] = 40.0
    report = apply_plan(driver, compile_plan(changed, VERIFIED_MAP))
    assert [op.type for op in report.operations] == ["update_element"]
    assert report.operations[0].name == "battery"


def test_profile_keys_without_a_haoe_field_are_reported_not_written() -> None:
    plan = compile_plan(example("solark_gateway_primary.yaml"), VERIFIED_MAP)
    hvac = next(e for e in plan.elements if e.name == "hvac")
    assert "min_setpoint_f" in hvac.ignored_keys
    assert hvac.sections == {}
    codes = {(issue.code, issue.path) for issue in prevalidate(plan)}
    assert ("profile_key_unmapped", "main.hvac") in codes


def test_version_mismatch_blocks_before_any_apply() -> None:
    driver = InMemoryHaeoDriver(version="9.9.9")
    report = apply_plan(driver, compile_plan(example("solark_gateway_primary.yaml"), VERIFIED_MAP))
    assert report.status == "blocked"
    assert report.issues[0].code == "haeo_version_unsupported"
    assert driver.calls == []


def test_missing_haoe_is_reported() -> None:
    issue = check_version(None)
    assert issue is not None and issue.code == "haeo_missing"


def test_dangling_connection_blocks_apply() -> None:
    profile = deep_copy(example("solark_gateway_primary.yaml"))
    profile["systems"][0]["connections"][0]["to"] = "ghost"
    driver = InMemoryHaeoDriver()
    report = apply_plan(driver, compile_plan(profile, VERIFIED_MAP))
    assert report.status == "blocked"
    assert driver.calls == []
    assert any(issue.code == "dangling_connection" for issue in report.issues)


def test_plan_round_trips_through_dict() -> None:
    plan = compile_plan(example("multi_hub_adu.json"), VERIFIED_MAP)
    restored = NetworkPlan.from_dict(plan.as_dict())
    assert restored.as_dict() == plan.as_dict()
    assert len(restored.hubs) == 2


def test_dual_optimizer_per_system_is_rejected() -> None:
    plan = compile_plan(example("solark_gateway_primary.yaml"), VERIFIED_MAP)
    duplicated = NetworkPlan(
        site_id=plan.site_id,
        deployment_profile=plan.deployment_profile,
        authority=plan.authority,
        hubs=(plan.hubs[0], plan.hubs[0]),
        elements=plan.elements,
        connections=plan.connections,
        type_map=plan.type_map,
    )
    codes = {issue.code for issue in prevalidate(duplicated)}
    assert "dual_optimizer" in codes


def test_battery_degradation_becomes_a_policy_rule() -> None:
    plan = compile_plan(example("solark_gateway_primary.yaml"), VERIFIED_MAP)
    policy = next(e for e in plan.elements if e.haeo_type == "policy")
    rule = policy.flat["rules"][0]
    battery = next(e for e in plan.elements if e.kind == "battery")
    assert rule["source"] == [battery.name]
    assert rule["target"] == ["*"]
    assert rule["price"] == {"type": "constant", "value": battery.profile_extras["degradation_cost"]["currency_per_kwh"]}
    assert policy.connection is None


def test_charger_is_a_deferrable_load_with_a_run_window() -> None:
    plan = compile_plan(example("solark_gateway_primary.yaml"), VERIFIED_MAP)
    ev = next(e for e in plan.elements if e.kind == "ev_charger")
    assert ev.haeo_type == "deferrable_load"
    assert ev.sections["schedule"]["window_calendar"] == {
        "type": "entity",
        "value": ["calendar.replace_me_ev_charging_window"],
    }
    assert ev.sections["power"]["max_power"] == {"type": "constant", "value": 11.0}
    assert ev.sections["pricing"]["deficit_price"]["value"] == 10.0


def test_policy_rule_naming_an_unknown_element_blocks() -> None:
    plan = compile_plan(example("solark_gateway_primary.yaml"), VERIFIED_MAP)
    elements = [
        replace(e, flat={"rules": [{**e.flat["rules"][0], "source": ["ghost"]}]})
        if e.haeo_type == "policy"
        else e
        for e in plan.elements
    ]
    issues = prevalidate(replace(plan, elements=tuple(elements)))
    assert "dangling_connection" in {i.code for i in issues}
