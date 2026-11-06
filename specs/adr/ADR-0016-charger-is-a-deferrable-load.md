# ADR-0016 — A charger is a deferrable load, not an `ev`

Status: accepted (2026-11-06)
Supersedes: the `ev_charger → ev` line in ADR-0013
Superseded by: —

## Context

The first element table mapped `ev_charger` to HAEO's `ev`. Reading
`core/schema/elements/ev.py` showed that `ev` models a **vehicle**:

- `vehicle.capacity`, `vehicle.energy_per_distance`, `vehicle.current_soc`
  (entity only), `vehicle.min_charge_percentage`
- `charging.max_charge_rate`, `charging.connected` (entity only)
- optional `trip.trip_calendar` / `trip.odometer` that derive `away`,
  `trip_start`, `trip_opened`, `trip_due`
- `public_charging.public_charging_price`, efficiency and advanced sections

A site profile knows a charger: rated amps, phases, a vendor, a window in which
charging may happen. It does not know how far the car will drive tomorrow, and a
cloud-primary site cannot read the vehicle's state of charge at all. Mapping a
charger onto `ev` would mean inventing capacity, consumption and a connected flag
— exactly what C-23 forbids.

`core/schema/elements/deferrable_load.py` asks for what a charger actually has:
`schedule.window_calendar` (when energy may be delivered), optional
`schedule.energy_meter`, `power.max_power`, and pricing `deficit_price` /
`overage_price` (defaults 10.0 / 0.0, F-050).

## Decision

1. `CANDIDATE_KIND_TO_TYPE["ev_charger"] = "deferrable_load"`.
2. The profile's `ev_charger` element requires `window_calendar` (validated by the
   site-profile schema) and may carry `max_charge_kw`, which becomes
   `power.max_power`; `deficit_price` and `overage_price` default to HAEO's own
   defaults.
3. Charger **control** stays a capability (`set_charger_amps`,
   `set_charging_schedule`) on the adapter layer (D06): the optimizer decides how
   much energy to deliver inside the window, the adapter decides how to ask the
   hardware for it.
4. HAEO's `ev` element is not used by v1. Its field table stays recorded in
   `fields.py` as `EV_VEHICLE_FIELDS` for the day a gateway profile carries
   vehicle state.
5. `UNRESOLVED_KINDS` shrinks to `meter`, `thermostat`, `relay`.

## Consequences

- A charger profile now needs a calendar entity (OQ-022): the installer supplies
  one, an HA helper provides one, or our integration creates one. Until that
  product decision is recorded, examples use a placeholder calendar id that fails
  loudly rather than silently scheduling nothing.
- Charging is priced by the optimizer through deficit/overage prices rather than
  by a per-kWh rate we compute: HAEO treats energy inside the window's requirement
  as required and energy beyond it as optional.
- Departure-time behaviour ("be full by 07:00") is expressed by the calendar, not
  by a profile field, so a rule pack can own departure logic later.

## Rejected alternatives

- **`ev` with invented vehicle data.** Violates C-23 and would produce plans whose
  SOC assumptions are fiction.
- **`load` with a forecast.** A load is not shiftable, so the optimizer could not
  move charging into a cheap window — the whole point of the element.
- **`buffer`.** Models stored energy with a level, not a delivery schedule; the
  charger has no tank.
- **Keeping `ev_charger` unmapped.** Blocks every gateway profile for a modelling
  gap that has a correct answer.
