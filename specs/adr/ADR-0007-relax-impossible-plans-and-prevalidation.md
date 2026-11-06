# ADR-0007 — "Relax impossible plans" ON in fleet mode; pre-validate before apply

| Field | Value |
|-------|-------|
| Status | accepted (the option key must be confirmed, OQ-006) |
| Date | 2026-11-05 |
| Source | Project brief |
| Constraints | C-05, C-12 |

## Context
The brief says HAEO has a "Relax impossible plans" hub setting, off by default, and repair issues for broken references and unresolvable constraints. These details are UNVERIFIED (OQ-006). Fleet reliability needs a plan even when constraints conflict.

## Decision
- In fleet mode, the bridge sets "Relax impossible plans" to ON.
- In single-home mode, the proposed default is ON, and the user can change it in the options flow. D04 confirms this.
- Before any apply, the bridge runs referential-integrity pre-validation. It raises fleetassistant repair issues instead of letting HAEO fail.

## Consequences
A relaxed plan must be flagged in telemetry. It is never reported as firm performance (C-12).

## Rejected alternatives
- **Leaving the setting off in fleet mode:** sites stop producing plans when constraints are infeasible.
- **Relying on HAEO's repairs only:** errors appear only after apply.
