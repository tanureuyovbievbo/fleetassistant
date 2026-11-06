# D06 — Control Adapter Layer

| Field | Value |
|-------|-------|
| ID | D06 |
| Epic | e06-control-adapters |
| Version | 0.0.0 (stub) |
| Status | implemented (stubs only) |
| Owner role | architect (design) → engineer (code) |
| Last updated | 2026-11-05 |
| Depends on | D01, D03, C-09, C-12, C-15, C-16, C-18, C-24, ADR-0002, OQ-005, OQ-013 |

> **Implementation:** capability descriptors, safety pipeline, executor with fail-safe, API and Modbus stub adapters; no vendor adapters yet.
>
> The outline below remains the acceptance contract; code lands against it.
>
> **Stub outline.** Required structure and acceptance criteria.

## Required outline

1. **Interface.** Python `Protocol` or ABC with async methods. Brief names → Python names:
   - `setExportLimit(kW)` → `set_export_limit(kw: float)`
   - `setBatteryTarget(%)` → `set_battery_target(pct: float)`
   - `setChargerAmps(A)` → `set_charger_amps(amps: float)`
   - `setThermostatSetpoint(°F)` → `set_thermostat_setpoint(deg_f: float)` (decide the internal unit and conversion policy)
   - `setChargingSchedule(...)` → `set_charging_schedule(schedule: ChargingSchedule)`
   - `shedCircuit(id, bool)` → `shed_circuit(circuit_id: str, shed: bool)`
2. **Capability descriptor.** `capability`, `min`, `max`, `unit`, `rate_limit` (writes per interval), `hysteresis`, `consent_required`, `backing` (`api` | `local`), `authority_tier` (`coarse` | `full`), `fail_safe_value`.
3. **Safety pipeline.** Every write follows this order: consent gate → clamp to min/max → hysteresis → rate limiter → commitments check → adapter call → read-back verification → audit record (C-18). A rejected write gets a reason code.
4. **Plan executor.** Reads the HAEO plan (entities F-ID-backed). Execution cadence. Mapping from plan to capability. Behavior on stale plans.
5. **Local fail-safe (C-15).** Loss-of-comms timeout, local default per capability, contactor and local automations, and non-performance reporting (C-12).
6. **Stub adapters** (same contract, both pass the same contract test suite):
   - `adapters/api_stub/` — simulates a vendor cloud API (latency, quota, coarse authority).
   - `adapters/modbus_stub/` — simulates a register map (local, full authority). Access path per OQ-013.
7. **Adapter certification checklist** for future real adapters: ToS risk and quota math (C-24), license audit (C-19), safe limits sourced from the device manual (S-ID).
8. Open questions · Constraint compliance · Change log.

## Acceptance criteria

- [ ] One shared contract test suite runs against both stubs.
- [ ] Out-of-range, no-consent, and rate-limited writes are rejected with a reason and an audit record.
- [ ] No module outside `adapters/` performs a device write (CI grep or import-linter rule).
- [ ] Human review gate passed.
