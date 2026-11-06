"""Safety pipeline: the gate every device write passes through (C-09, C-12, C-18).

Order of checks, all recorded in the audit log:
  1. adapter and capability exist
  2. value is finite; clamp into [min, max]
  3. consent (blocks when required and not granted)
  4. rate limit (token bucket per element+capability)
  5. hysteresis (skip writes smaller than the declared deadband)
  6. adapter write (the only device touchpoint)
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from datetime import UTC, datetime

from ..audit import AuditLog
from .base import AdapterError, Capability, Command, ControlAdapter, WriteResult


class TokenBucket:
    """Simple per-key token bucket, refilled continuously."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._state: dict[str, tuple[float, float]] = {}

    def take(self, key: str, per_minute: int) -> bool:
        now = self._clock()
        tokens, last = self._state.get(key, (float(per_minute), now))
        tokens = min(float(per_minute), tokens + (now - last) * per_minute / 60.0)
        if tokens < 1.0:
            self._state[key] = (tokens, now)
            return False
        self._state[key] = (tokens - 1.0, now)
        return True


class SafetyPipeline:
    """Validates, rate-limits, and audits control commands."""

    def __init__(
        self,
        adapters: dict[str, ControlAdapter],
        audit: AuditLog,
        *,
        consent_granted: bool = False,
        bucket: TokenBucket | None = None,
    ) -> None:
        self._adapters = adapters
        self._audit = audit
        self._consent_granted = consent_granted
        self._bucket = bucket or TokenBucket()
        self._last_applied: dict[tuple[str, str], float] = {}

    # -- introspection ------------------------------------------------------
    def capabilities(self) -> dict[str, dict[str, Capability]]:
        return {element_id: adapter.capabilities() for element_id, adapter in self._adapters.items()}

    def set_consent(self, granted: bool) -> None:
        self._consent_granted = granted

    @property
    def consent_granted(self) -> bool:
        return self._consent_granted

    # -- the gate -----------------------------------------------------------
    def submit(self, command: Command, now: datetime | None = None) -> WriteResult:
        stamp = now or datetime.now(UTC)
        adapter = self._adapters.get(command.element_id)
        if adapter is None:
            return self._reject(command, "unknown_element", f"no adapter for {command.element_id!r}", stamp)

        capability = adapter.capabilities().get(command.capability)
        if capability is None:
            return self._reject(command, "unknown_capability", f"{adapter.adapter_id} has no {command.capability!r}", stamp)

        if isinstance(command.value, bool) or not isinstance(command.value, (int, float)) or not math.isfinite(command.value):
            return self._reject(command, "invalid_value", "value must be a finite number", stamp)

        clamped = capability.clamp(float(command.value))
        clamped_flag = clamped != float(command.value)

        if capability.consent_required and not self._consent_granted:
            return self._reject(command, "consent_missing", "customer consent has not been granted", stamp, capability)

        key = (command.element_id, command.capability)
        if not self._bucket.take(f"{command.element_id}:{command.capability}", capability.rate_limit_per_minute):
            return self._reject(command, "rate_limited", "rate limit exceeded; command dropped", stamp, capability)

        previous = self._last_applied.get(key)
        if previous is not None and abs(clamped - previous) < capability.hysteresis:
            return self._record(
                command,
                capability,
                status="skipped",
                effective=previous,
                reason=f"within hysteresis ({capability.hysteresis} {capability.unit})",
                stamp=stamp,
            )

        try:
            adapter.write(command.capability, clamped)
        except AdapterError as exc:
            return self._record(
                command,
                capability,
                status="rejected",
                effective=None,
                reason=f"adapter_error: {exc}",
                stamp=stamp,
            )

        self._last_applied[key] = clamped
        reason = "clamped to limits" if clamped_flag else "applied"
        return self._record(
            command,
            capability,
            status="clamped" if clamped_flag else "applied",
            effective=clamped,
            reason=reason,
            stamp=stamp,
        )

    # -- recording ----------------------------------------------------------
    def _reject(
        self,
        command: Command,
        code: str,
        reason: str,
        stamp: datetime,
        capability: Capability | None = None,
    ) -> WriteResult:
        record = self._audit.append(
            "control.rejected",
            {
                "code": code,
                "element_id": command.element_id,
                "capability": command.capability,
                "requested_value": command.value,
                "requested_by": command.requested_by,
                "source": command.source,
                "reason": reason,
                "authority": capability.authority if capability else None,
            },
            stamp,
        )
        return WriteResult(
            status="rejected",
            element_id=command.element_id,
            capability=command.capability,
            requested_value=float(command.value) if isinstance(command.value, (int, float)) and not isinstance(command.value, bool) else float("nan"),
            effective_value=None,
            reason=f"{code}: {reason}",
            audit_id=record.seq,
            authority=capability.authority if capability else None,
        )

    def _record(
        self,
        command: Command,
        capability: Capability,
        *,
        status: str,
        effective: float | None,
        reason: str,
        stamp: datetime,
    ) -> WriteResult:
        record = self._audit.append(
            "control.write",
            {
                "status": status,
                "element_id": command.element_id,
                "capability": command.capability,
                "requested_value": command.value,
                "effective_value": effective,
                "unit": capability.unit,
                "backing": capability.backing,
                "authority": capability.authority,
                "requested_by": command.requested_by,
                "source": command.source,
                "reason": reason,
            },
            stamp,
        )
        return WriteResult(
            status=status,  # type: ignore[arg-type]
            element_id=command.element_id,
            capability=command.capability,
            requested_value=float(command.value),
            effective_value=effective,
            reason=reason,
            audit_id=record.seq,
            authority=capability.authority,
        )
