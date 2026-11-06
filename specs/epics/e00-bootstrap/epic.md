# e00 — Repository bootstrap and agentic harness

| Field | Value |
|-------|-------|
| Status | accepted (2026-11-05) |
| Deliverable | none |
| Update log | `docs/updates/2026-11-05-bootstrap.md` |

## Goal
Create the documentation, plans, constraint register, verification ledgers, ADRs, epic capsules, and a model-agnostic agent harness (`.pi/`). No implementation code.

## Stories
- S1 Charter: brief stored verbatim, constraints C-01..C-24 extracted.
- S2 Verification: sources, facts ledger, open questions seeded with fetched HAEO and HA facts.
- S3 Plans: release plan, epics e01..e12, deliverable skeletons D01..D12.
- S4 Harness: agents, skills, prompts in `.pi/`. No pinned models.
- S5 Placeholders: code directories with README files that state the owning deliverable.

## Acceptance
- [x] Every deliverable in the brief has a skeleton and an epic.
- [x] Every non-negotiable maps to a constraint ID and, where architectural, to an ADR.
- [x] No implementation code exists.
