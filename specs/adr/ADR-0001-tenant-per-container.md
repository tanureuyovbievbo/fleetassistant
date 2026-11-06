# ADR-0001 — Tenant per container; never fork HA Core

| Field | Value |
|-------|-------|
| Status | accepted |
| Date | 2026-11-05 |
| Source | Project brief |
| Constraints | C-01 |

## Context
HA is single-tenant. A site has about 200–600 entities. HA degrades past tens of thousands of entities in one event loop, and HAEO solves inside that loop (brief).

## Decision
Each tenant runs in its own HA container. We never fork HA Core to make it multi-tenant. We never host several tenants as config entries in one shared core.

## Consequences
Fleet orchestration (D08) manages many small containers. The compute cost per container must be measured (OQ-015). Isolation and blast radius are per tenant.

## Rejected alternatives
- **Multi-tenant core fork:** permanent merge burden, and it breaks the upstream compatibility model.
- **Tenant per config entry in a shared core:** one event loop serves all tenants, so tenants slow each other down. A secret-isolation failure exposes every tenant.
