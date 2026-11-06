# 2026-11-05 — v1 core implementation (increment 1)

**Role:** engineer. **Trigger:** user m00288, "Begin coding based on plans".
**Scope:** the pure-Python core of the v1 site layer plus the Home Assistant glue and CI. Docs written during bootstrap were used as the plan; no deliverable gate was re-opened.

## What now exists

| Area | Module | Verified behaviour |
|------|--------|-------------------|
| Schema | `profile/schema.py`, `profile/loader.py` | 3 worked examples validate; 4 invalid fixtures fail with a specific code |
| Bridge | `haeo_bridge/{plan,prevalidate,apply}.py` | compile → pre-validate → idempotent apply; blocked while HAEO names are unverified |
| Pricing | `pricing/{providers,series,overlay,compiler}.py` | flat/TOU/dynamic, overlays, degradation term, zero rule packs |
| Control | `adapters/{base,safety,stubs}.py`, `executor.py` | clamp, consent, rate limit, hysteresis, fail-safe, identical contract for API and Modbus stubs |
| Records | `audit.py`, `ledger.py`, `telemetry.py` | tamper-evident audit chain, over-commitment rejection, telemetry envelope + dedupe |
| HA glue | `__init__.py`, `runtime.py`, `config_flow.py` | config + options flow, repairs on invalid profile, no module-level HA import in the core |
| Tooling | `tools/check_boundaries.py`, `.github/workflows/*` | C-06/C-08/C-09 probes, CI, release zip, manual live-HAEO contract run |

Test count: **102 passing** (`pytest -q`), ruff clean, boundary probes clean.

## Deliberate refusals

- `haeo_bridge/plan.py:DEFAULT_TYPE_MAP` maps every kind to `None`. A plan therefore
  fails pre-validation with `haeo_type_unverified` and never reaches a config flow.
  This is C-23 working as designed, not an unfinished function.
- `pricing/series.py:FORECAST_FORMAT_VERIFIED` is `False`, and
  `pricing/compiler.py:INPUT_NAMES_VERIFIED` is `False`. Emitted payloads carry
  `format_verified: false` so a consumer cannot mistake them for a verified contract.
- The degradation input representation is emitted as data with
  `representation_verified: false` (OQ-012) rather than guessed into a HAEO field.

## Open gates after this increment

1. **OQ-002 / OQ-006 / OQ-007** — HAEO element types, hub option keys, forecast payload.
   These require the e04 spike against a live HAEO `v0.5.0`. Until they close, no site
   can be provisioned, which is the honest state.
2. **OQ-001** — dependency policy conflict (HA dev docs vs brief). Current build ships
   zero requirements and therefore cannot use highspy itself; it only depends on HAEO's
   own installation.
3. **OQ-003** — license decision still blocks the public release, not the code.
4. `site_profiles/examples/tesla_cloud_primary.yaml` tariff values are marked PLACEHOLDER.
   They are illustrative site data, not a claim about any real tariff.

## Next increments (in order)

1. e04 spike: read the real HAEO config-flow schema at v0.5.0, fill `DEFAULT_TYPE_MAP` and
   the hub option keys, flip `verified`, and turn the `xfail(strict=True)` contract tests green.
2. HA integration tests with `pytest-homeassistant-custom-component` (config flow, repairs,
   unload) and a `haeo_bridge/ha_driver.py` implementing `HaeoDriver` over
   `hass.config_entries.flow.async_init/async_configure`.
3. Telemetry publisher (MQTT/HTTP client seam) and the fleet-side ingest stub.
