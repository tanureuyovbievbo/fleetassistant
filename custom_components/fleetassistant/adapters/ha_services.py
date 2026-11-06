"""Local-backed adapters that drive Home Assistant entities (step 3 of the roadmap).

A gateway site's control authority is only real when a write reaches hardware.
Most of that hardware is already an entity in the same Home Assistant: a Z-Wave
relay is ``switch.shed_water_heater``, a thermostat is ``climate.house``, an
inverter's export limit is a ``number``. This module turns those entities into
``ControlAdapter`` implementations behind the same contract the vendor-API stubs
use (C-09): nothing above it knows whether a kilowatt left through a cloud API or
a local Modbus register.

Three deliberate choices:

* **No Home Assistant import.** The adapter takes an injected ``ServiceCaller``.
  A write is a function call, so the adapter is testable without a running HA and
  the HA glue (which does import Home Assistant) stays in ``runtime.py``.
* **Bindings are explicit data.** ``switch.turn_off`` vs ``number.set_value`` is
  decided per capability by a binding object, not by guessing from the entity
  domain. A capability with no binding is refused at construction, not at 2 a.m.
* **Read-back is not invented.** ``read_state`` reports only what this adapter
  last wrote. Reading the real state needs the state machine, arrives with the
  executor (RL-23), and is honestly absent until then.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..profile.schema import Issue
from .base import AdapterError, Capability, ControlAdapter

ServiceCaller = Callable[[str, str, Mapping[str, Any]], Any]
"""``caller(domain, service, data)`` — blocking, raises on failure."""

UNSUPPORTED_CAPABILITIES = frozenset({"set_charging_schedule"})
"""A schedule is a sequence, not a scalar; no generic HA service takes one."""


class ServiceBinding(Protocol):
    """How one capability becomes one Home Assistant service call."""

    domain: str

    def call(self, caller: ServiceCaller, value: float) -> float:
        """Perform the call and return the value the device was asked for."""
        ...


@dataclass(frozen=True)
class SwitchBinding:
    """On/off control. ``True`` means "shed" — i.e. turn the switch off."""

    entity_id: str
    on_service: str = "turn_on"
    off_service: str = "turn_off"
    domain: str = field(default="switch", init=False)

    def call(self, caller: ServiceCaller, value: float) -> float:
        service = self.off_service if value else self.on_service
        caller(self.domain, service, {"entity_id": self.entity_id})
        return 1.0 if value else 0.0


@dataclass(frozen=True)
class NumberBinding:
    """A numeric setpoint. ``scale`` converts our unit to the entity's unit."""

    entity_id: str
    value_key: str = "value"
    scale: float = 1.0
    service: str = "set_value"
    domain: str = field(default="number", init=False)

    def call(self, caller: ServiceCaller, value: float) -> float:
        caller(self.domain, self.service, {"entity_id": self.entity_id, self.value_key: value * self.scale})
        return value


@dataclass(frozen=True)
class ClimateBinding:
    """A thermostat setpoint in °F, sent as °C when the entity wants Celsius."""

    entity_id: str
    value_key: str = "temperature"
    fahrenheit_to_celsius: bool = True
    service: str = "set_temperature"
    domain: str = field(default="climate", init=False)

    def call(self, caller: ServiceCaller, value: float) -> float:
        payload: dict[str, Any] = {"entity_id": self.entity_id}
        payload[self.value_key] = (value - 32.0) * 5.0 / 9.0 if self.fahrenheit_to_celsius else value
        caller(self.domain, self.service, payload)
        return value


#: Which binding serves which capability, by entity domain. A control may name an
#: entity in a neighbouring domain (a relay sold as ``light``), so the mapping is
#: consulted with the entity's own prefix and falls back to the capability row.
BINDING_BY_CAPABILITY: dict[str, Callable[[str], ServiceBinding]] = {
    "set_export_limit": lambda entity_id: NumberBinding(entity_id),
    "set_battery_target": lambda entity_id: NumberBinding(entity_id),
    "set_charger_amps": lambda entity_id: NumberBinding(entity_id),
    "set_thermostat_setpoint": lambda entity_id: ClimateBinding(entity_id),
    "shed_circuit": lambda entity_id: SwitchBinding(entity_id),
}


