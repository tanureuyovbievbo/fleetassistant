# Tech stack (planned)

| Field | Value |
|-------|-------|
| Status | planned — no code yet |
| Updated | 2026-11-05 |
| Authoritative detail | D01 (architecture), D02 (packaging) |

## v1 — Home Assistant integration

| Concern | Choice | Basis |
|---------|--------|-------|
| Runtime | Python, inside the HA asyncio event loop | HA integration model |
| Form factor | `custom_components/fleetassistant/`, distributed through HACS | C-02, ADR-0008 |
| Optimizer | HAEO (domain `haeo`, HiGHS via highspy) — composed, not embedded | F-001, F-006, F-013, C-04 |
| HAEO pin (working target) | `v0.5.0` | F-011, ADR-0004 (re-confirm in D04) |
| Minimum HA (working floor) | 2026.1.1 (HAEO's floor) | F-010, OQ-004 |
| Configuration | Config flow + options flow; repairs for errors | C-05 |
| Our runtime dependencies | None beyond HA core packages (target) | C-08, OQ-001 |
| Schema validation | Decide in D03: an HA-core-available library (for example `voluptuous`, which HA uses) or vendored pure Python. Confirm availability (C-08, C-23). | D03 |
| Tests | pytest, pytest-homeassistant-custom-component, contract tests vs live HAEO in a container | TEST_PLAN |
| Lint / types | ruff, mypy | CONVENTIONS §5 |
| CI | GitHub Actions: lint, tests, hassfest, HACS validation, contract matrix, release zip | D02 |

## v2 — Fleet services (outside HA)

The fleet stack is decided in D08. Fixed requirements: tenant per container (C-01), WireGuard client-only (C-17), per-tenant secrets and encryption at rest (C-18), an append-only audit store, and an LP solver for fleet allocation (D09). Fleet services are not bound by HA's dependency rules, but are bound by the license audit (C-19).

## Module boundaries (enforced)

```
custom_components/fleetassistant/
  haeo_bridge/   ← only HAEO touchpoint (C-06, C-07)
  adapters/      ← only device touchpoint (C-09)
  profile/       ← schema, validation, renderer (C-10)
  pricing/       ← providers, overlay, degradation, rule-pack registry (C-13, C-14)
  ledger/        ← commitments ledger (C-16)
  telemetry/     ← schema + publisher (D07)
  audit/         ← append-only audit log (C-18)
  executor/      ← plan execution cadence (D06)
```
