# AGENTS.md — fleetassistant

Canonical instructions for any AI coding agent working in this repository. This file is **model-agnostic**. Models can change between sessions and between workflow steps. Do not rely on memory from earlier sessions. Rely on the files listed below.

`CLAUDE.md` and any other vendor-specific instruction files are pointers to this file. Edit this file only.

<!-- BEGIN bigpowers:project -->
## Project

- **Name:** fleetassistant (display name). Python domain: `fleetassistant`.
- **What:** A Home Assistant custom integration (v1, distributed through HACS) that composes HAEO as the site optimizer. Fleet services follow later (v2).
- **Phase:** Planning and documentation. Implementation has not started.
- **Language and runtime (v1):** Python, running inside the Home Assistant event loop (asyncio).
- **Source of the brief:** [`docs/00-charter/PROJECT_BRIEF.md`](docs/00-charter/PROJECT_BRIEF.md).
<!-- END bigpowers:project -->

<!-- BEGIN bigpowers:context-routing -->
> **New agent?** Read `docs/HANDOFF.md` first. It lists the execution order and known traps.

## Session start (MUST do, in this order)

1. Read [`specs/state.yaml`](specs/state.yaml). It holds the current deliverable, status, and next action.
2. Read [`docs/constraints/CONSTRAINTS.md`](docs/constraints/CONSTRAINTS.md). The constraints C-01 to C-24 are non-negotiable.
3. Read the active epic capsule: `specs/epics/<active_epic>/epic.md`.
4. Read [`docs/verification/OPEN_QUESTIONS.md`](docs/verification/OPEN_QUESTIONS.md) and [`docs/verification/FACTS_LEDGER.md`](docs/verification/FACTS_LEDGER.md).
5. Read the newest file in [`docs/updates/`](docs/updates/).

## Where things live

| Need | File |
|------|------|
| Deliverable order and status | `specs/release-plan.yaml`, `specs/execution-status.yaml` |
| One deliverable's scope, tasks, exit criteria | `specs/epics/eNN-*/epic.md` |
| Deliverable document (output) | `docs/deliverables/Dnn-*.md` |
| Decisions | `specs/adr/ADR-*.md` |
| Verified facts with sources | `docs/verification/FACTS_LEDGER.md` |
| Unverified items and open questions | `docs/verification/OPEN_QUESTIONS.md` |
| Glossary | `specs/product/GLOSSARY_LATEST.yaml` |
| Agent roles, skills, workflows | `.pi/agents/`, `.pi/skills/`, `.pi/prompts/` |
<!-- END bigpowers:context-routing -->

## Hard rules (MUST / NEVER)

- MUST stop for human review after each deliverable. NEVER start the next deliverable without approval.
- MUST cite a primary source (URL and access date) for every regulatory, rate, market, certification, or standards claim.
- MUST mark any claim you cannot verify as `UNVERIFIED` and add it to `OPEN_QUESTIONS.md`.
- NEVER cite a document you did not fetch in this session or that is not in `FACTS_LEDGER.md`.
- NEVER invent rates, capacity minimums, incentive amounts, certification costs, timelines, entity names, service names, flow steps, config keys, or units.
- MUST confirm HAEO names and fields against haeo.io docs or the `hass-energy/haeo` source at the pinned version.
- MUST confirm HA API shapes against developers.home-assistant.io.
- NEVER fork Home Assistant Core. NEVER write into HAEO files, storage, or internals.
- NEVER let any module except a control adapter touch a device.
- NEVER claim OpenADR, SPARc, UL, IEEE, ISO, or utility certification or registration without dated evidence.
- NEVER use the Home Assistant brand as our brand. Use "powered by Home Assistant · built on HAEO".
- MUST flag any design that needs two optimizers per site as a defect.
- MUST keep agent prompts and skills model-agnostic. NEVER add model-specific syntax or a `model:` pin to `.pi/agents/*.md` unless a human asks for it.

## Session end (MUST do)

1. Update `specs/state.yaml`: `last_session`, `current`, `next_action`, `decisions`.
2. Update `specs/execution-status.yaml` for any status change.
3. Add a dated entry in `docs/updates/` (template: `docs/updates/_TEMPLATE.md`).
4. Add an entry under `[Unreleased]` in `CHANGELOG.md` if repository content changed.

<!-- BEGIN bigpowers:tooling -->
## Tooling

- **Harness:** pi. Project agents are in `.pi/agents/`, skills in `.pi/skills/`, and prompts in `.pi/prompts/`. Call project agents with `agentScope: "both"`.
- **Global skills that fit this project:** `survey-context`, `session-state`, `elaborate-spec`, `write-document`, `spike-prototype`, `plan-work`, `develop-tdd`, `audit-code`, `request-review`, `security-review`, `grill-with-docs`, `trace-requirement`, `commit-message`.
- **Commits:** Conventional Commits. Examples: `docs(d01): ...`, `feat(bridge): ...`, `test(contract): ...`.
- **Workflow mode:** `team-pr` (see `specs/state.yaml`).
<!-- END bigpowers:tooling -->

<!-- BEGIN bigpowers:learned-preferences -->
## Learned preferences

- The user wants documentation and scaffolding to be complete before implementation begins. A different model may implement each deliverable.
<!-- END bigpowers:learned-preferences -->

## Harness

- **Goal:** A deliverable-by-deliverable agentic workflow: draft → verify sources → review constraints → human gate.
- **Trigger:** Use `/deliver <Dnn>` for deliverable work. Use `/verify-claims <path>` for a source audit. Use `/review-constraints <path>` for a constraint review. Use `/status-update` at session end. Simple questions can be answered directly.

| Date | Change | Target | Reason |
|------|--------|--------|--------|
| 2026-11-05 | Initial harness | all of `.pi/` | Bootstrap |
| 2026-11-05 | Product rename to fleetassistant | all of `.pi/` (name, domain, paths) | ADR-0011 |
