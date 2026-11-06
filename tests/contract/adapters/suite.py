"""Shared adapter contract suite.

Any adapter — stub, API-backed, or Modbus-backed — must pass this. The contract
is what makes "identical contract, different transport" true (C-09).
"""

from __future__ import annotations

import pytest

from custom_components.fleetassistant.adapters import AdapterError, ApiStubAdapter, ControlAdapter, ModbusStubAdapter


def adapter_factories() -> list:
    return [ApiStubAdapter, ModbusStubAdapter]


@pytest.mark.parametrize("factory", adapter_factories(), ids=lambda f: f.__name__)
class TestAdapterContract:
    def test_is_a_control_adapter(self, factory) -> None:
        assert isinstance(factory(), ControlAdapter)

    def test_declares_capabilities_with_safety_envelope(self, factory) -> None:
        caps = factory().capabilities()
        assert caps, "an adapter with no capabilities is useless"
        for name, cap in caps.items():
            assert cap.name == name
            assert cap.min_value < cap.max_value
            assert cap.min_value <= cap.fail_safe_value <= cap.max_value
            assert cap.rate_limit_per_minute > 0
            assert cap.hysteresis >= 0
            assert cap.backing in ("api", "local")
            assert cap.authority in ("coarse", "full")

    def test_backing_matches_the_adapter_class(self, factory) -> None:
        adapter = factory()
        for cap in adapter.capabilities().values():
            assert cap.backing == adapter.backing

    def test_read_state_is_a_mapping_with_values(self, factory) -> None:
        state = factory().read_state()
        assert isinstance(state, dict)
        assert "values" in state and isinstance(state["values"], dict)

    def test_write_updates_state(self, factory) -> None:
        adapter = factory()
        cap = next(iter(adapter.capabilities().values()))
        value = (cap.min_value + cap.max_value) / 2
        adapter.write(cap.name, value)
        assert adapter.read_state()["values"][cap.name] == value

    def test_unknown_capability_raises_adapter_error(self, factory) -> None:
        with pytest.raises(AdapterError):
            factory().write("not_a_capability", 1.0)
