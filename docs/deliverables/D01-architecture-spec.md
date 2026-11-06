# D01 — Architecture Specification

| Field | Value |
|-------|-------|
| ID | D01 |
| Epic | e01-architecture-spec |
| Version | 0.0.0 (stub) |
| Status | not-started |
| Owner role | architect |
| Last updated | 2026-11-05 |
| Depends on | Brief, C-01…C-24, ADR-0001…ADR-0010, F-001…F-014 |

> **Stub.** This file defines the required outline and acceptance criteria. The drafting agent replaces each `TODO` and keeps the headings.

## Required outline

1. **Purpose and scope.** v1 (integration) compared with v2 (fleet). Out-of-scope list.
2. **System context.** Mermaid C4-style context diagram: homeowner/installer, HA instance, HAEO, fleetassistant, vendor clouds, local devices, fleet services (v2), partner aggregator (later).
3. **v1 integration scope.** Components and responsibilities:
   - Site profile loader and validator
   - Renderer (profile → HA artifacts and HAEO network plan)
   - HAEO bridge (`haeo_bridge/`, versioned, the only HAEO touchpoint)
   - Price/target model (providers, overlay, degradation term, rule-pack registry)
   - Control-adapter layer (the only device touchpoint)
   - Plan executor (reads the HAEO plan and calls adapters at a set cadence)
   - Commitments ledger
   - Telemetry publisher
   - Audit log
   - Repairs and diagnostics
4. **v2 fleet services (overview only).** Tenancy and identity, provisioning, OTA, observability, dispatch, settlement, consumer app. These are detailed in D08 and D09.
5. **Deployment profiles.** Cloud-primary compared with gateway-primary: a table of control authority per capability, connectivity, fail-safe, and dispatch eligibility. Describe the upgrade path (re-point the profile, no re-onboarding).
6. **Data flows.** Mermaid sequence diagrams:
   - (a) install and onboarding
   - (b) profile → render → HAEO provisioning
   - (c) price and forecast inputs → HAEO solve → plan → executor → adapters
   - (d) telemetry → fleet
   - (e) fleet dispatch target → site (later phase)
   - (f) loss of comms → local defaults
7. **Control-adapter seam.** Interface summary, capability descriptor, authority tiers. Full detail is in D06.
8. **Site profile as source of truth.** The render pipeline, determinism, diff → change plan, and the fleet-mode rule that forbids hand edits.
9. **HAEO bridge design.** Version pinning, flow-driving mechanism (see OQ-002, OQ-009), pre-validation, idempotent apply, drift detection, contract tests, and the upgrade procedure.
10. **Control authority and performance claims.** Tier rules (C-12) and non-performance reporting.
11. **Security and privacy architecture.** Summary that links to `SECURITY_PLAN_LATEST.md`.
12. **Rejected alternatives**, each with reasons and the constraint or fact it violates:
    - Multi-tenant HA Core fork (C-01)
    - Hub-and-spoke `remote_homeassistant` as production (single point of failure, authority ambiguity, C-11/C-12; verify the integration's status and license before citing)
    - Dual HAEO per site (cloud + gateway) (C-11)
    - Writing HAEO storage directly (C-06)
    - HAOS add-on as the primary form factor (C-02; does not run on HA Container/Core installs; Supervisor dependency)
13. **Open questions.**
14. **Constraint compliance.**
15. **Change log.**

## Acceptance criteria

- [ ] Every component in §3 has one owner module path under `custom_components/fleetassistant/`.
- [ ] Only the bridge touches HAEO. Only adapters touch devices. Both are shown in a diagram.
- [ ] No HAEO or HA identifier appears without an F-ID or an UNVERIFIED mark (C-23).
- [ ] Each rejected alternative cites the violated C-ID.
- [ ] No design requires two optimizers for one site (C-11).
- [ ] The constraint compliance table covers C-01 to C-24.
- [ ] A human has reviewed and approved the document (gate).
