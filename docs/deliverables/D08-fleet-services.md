# D08 — Fleet Services Specification + Scaffolding

| Field | Value |
|-------|-------|
| ID | D08 |
| Epic | e08-fleet-services |
| Version | 0.0.0 (stub) |
| Status | in-progress (version matrix written; tenancy/provisioning/orchestration open) |
| Owner role | architect (spec) → engineer (scaffolding) |
| Last updated | 2026-11-06 |
| Depends on | D01–D07, C-01, C-11, C-12, C-17, C-18, C-19, C-20, ADR-0001, ADR-0009, OQ-009, OQ-015 |

> **In progress.** The outline below is the spec skeleton. Item 4 (OTA and version
> matrix) now has an implementation document: [`docs/ops/VERSION_MATRIX.md`](../ops/VERSION_MATRIX.md),
> which records the single supported HA × HAEO × fleetassistant combination, the
> procedure that turns an unverified combination into a supported one, and the
> per-tenant rollback table. Everything else in this deliverable is still outline:

## Implementation notes

- **Version matrix (item 4).** `docs/ops/VERSION_MATRIX.md` pins the layers and
  says where each pin lives (`hacs.json`, `SUPPORTED_HAEO_VERSIONS`,
  `manifest.json`, a pack's `integration.domain`). The only row so far is marked
  UNVERIFIED because no live instance has run; the `xfail(strict=True)` contract
  tests are the tripwire that flips it.
- **Rollback (item 4).** Rollback is per tenant and per layer: HAEO pin, image
  tag, integration release zip. The site profile lives outside the integration,
  so a rollback never re-onboards a site (C-10).
- **Not started:** tenancy/identity (item 1), headless provisioning sequence
  (item 2), WireGuard topology (item 3), per-stack contract matrix (item 5),
  observability SLOs (item 6), compute math (item 7, blocked on OQ-015), the
  licence audit (item 8, blocked on OQ-003/OQ-023).

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
- [x] A rollback path exists for every OTA ring (per-layer, per-tenant; `docs/ops/VERSION_MATRIX.md`).
- [ ] Human review gate passed.
