# SPIKE — HAEO v0.5.0 configuration surface

| Field | Value |
|-------|-------|
| Date | 2026-11-05 |
| Question | What does HAEO v0.5.0 actually store for a hub, its elements, and its connections, and in what shape? |
| Method | Read the pinned source at tag `v0.5.0` (commit `705bde0b1a43997dc844b60b32cbbb92032c96ea`). No live instance was available. |
| Outcome | Names and shapes are now source-verified. The apply gate stays **closed** until a live instance confirms them (C-23, ADR-0012). |
| Cost | One session; 10 source files read. No code was guessed, so nothing has to be un-guessed. |

## Why spike this first

The bridge is the highest-risk part of v1: it drives another integration's UI
flow, which its maintainers describe as a private API. Every hour spent on the
control adapters, pricing, or telemetry assumes the bridge can write a network.
Reading the source first means the rest of the code is written against facts.

## What the source says

### Hub

- Creation data is **sectioned**:
  `{integration_type: "hub", common: {name, horizon}, advanced: {debounce_seconds: 2, advanced_mode: false}}` [F-017].
- The setup form has only three fields: name, horizon, advanced mode [F-028].
- The horizon is a **tagged value**, never a bare string: preset → `{"value": "5_days"}`, forecast sensor → `{"value": ["sensor.x"]}` [F-022].
- Presets are `2_days`, `3_days`, `5_days`, `7_days`; there is no arbitrary-days preset [F-023]. Default layout is 5×1 min, 11×5 min, 46×30 min, 48×60 min [F-024].
- Unique id is `haeo_hub_<name>` and duplicate names are rejected with `name_exists` [F-019].
- "Relax impossible plans" is `relax_infeasible`, lives in the **options** flow's advanced section, default `False` [F-025]. A hub cannot be created with it set.
- A new hub is created with two subentries of its own: a `network` subentry and a switchboard `junction` [F-020].

### Elements and connections

- They are **config subentries** of the hub entry, not separate config entries [F-018]. `subentry_type` equals the element type; a bare element subentry starts as `{name, element_type}`.
- Element flows are filtered by an `advanced` flag per type, so advanced-mode hubs expose more types.
- Field values are **tagged**: `{"type": "entity", "value": [entity_id, ...]}` (optionally with `on_states`/`off_states`) or `{"type": "constant", "value": <float|bool>}` [F-021].
- There are 13 element types [F-015]: `battery, battery_section, buffer, connection, deferrable_load, ev, grid, inverter, junction, load, node, solar, policy`.
- **There is no `meter`, `thermostat`, or `relay` element** [F-016].

### Forecast inputs

- A `forecast` attribute point names its boundary `time`, ignores other keys, and carries the value under `value`; `n + 1` boundaries describe `n` periods; tz-less times are read in the HA time zone; fewer than two increasing times is an error [F-027].
- HAEO ships one extractor per recognised source format, so "a forecast sensor" is not one shape but a family (OQ-007 still open for price/load/solar).

### Pricing

- A `policy` element type exists, and the battery and load element forms carry "policy pricing" hints [F-029]. Field names for segments, Tagged Power, and the shadow-price outputs are still open (OQ-011).

## What changed in the code

| Change | File |
|--------|------|
| Recorded the whole source-verified surface in one place, with anchors and a separate live-verified flag | `custom_components/fleetassistant/haeo_bridge/contracts.py` |
| Kind → element type map now carries real names for grid, solar, battery, load, ev; `meter`, `thermostat`, `relay` stay `None` | `custom_components/fleetassistant/haeo_bridge/plan.py` |
| Hub records are built as HAEO stores them: `config_data()` (sectioned creation data, tagged horizon) and `options_data()` (`relax_infeasible` written explicitly) | `custom_components/fleetassistant/haeo_bridge/plan.py` |
| Two distinct blocking codes: `haeo_type_unverified` (live gate) and `haeo_kind_unmapped` (modelling gap); plus `haeo_type_unknown` and `horizon_preset_unsupported` | `custom_components/fleetassistant/haeo_bridge/prevalidate.py` |
| Forecast items use HAEO's `time` boundary key, with `datetime` available for generic HA consumers | `custom_components/fleetassistant/pricing/series.py` |
| Offline regression tests over the recorded surface | `tests/unit/test_haeo_contract_surface.py` |

## What is still open

| Item | Tracked as |
|------|-----------|
| Which HAEO element models our `meter`, `thermostat`, `relay` kinds | OQ-002 (needs an ADR, not a lookup) |
| Per-type required field keys and units (e.g. grid `power_limits` → `CONF_MAX_POWER_SOURCE_TARGET`) | OQ-017 |
| HA API for creating config subentries programmatically, and its headless reachability | OQ-016, OQ-009 |
| Sensor formats HAEO accepts for price, load, solar inputs | OQ-007 |
| Policy/segment/Tagged Power field names and shadow-price outputs | OQ-011 |
| Repair issue translation keys for broken references | OQ-006 |

## Live confirmation procedure

1. Install HA `2026.1.1` (HAEO's floor, [F-010]) plus `haeo` `v0.5.0` from the release zip, with `highspy`/`numpy` available.
2. Run the `haeo-contract` workflow with `haeo_version=0.5.0`; the three `xfail(strict=True)` tests must start failing, which is the signal to flip constants.
3. Create a hub through the flow, then read it back: confirm `common.horizon` holds a tagged value and that `advanced.relax_infeasible` is present after the options write.
4. Create one element per kind we use and confirm the subentry `data` keys we write are accepted.
5. Feed a compiled price series to an input sensor and confirm HAEO reads it.
6. Only then set `HAEO_SURFACE_LIVE_VERIFIED = True`, mark the type map verified, and record the live run in `docs/verification/`.

## Rejected shortcuts

- **Filling the kind map from memory.** Rejected: our own brief asserted an "Element entries" model that v0.5.0 does not have, which is exactly the failure mode this rule exists for.
- **Copying field names out of the HAEO user docs.** Rejected for now: the docs describe the UI, and UI labels are not stored keys. Source first, live second.
- **Driving HAEO by writing its storage file.** Rejected outright (C-06), independent of what the spike found.
- **Treating a live rejection as the source of truth without reading the code.** Rejected: a live error tells you a key is wrong, not which key is right.
