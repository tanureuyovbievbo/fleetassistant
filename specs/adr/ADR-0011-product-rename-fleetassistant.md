# ADR-0011 — Product renamed to fleetassistant

| Field | Value |
|-------|-------|
| Status | accepted |
| Date | 2026-11-05 |
| Source | Human instruction: "rename the product to fleetassistant to match the repo" |
| Constraints | C-03, C-20, C-21 |
| Resolves | OQ-008 |
| Amends | Brief naming (display name "HA-OPENDERMS", domain `openderms`); ADR-0008 |

## Context
The repository is `fleetassistant`, but the brief named the product "HA-OPENDERMS" with domain `openderms` (OQ-008). HACS shows repository names, so a mismatch confuses users.

## Decision
- Product and display name: **fleetassistant**.
- HA domain: `fleetassistant`. It is a lowercase Python identifier with no dashes, and it does not collide with `haeo`.
- Integration path: `custom_components/fleetassistant/`.
- The brief stays verbatim. A note in `docs/00-charter/PROJECT_BRIEF.md` maps "HA-OPENDERMS"/"OpenDERMS" to fleetassistant.
- Every brief rule tied to the old name still applies: domain format, no collision, naming honesty, and "powered by Home Assistant · built on HAEO" marketing.

## Consequences
- Before release (D02), check HA core integrations and the HACS default list for an existing `fleetassistant` domain or name. If a collision exists, a new ADR picks a different domain.
- The name contains "assistant", which echoes "Home Assistant". Marketing MUST NOT suggest an official Home Assistant product (C-20). The claims-auditor checks this.
- The display name may later get a styled form (for example "Fleet Assistant"). Changing the display name only needs a new ADR. Changing the domain after release breaks existing installs, so the domain is fixed from v1.

## Rejected alternatives
- **Rename the repo to match HA-OPENDERMS:** the human chose the opposite direction.
- **Keep domain `openderms` with the new display name:** two names for one product confuse users and support.
