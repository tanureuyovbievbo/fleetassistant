# Handoff — start here (new agent)

| Field | Value |
|-------|-------|
| Written | 2026-11-05 |
| Repo state | Bootstrap complete (e00). Docs and plans only. **No implementation code.** |
| Product | fleetassistant (domain `fleetassistant`, ADR-0011) — HACS integration that composes HAEO |

## 1. Load context (in this order)
1. `AGENTS.md` — rules, session protocol, hard constraints.
2. `specs/state.yaml` — current epic, step, `next_action`, pending human decisions.
3. `docs/constraints/CONSTRAINTS.md` — C-01..C-24 (non-negotiables).
4. `docs/verification/FACTS_LEDGER.md` and `OPEN_QUESTIONS.md` — what is verified and what is not.
5. `.pi/README.md` and `.pi/skills/deliverable-lifecycle/SKILL.md` — how work flows.
6. The active epic: `specs/epics/e01-architecture-spec/epic.md` and `e01-tasks.yaml`.

## 2. Before any work
- [ ] Commit the bootstrap (it is uncommitted). Suggested message: `docs: bootstrap fleetassistant planning, specs, and agent harness`.
- [ ] Ask the human for the pending decisions in `specs/state.yaml` (`human_decisions_pending`): OQ-003 (license) and SPIKE-PULL-AHEAD.

## 3. Execution order
| # | Work | Command | Stop? |
|---|------|---------|-------|
| 1 | D01 architecture spec. Start with source verification of HAEO and HA docs (e01 S1). | `/deliver D01` | Human gate |
| 1b | *If approved:* e04 S1 HAEO config-flow spike in parallel (highest risk). Throwaway. Follow `.pi/skills/haeo-bridge-contract`. | engineer agent, `spike-prototype` skill | Report to human |
| 2 | D02 HACS packaging + loadable scaffold. Resolve OQ-001 (dependency install conflict). License ADR. Name collision check. | `/deliver D02` | Human gate |
| 3 | D03 site profile schema + 3 examples + validator | `/deliver D03` | Human gate |
| 4 | D04 HAEO bridge (spike → IR → pre-validator → applier → version guard → contract tests) | `/deliver D04` | Human gate |
| 5 | D05 price/target model + commitments ledger | `/deliver D05` | Human gate |
| 6 | D06 control adapters + executor + audit + fail-safe | `/deliver D06` | Human gate |
| 7 | D07 telemetry schema + publisher | `/deliver D07` | Human gate |
| 8+ | D08..D12 per `specs/release-plan.yaml` | `/deliver Dnn` | Human gate each |

Without the `/deliver` prompt, follow `.pi/prompts/deliver.md` by hand: verify → draft → review (reviewer + claims-auditor) → fix (max 2 loops) → update log → stop.

## 4. Known traps
- **OQ-001:** the brief says HA does not install custom-integration requirements. The HA developer docs say it tries to (F-014). Keep zero extra dependencies until D02 resolves this.
- **HAEO details are UNVERIFIED:** flow steps, field keys, element types, horizon format, "Relax impossible plans" key, shadow-price entities (OQ-002, -006, -007, -009, -011). Never guess them. The spike and source review must answer them.
- **HAEO pin:** working target `v0.5.0` (F-011). Re-confirm the latest release at D04 start.
- **Boundaries:** HAEO only through `haeo_bridge/` and the config-flow API. Devices only through `adapters/`. No `.storage` writes.
- **No regional tariff numbers in core.** v1 must run with zero rule packs.
- **Repo path:** the working copy is under `C:\Windows\System32\`. Tools may hit permission or 32/64-bit path redirection issues there. Prefer a clone in a user directory.

## 5. End of every session
Update `specs/state.yaml` (`current`, `next_action`), `specs/execution-status.yaml`, and add `docs/updates/YYYY-MM-DD-<topic>.md` with the model name used.
