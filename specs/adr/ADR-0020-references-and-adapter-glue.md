# ADR-0020 — Entities are checked at setup, and device I/O never leaves the adapter layer

Status: accepted (2026-11-06)
Supersedes: — (amends the C-08/C-09 probe in `tools/check_boundaries.py`)
Superseded by: —

## Context

Two gaps were closed in the same increment, and both changed where code lives.

**One.** A profile names entities by string. Home Assistant accepts any string. A
typo therefore produced a site that loaded cleanly, provisioned HAEO against
`unknown`, and planned nothing — a failure visible only in a bill. Separately, our
own published price sensors were referenced by the compiled plan with nobody
proving they existed.

**Two.** The C-09 probe forbids `services.async_call(` outside `adapters/`, and the
C-08 probe forbids importing Home Assistant outside a short allow-list. Those two
rules collide the moment an adapter needs to call an HA service: the knowledge of
"how a device is driven" would have to sit in `runtime.py`, which is exactly what
C-09 exists to prevent.

## Decision

1. **The profile is checked against the live state machine at setup.**
   `references.py` (pure) extracts every entity reference — element
   `forecast_entity`/`price_entity`/`connected_entity`/`current_soc_entity`,
   control `entity_id`, `window_calendar`, and the HAEO horizon sensor — and
   `runtime.py` supplies a snapshot from `hass.states`. Missing → error repair;
   unreadable → warning; forecast with fewer than two boundaries → error (HAEO
   cannot build a horizon, F-016); calendar in the wrong domain → error.
2. **A missing reference never fails setup.** The site is otherwise usable, and the
   repair names the entity. Re-checking on reload clears repairs that no longer
   apply.
3. **Our own price sensors are exempt from the check**, because a missing one is
   our defect, not the user's.
4. **The service call lives in `adapters/ha_caller.py`.** Adapters keep taking an
   injected caller (pure, testable); the one module that imports Home Assistant to
   build that caller sits inside `adapters/`, and the C-08 allow-list names that
   path explicitly rather than the whole directory.
5. **Bindings are data, not inference.** `SwitchBinding`, `NumberBinding`,
   `ClimateBinding` are chosen per capability by `BINDING_BY_CAPABILITY`; an
   unknown capability or a local-backed control with no entity is a **warning
   repair** (`control_unbound`), not a crash and not a guess.
6. **Read-back is not faked.** `read_state` returns only what this adapter wrote;
   real state requires the state machine and arrives with the executor (RL-23).

## Consequences

- A typo in `forecast_entity` now produces a repair at install time naming the
  entity, instead of a silent plan against `unknown`.
- `read_state`'s honesty has a cost: a write that failed at the hardware level looks
  applied. Recorded as RL-23 rather than papered over with a plausible number.
- The °F→°C conversion and "shed means off" are conventions we chose, not verified
  vendor semantics (RL-25). They are visible in one class each, so correcting one is
  a one-line change.
- The boundary probe gained a *path*, not a directory: `adapters/ha_caller.py`. Any
  future HA-importing glue must be named there deliberately.

## Rejected alternatives

- **Validating references lazily (first plan run).** The damage is already the plan.
- **Treating a missing entity as a config-entry failure.** Turns a repairable typo
  into a dead entry with no path forward.
- **Importing homeassistant inside `ha_services.py`.** Breaks every unit test and the
  "core is plain Python" property that keeps the suite fast.
- **Letting `runtime.py` own `services.async_call`.** Silently hollows out C-09: the
  next person adds a direct device call "just here".
- **Inferring the service from the entity domain** (`switch.*` → `turn_on`). A relay
  is sometimes a `light`; the capability decides the semantics, the binding decides
  the call.
