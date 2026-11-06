# 2026-11-06 — The dispatch loop, and a read-back that reads the device

**Increment:** connect the optimizer's plan to real device writes on a cadence, expire
it honestly, and fall back once when the optimizer goes quiet.

## What changed

| File | Change |
| --- | --- |
| `custom_components/fleetassistant/dispatch.py` | New. `PlanSnapshot`, `PlanSource`, `StaticPlanSource`, `MappedPlanSource`, `Dispatcher`, `DispatchOutcome`, `DispatchState`, `DEFAULT_MAX_PLAN_AGE` (15 min), `DEFAULT_FAIL_SAFE_AFTER` (30 min) |
| `custom_components/fleetassistant/runtime.py` | `_start_dispatch` (timer, repair `dispatch_failed_safe`, clears it on recovery), `_plan_mapping`, `_entity_state`; unload cancels the timer and forces the fail-safe |
| `custom_components/fleetassistant/site.py` | `dispatcher`, `dispatch_source`, `dispatch_unsub`, `dispatch_state`; diagnostics gained `dispatch` |
| `custom_components/fleetassistant/const.py` | `CONF_DISPATCH_ENABLED`, `DEFAULT_DISPATCH_ENABLED=False`, `DISPATCH_INTERVAL_SECONDS=60` |
| `custom_components/fleetassistant/config_flow.py` | Options toggle `dispatch_enabled` |
| `custom_components/fleetassistant/profile/schema.py` | Controls may declare `plan_entity` (entity id) — the entity that publishes this control's setpoint |
| `custom_components/fleetassistant/references.py` | `plan_entity` is a reference; a missing plan entity is a repair, not a silent no-op |
| `custom_components/fleetassistant/adapters/ha_services.py` | `read_state` reads the state machine via the injected reader; falls back to the last write |
| `tests/unit/test_dispatch.py` | 18 tests |
| `specs/adr/ADR-0021-dispatch-loop-and-fail-safe.md` | New, accepted |

## Why this shape

The design question was not "how do we write setpoints" (the executor could already
do that) but "what do we do at 15:07 when the plan was built for 15:00". The answer
had to be a decision, not a default: a stale plan is discarded, silence is tolerated
for a bounded time, and the fail-safe is written once per outage rather than every
tick. The three rules are unit tests (`test_a_stale_plan_is_discarded_and_the_site_fails_safe`,
`test_within_the_grace_period_a_silent_optimizer_is_tolerated`,
`test_after_the_grace_period_silence_fails_safe_exactly_once`) precisely because they
are the ones a future refactor would quietly "simplify".

`MappedPlanSource` reads only entities the installer named. The alternative — asking
HAEO for its plan by convention — is the exact failure ADR-0012 exists to prevent, and
OQ-022 (which entity actually carries a plan value) is still open. The cost is one
extra profile field per control and one repair when it is missing, which is the honest
cost of not guessing.

Read-back now reads `hass.states`. It is still a float with no timestamp or quality
flag (RL-27) and the device's own semantics are assumed rather than verified (RL-25) —
but "did the relay actually open" is now answerable at all, which it was not before.

## Verification

- `python -m pytest -q` → 213 passed, 7 live deselected.
- `python -m ruff check .` → clean.
- `python tools/check_boundaries.py` → `constraint probes: clean` (`dispatch.py`
  imports only the executor, audit, and adapters; `runtime.py` is the only place that
  starts the loop, and the loop calls the safety pipeline, never an adapter directly).
- Markdown relative links resolve.

## Deliberately not done

- No plan entity is mapped in the examples: HAEO's plan entity ids are not verified
  (OQ-022). A site that enables dispatch without a mapping gets one audit record
  (`dispatch.disabled`) and no timer.
- The interval is a fixed 60 s (RL-28), and the fail-safe is static setpoints, not the
  contactor-plus-local-automation layer C-20 requires for gateway-primary sites
  (RL-26).
- Nothing publishes telemetry yet, so a dispatch sequence is auditable in the log and
  invisible to the fleet (D07).
