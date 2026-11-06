# e08 — Fleet services spec + scaffolding (D08)

| Field | Value |
|-------|-------|
| Deliverable | `docs/deliverables/D08-fleet-services.md` |
| Depends on | e07 accepted |
| Constraints | C-01, C-17, C-18, C-19, C-20 |
| ADRs | ADR-0001, ADR-0009 |
| Output paths | `fleet/` |

## Goal
Tenancy and identity, headless provisioning, OTA and the version matrix (HA × HAEO × our integrations) with rollback, a per-stack contract-test matrix, observability SLOs, and per-tenant container orchestration with the compute math.

## Stories
| ID | Story | Owner role |
|----|-------|-----------|
| S1 | Tenancy and identity model; per-site certificates; CA lifecycle. | architect |
| S2 | Headless provisioning sequence through the HA config-flow REST API (verified shapes). | architect, source-verifier |
| S3 | WireGuard client-only topology. No inbound ports. | architect |
| S4 | OTA plus version matrix with rollback; canary rings. | architect |
| S5 | Compute math: measured per-container CPU/RAM at 200/400/600 entities including a HAEO solve. Use measurements, not estimates (OQ-015). | engineer |
| S6 | Observability SLOs and error budgets. | architect |
| S7 | License audit of every integration in the paid fleet (C-19). | source-verifier |
| S8 | Scaffolding under `fleet/` (orchestration manifests and a provisioning CLI skeleton). | engineer |
| S9 | Reviews and human gate. | reviewer, claims-auditor, human |

## Acceptance criteria
- [ ] No design element puts two tenants in one HA process.
- [ ] No shared admin tokens anywhere, including CI, images, and docs.
- [ ] Compute math is based on measured numbers with method and date.
- [ ] Rollback is tested in a documented drill.
