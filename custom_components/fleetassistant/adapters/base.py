"""Control adapter contract — the only seam that touches a device (C-09).

Every controllable thing (battery, inverter export limit, EV charger,
thermostat, relay) is reached through ``ControlAdapter.write(capability, value)``.
Nothing else in the codebase may call a vendor API, a Modbus register, or an HA
service on a device.

Capabilities carry their own safety envelope: min/max, rate limit, hysteresis,
consent requirement, backing and authority tier. The safety pipeline
(``safety.py``) enforces all of it before ``write`` is ever called.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Literal

Backing = Literal["api", "local"]
Authority = Literal["coarse", "full"]
WriteStatus = Literal["applied", "clamped", "skipped", "rejected"]


class AdapterError(RuntimeError):
    """Raised by an adapter when the device refused or failed a write."""


@dataclass(frozen=True)
class Capability:
    name: str
    unit: str
    min_value: float
    max_value: float
    rate_limit_per_minute: int
    hysteresis: float
    consent_required: bool
    backing: Backing
    authority: Authority
    fail_safe_value: float

    def contains(self, value: float) -> bool:
        return self.min_value <= value <= self.max_value

    def clamp(self, value: float) -> float:
        return max(self.min_value, min(self.max_value, value))


@dataclass(frozen=True)
class Command:
    element_id: str
    capability: str
    value: float
    requested_by: str
    reason: str = ""
    source: str = "manual"


@dataclass(frozen=True)
class WriteResult:
    status: WriteStatus
    element_id: str
    capability: str
    requested_value: float
    effective_value: float | None
    reason: str
    audit_id: int
    authority: Authority | None = None

    @property
    def ok(self) -> bool:
        return self.status in ("applied", "clamped")


class ControlAdapter(ABC):
    """Base class for API-backed and local-backed adapters.

    Implementations MUST be the only code that talks to the device. They MUST
    NOT perform their own clamping or consent checks — the safety pipeline owns
    that — but they MUST fail loudly (``AdapterError``) when a write does not
    land.
    """

    adapter_id: str = "base"
    backing: Backing = "api"

    @abstractmethod
    def capabilities(self) -> dict[str, Capability]:
        """Declared capabilities, keyed by capability name."""

    @abstractmethod
    def read_state(self) -> dict[str, Any]:
        """Best-effort current device state, for telemetry and audits."""

    @abstractmethod
    def write(self, capability: str, value: float) -> None:
        """Apply one already-validated value. Raise AdapterError on failure."""
