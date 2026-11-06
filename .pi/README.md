# .pi — agentic harness for fleetassistant

Model-agnostic by design (ADR-0010). No agent pins a model. Any capable model can play any role. State is passed through files, never through chat history.

## Agents (`.pi/agents/`)
| Agent | Writes | Purpose |
|-------|--------|---------|
| `architect` | deliverables, ADRs, plans | Design deliverables D01..D12 |
| `source-verifier` | verification ledgers | Fetch primary sources; record F/S/OQ entries |
| `engineer` | code, tests, CI, spikes | Implement accepted designs with TDD |
| `reviewer` | `_workspace/*_review_constraints.md` only | Constraint and ADR review (read-only) |
| `claims-auditor` | `_workspace/*_review_claims.md` only | Evidence and naming audit (read-only) |

## Skills (`.pi/skills/`)
| Skill | Use |
|-------|-----|
| `verify-sources` | How to fetch, cite, and record facts |
| `deliverable-lifecycle` | Steps, files, and state updates for every deliverable |
| `constraints-check` | C-01..C-24 review procedure and automated probes |
| `haeo-bridge-contract` | HAEO spike, bridge invariants, contract tests, version bumps |

## Prompts (`.pi/prompts/`)
| Command | Does |
|---------|------|
| `/deliver <Dnn>` | verify → draft → review → fix → **stop at the human gate** |
| `/verify-claims <Dnn or OQ-NNN or claim>` | Evidence pass on demand |
| `/review-constraints <target>` | Reviewer + claims auditor in parallel |
| `/status-update` | Writes a status entry to `docs/updates/` |

## Handoff files
Transient handoff files live in `_workspace/` (git-ignored). Names: `<Dnn>_<agent>_<artifact>.md`, for example `D04_verify_report.md`. Durable outcomes MUST be copied into `docs/` or `specs/`.

## Switching models mid-workflow
1. The new model reads `AGENTS.md`, then `specs/state.yaml`.
2. It continues from `current.step` using `.pi/skills/deliverable-lifecycle`.
3. It records the model name in the update log entry (traceability only).

## Global bigpowers skills that fit
`survey-context`, `session-state`, `spike-prototype` (e04 S1), `plan-work`, `develop-tdd`, `audit-code`, `request-review`, `security-review`, `grill-with-docs`, `trace-requirement`, `commit-message`.