class HaServiceAdapter(ControlAdapter):
    """One controllable element, reached through Home Assistant services."""

    backing = "local"

    def __init__(
        self,
        adapter_id: str,
        caller: ServiceCaller,
        capabilities: Iterable[Capability] | Mapping[str, Capability],
        bindings: Mapping[str, ServiceBinding],
        *,
        label: str = "",
    ) -> None:
        self.adapter_id = adapter_id
        self.label = label or adapter_id
        self._caller = caller
        self._capabilities = dict(capabilities) if isinstance(capabilities, Mapping) else {
            capability.name: capability for capability in capabilities
        }
        self._bindings = dict(bindings)
        missing = set(self._capabilities) - set(self._bindings)
        if missing:
            raise AdapterError(f"{adapter_id}: no service binding for {sorted(missing)}")
        self._last: dict[str, float] = {}

    def capabilities(self) -> Mapping[str, Capability]:
        return dict(self._capabilities)

    def read_state(self) -> Mapping[str, float]:
        """Last value written by this adapter — not the device's real state (RL-23)."""
        return dict(self._last)

    def write(self, capability: str, value: float) -> float:
        binding = self._bindings.get(capability)
        if binding is None:
            raise AdapterError(f"{self.adapter_id}: capability {capability!r} is not bound")
        try:
            applied = binding.call(self._caller, float(value))
        except Exception as err:  # noqa: BLE001 - any transport failure is a failed write
            raise AdapterError(f"{self.adapter_id}: {capability} write failed: {err}") from err
        self._last[capability] = applied
        return applied


def capability_from_control(control: Mapping[str, Any], *, authority: str | None = None) -> Capability:
    """Build a ``Capability`` from a profile control block."""
    return Capability(
        name=str(control["capability"]),
        unit=str(control["unit"]),
        min_value=float(control["min"]),
        max_value=float(control["max"]),
        rate_limit_per_minute=int(control["rate_limit_per_minute"]),
        hysteresis=float(control["hysteresis"]),
        consent_required=bool(control.get("consent_required", False)),
        backing=control.get("backing", "local"),
        authority=authority or control.get("authority") or "full",
        fail_safe_value=float(control["fail_safe_value"]),
    )


def binding_for(control: Mapping[str, Any]) -> ServiceBinding:
    """Resolve the service binding for one control, or raise ``AdapterError``."""
    capability = str(control.get("capability") or "")
    entity_id = str(control.get("entity_id") or "")
    if capability in UNSUPPORTED_CAPABILITIES:
        raise AdapterError(f"{control.get('id')}: {capability} has no generic Home Assistant service")
    factory = BINDING_BY_CAPABILITY.get(capability)
    if factory is None:
        raise AdapterError(f"{control.get('id')}: unknown capability {capability!r}")
    if not entity_id:
        raise AdapterError(f"{control.get('id')}: {capability} is local-backed but names no entity_id")
    binding = factory(entity_id)
    scale = control.get("scale")
    if scale is not None and isinstance(binding, NumberBinding):
        binding = NumberBinding(entity_id, value_key=binding.value_key, scale=float(scale))
    return binding


def build_ha_adapters(
    profile: Mapping[str, Any],
    caller: ServiceCaller,
) -> tuple[dict[str, HaServiceAdapter], list[Issue]]:
    """Build one adapter per local-backed control, grouped by element.

    Returns ``(adapters, issues)``; a control that cannot be bound becomes a
    warning-level issue naming it, so one bad control never sinks the entry.
    """
    by_element: dict[str, list[Mapping[str, Any]]] = {}
    issues: list[Issue] = []
    for index, control in enumerate(profile.get("controls") or []):
        if not isinstance(control, Mapping):
            continue
        if str(control.get("backing", "")) != "local":
            continue
        try:
            binding_for(control)
        except AdapterError as err:
            issues.append(Issue("control_unbound", f"$.controls[{index}]", str(err), severity="warning"))
            continue
        by_element.setdefault(str(control.get("element")), []).append(control)

    adapters: dict[str, HaServiceAdapter] = {}
    for element, controls in by_element.items():
        capabilities: dict[str, Capability] = {}
        bindings: dict[str, ServiceBinding] = {}
        for control in controls:
            capability = capability_from_control(control)
            capabilities[capability.name] = capability
            bindings[capability.name] = binding_for(control)
        adapters[element] = HaServiceAdapter(element, caller, capabilities, bindings, label=element)
    return adapters, issues
