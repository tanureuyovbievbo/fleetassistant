# e10 — Rule pack: California (D10, later phase)

| Field | Value |
|-------|-------|
| Deliverable | `docs/deliverables/D10-rule-pack-california.md` |
| Depends on | e09 accepted; rule-pack interface from e05 |
| Constraints | C-13, C-21, C-22 |

## Goal
Research and specify the California pack: licensing, registration, metering and settlement data path, certifications (OpenADR 2.0b VEN, SPARc, UL 2933, CETS, IEEE 1547-2018 / UL 1741 SB), fast-to-revenue ordering, and a partner-aggregator-first path. Rates and programs: TOU/EV rates, NEM 3.0 export curves, ELRP/DRIP/BatteryVPP targets. Every item is cited or marked UNVERIFIED.

## Stories
| ID | Story | Owner role |
|----|-------|-----------|
| S1 | Source list: CPUC, CEC, CAISO, IOU program pages, OpenADR Alliance, CEC-AC, UL, IEEE. Fetch and record. | source-verifier |
| S2 | Certification matrix with applicability, cost, and timeline. Cost and timeline are UNVERIFIED unless fetched. | source-verifier, architect |
| S3 | Fast-to-revenue ordering and the partner-aggregator-first path. | architect |
| S4 | Pack content spec (data only, with provenance per number). | architect |
| S5 | Claims audit (strict) and human gate. | claims-auditor, human |

## Acceptance criteria
- [ ] Zero uncited numbers.
- [ ] No implied certification or membership (C-21).
- [ ] Each program statement has a URL and fetch date.
