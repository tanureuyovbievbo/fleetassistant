# e07 — Telemetry & measurement schema (D07)

| Field | Value |
|-------|-------|
| Deliverable | `docs/deliverables/D07-telemetry-measurement-schema.md` |
| Depends on | e06 accepted |
| Constraints | C-12, C-16, C-18, C-24 |
| Output paths | `custom_components/fleetassistant/telemetry/`, `site_profiles/schema/` (telemetry schemas may live under `docs/schemas/`; decide in D07) |

## Goal
Versioned payloads, cadences, source authority (gateway > vendor cloud), quality flags, HAEO plan and performance capture, and the single reconciled performance record that later feeds claims and payouts.

## Stories
| ID | Story | Owner role |
|----|-------|-----------|
| S1 | Envelope schema (site_id, seq, schema_version, source, authority, quality) and payload types. | architect |
| S2 | Cadence table with vendor quota math per cloud adapter (C-24). | architect, source-verifier |
| S3 | HAEO plan capture (plan snapshot, relaxed flag, shadow prices if exposed). | engineer |
| S4 | Reconciled performance record: baseline method placeholder (program-specific methods arrive with rule packs), delivered vs committed, authority, quality. | architect |
| S5 | Publisher with local buffering and dedupe (T-12). Field-level minimization and retention table. | engineer |
| S6 | Reviews and human gate. | reviewer, claims-auditor, human |

## Acceptance criteria
- [ ] Every field has a purpose and retention period (minimization).
- [ ] Gateway data always outranks vendor-cloud data for the same quantity.
- [ ] Relaxed plans and coarse-tier data are flagged and never reported as firm.
- [ ] T-12 passes.
