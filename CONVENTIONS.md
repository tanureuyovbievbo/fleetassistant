# CONVENTIONS.md — fleetassistant

These rules apply to every contributor, human or AI. Directive lines use MUST / NEVER and are kept short.

## 1. Always Green

- MUST keep `main` buildable and testable at every commit.
- MUST make each increment run and be testable by itself (brief requirement).
- MUST NOT merge a change with failing tests, lint, or type checks.

## 2. Discovered defects

- MUST fix a defect you find, or log it in `specs/bugs/registry.yaml` in the same session.
- NEVER dismiss a failure. Banned phrases: "pre-existing issue", "unrelated failure", "flaky, ignore", "out of scope, skipping".

## 3. Verification discipline (documentation)

- MUST cite primary sources for regulatory, program, rate, market, certification, and standards statements. Accepted sources include CEC, CPUC, CAISO, IOU program pages, the OpenADR Alliance, CEC-AC, UL, IEEE, and NIST.
- Citation format: `[S-NNN]` inline. The entry goes in `docs/verification/SOURCES.md` with URL, title, publisher, and access date (YYYY-MM-DD).
- MUST mark unverifiable claims inline as `**UNVERIFIED**` and add them to `OPEN_QUESTIONS.md` as `OQ-NNN`.
- MUST record verified technical facts (HAEO, HA, vendor APIs) in `FACTS_LEDGER.md` as `F-NNN` with source and date.
- NEVER cite a page that was not fetched. Search-result snippets do not count as a fetched source.
- MUST name the vendor API terms-of-service risk for every adapter that targets a closed ecosystem.
- MUST show the quota math before promising any telemetry cadence. Formula: calls per site per day multiplied by sites, compared to the vendor limit.
- MUST date every certification or compliance statement and back it with evidence.

## 4. Documentation style

- Write in clear technical English (ASD-STE100 spirit): short sentences, active voice, one idea per sentence.
- Every deliverable document starts with a front-matter table: ID, title, version, status, owner role, last updated, and the source and fact IDs it depends on.
- Every deliverable ends with these sections: **Open questions**, **Constraint compliance** (C-xx checklist), and **Change log**.
- Diagrams: use Mermaid in Markdown. NEVER use binary images for architecture diagrams.
- Statuses: `draft` → `in-review` → `accepted` → `superseded`.

## 5. Code (applies when implementation starts)

- Python: follow Home Assistant integration conventions. Use async-first code. Use type hints everywhere. Lint with `ruff`. Type-check with `mypy --strict` where practical.
- Domain `fleetassistant`. NEVER use `haeo` or any other existing integration domain.
- Use only the dependencies allowed by C-08. See `docs/deliverables/D02-hacs-packaging.md`.
- Only `custom_components/fleetassistant/adapters/` touches devices (C-09).
- Only `custom_components/fleetassistant/haeo_bridge/` touches HAEO (C-07).
- Tests use `pytest` with `pytest-homeassistant-custom-component`. Contract tests run against a live HAEO at the pinned version.
- Tests follow F.I.R.S.T: fast, independent, repeatable, self-validating, timely.
- Commits follow Conventional Commits. Scopes: `d01`…`d12`, `bridge`, `adapters`, `pricing`, `telemetry`, `profile`, `fleet`, `agg`, `harness`, `docs`.

## 6. Agentic workflow

- MUST keep `.pi/agents`, `.pi/skills`, and `.pi/prompts` model-agnostic. Do not use model-specific tags, tool names, or pinned models.
- MUST put intermediate agent output in `_workspace/` (git-ignored). Only final artifacts go in `docs/` or `specs/`.
- MUST keep one human review gate per deliverable.
- When a step is handed to a different model, the handoff is the files only: `specs/state.yaml`, the epic capsule, and the newest update entry. Do not assume a shared chat history.
