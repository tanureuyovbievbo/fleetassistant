# D08 — Fleet Services Specification + Scaffolding

| Field | Value |
|-------|-------|
| ID | D08 |
| Epic | e08-fleet-services |
| Version | 0.0.0 (stub) |
| Status | not-started |
| Owner role | architect (spec) → engineer (scaffolding) |
| Last updated | 2026-11-05 |
| Depends on | D01–D07, C-01, C-11, C-12, C-17, C-18, C-19, C-20, ADR-0001, ADR-0009, OQ-009, OQ-015 |

> **Stub.** Required outline and acceptance criteria only.

## Required outline

1. **Tenancy and identity.** One tenant = one HA container (C-01). Tenant ID, site ID, per-site device identity, client certificates, the certificate lifecycle (issue, rotate, revoke), and per-tenant secret isolation (C-18).
2. **Headless provisioning.** Sequence: create container → bootstrap HA → onboarding via API → install HAEO + fleetassistant at pinned versions → create config entries via the config-flow REST API → apply the site profile. No shared admin tokens. Scoped OAuth2 via Application Credentials (C-17). Every API shape is F-ID-backed.
3. **Networking.** WireGuard client-only from the gateway. No inbound ports. Nabu Casa cloud is not used as our relay (C-20).
4. **OTA and version matrix.** HA × HAEO × fleetassistant (× device integrations): supported combinations, canary rings, health gates, and rollback (snapshot plus pinned versions).
5. **Per-stack contract-test matrix.** Stack (vendor/protocol) × adapter × HAEO version → test suite and status.
6. **Observability SLOs.** For example plan freshness, telemetry completeness, control-write success, and solve duration. Targets are proposed, and marked as proposals until measured.
7. **Per-tenant container orchestration and compute math.** Entities per site (200–600 per brief), CPU/RAM per container measured at the solve cadence (OQ-015), packing density, and the cost per site. No numbers without a benchmark source.
8. **License audit.** Create `docs/verification/LICENSE_AUDIT.md` for every third-party integration in the fleet image (C-19).
9. **Scaffolding.** `fleet/` directory skeleton with READMEs and interface stubs only (no business logic). Infra-as-code layout proposal.
10. Open questions · Constraint compliance · Change log.

## Acceptance criteria

- [ ] No design places two tenants in one HA process.
- [ ] No inbound ports. No shared admin tokens.
- [ ] Compute math uses only measured or cited numbers.
- [ ] A rollback path exists for every OTA ring.
- [ ] Human review gate passed.
