# D10 — Rule Pack: California (later phase)

| Field | Value |
|-------|-------|
| ID | D10 |
| Epic | e10-rule-pack-california |
| Version | 0.0.0 (stub) |
| Status | not-started (later phase — not a v1 feature) |
| Owner role | source-verifier (research) → architect (pack design) |
| Last updated | 2026-11-05 |
| Depends on | D05 (rule-pack interface), D07, D09, C-13, C-21, C-22, OQ-014 |

> **Stub.** Every factual statement in this deliverable MUST carry an S-ID from a fetched primary source (CEC, CPUC, CAISO, IOU program pages, OpenADR Alliance, CEC-AC, UL, IEEE, NIST), or be marked **UNVERIFIED** and listed under OQ-014. Do not invent rates, minimums, incentive amounts, certification costs, or timelines.

## Required outline

1. **Scope.** TOU/EV rate schedules, NEM 3.0 export value curves, and program targets (ELRP, DRIP, BatteryVPP — confirm the current names and status of each program from primary sources).
2. **Licensing and registration.** Which entity registrations apply to us or to a partner aggregator (for example as a demand response provider). Cite each one.
3. **Metering and settlement data path.** Data sources, baseline methods, and how they map to the D07 reconciled record.
4. **Certifications** — for each: what it is, who certifies, whether it applies to us, the evidence required, and cost/time (UNVERIFIED unless cited):
   - OpenADR 2.0b VEN
   - CEC-AC SPARc
   - UL 2933
   - CETS
   - IEEE 1547-2018 / UL 1741 SB (inverter-level; usually the device vendor's responsibility — verify)
5. **Fast-to-revenue ordering.** Partner-aggregator-first path compared with direct enrollment. Dependencies and gates.
6. **Pack implementation plan.** Data files under `rule_packs/us-ca/` following the D05 interface. Each number carries provenance.
7. **Naming honesty (C-21).** Statements we may and may not make, with dates.
8. Open questions · Constraint compliance · Change log.

## Acceptance criteria

- [ ] `/verify-claims` reports zero uncited factual statements.
- [ ] Every certification line has a status (`not started`, `in progress`, `achieved` with a date and evidence, or `not applicable` with a reason).
- [ ] Human review gate passed.
