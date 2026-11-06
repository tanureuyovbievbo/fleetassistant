"""Stub adapters behind the identical contract (C-09).

Both are fakes: they hold state in memory and simulate realistic constraints.
They exist so the contract suite (tests/contract/adapters) has two
implementations to prove that API-backed and Modbus-backed adapters are
interchangeable. Real adapters replace them one vendor at a time.

Do not add vendor behaviour here. Vendor adapters get their own module and must
pass the same suite.
"""

from __future__ import annotations

from typing import Any

from .base import AdapterError, Capability, ControlAdapter


class _StubBase(ControlAdapter):
    def __init__(self, adapter_id: str, capabilities: dict[str, Capability], initial: dict[str, float] | None = None) -> None:
        self.adapter_id = adapter_id
        self._caps = capabilities
        self._state: dict[str, float] = {name: cap.fail_safe_value for name, cap in capabilities.items()}
        self._state.update(initial or {})
        self.write_log: list[tuple[str, float]] = []
        self.fail_next_write = False

    def capabilities(self) -> dict[str, Capability]:
        return dict(self._caps)

    def read_state(self) -> dict[str, Any]:
        return {"adapter_id": self.adapter_id, "backing": self.backing, "values": dict(self._state)}

    def write(self, capability: str, value: float) -> None:
        if capability not in self._caps:
            raise AdapterError(f"unsupported capability {capability!r}")
        if self.fail_next_write:
            self.fail_next_write = False
            raise AdapterError("simulated device failure")
        self._state[capability] = float(value)
        self.write_log.append((capability, float(value)))


class ApiStubAdapter(_StubBase):
    """Stands in for a cloud API adapter (Tesla Fleet, SolarEdge, Enphase, ...)."""

    backing = "api"

    def __init__(self, adapter_id: str = "api_stub", *, max_kw: float = 5.0) -> None:
        super().__init__(
            adapter_id,
            {
                "set_export_limit": Capability(
                    name="set_export_limit",
                    unit="kW",
                    min_value=0.0,
                    max_value=max_kw,
                    rate_limit_per_minute=6,
                    hysteresis=0.1,
                    consent_required=True,
                    backing="api",
                    authority="coarse",
                    fail_safe_value=0.0,
                )
            },
        )


class ModbusStubAdapter(_StubBase):
    """Stands in for a local Modbus adapter (inverter register writes)."""

    backing = "local"

    def __init__(self, adapter_id: str = "modbus_stub", *, max_kw: float = 10.0, capacity_kwh: float = 20.0) -> None:
        super().__init__(
            adapter_id,
            {
                "set_export_limit": Capability(
                    name="set_export_limit",
                    unit="kW",
                    min_value=0.0,
                    max_value=max_kw,
                    rate_limit_per_minute=12,
                    hysteresis=0.05,
                    consent_required=False,
                    backing="local",
                    authority="full",
                    fail_safe_value=0.0,
                ),
                "set_battery_target": Capability(
                    name="set_battery_target",
                    unit="%",
                    min_value=5.0,
                    max_value=100.0,
                    rate_limit_per_minute=6,
                    hysteresis=1.0,
                    consent_required=False,
                    backing="local",
                    authority="full",
                    fail_safe_value=50.0,
                ),
            },
            initial={"set_battery_target": capacity_kwh},
        )
