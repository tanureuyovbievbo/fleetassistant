# e01 — Architecture spec (D01)

| Field | Value |
|-------|-------|
| Deliverable | `docs/deliverables/D01-architecture-spec.md` |
| Depends on | e00 |
| Constraints | all (C-01..C-24) |
| Prompt | `/deliver D01` |

## Goal
A reviewed architecture spec covering v1 integration scope, v2 fleet services, the two deployment profiles, data flows, the control-adapter seam, site profile as source of truth, HAEO bridge design, and rejected alternatives.

## Stories
| ID | Story | Owner role |
|----|-------|-----------|
| S1 | Fetch and record the HAEO docs (hub, elements, connections, horizon, pricing, shadow prices, repairs) and the HA docs (config flow, options flow, repairs, REST, WebSocket, Application Credentials). Update SOURCES, FACTS_LEDGER, OPEN_QUESTIONS. | source-verifier |
| S2 | Draft D01 sections 1–9 from the template, using only F-IDs and constraint IDs. | architect |
| S3 | Rejected-alternatives section: multi-tenant core fork, hub-and-spoke `remote_homeassistant` in production, dual HAEO per site, writing HAEO storage directly, HAOS add-on as the primary form factor. Each with reasons. | architect |
| S4 | Data-flow diagrams (Mermaid) for cloud-primary, gateway-primary, and upgrade path. | architect |
| S5 | Constraints review and claims audit. | reviewer, claims-auditor |
| S6 | Threat model pass with the `security-review` skill. Update the SECURITY_PLAN. | reviewer |
| S7 | Human gate. | human |

## Acceptance criteria
- [ ] Every architectural claim about HAEO or HA cites an F-ID or is marked UNVERIFIED with an OQ.
- [ ] A dual-optimization path does not exist. If any design forces one, it is flagged as a defect (C-11).
- [ ] Authority tiers and fail-safe behavior are explicit for each deployment profile (C-12, C-15).
- [ ] The upgrade cloud-primary → gateway-primary needs no re-onboarding (profile re-point only).
- [ ] The rejected-alternatives section covers all five named alternatives.
- [ ] `_workspace/D01_review_constraints.md` and `_workspace/D01_review_claims.md` both PASS.
