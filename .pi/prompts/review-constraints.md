---
description: Run the constraints review and the claims audit in parallel on any artifact (deliverable, PR diff, or path).
argument-hint: "<path | Dnn | git-range>"
---

# /review-constraints $ARGUMENTS

1. Resolve the target: a path, `docs/deliverables/Dnn-*.md`, or `git diff <range>`. Use the prefix `Dnn` for report names; for an ad-hoc target, use `ADHOC-<date>`.
2. Use the `subagent` tool in parallel mode (`agentScope: "both"`):
   - `reviewer`: "Follow .pi/skills/constraints-check on <target>. Output _workspace/<prefix>_review_constraints.md."
   - `claims-auditor`: "Audit <target>. Output _workspace/<prefix>_review_claims.md."
3. Summarize both verdicts and the BLOCKER and MAJOR findings for the human. Do not fix anything.
