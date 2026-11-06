"""Local-backed adapters drive Home Assistant entities (step 3).

The point of these tests is not that a dict gets built — it is that a kilowatt
leaves through the same contract a vendor API would use, with the safety envelope
still in front of it and an audit record behind it.
"""

from __future__ import annotations

import pytest
from helpers import example

from custom_components.fleetassistant.adapters.base import AdapterError, Command
from custom_components.fleetassistant.adapters.ha_services import (
    ClimateBinding,
    HaServiceAdapter,
    NumberBinding,
    SwitchBinding,
    binding_for,
    build_ha_adapters,
    capability_from_control,
)
from custom_components.fleetassistant.adapters.safety import SafetyPipeline
from custom_components.fleetassistant.audit import AuditLog


class Recorder:
    """A service caller that remembers what it was asked to do."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []
        self.fail = False

    def __call__(self, domain: str, service: str, data: dict) -> None:
        if self.fail:
            raise RuntimeError("connection refused")
        self.calls.append((domain, service, dict(data)))


def _control(**overrides):
    control = {
        "id": "export_limit",
        "element": "grid",
        "capability": "set_export_limit",
        "unit": "kW",
        "min": 0.0,
        "max": 12.0,
        "rate_limit_per_minute": 12,
        "hysteresis": 0.1,
        "consent_required": True,
        "backing": "local",
        "authority": "full",
        "fail_safe_value": 12.0,
        "entity_id": "number.solark_export_limit",
    }
    control.update(overrides)
    return control


def _adapter(caller, control=None) -> HaServiceAdapter:
    control = control or _control()
    capability = capability_from_control(control)
    return HaServiceAdapter("grid", caller, {capability.name: capability}, {capability.name: binding_for(control)})


# --- bindings ---------------------------------------------------------------


def test_a_number_binding_sets_the_entities_value():
    caller = Recorder()
    NumberBinding("number.export_limit").call(caller, 5.5)
    assert caller.calls == [("number", "set_value", {"entity_id": "number.export_limit", "value": 5.5})]


def test_a_number_binding_scales_our_unit_into_the_entity_unit():
    caller = Recorder()
    NumberBinding("number.export_limit_w", scale=1000.0).call(caller, 5.5)
    assert caller.calls[0][2]["value"] == 5500.0


def test_shedding_means_turning_the_switch_off():
    caller = Recorder()
    SwitchBinding("switch.water_heater").call(caller, 1.0)
    SwitchBinding("switch.water_heater").call(caller, 0.0)
    assert [call[1] for call in caller.calls] == ["turn_off", "turn_on"]


def test_a_fahrenheit_setpoint_is_sent_as_celsius():
    caller = Recorder()
    ClimateBinding("climate.house").call(caller, 68.0)
    assert caller.calls[0][0] == "climate"
    assert caller.calls[0][1] == "set_temperature"
    assert caller.calls[0][2]["temperature"] == pytest.approx(20.0)


def test_a_setpoint_can_be_sent_unconverted_when_the_entity_is_fahrenheit():
    caller = Recorder()
    ClimateBinding("climate.house_f", fahrenheit_to_celsius=False).call(caller, 68.0)
    assert caller.calls[0][2]["temperature"] == 68.0


# --- the adapter ------------------------------------------------------------


def test_a_write_returns_the_value_the_device_was_asked_for():
    caller = Recorder()
    adapter = _adapter(caller)
    assert adapter.write("set_export_limit", 7.25) == 7.25
    assert adapter.backing == "local"
    assert adapter.read_state() == {"set_export_limit": 7.25}


def test_a_transport_failure_is_an_adapter_error_not_a_silent_no_op():
    caller = Recorder()
    caller.fail = True
    with pytest.raises(AdapterError, match="connection refused"):
        _adapter(caller).write("set_export_limit", 3.0)


def test_an_unbound_capability_is_refused_at_construction():
    caller = Recorder()
    capability = capability_from_control(_control())
    with pytest.raises(AdapterError, match="no service binding"):
        HaServiceAdapter("grid", caller, {capability.name: capability}, {})


def test_an_unsupported_capability_is_named_not_guessed():
    with pytest.raises(AdapterError, match="no generic Home Assistant service"):
        binding_for(_control(capability="set_charging_schedule", unit="json"))


def test_a_local_control_without_an_entity_cannot_be_bound():
    control = _control()
    control.pop("entity_id")
    with pytest.raises(AdapterError, match="names no entity_id"):
        binding_for(control)


# --- safety in front of the adapter ----------------------------------------


def test_the_safety_pipeline_still_clamps_and_audits_before_the_service_call():
    caller = Recorder()
    adapter = _adapter(caller)
    audit = AuditLog()
    pipeline = SafetyPipeline({"grid": adapter}, audit, consent_granted=True)

    result = pipeline.submit(Command("grid", "set_export_limit", 40.0, requested_by="optimizer"))

    assert result.status == "clamped"
    assert result.effective_value == 12.0
    assert caller.calls[0][2]["value"] == 12.0
    assert audit.records()[-1].payload["capability"] == "set_export_limit"


def test_without_consent_nothing_reaches_the_entity():
    caller = Recorder()
    pipeline = SafetyPipeline({"grid": _adapter(caller)}, AuditLog())
    result = pipeline.submit(Command("grid", "set_export_limit", 5.0, requested_by="optimizer"))
    assert result.status == "rejected"
    assert result.reason.startswith("consent_missing")
    assert caller.calls == []


# --- the factory ------------------------------------------------------------


def test_the_factory_builds_one_adapter_per_local_element():
    profile = example("solark_gateway_primary.yaml")
    for control in profile["controls"]:
        if control["backing"] == "local":
            control["entity_id"] = f"number.{control['element']}_{control['capability']}"

    adapters, issues = build_ha_adapters(profile, Recorder())

    assert issues == []
    # hvac is api-backed (ecobee cloud), so it has no local adapter (C-09).
    assert set(adapters) == {"grid", "battery", "ev"}
    assert adapters["grid"].capabilities()["set_export_limit"].max_value == 12.0
    assert adapters["grid"].capabilities()["set_export_limit"].consent_required is True


def test_an_unbindable_control_becomes_a_warning_not_a_failed_entry():
    profile = example("solark_gateway_primary.yaml")
    # A local-backed control with its entity id removed cannot be bound.
    profile["controls"][1].pop("entity_id")
    profile["controls"][2].pop("entity_id")
    adapters, issues = build_ha_adapters(profile, Recorder())

    assert set(adapters) == {"grid"}
    assert [issue.code for issue in issues] == ["control_unbound", "control_unbound"]
    assert all(issue.severity == "warning" for issue in issues)


def test_api_backed_controls_are_not_bound_locally():
    adapters, issues = build_ha_adapters(example("tesla_cloud_primary.yaml"), Recorder())
    assert adapters == {}
    assert issues == []


# --- read-back --------------------------------------------------------------


def test_read_state_prefers_the_device_over_the_last_write():
    caller = Recorder()
    states = {"number.solark_export_limit": "4.0"}
    adapter = HaServiceAdapter(
        "grid",
        caller,
        {"set_export_limit": capability_from_control(_control())},
        {"set_export_limit": NumberBinding("number.solark_export_limit")},
        reader=states.get,
    )
    adapter.write("set_export_limit", 7.0)  # the device did not take it
    assert adapter.read_state()["set_export_limit"] == 4.0


def test_read_state_falls_back_to_the_last_write_when_the_entity_is_gone():
    caller = Recorder()
    adapter = HaServiceAdapter(
        "grid",
        caller,
        {"set_export_limit": capability_from_control(_control())},
        {"set_export_limit": NumberBinding("number.gone")},
        reader=lambda entity_id: None,
    )
    adapter.write("set_export_limit", 6.0)
    assert adapter.read_state()["set_export_limit"] == 6.0


def test_a_switch_state_is_read_back_as_zero_or_one():
    caller = Recorder()
    adapter = HaServiceAdapter(
        "relay",
        caller,
        {"shed_circuit": capability_from_control(_control(capability="shed_circuit", unit="bool", min=0, max=1))},
        {"shed_circuit": SwitchBinding("switch.water_heater")},
        reader={"switch.water_heater": "off"}.get,
    )
    assert adapter.read_state()["shed_circuit"] == 0.0
