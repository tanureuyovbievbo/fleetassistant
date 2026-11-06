# 2026-11-06 — HAEO element field table and topology as connection fields

## What changed

- `custom_components/fleetassistant/haeo_bridge/fields.py` (new) records the element
  surface of HAEO v0.5.0 as data: for each HAEO element type (`grid`, `battery`,
  `load`, `solar`, `ev`) the section name, field name, value kind (constant, entity,
  number, status, price, energy, power), profile key, required flag, default, unit
  and source. `PROFILE_ONLY_KEYS` names the profile keys HAEO has no field for
  (`vendor`, `model`, `topology`, `peak_kw`, `degradation_cost`, …), and
  `ELEMENT_FIELDS_LIVE_VERIFIED = False` keeps the live gate closed.
- `haeo_bridge/plan.py` — `ElementPlan` now carries `sections`, `connection`,
  `missing_fields`, `ignored_keys` and `profile_extras`; `compile_plan()` synthesises
  one `junction` bus per system and points every connected element at it. Grid price
  fields are filled from the price sensors we publish
  (`pricing.compiler.price_entity_id`), overridable with `compile_plan(price_entities=…)`.
- `haeo_bridge/apply.py`, `flows.py`, `contracts.py` — connection operations removed
  from the driver (topology is a field), payload comparison matches what HAEO reports,
  and pruning is off: an element we did not create yields the warning
  `element_not_pruned` instead of a deletion.
- `haeo_bridge/prevalidate.py` — new `haeo_field_missing`, `element_unconnected`,
  `dangling_connection` for a bad `connection` target, and the warning
  `profile_key_unmapped`.
- Tests: `tests/unit/test_haeo_bridge.py` and `tests/unit/test_ha_driver.py` rebuilt
  around real field names and a bus junction; new proofs that topology is a field, that
  an unexpected element is reported and not deleted, and that grid prices come from our
  published sensors.

## Why this matters

The bridge previously could not describe a site without inventing a `connection`
object HAEO does not have, and it could not write a single element field without a
placeholder. Both are gone: every payload key now traces to a fetched schema file,
and the plan's topology is expressed in HAEO's own vocabulary. OQ-017 moves from
open to in-progress (source resolved, live pending) and OQ-018 narrows to the
junction question.

## Verification

- `python -m pytest -q` → 127 passed, 7 live tests deselected.
- `python -m ruff check .` → clean.
- `python tools/check_boundaries.py` → `constraint probes: clean`.
- Markdown relative-link scan → no broken links.

## Not done

- No live run: `ELEMENT_FIELDS_LIVE_VERIFIED`, `HAEO_SURFACE_LIVE_VERIFIED` and
  `HA_PORT_LIVE_VERIFIED` are all still `False`, so `apply_plan` blocks on
  `haeo_type_unverified` for any real profile. Units (kW vs W, % vs 0–1) are recorded
  from schema hints and remain unconfirmed by a write.
- `ev_charger` is unmapped (OQ-019) and the priced degradation term still has no
  decided carrier (OQ-020); both block profiles that use them.
- `runtime.py` does not call the driver yet — deliberately, because a live apply would
  otherwise fire on setup for every user.
