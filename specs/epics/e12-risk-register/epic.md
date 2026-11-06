# e12 — Risk register (D12)

| Field | Value |
|-------|-------|
| Deliverable | `docs/deliverables/D12-risk-register.md` |
| Depends on | e11; seeded at bootstrap; updated at every gate |

## Goal
Technical, operational, regulatory, and vendor-dependency risks with mitigations, plus the top 10 numbers to verify against primary sources before committing capital.

## Stories
| ID | Story | Owner role |
|----|-------|-----------|
| S1 | Collect risks raised in D01..D11 and OPEN_QUESTIONS. | architect |
| S2 | Score likelihood × impact. Assign an owner role and a mitigation. | architect |
| S3 | Top-10 numbers list with the primary source to check and the current status. | source-verifier |
| S4 | Human gate. | human |

## Acceptance criteria
- [ ] Every risk has a mitigation and a trigger.
- [ ] Every top-10 number is VERIFIED with a source or explicitly UNVERIFIED.
