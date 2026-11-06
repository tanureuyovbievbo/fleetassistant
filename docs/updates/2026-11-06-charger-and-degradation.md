# 2026-11-06 — Charger carrier, degradation pricing, and the ratio trap

## What changed

- **A charger is a deferrable load.** `ev_charger` now compiles to HAEO's
  `deferrable_load`: `schedule.window_calendar` (required), `power.max_power` from
  `max_charge_kw`, pricing `deficit_price` / `overage_price` at HAEO's defaults.
  `UNRESOLVED_KINDS` is down to `meter`, `thermostat`, `relay`. ADR-0016.
- **Degradation is a policy rule.** Each battery with a `degradation_cost` yields a
  `<battery>_degradation` policy element whose single rule prices the battery's
  discharge, because HAEO puts a rule's price on the source's outbound edges when a
  single source faces a wildcard destination (F-056). ADR-0017.
- **Percentages are ratios.** HAEO multiplies `*_percentage` fields by capacity, so
  they are 0..1. `fields.tag_value("ratio", 20)` now writes `0.2`; before this the
  payload claimed a 2000 % floor. SOC output is declared in `%` but carries ratios
  (F-053), so reading it back needs the same conversion.
- **Policy support in the plan and the checks.** `ElementPlan.flat` carries keys that
  live next to the sections (`rules`); pre-validation rejects a connected policy, a
  policy without rules, a negative price, and a rule that names an unknown element.
- **Schema keys for the fields we now fill**: `window_calendar` is required for
  `ev_charger`; `initial_soc_pct`, `import_price_entity`, `export_price_entity`,
  `deficit_price`, `overage_price`, `connected_entity` and friends are allowed keys
  instead of "unknown key" errors.

## Why this matters

Two modelling gaps were blocking every realistic profile. Both now have answers read
from HAEO's own source rather than invented: a charger has a schedule, not a battery
of unknown size, and cycling wear is a price on a flow, which is exactly what HAEO's
policy compiler exists to place. The ratio fix is the kind of defect that would have
passed review and then modelled a battery that can never charge.

## Verification

- `python -m pytest -q` → 130 passed, 7 live tests deselected.
- `python -m ruff check .` → clean.
- `python tools/check_boundaries.py` → `constraint probes: clean`.
- Evidence: SOURCES S-029..S-032, FACTS F-050..F-056; OQ-019/OQ-020 resolved from
  source; OQ-021 (efficiency units) and OQ-022 (who supplies the calendar) opened.

## Not done

- No live run: `ELEMENT_FIELDS_LIVE_VERIFIED` and `HAEO_SURFACE_LIVE_VERIFIED` remain
  `False`, so `apply_plan` still blocks on `haeo_type_unverified`.
- Charging-side wear is deliberately unpriced (OQ-020 open half).
- The deferrable-load calendar is a placeholder in the gateway example; deciding
  whether our integration creates calendars is a product call (OQ-022).
- `meter`, `thermostat`, `relay` still have no element carrier.
