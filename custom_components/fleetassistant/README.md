# custom_components/fleetassistant

Home Assistant custom integration. Copy (or install via HACS) into
`config/custom_components/fleetassistant/`, restart HA, then add the integration
through the UI. YAML setup is not supported (C-05).

## Module map

| Module | Responsibility | Constraint |
|--------|----------------|-----------|
| `__init__.py` | Entry points; no module-level HA import | C-08 |
| `runtime.py` | Setup/unload per config entry, repair issues | C-05 |
| `config_flow.py` | Config flow + options flow | C-05 |
| `site.py` | Site runtime container, default profile | — |
| `profile/` | Versioned site-profile schema, loader, migrations | C-10 |
| `haeo_bridge/` | Plan compile → pre-validate → apply via config flow | C-06, C-07, C-23 |
| `pricing/` | Generic price/target model, degradation term | C-13, C-14 |
| `adapters/` | Capability declarations, safety pipeline, stubs | C-09 |
| `executor.py` | Plan execution, staleness, fail-safe | C-12, C-15 |
| `audit.py` | Hash-chained append-only audit log | C-18 |
| `ledger.py` | Per-site commitments ledger | C-16 |
| `telemetry.py` | Envelope v1 validation, dedupe, reconciliation inputs | D07 |

## Boundaries (mechanically checked)

`python tools/check_boundaries.py` fails the build when:

- anything outside `haeo_bridge/` imports HAEO internals (C-06);
- any file references `.storage` (C-06);
- anything outside `adapters/` calls device services (C-09);
- `manifest.json` declares pip requirements (C-08).

## Unverified items this code refuses to guess

- HAEO element type names (`haeo_bridge/plan.py:DEFAULT_TYPE_MAP` — all `None`),
  hub option keys (`HubPlan.options`), forecast payload shape
  (`pricing/series.py:FORECAST_FORMAT_VERIFIED`), and the degradation input
  representation (`pricing/compiler.py:INPUT_NAMES_VERIFIED`).
- While those are unverified, a plan is **blocked** before any config-flow call.
  That is intentional (C-23): fail at home, not on a customer site.
