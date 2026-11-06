# Test plan (living)

| Field | Value |
|-------|-------|
| Status | draft skeleton — expand with `plan-tests` per implementation epic |
| Updated | 2026-11-05 |

## Levels

| Level | Location | Runs against | Gate |
|-------|----------|--------------|------|
| Unit | `tests/unit/` | Pure Python, HA test harness | Every PR |
| Integration | `tests/integration/` | `pytest-homeassistant-custom-component` HA instance | Every PR |
| Contract — HAEO | `tests/contract/haeo/` | Live HA + **pinned** HAEO in a container | Every PR touching the bridge, nightly, every HAEO version bump |
| Contract — adapters | `tests/contract/adapters/` | Shared suite run against every adapter (stubs first) | Every PR touching adapters |
| Schema | `tests/schema/` | Site profile and telemetry JSON Schemas plus examples | Every PR |
| Static boundary checks | CI | grep or import-linter: only `haeo_bridge/` touches HAEO, only `adapters/` touches devices, no `.storage` writes | Every PR |
| Packaging | CI | hassfest, HACS action | Every PR, release |

## Must-have scenarios (traceable to constraints)

| ID | Scenario | Constraint | Epic |
|----|----------|-----------|------|
| T-01 | The three profile examples validate. The invalid-reference fixture fails with a clear error. | C-10 | e03 |
| T-02 | The bridge creates a hub, elements, and connections on a live pinned HAEO. | C-06, C-07 | e04 |
| T-03 | Re-applying the same profile produces zero operations. | C-10 | e04 |
| T-04 | An invalid reference is caught before apply → repair issue raised, nothing applied. | C-05 | e04 |
| T-05 | A HAEO version mismatch → repair issue, no apply. | C-07 | e04 |
| T-06 | Zero rule packs installed → valid HAEO price inputs. | C-13 | e05 |
| T-07 | The degradation term is present in compiled inputs. Never silently zero. | C-14 | e05 |
| T-08 | Out-of-range, no-consent, and rate-limited writes are rejected with reason and audit record. | C-09, C-18 | e06 |
| T-09 | Both stub adapters pass the identical contract suite. | C-09 | e06 |
| T-10 | Loss of comms → fail-safe values applied, non-performance reported. | C-12, C-15 | e06 |
| T-11 | An overlapping commitment over capacity is rejected by the ledger. | C-16 | e05/e06 |
| T-12 | Telemetry envelope validates. Dedupe on `(site_id, seq)`. | D07 | e07 |
