# D03 — Site Profile Schema (versioned)

| Field | Value |
|-------|-------|
| ID | D03 |
| Epic | e03-site-profile-schema |
| Version | 0.0.0 (stub) |
| Status | implemented |
| Owner role | architect |
| Last updated | 2026-11-05 |
| Depends on | D01, D02, C-09, C-10, C-12, C-14, C-16, ADR-0005 |

> **Implementation:** schema v1 validator + published JSON Schema + 3 examples + 4 invalid fixtures; migrations are a seam only (no v2 yet).
>
> The outline below remains the acceptance contract; code lands against it.
>
> **Stub outline.** Required structure and acceptance criteria.

## Output files

- `site_profiles/schema/site-profile.v1.schema.json` (JSON Schema draft 2020-12)
- `site_profiles/examples/tesla-cloud-primary.yaml`
- `site_profiles/examples/solark-shelly-ac-ev-gateway-primary.yaml`
- `site_profiles/examples/multi-hub-adu.yaml`
- This document (rationale and field reference)

## Required outline

1. **Versioning policy.** `schema_version` field, SemVer rules, the migration function contract (vN → vN+1), and the deprecation window.
2. **Top-level structure.** Proposed sections (final names decided in this deliverable): `schema_version`, `site` (id, timezone, location granularity per C-18 minimization), `deployment_profile` (`cloud_primary` | `gateway_primary`), `systems[]` (one per HAEO hub), `metering` (topology, meters, CT points, source authority), `assets[]` (inverters, batteries, PV, EVSE, HVAC, relays/circuits), `controllables[]` (capability → adapter binding + limits), `pricing` (provider refs, overlay refs, `battery_degradation_cost`), `consent` (per capability, per program), `commitments` (ledger seed; empty in v1), `rule_packs[]` (references only), `telemetry` (cadence and minimization flags), `fail_safe` (gateway-primary only).
3. **Capability limits.** These mirror the C-09 descriptor: `min`, `max`, `rate_limit`, `hysteresis`, `consent_required`, `backing`.
4. **Referential integrity rules.** Unique IDs, every reference resolves, every system has a grid/meter node, every connection connects existing nodes. These rules are shared with the D04 pre-validation.
5. **Secrets.** The profile NEVER contains secrets. Use references to HA Application Credentials or secret store keys (C-17, C-18).
6. **Upgrade path.** A cloud-primary profile becomes gateway-primary by changing a diff, with no re-onboarding (brief). Show the diff between example 1 and a hypothetical upgrade.
7. **Worked examples** (3), with comments explaining each choice. Every vendor device type and every entity reference is either an F-ID-backed name or a clearly marked placeholder (C-23).
8. Open questions · Constraint compliance · Change log.

## Acceptance criteria

- [ ] All three examples validate against the schema (a test is listed in `specs/tech-architecture/TEST_PLAN_LATEST.md`).
- [ ] An invalid-reference fixture fails with a clear error message.
- [ ] The `battery_degradation_cost` field exists and is required when a battery exists (C-14).
- [ ] No secrets and no precise geolocation by default (C-18).
- [ ] Human review gate passed.
