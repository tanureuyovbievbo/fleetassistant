# ADR-0008 — HACS integration is the primary form factor (not an HAOS add-on)

| Field | Value |
|-------|-------|
| Status | accepted (name amended by ADR-0011) |
| Date | 2026-11-05 |
| Source | Project brief |
| Constraints | C-02, C-03 |

## Context
The product must install into an existing HA, including Container and Core installs. It must compose HAEO in the same process.

## Decision
Ship as `custom_components/fleetassistant/` through HACS, with display name "fleetassistant" and domain `fleetassistant`. Fleet-side services run outside HA (v2).

## Consequences
v1 has no Supervisor-managed sidecar process. Heavy work runs either in HA's event loop (bounded) or in fleet services.

## Rejected alternatives
- **HAOS add-on as the primary form factor:** needs Supervisor, which Container and Core installs do not have. It runs as a separate process without in-process config-flow access.
- **HA Core fork:** violates C-01.
