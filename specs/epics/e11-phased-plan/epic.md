# e11 — Phased plan with gates (D11)

| Field | Value |
|-------|-------|
| Deliverable | `docs/deliverables/D11-phased-plan.md` |
| Depends on | e10 (first full version); revisited at every gate |

## Goal
Phases: reference site → integration v1 → fleet layer → aggregation v1 (partner signal) → aggregation v2 (own certified signal) → scale. Each phase has exit criteria, KPIs, staffing, and cost bands.

## Stories
| ID | Story | Owner role |
|----|-------|-----------|
| S1 | Exit criteria and KPIs per phase, linked to epics and tests. | architect |
| S2 | Staffing by role per phase. | architect |
| S3 | Cost bands with method. Every external price is cited or UNVERIFIED. | architect, source-verifier |
| S4 | Claims audit and human gate. | claims-auditor, human |

## Acceptance criteria
- [ ] Every gate has measurable exit criteria.
- [ ] Cost bands state their assumptions. No invented prices.
