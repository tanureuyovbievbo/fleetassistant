# D07 — Telemetry & Measurement Schema

| Field | Value |
|-------|-------|
| ID | D07 |
| Epic | e07-telemetry-schema |
| Version | 0.0.0 (stub) |
| Status | in-progress |
| Owner role | architect |
| Last updated | 2026-11-05 |
| Depends on | D03, D04, D06, C-12, C-18, C-24, OQ-005 |

> **Implementation:** envelope v1, validator, dedupe, summary exist; publisher transport and fleet ingest not started.
>
> The outline below remains the acceptance contract; code lands against it.
>
> **Stub outline.** Required structure and acceptance criteria.

## Output files

- `docs/deliverables/D07-telemetry-measurement-schema.md` (this file)
- `custom_components/fleetassistant/telemetry/schema/*.v1.schema.json` (created at implementation)

## Required outline

1. **Envelope.** `schema`, `schema_version`, `site_id` (pseudonymous), `system_id`, `ts`, `seq`, `source`, `authority`, `quality`, `payload`.
2. **Payload types.** `measurement` (power, energy, SOC, temperature), `plan_snapshot` (HAEO plan + shadow prices + inputs hash), `control_event` (mirrors the audit record), `availability`, `health`.
3. **Cadences.** Per payload and per deployment profile. Quota math for each cloud vendor before promising a cadence (C-24).
4. **Source authority.** Gateway meter > gateway device > vendor cloud > estimate. Conflict resolution rules.
5. **Quality flags.** `ok`, `estimated`, `stale`, `gap_filled`, `clock_skew`, `out_of_range`, `vendor_delayed`.
6. **Plan and performance capture.** What we store from each HAEO solve to later prove performance against the plan.
7. **Reconciled performance record.** A single record per site per interval per program commitment. It feeds claims and payouts (D09). Includes baseline method references (method names only; region rules come from rule packs).
8. **Transport.** Options (MQTT over WireGuard, HTTPS batch), at-least-once delivery, dedupe on `(site_id, seq)`, offline buffering.
9. **Privacy (C-18).** Minimization table (field → purpose → retention → deletion path).
10. Open questions · Constraint compliance · Change log.

## Acceptance criteria

- [ ] Every field has a unit, a type, and a minimization justification.
- [ ] Every vendor cadence has quota math or an UNVERIFIED mark.
- [ ] The reconciled record definition is unambiguous enough to compute a payout from.
- [ ] Human review gate passed.
