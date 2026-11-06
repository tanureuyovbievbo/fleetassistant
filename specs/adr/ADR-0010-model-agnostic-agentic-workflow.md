# ADR-0010 — Model-agnostic agentic workflow with files as the handoff

| Field | Value |
|-------|-------|
| Status | accepted |
| Date | 2026-11-05 |
| Source | User instruction at bootstrap |
| Constraints | AGENTS.md, CONVENTIONS.md §6 |

## Context
Different AI models may run different steps of the workflow. Chat history does not transfer between models.

## Decision
- Agent roles, skills, and prompts in `.pi/` are generic: no pinned models and no vendor-specific syntax.
- Every step reads its inputs from repo files and writes its outputs to repo files: `specs/state.yaml`, epic capsules, `_workspace/` handoff files, and `docs/updates/`.
- Every deliverable stops at a human gate.

## Consequences
Instructions are slightly more verbose. Each update entry records the model used, for traceability only.

## Rejected alternatives
- **Model-tuned prompts per role:** they break when the model is switched.
- **Chat-only handoff:** context is lost when the model is switched.
