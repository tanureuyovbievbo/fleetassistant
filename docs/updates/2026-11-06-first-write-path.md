# 2026-11-06 — The first write path is wired (and switched off)

## What changed

- **A review register exists.** `docs/verification/REVIEW_LATER.md` lists every
  place where the code ships a deliberate simplification: 18 entries, each with the
  file, the gap, the trigger that makes it urgent, and the deliverable that owns it.
  Code refers to entries as `RL-xx`, and `tests/unit/test_review_register.py` fails
  if a reference has no row, if a row has no trigger or owner, or if the three
  degradation gaps stop being named.
- **The degradation logic states its own gaps.** `_degradation_policies` in
  `haeo_bridge/plan.py` now documents RL-01 (only discharge wear is priced), RL-02
  (the price is a constant snapshot) and RL-03 (a wildcard target is exact for one
  battery, and double-prices with two). Same for the efficiency units (RL-04), the
  pruning switch (RL-10) and the flag itself (RL-14).
- **`runtime.py` calls the driver** behind the options flag `apply_haeo_plan`
  (default **off**). When on, setup compiles the plan, runs `apply_plan` with
  `FlowHaeoDriver(HomeAssistantFlowPort(hass))` in an executor thread, stores the
  report on `SiteRuntime`, appends a `haeo.apply` audit record, and raises a repair
  issue when the result is `blocked` or `partial` (clearing it when it later
  succeeds).
- **`HomeAssistantFlowPort` is now synchronous and loop-bridged.** Each call
  schedules the manager coroutine on `hass.loop` and blocks on the future, so it can
  run in an executor thread and must never be called from the event loop (RL-13).
  `FlowHaeoDriver._await` tolerates a port that returns values instead of
  coroutines, and `tests/unit/test_ha_driver.py::test_a_blocking_port_is_accepted`
  proves the driver works with one.
- **Options flow** gained the provisioning toggle with description text that says
  what it does and why it is off; `strings.json` and `translations/en.json` gained
  `issues.haeo_apply_incomplete`.

## Why this matters

The bridge could already answer HAEO's flows, but nothing in Home Assistant ever
called it. Now one option flips a site from "compiles a plan" to "provisions HAEO",
and the flip is a user decision, not a release decision — because until a live
instance accepts our payloads (OQ-017), provisioning would write payloads nobody has
verified. The default-off flag is how C-23 and ADR-0012 coexist with a real write
path.

## Verification

- `python -m pytest -q` → 134 passed, 7 live tests deselected.
- `python -m ruff check .` → clean.
- `python tools/check_boundaries.py` → `constraint probes: clean`.
- The blocking-port test is the regression guard for the executor/loop boundary: it
  would have caught `asyncio.run` being applied to an already-resolved value.

## Not done

- No live run yet. `HAEO_SURFACE_LIVE_VERIFIED` and `HA_PORT_LIVE_VERIFIED` remain
  `False`, so an armed site reports `blocked` with `haeo_type_unverified` and writes
  nothing.
- No re-apply on option change and no drift repair (RL-14).
- OQ-021 (efficiency units) is still open; it is next because it can silently corrupt
  a plan's physics (RL-04).
