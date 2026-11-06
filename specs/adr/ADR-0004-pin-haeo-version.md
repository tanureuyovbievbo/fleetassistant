# ADR-0004 — Pin the HAEO version; working target v0.5.0

| Field | Value |
|-------|-------|
| Status | accepted (the version value must be re-confirmed at D04 start) |
| Date | 2026-11-05 |
| Source | F-007, F-011 |
| Constraints | C-07, C-23 |

## Context
The bridge depends on private flow details. The latest HAEO release at bootstrap is `v0.5.0`, published 2026-10-27 [F-011]. The `main` manifest version is `0.5.0` [F-007].

## Decision
fleetassistant declares `SUPPORTED_HAEO_VERSIONS`. The initial working target is `v0.5.0`. On a version mismatch, fleetassistant raises a repair issue and applies nothing. A version bump requires passing contract tests and an update to the OTA version matrix (D08).

## Consequences
Users on other HAEO versions see a repair issue. We must watch HAEO releases. This is a recurring task in the OTA process.

## Rejected alternatives
- **Floating on the latest HAEO:** breakage is unpredictable.
- **Vendoring HAEO:** violates C-04 and C-06.
