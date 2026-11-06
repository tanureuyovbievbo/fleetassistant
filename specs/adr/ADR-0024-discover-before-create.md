# ADR-0024: Discover before you create

- **Status:** accepted (rule is binding now; the driver does not implement it yet — see *Not yet implemented*)
- **Date:** 2026-11-06
- **Deciders:** project owner (human, m02051)
- **Related:** C-25, ADR-0015 (topology as connection fields), OQ-018

## Context

HAEO creates records the moment a hub is created: a `network` subentry and a
`switchboard` **junction** (F-061/F-062). The junction's title comes from a
translated string, so it is readable but not predictable. Our compiler, unable to
name a hub record it does not own, synthesized its own junction
(`fields.bus_name(system_id)` → `<system_id>_bus`) and pointed every element at
it — a second centre in a graph that has exactly one.

The general failure is not the bus. It is that the bridge **assumed** a shape of
the target instead of **reading** it. The same mistake has three more mouths:
creating an element whose name already exists, re-creating a hub the site already
has, and deleting a subentry HAEO created because it did not match our plan.

## Decision

Every write path reads the target first, and creation is the last resort.

1. **Read before write.** `apply_plan` may not call a `create_*` method for a
   target it has not first seen in `list_hubs()` / `list_elements()`. The list
   read is part of the apply, not an optimization.
2. **Reuse what exists.** An element whose name matches the plan is *adopted*:
   the plan's payload is diffed against it and only differences are written.
   A pre-existing element the plan does not describe is left alone and reported
   (warning `element_not_pruned`), never deleted.
3. **Reference a pre-existing element symbolically.** Where HAEO owns a record
   whose name we cannot know offline (the hub switchboard junction, the
   `network` subentry), the plan carries a sentinel (`HUB_SWITCHBOARD`) that the
   driver resolves from the hub's own subentries at apply time, after the hub
   exists. No translated string is ever written into a plan or a profile.
4. **Ownership decides deletion.** We delete only subentries the previous plan
   declared and this one does not (`OperationType.REMOVE_*` against our own
   element list). Anything else in the entry is HAEO's or the user's.
5. **A read failure stops the apply.** If the target cannot be listed, the apply
   is blocked with a repair, not attempted blind — same rule as ADR-0012.

## Consequences

- `compile_plan` loses `_bus_element`; `ElementPlan.connection` accepts the
  sentinel; `prevalidate` rejects a connection target that is neither a planned
  element nor the sentinel.
- `preflight.py` prints `<hub switchboard>` for an unresolved sentinel instead of
  a fabricated name.
- `PRUNE_UNKNOWN_ELEMENTS` stays `False` permanently: with discovery-first there
  is nothing unexpected to prune, and the flag becomes dead weight.
- A plan is no longer self-contained. Applied topology is only fully known after
  the read, which is why diagnostics print both the plan and the observed entry.
- Cost: one extra read per apply, and an apply that cannot start without HAEO
  answering. Both are cheap next to writing a duplicate element into a hub.

## Rejected alternatives

- **Deterministic private names (`<system>_bus`).** What we have: stable offline,
  but it manufactures a second centre and hides a real topology fact inside a
  string.
- **Hardcoding `"Switchboard"`.** Correct in English only; the title is a
  translation key (F-062).
- **Delete HAEO's switchboard and own the centre.** Makes us responsible for a
  record HAEO's model expects, and needs pruning on — the exact thing that would
  delete user elements next.
- **Trust the plan and create unconditionally.** Collides on the second apply and
  on any hub the user configured by hand.

## Enforcement

- Constraint **C-25** in `docs/constraints/CONSTRAINTS.md`.
- `tests/unit/test_ha_driver.py::test_a_preexisting_switchboard_is_reused_not_duplicated`
  — `xfail(strict=True)` until the sentinel lands, so implementing it forces the
  test to be turned on rather than quietly passing.
- `tests/unit/test_haeo_bridge.py` keeps the adoption and no-prune behaviour
  covered on the in-memory driver.

## Not yet implemented

`HUB_SWITCHBOARD` resolution and the removal of `_bus_element` (OQ-018 option 1).
Tracked in `docs/verification/REVIEW_LATER.md` as RL-34.
