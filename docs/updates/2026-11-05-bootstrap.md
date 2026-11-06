# 2026-11-05 — bootstrap

| Field | Value |
|-------|-------|
| Role(s) | architect (bootstrap) |
| Model(s) used | recorded in git history (traceability only) |
| Epic / deliverable | e00 / — |

## Done
- Created the repository scaffold: README, AGENTS.md (canonical, model-agnostic), CLAUDE.md pointer, CONVENTIONS.md, CHANGELOG.md, .gitignore.
- Preserved the founding brief verbatim in `docs/00-charter/PROJECT_BRIEF.md`.
- Extracted constraints C-01…C-24 with reviewer checks.
- Created deliverable stubs D01…D12 with required outlines and acceptance criteria. D12 has a seeded risk register.
- Created the planning spine in `specs/`: state, release plan (e00–e12), execution status, planning status, vision, scope, glossary, ADR-0001…ADR-0010, tech-architecture plans, bug registry.
- Created the harness in `.pi/`: 5 generic agent roles, 4 project skills, 4 orchestration prompts.
- Created placeholder directories with READMEs (no code): `custom_components/openderms/`, `site_profiles/`, `rule_packs/`, `fleet/`, `tests/`.
- Per user instruction: **no implementation code**. A different model will implement.

## Decisions (link ADRs)
- ADR-0001…ADR-0010 record the brief's non-negotiables as accepted decisions.
- ADR-0004: working HAEO pin target is `v0.5.0` (F-011). It must be re-confirmed in D04.

## New facts / sources
- S-001…S-006 and F-001…F-014 (HAEO manifest, hacs.json, releases, license; HA manifest requirements doc).

## New or changed open questions
- OQ-001…OQ-015 created. **OQ-001 is a conflict between the brief and the HA developer docs** about dependency installation. OQ-003 (license) and OQ-008 (repo name) need a human.

## Blockers / needs human
- OQ-003 license decision (needed by the D02 gate).
- OQ-008 repo rename decision (optional, before HACS submission).
- Decide whether to pull the e04 S1 HAEO bridge spike ahead to run in parallel with D01 (recommended; see `specs/release-plan.yaml` note).

## Next action (exact, for the next agent)
- Run `/deliver D01` (`.pi/prompts/deliver.md`). Start with the source-verifier fetching the HAEO docs (haeo.io) and HA config-flow docs queued in `docs/verification/SOURCES.md`.
