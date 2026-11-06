---
description: Produce a project status update (state, progress per epic, open questions, decisions needed) and write it to docs/updates/.
argument-hint: "[optional focus]"
---

# /status-update $ARGUMENTS

No subagents are needed.

1. Read `specs/state.yaml`, `specs/execution-status.yaml`, `specs/release-plan.yaml`, `docs/verification/OPEN_QUESTIONS.md`, and the newest file in `docs/updates/`.
2. Write `docs/updates/<YYYY-MM-DD>-status.md` from `docs/updates/_TEMPLATE.md`, with:
   - Current epic and step, and `next_action`.
   - A table of epics with their status.
   - Open questions that block the next two epics.
   - Human decisions pending.
   - Risks that changed (link to D12).
3. Add one line to `CHANGELOG.md` under `Unreleased` only if a deliverable status changed.
4. Print the summary.
