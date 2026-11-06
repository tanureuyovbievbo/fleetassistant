# Documentation index

| Area | Path | Contents |
|------|------|----------|
| Charter | [`00-charter/PROJECT_BRIEF.md`](00-charter/PROJECT_BRIEF.md) | Founding brief, kept verbatim as the source of truth. |
| Constraints | [`constraints/CONSTRAINTS.md`](constraints/CONSTRAINTS.md) | C-01…C-24, each with a rule, the reason, and a reviewer check. |
| Deliverables | [`deliverables/`](deliverables/) | D01…D12. Each is a stub with a required outline and acceptance criteria until drafted. |
| Verification | [`verification/`](verification/) | `SOURCES.md` (S-IDs), `FACTS_LEDGER.md` (F-IDs), `OPEN_QUESTIONS.md` (OQ-IDs). `LICENSE_AUDIT.md` is added in D08. |
| Updates | [`updates/`](updates/README.md) | Dated session and progress log, one file per session. |
| Workflow | [`WORKFLOW.md`](WORKFLOW.md) | How agents and humans move a deliverable from stub to accepted. |

## Deliverable status

The live status is in [`../specs/execution-status.yaml`](../specs/execution-status.yaml). The table below is for orientation only.

| ID | Title | Epic | Status |
|----|-------|------|--------|
| D01 | Architecture spec | e01 | not-started (**next**) |
| D02 | HACS packaging spec | e02 | not-started |
| D03 | Site profile schema | e03 | not-started |
| D04 | HAEO provisioning bridge (spike first) | e04 | not-started |
| D05 | Generic price/target model | e05 | not-started |
| D06 | Control adapter layer | e06 | not-started |
| D07 | Telemetry & measurement schema | e07 | not-started |
| D08 | Fleet services spec + scaffolding | e08 | not-started |
| D09 | Aggregation services | e09 | not-started |
| D10 | Rule pack: California (later phase) | e10 | not-started |
| D11 | Phased plan with gates | e11 | not-started |
| D12 | Risk register (seeded) | e12 | not-started |

## ID conventions

| Prefix | Meaning | Registry |
|--------|---------|----------|
| `C-NN` | Non-negotiable constraint | `constraints/CONSTRAINTS.md` |
| `Dnn` | Deliverable | `deliverables/` |
| `eNN` | Epic (one per deliverable; e00 = bootstrap) | `../specs/epics/` |
| `S-NNN` | Fetched source | `verification/SOURCES.md` |
| `F-NNN` | Verified fact | `verification/FACTS_LEDGER.md` |
| `OQ-NNN` | Open question / UNVERIFIED item | `verification/OPEN_QUESTIONS.md` |
| `ADR-NNNN` | Architecture decision record | `../specs/adr/` |
| `R-NNN` | Risk | `deliverables/D12-risk-register.md` |
| `BUG-NNN` | Defect | `../specs/bugs/registry.yaml` |
