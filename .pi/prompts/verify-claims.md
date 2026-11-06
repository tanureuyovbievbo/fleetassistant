---
description: Verify a list of claims (or every UNVERIFIED item for a deliverable) against primary sources and update the verification ledgers.
argument-hint: "<Dnn | OQ-NNN... | free-text claim>"
---

# /verify-claims $ARGUMENTS

1. Read `.pi/skills/verify-sources/SKILL.md` and `docs/verification/OPEN_QUESTIONS.md`.
2. Build the claim list:
   - `Dnn` → every UNVERIFIED mark in `docs/deliverables/Dnn-*.md`, plus open OQs that block Dnn.
   - `OQ-NNN` → those questions.
   - Free text → that claim.
3. If the list has more than 8 independent claims, split it into groups by source domain (HAEO, HA, HACS, vendor, regulatory). Run the `subagent` tool in parallel mode (`agentScope: "both"`, agent `source-verifier`), one group per task. Otherwise run a single task.
4. Merge the results. Make sure the IDs are unique and append-only. Resolve ID collisions by renumbering the newest entries.
5. Report: newly VERIFIED, still UNVERIFIED, and new CONFLICTS (discrepancies with the brief).

## Test scenarios
- `/verify-claims OQ-001` → fetches the HA and HACS dependency docs, then resolves or narrows OQ-001.
