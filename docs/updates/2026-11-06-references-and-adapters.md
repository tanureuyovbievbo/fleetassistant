# 2026-11-06 — Entity references checked at setup; local adapters that actually write

Steps 2 and 3 of the roadmap, in one increment: the profile's promises are now
verified against Home Assistant, and a gateway site can drive its entities.

## What changed

**References (`references.py`, `runtime.py`).** Every entity a profile names is
collected — element `forecast_entity` / `import_price_entity` /
`export_price_entity` / `connected_entity` / `current_soc_entity`, control
`entity_id`, `window_calendar`, and the HAEO horizon sensor — and checked against
`hass.states` during setup:

| Situation | Result |
| --- | --- |
| entity does not exist | error repair `entity_missing`, naming the entity and the profile path |
| state is `unavailable`/`unknown` | warning repair `entity_unavailable` |
| forecast with fewer than 2 points | error repair `entity_no_forecast` (HAEO cannot build a horizon) |
| calendar reference that is not `calendar.*` | error repair `calendar_domain_mismatch` |
| our own published price sensor | exempt — a missing one is our defect |

Setup still succeeds in every case; the repair is what the user sees, and a reload
clears the repairs that no longer apply. This is the same class of defect as the
old RL-06, one layer up: HA accepts any string, so the plan silently optimised
against `unknown`.

**Adapters (`adapters/ha_services.py`, `adapters/ha_caller.py`).** Local-backed
controls now become adapters bound to real entities: `set_export_limit` /
`set_battery_target` / `set_charger_amps` → `number.set_value` (with an optional
`scale` for kW→W), `set_thermostat_setpoint` → `climate.set_temperature` (°F→°C),
`shed_circuit` → `switch.turn_off`/`turn_on`. The adapters stay pure — they take an
injected `ServiceCaller` — while the one module that imports Home Assistant to
build that caller lives in `adapters/ha_caller.py`, named explicitly in the C-08
allow-list (ADR-0020). A control that cannot be bound (missing `entity_id`,
`shed_circuit` on nothing, an unsupported capability such as
`set_charging_schedule`) becomes a warning repair `control_unbound`; the rest of
the site still works.

`read_state()` returns only what the adapter last wrote. That honesty is recorded
as RL-23 — a hardware-level failure still looks applied until the executor can read
real state.

## Verification

- `python -m pytest` → **192 passed**, 7 live deselected (28 new).
- `python -m ruff check .` → clean; `python tools/check_boundaries.py` → clean;
  markdown links resolve.
- New tests: 13 in `tests/unit/test_references.py`, 15 in
  `tests/unit/test_ha_service_adapters.py` (bindings, clamping and consent through
  the real `SafetyPipeline`, transport failure → `AdapterError`, factory grouping,
  unbound-control warnings, api-backed controls never bound locally).
- The schema gained `entity_id` (pattern-checked, warned about when missing on a
  local control or present on an api-backed one) and `scale`; the gateway example
  now names the entities it drives (`number.solark_export_limit_kw`,
  `number.eg4_battery_target_soc`, `number.wallbox_max_amps`).

## Not done

- No write path yet: adapters are built during setup, but nothing sends a plan
  through them — the executor wiring is the next increment, and it needs
  `read_state` to mean something (RL-23).
- References are checked once per setup; a later rename is only caught on reload
  (RL-24).
- "Shed means off" and °F→°C are our conventions, not verified vendor semantics
  (RL-25).
- `set_charging_schedule` remains unbound: no generic HA service accepts a schedule.
