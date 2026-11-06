# ADR-0002 — Single control-adapter interface for all device access

| Field | Value |
|-------|-------|
| Status | accepted |
| Date | 2026-11-05 |
| Source | Project brief |
| Constraints | C-09, C-12, C-15, C-18 |

## Context
Safety, consent, audit, and authority tiers must apply to every device write without exception.

## Decision
All device access goes through one interface: `set_export_limit`, `set_battery_target`, `set_charger_amps`, `set_thermostat_setpoint`, `set_charging_schedule`, `shed_circuit`. Each capability has a descriptor with min/max, rate limit, hysteresis, consent, backing (`api`/`local`), and authority tier. API adapters come first and Modbus adapters later, with the identical contract.

## Consequences
Adding a vendor means adding an adapter and nothing else. A boundary check in CI enforces that no other module writes to a device. Every write passes through one safety pipeline and emits an audit record.

## Rejected alternatives
- **Direct service calls from automations or the executor:** there is no central safety pipeline and no audit.
- **One interface per vendor:** there is no shared contract test suite, and safety behavior differs per vendor.
