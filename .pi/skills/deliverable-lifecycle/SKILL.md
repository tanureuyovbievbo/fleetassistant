---
name: deliverable-lifecycle
description: The step-by-step lifecycle every fleetassistant deliverable (D01..D12) follows — context-check, verify, draft, review, fix, gate — with the files each step reads and writes and how specs/state.yaml is updated. Use when starting, resuming, or handing off any deliverable, especially after a model switch.
---

# deliverable-lifecycle

The workflow is model-agnostic. All state lives in files. A new model resumes by reading `specs/state.yaml`.

## Steps
| Step | Role | Reads | Writes | Exit condition |
|------|------|-------|--------|----------------|
| 0 context-check | orchestrator | `specs/state.yaml`, `_workspace/` | `specs/state.yaml` (`step`) | Mode chosen: initial, resume, or partial rerun |
| 1 verify | source-verifier | deliverable, ledgers | ledgers, `_workspace/Dnn_verify_report.md` | Every needed fact is VERIFIED or has an OQ |
| 2 draft | architect (design) or engineer (code) | constraints, ledgers, epic | deliverable or code, `_workspace/Dnn_architect_notes.md` or `Dnn_engineer_report.md` | Template sections or tasks complete |
| 3 review | reviewer + claims-auditor (in parallel) | artifact | `_workspace/Dnn_review_constraints.md`, `_workspace/Dnn_review_claims.md` | Both reports exist |
| 4 fix | architect or engineer | review reports | artifact | Findings addressed. Maximum 2 loops, then escalate to the human. |
| 5 gate | human | everything | `specs/execution-status.yaml`, `specs/state.yaml` | Human sets the epic to `accepted` or `changes-requested` |
| 6 close | orchestrator | — | `docs/updates/YYYY-MM-DD-Dnn.md`, `CHANGELOG.md` | Update log written |

## Context-check rules
- No `_workspace/Dnn_*` files → **initial** run.
- Some files exist and `state.yaml` `step` < gate → **resume** from the recorded step.
- The human requests a change to an accepted deliverable → **partial rerun**: steps 2–5 only on the named sections. The deliverable change log gets a new row.

## state.yaml update (end of every step)
```yaml
current:
  epic: eNN-slug
  deliverable: Dnn
  status: in-progress      # not-started | in-progress | in-review | changes-requested | accepted
  step: review
next_action: "<one sentence a different model can execute>"
```

## Stop rule
After step 5 for a deliverable, stop. The next deliverable starts only after a human instruction (brief: "stop for review between each").
