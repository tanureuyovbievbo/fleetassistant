# Security & privacy plan (living)

| Field | Value |
|-------|-------|
| Status | draft skeleton — expand in D01, D06, D07, D08 |
| Updated | 2026-11-05 |
| Constraints | C-17, C-18, C-19, C-20 |
| Target | Design for SOC 2 scope from day one (the trust services criteria list must be fetched before mapping; until then, UNVERIFIED) |

## Control map

| # | Requirement (brief) | Control | Where specified | Evidence / test |
|---|---------------------|---------|-----------------|-----------------|
| 1 | Headless provisioning via the config-flow REST API | Scoped provisioning credential, short-lived, per site | D08 §2 | TODO |
| 2 | Per-site device identity + client certificates | Per-site cert, rotation, revocation list | D08 §1 | TODO |
| 3 | WireGuard client-only, no inbound ports | Gateway initiates. Firewall default-deny inbound. | D08 §3 | Port scan in CI/QA |
| 4 | Scoped OAuth2 via HA Application Credentials | Vendor OAuth through Application Credentials, never hard-coded | D06, D08 | TODO |
| 5 | Never ship shared admin tokens | Secret scanning in CI. Images built without tokens. | D02, D08 | Secret scan job |
| 6 | Per-tenant secret isolation | Separate secret store namespace per tenant container | D08 | TODO |
| 7 | Encryption at rest | Volume encryption plus secret-store encryption | D08 | TODO |
| 8 | Telemetry minimization | Field-level purpose and retention table | D07 §9 | Schema review |
| 9 | CCPA/CPRA-conscious retention and deletion | Retention schedule, deletion workflow, export on request (cite the CPPA/statute when written) | D07, D08 | TODO |
| 10 | Append-only audit log of every dispatch and control write | Audit record emitted by the adapter safety pipeline, hash-chained or WORM storage | D06 §3, D08 | Unit test: every write → one audit record |
| 11 | Licensing hygiene | License audit per integration | D08 §8 | LICENSE_AUDIT.md |
| 12 | Nabu Casa cloud not used as our relay | Own WireGuard path | D08 §3 | Architecture review |

## Threat model

To be produced with the `security-review` skill at the D01 gate (STRIDE per data flow in D01 §6).
