# ADR-0005 — Site profile as code is the source of truth

| Field | Value |
|-------|-------|
| Status | accepted |
| Date | 2026-11-05 |
| Source | Project brief |
| Constraints | C-10 |

## Context
Fleet operations need per-site configuration that is reproducible and reviewable. A cloud-primary site must upgrade to gateway-primary without re-onboarding.

## Decision
A versioned site profile (D03) is the only input. A deterministic renderer emits config entries, helpers, automations, and the HAEO network plan. A profile diff produces a change plan. In fleet mode there is no hand-edited per-site config.

## Consequences
A schema migration policy is required. The UI options flow edits the profile, not the generated artifacts.

## Rejected alternatives
- **Hand-configured sites with exported backups:** not reproducible, and they drift.
- **A per-vendor setup wizard with no profile:** no source of truth.
