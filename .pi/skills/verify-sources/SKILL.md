---
name: verify-sources
description: Fetch primary sources and record facts, citations, and UNVERIFIED items in the fleetassistant verification ledgers. Use whenever a deliverable mentions HAEO behavior, HA APIs, HACS rules, vendor APIs or ToS, rates, programs, regulators, certifications, or standards — even if the fact "seems known".
---

# verify-sources

## Ledgers
| File | ID | Holds |
|------|----|-------|
| `docs/verification/SOURCES.md` | S-NNN | URL, title, publisher, fetch date, pinned version or tag |
| `docs/verification/FACTS_LEDGER.md` | F-NNN | Fact statement, S-ID, quoted passage, status |
| `docs/verification/OPEN_QUESTIONS.md` | OQ-NNN | Question, why it matters, blocking deliverable, owner role, status |

IDs are append-only. Never renumber. Never delete; mark entries `superseded by F-NNN` instead.

## Procedure
1. List the claims to check (from the task or the architect's notes).
2. For each claim, choose the primary source:
   - HAEO behavior and names → haeo.io docs, plus `github.com/hass-energy/haeo` at the pinned tag (see ADR-0004).
   - HA APIs → developers.home-assistant.io (or its GitHub source repo).
   - HACS rules → hacs.xyz docs, or the hacs/default repo for submission rules.
   - Vendor APIs → the official developer portal and its terms of service.
   - Regulatory or program items → CPUC, CEC, CAISO, IOU program pages, OpenADR Alliance, CEC-AC, UL, IEEE, NIST.
3. Fetch it. If the fetch fails, the claim stays UNVERIFIED. Never fall back to memory.
4. Record the source (S-ID), then the fact (F-ID) with a short quoted passage (≤ 2 sentences).
5. If the source contradicts the brief or an earlier fact → add an OQ with type `discrepancy`. Quote both sides.
6. Write `_workspace/<Dnn>_verify_report.md`:

```markdown
| Claim | Status | Evidence |
|-------|--------|----------|
| HAEO requires highspy>=1.15.1 | VERIFIED | F-005 |
| HAEO hub flow has field X | UNVERIFIED | OQ-002 |
```

## Quality bar
- A fact about code → pin a tag or commit.
- A number (rate, cap, fee, timeline) → it must appear verbatim in the quoted passage.
- Vendor ToS → quote the clause that limits automation, polling, or commercial use (C-24).
- Quota math → show requests per day = sites × polls per hour × 24, compared with the published limit.
