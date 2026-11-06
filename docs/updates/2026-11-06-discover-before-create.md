# Discover before you create

**Date:** 2026-11-06
**Scope:** rule + enforcement (no behaviour change yet)
**ADR:** [ADR-0024](../../specs/adr/ADR-0024-discover-before-create.md)
**Constraint:** C-25

## What changed

- `specs/adr/ADR-0024-discover-before-create.md` (accepted, rule binding, driver pending).
- `docs/constraints/CONSTRAINTS.md` — **C-25**: read the target before writing it,
  reuse a pre-existing hub record, delete only what our own previous plan created.
- `docs/verification/REVIEW_LATER.md` — **RL-34**: the compiler still synthesizes
  `<system_id>_bus`; symbolic switchboard resolution is not implemented.
- `CONVENTIONS.md` — "Discovery before creation" section, so the rule survives in
  the file agents read before touching code.
- `tests/unit/test_ha_driver.py::test_a_preexisting_switchboard_is_reused_not_duplicated`
  — `xfail(strict=True)`: a hub pre-populated with HAEO's `network` + `switchboard`
  junction must end with exactly one junction, and the grid must point at it.

## Why now

The owner asked, after the OQ-018 analysis, that future implementation check for a
pre-existing element first (m02051). The bus was the visible symptom; "assume the
target's shape instead of reading it" is the reusable defect.

## Why the test is a strict xfail

It fails today for the right reason: the plan adds `main_bus` beside HAEO's
`Switchboard` and wires the grid to its own centre. `strict=True` means the day the
sentinel lands the test reports an unexpected pass instead of quietly passing —
someone must turn it on and delete `_bus_element`.

## Verification

- `python -m pytest` → 312 passed, 7 deselected, 1 xfailed
- `python -m ruff check .` → clean
- `python tools/check_boundaries.py` → constraint probes: clean

## Not done

`HUB_SWITCHBOARD` sentinel, `_bus_element` removal, sentinel resolution in
`FlowHaeoDriver.create_element`, `prevalidate` accepting the sentinel (OQ-018
option 1, RL-34).
