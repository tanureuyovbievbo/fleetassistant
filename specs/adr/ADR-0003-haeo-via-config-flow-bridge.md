# ADR-0003 — Configure HAEO only through HA's config-flow API, through one versioned bridge

| Field | Value |
|-------|-------|
| Status | accepted |
| Date | 2026-11-05 |
| Source | Project brief; F-002 |
| Constraints | C-04, C-06, C-07 |

## Context
HAEO uses `config_flow: true` [F-002]. The brief says HAEO is configured through the UI and config flow only: hub, then elements, then connections. The exact steps and fields are UNVERIFIED (OQ-002). The flow fields are an unstable private API.

## Decision
One module, `custom_components/fleetassistant/haeo_bridge/`, drives HAEO hub, element, and connection creation through HA's config-flow API. It never writes HAEO files or storage. It is versioned per supported HAEO version and contract-tested against a live HAEO.

## Consequences
The bridge breaks when HAEO changes its flows. Contract tests detect this before a release. Headless fleet provisioning depends on whether HAEO flows, including any subentry flows, can be driven over REST or WebSocket (OQ-009).

## Rejected alternatives
- **Writing `.storage/core.config_entries` directly:** bypasses validation, corrupts data when the schema changes, and violates the composability rule (C-06).
- **Forking HAEO to add a YAML import:** permanent fork burden (C-04).
- **Reimplementing the optimizer:** violates C-04 and C-11.
