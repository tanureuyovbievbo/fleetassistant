---
name: constraints-check
description: Check an fleetassistant deliverable, plan, or code change against the non-negotiable constraint register C-01..C-24 and the ADRs, producing a PASS/FAIL table with file:line findings. Use for every review, before every gate, and whenever a design touches tenancy, HAEO, devices, pricing, security, licensing, or naming.
---

# constraints-check

## Procedure
1. Load `docs/constraints/CONSTRAINTS.md` and `specs/adr/README.md`.
2. For each C-ID, decide PASS, FAIL, or N/A for the artifact. Write one line of reason.
3. Run the automated probes below where code exists. Record each command and its result.
4. Classify findings: BLOCKER (violates a constraint), MAJOR (risk of violation or a missing control), MINOR (clarity).
5. Write the report (format below).

## Automated probes (when code exists)
| Constraint | Probe (adapt the paths) |
|------------|-------------------------|
| C-03 | `grep -R '"domain"' custom_components/*/manifest.json` → only `fleetassistant` |
| C-06 | `grep -RnE '\.storage|core\.config_entries' custom_components/fleetassistant` → no write paths |
| C-07 | `grep -Rln 'haeo' custom_components/fleetassistant --include=*.py` → only under `haeo_bridge/` (plus constants) |
| C-08 | `manifest.json` `requirements` is empty or approved in D02 |
| C-09 | Device service calls (`async_call`, Modbus clients) appear only under `adapters/` |
| C-17/C-18 | Secret scan: no tokens, passwords, or keys in the repo |
| C-21 | `grep -RniE 'certified|compliant|OpenADR|SPARc'` in docs → each hit is qualified and cited |

## Report format
```markdown
# Dnn constraints review — <date>
Verdict: PASS | FAIL

| C-ID | Result | Reason / evidence |
|------|--------|-------------------|

## Findings
| Severity | File:line | Constraint | Finding | Required action |
|----------|-----------|------------|---------|-----------------|
```

Any FAIL on C-01, C-04, C-06, C-07, C-09, C-11, or C-21 is always a BLOCKER.
