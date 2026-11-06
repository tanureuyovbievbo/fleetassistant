# 2026-11-05 — e04 spike, source half: HAEO v0.5.0 surface read and recorded

**Role:** source-verifier
**Epic:** e04-haeo-bridge (story S1)
**Trigger:** the human chose to run the spike from the pinned HAEO source before writing any HA driver code.

## What changed

| Area | Change |
|------|--------|
| Code | `haeo_bridge/contracts.py` (new, records the whole surface), `plan.py` (`HubPlan.config_data()`/`options_data()`, real type names), `prevalidate.py` (four codes instead of one), `pricing/series.py` (`forecast_item`) |
| Tests | `tests/unit/test_haeo_contract_surface.py` (11 offline tests), updated bridge/pricing tests, reshaped live xfail tests |
| Verification | SOURCES S-007..S-016, FACTS F-015..F-030, OQ-002/006/007/009 narrowed, OQ-016/OQ-017 opened |
| Decisions | ADR-0013 (proposed): one HAEO element per profile kind, unmapped kinds block |
| Spike note | `specs/archive/spikes/SPIKE-2026-11-05-haeo-v050-surface.md` |

## The three findings that changed the design

1. **Elements and connections are config _subentries_ of the hub entry, not config entries.**
   The brief said "Element entries". At v0.5.0 there is one config entry per hub
   (`HaeoConfigFlow = HubConfigFlow`) and every element is a subentry whose
   `subentry_type` is the element type. This changes the runtime driver (it must
   create subentries, not entries) but not the plan: `ElementPlan` already carries
   `(system_id, name, kind, haeo_type, params, inputs)`.
2. **HAEO has 13 element types and none of them is `meter`, `thermostat`, or `relay`.**
   Four of our kinds map cleanly. The other three are now an explicit modelling
   question (ADR-0013) instead of a lookup that would have produced a plausible,
   wrong answer.
3. **The horizon is a tagged value, and "Relax impossible plans" is options-only.**
   `{"value": "5_days"}` versus `{"value": ["sensor.x"]}`, and `relax_infeasible`
   defaults to `False` — so writing our fleet default (`True`) is a deliberate act
   on the options flow, not an omission. That matches ADR-0009 and is now testable
   offline.

## What deliberately did not change

- `HAEO_SURFACE_LIVE_VERIFIED` stays `False`; `HaeoTypeMap.verified` stays `False`;
  `pricing/series.py:FORECAST_FORMAT_VERIFIED` stays `False`.
- The apply gate still blocks. Reading a file is not verification of a live flow
  (C-23), and the difference is exactly what this spike recorded.

## Verification run

```
python -m pytest -q            -> all tests pass (114)
ruff check .                   -> clean
python tools/check_boundaries.py -> constraint probes: clean
```

## Open after this session

- `SPIKE-LIVE-ACCESS` (human): a live HA 2026.1.1 + HAEO v0.5.0 instance, or a run
  of the `haeo-contract` workflow, to close OQ-002/OQ-006/OQ-007 and flip the gate.
- OQ-016: HA API for creating config subentries programmatically (unblocks the real driver).
- OQ-017: per-element required field keys and units.
- ADR-0013 is `proposed`; a human or the architect must accept it before v1 apply is unblocked.
