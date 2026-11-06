# Elements connect to HAEO's switchboard, not to ours

**Date:** 2026-11-06
**Scope:** HAEO bridge (topology)
**ADR:** [ADR-0025](../../specs/adr/ADR-0025-switchboard-sentinel.md)
**Closes:** OQ-018 decision, RL-09, RL-34, the ADR-0024 follow-up

## The defect

`compile_plan` synthesized `fields.bus_name(system_id)` (`<system>_bus`) and pointed
every connected element at it. HAEO creates its own `junction` (the switchboard,
titled from a translated string) when the hub is created, so a real hub ended up
with two centres, and HAEO's own element had no edges.

## The fix

- `fields.HUB_SWITCHBOARD = "hub_switchboard"` + `is_switchboard()`; `bus_name`
  deleted. The plan carries the sentinel for every element in `CONNECTED_KINDS`.
- `FlowHaeoDriver._switchboard()` reads the hub's first `junction` subentry and
  substitutes its title into the element payload. Zero junctions →
  `switchboard_missing` (blocking). Several → first is the switchboard, warning
  `switchboard_ambiguous`.
- `apply._element_payload` / `_differs` ignore the connection field while it is
  symbolic — the plan and HAEO spell that name differently by construction, so
  comparing it would report a change on every apply.
- `list_elements` marks junction subentries `managed: False`, so the no-prune diff
  no longer calls HAEO's switchboard garbage.
- `tools/preflight.py` prints `topology connected elements -> <hub switchboard>
  (resolved at apply)` instead of a fabricated name.
- `_bus_element` deleted; ADR-0015 marked partly superseded; ADR-0024 marked
  implemented.

## Verification

- `python -m pytest` → 316 passed, 7 deselected
- `python -m ruff check .` → clean
- `python tools/check_boundaries.py` → constraint probes: clean
- `python tools/preflight.py site_profiles/examples/solark_gateway_primary.yaml`
  → `1 hub(s), 8 element(s), 4 control(s)` (was 9: the synthetic junction is gone)
  and the two expected blocking errors (`haeo_type_unverified`, `haeo_kind_unmapped`)

## New tests

| Test | Proves |
|---|---|
| `test_a_preexisting_switchboard_is_reused_not_duplicated` | the strict xfail from ADR-0024, now green: one junction survives, the grid points at it |
| `test_the_hubs_own_switchboard_is_never_reported_as_garbage` | junction subentries are not pruned nor warned about |
| `test_a_hub_without_a_junction_cannot_resolve_the_switchboard` | absence blocks with `switchboard_missing` instead of creating a second centre |
| `test_several_junctions_report_which_one_was_used` | first junction wins, extra one is kept, warning is non-blocking |

## Not done

A live instance must confirm HAEO accepts the resolved (possibly translated) title
as a `connection_target`. That is the last item on OQ-018 and it cannot be closed
offline.
