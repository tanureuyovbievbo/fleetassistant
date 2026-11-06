---
description: Run one fleetassistant deliverable (D01..D12) through verify → draft → review → fix, then stop for the human gate.
argument-hint: "<Dnn> [resume|rerun <sections>]"
---

# /deliver $ARGUMENTS

You orchestrate one deliverable. Use the `subagent` tool with `agentScope: "both"` to run project agents from `.pi/agents/`. Do not pin a model; agents inherit the current one.

## Phase 0 — context check
1. Read `AGENTS.md`, `specs/state.yaml`, `specs/release-plan.yaml`, and `.pi/skills/deliverable-lifecycle/SKILL.md`.
2. Resolve `<Dnn>` → epic `specs/epics/eNN-*/` and file `docs/deliverables/Dnn-*.md`.
3. Check the dependency: the previous epic MUST be `accepted` in `specs/execution-status.yaml` (exception: a human-approved spike pull-ahead). If it is not, stop and report.
4. Pick the mode: initial, resume (from `state.yaml` `step`), or rerun (named sections only). Update `state.yaml`.

## Phase 1 — verify (single)
`subagent` agent `source-verifier`: "Follow .pi/skills/verify-sources. Deliverable <Dnn>. Claims list: the deliverable's Inputs section, open OQs tagged <Dnn>, and _workspace/<Dnn>_architect_notes.md if it exists. Output _workspace/<Dnn>_verify_report.md."

## Phase 2 — draft (single)
- Design deliverable → agent `architect`: "Draft or revise docs/deliverables/<Dnn>-*.md per the epic acceptance criteria. Use only F-IDs from the ledger. Write _workspace/<Dnn>_architect_notes.md."
- Code tasks in the epic → agent `engineer`: "Execute the todo tasks in specs/epics/<epic>/<epic>-tasks.yaml in order, test first. Write _workspace/<Dnn>_engineer_report.md."
- If the architect notes request new facts, run Phase 1 once more, then re-draft once.

## Phase 3 — review (parallel)
- agent `reviewer`: "Follow .pi/skills/constraints-check on <artifact>. Output _workspace/<Dnn>_review_constraints.md."
- agent `claims-auditor`: "Audit <artifact>. Output _workspace/<Dnn>_review_claims.md."

## Phase 4 — fix (at most 2 loops)
If either verdict is FAIL, send both reports to the drafting agent and re-run Phase 3. After 2 failed loops, stop and escalate the remaining findings to the human.

## Phase 5 — gate (stop)
1. Set the epic to `in-review` in `specs/execution-status.yaml`. Set `state.yaml` `step: gate`.
2. Write `docs/updates/<YYYY-MM-DD>-<Dnn>.md` from `docs/updates/_TEMPLATE.md`.
3. Report to the human: a summary, the verdicts, new OQs, and the decisions needed. **Stop.** Do not start the next deliverable.

## Error policy
A failed subagent → retry once with the same task. If it fails again, continue, record the gap in the update log, and tell the human.

## Test scenarios
- Normal: `/deliver D01` on a fresh repo → verify report, draft, two PASS reviews, update log, stop.
- Error: `/deliver D03` while e02 is not accepted → stops at Phase 0 with the reason.
