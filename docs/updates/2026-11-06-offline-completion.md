# 2026-11-06 — Every step that does not need a human or a live instance

The instruction was to complete everything that does not require a human decision
or a live Home Assistant + HAEO instance. Seven steps were on the roadmap; six are
now implemented, and the seventh (the version matrix) is written but its single
row is honestly marked unverified.

## What changed

| Step | Artifact | What it does |
| --- | --- | --- |
| Telemetry producer | `custom_components/fleetassistant/telemetry/producer.py` | Turns observations, plan records, dispatch outcomes and device read-backs into envelopes that pass the v1 validator. One envelope per `(quality, source, authority)` group, because the schema carries a single quality and mixing measured with estimated would lie structurally. |
| Device packs | `custom_components/fleetassistant/device_packs/__init__.py`, `device_packs/examples/solark_example/pack.json` | Data-only brand contracts (ADR-0022): per-capability entity binding, safety envelope, `iot_class`, sources, `verified`. A cloud integration cannot bind full authority; an unsourced or unverified pack says so. |
| Commitments guard | `ledger.py` (`conflicts`, `headroom`), `dispatch.py` (`_conflict`) | A dispatch that would deliver a capability another program already holds is refused **before** the executor runs, and audited as `dispatch.refused`. C-16 moves from "a data structure exists" to "the dispatch path consults it". |
| Price repairs | `runtime._publish_price_repairs` | Divergences and degraded forecasts become repairs, with the worst period spelled out. Closes RL-22. |
| Reference re-check | `runtime._watch_references` | Every referenced entity is subscribed; a rename or removal raises its repair within one state event instead of at the next restart. Closes RL-24. |
| Fleet allocation | `fleet/allocation.py` | Merit-order allocation with availability, opt-out, comfort reserve, battery-life and share caps; simultaneous capacity from windows; dispatch deltas with hysteresis; bounded feedback trim. |
| Preflight tool | `tools/preflight.py` | Offline: validate, compile, prevalidate, resolve tariffs, list references. Exit code 1 on any error. The examples exit BLOCKED on the two deliberate gates. |
| Telemetry transport | `custom_components/fleetassistant/telemetry/transport.py` | Validates before sending, falls through sinks (a 4xx at one sink still tries the next, a 5xx spools), and keeps a bounded oldest-first spool so a network blip costs nothing and a long outage is visible. |
| Version matrix | `docs/ops/VERSION_MATRIX.md` | The four layers, where each pin lives, the one (unverified) supported combination, how a combination becomes supported, and the per-tenant rollback table. |

## Why the producer splits envelopes

The v1 envelope carries one `quality` and one `authority`. `Executor` writes a
setpoint and gets back a `WriteResult`; the device then reports a value that may
differ. Emitting both in one payload would either launder a commanded value into
`measured` (breaking `is_firm()`) or discard the confirmation. So the producer
builds up to three envelopes per interval and leaves the reconciliation to
`summarise()`.

## Why the share cap is a share of the target

The first implementation capped a share of each site's nameplate. A test showed
the cheapest 20 kW site then absorbed a 10 kW event entirely, which is the
opposite of spreading it. The cap is now `share × target`, so a 0.5 cap makes
every site a 5 kW contributor to a 10 kW event.

## Verification

- `python -m pytest -q` → 304 passed, 7 deselected (live).
- `python -m ruff check .` → clean.
- `python tools/check_boundaries.py` → `constraint probes: clean`.
- `python tools/preflight.py site_profiles/examples/solark_gateway_primary.yaml`
  → 1 hub, 9 elements, 4 controls, 49 price points per input, 6 references, and
  BLOCKED on `haeo_type_unverified` + `haeo_kind_unmapped` — the two gates that
  need a live instance and a modelling decision respectively.

## Still blocked

| Item | Needs |
| --- | --- |
| Flip `HAEO_SURFACE_LIVE_VERIFIED`, `ELEMENT_FIELDS_LIVE_VERIFIED`, `HA_PORT_LIVE_VERIFIED` | a live HA 2026.1.1 + HAEO v0.5.0 run (`pytest -m live`) |
| `meter`/`thermostat`/`relay` carriers (OQ-019/ADR-0013) | a modelling decision, then a field table |
| Any real device pack | OQ-023 research (per brand: entities, models, licence, ToS) |
| Licence decision (OQ-003) | human |
| Cloud tariff fetcher (RL-20) | a vendor contract and quota math |
