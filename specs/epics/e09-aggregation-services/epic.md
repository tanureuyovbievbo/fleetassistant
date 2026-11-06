# e09 — Aggregation services (D09)

| Field | Value |
|-------|-------|
| Deliverable | `docs/deliverables/D09-aggregation-services.md` |
| Depends on | e08 accepted |
| Constraints | C-11, C-12, C-16, C-21, C-22 |

## Goal
Capability ledger, qualified-capacity model with simultaneity math, an allocation solver that uses HAEO shadow prices as site marginal cost to build a fleet LP for the aggregate target (honoring availability, opt-outs, comfort floors, battery-life caps, fairness), a feedback trim loop, and a settlement/payout pipeline.

## Stories
| ID | Story | Owner role |
|----|-------|-----------|
| S1 | Verify how HAEO exposes shadow prices (entities/attributes, units, time alignment) — OQ-011. | source-verifier |
| S2 | Capability ledger and qualified-capacity model; simultaneity math with stated assumptions. | architect |
| S3 | Fleet LP formulation. The fleet solver allocates targets; it never re-optimizes a site (C-11). | architect |
| S4 | Feedback trim loop using reconciled telemetry. | architect |
| S5 | Settlement pipeline from the reconciled performance record to payouts; audit trail. | architect |
| S6 | Reviews and human gate. | reviewer, claims-auditor, human |

## Acceptance criteria
- [ ] Sites receive targets or prices from the fleet, and HAEO remains the only site optimizer.
- [ ] Coarse-tier capacity is never counted as firm.
- [ ] The commitments ledger prevents double counting across programs.
- [ ] Every program or market statement is cited or UNVERIFIED.
