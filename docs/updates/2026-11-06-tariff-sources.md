# 2026-11-06 — Tariff sources: user input, cloud quotes, and the authority between them

## What changed

- **Prices are now published.** `custom_components/fleetassistant/sensor.py` creates
  one sensor per price input, using the exact object id the compiled plan references
  (`sensor.fleetassistant_<site>_price_import` / `_price_export`). Each carries the
  series in a `forecast` attribute (F-016's `{"time", "value"}` shape) plus
  provenance. This closes the gap where a plan pointed at entities nobody published.
- **Two sources merge under an explicit authority** (ADR-0019):
  `custom_components/fleetassistant/pricing/sources.py` adds `SeriesResult`,
  `CloudTariffSource` (injected fetcher, TTL, request counter), `merge_tariffs`,
  `MergedTariff` and `Divergence`. Authorities: `cloud`, `user`,
  `user_unless_stale`; defaults follow the deployment profile.
- **Staleness is data, not failure.** Lapsed quotes become `stale`, a fresh secondary
  wins, and every fallback/stale/missing period is counted and warned about.
- **Disagreement is recorded.** Both values and the applied one travel in the
  sensor's attributes and diagnostics — no silent override.
- **`resolve_tariffs()`** (in `pricing/compiler.py`) builds both inputs, so the whole
  path is testable without Home Assistant; `runtime.py` calls it during setup,
  audits the result, and forwards the `sensor` platform.
- **Profile + options**: `pricing.authority`, `pricing.cloud.stale_after_minutes` and
  `pricing.export.{currency_per_kwh,hour_multipliers}` are validated; the options flow
  gained a `price_authority` selector (empty = deployment default).

## A latent import cycle, found by wiring

Adding `from .sources import …` to `pricing/compiler.py` broke every import with
`ImportError: cannot import name 'INPUT_NAMES' from partially initialized module`.
Cause: `pricing/series.py` imported `haeo_bridge.contracts`, whose package `__init__`
imports `apply → plan → pricing.compiler`. It only ever worked because tests
happened to import `haeo_bridge` first. `series.py` now resolves the contract lazily
inside `forecast_item()`, so import order no longer matters. Recorded here because
the same trap is one import away anywhere in `pricing/`.

## Verification

- `python -m pytest -q` → 164 passed, 7 live tests deselected.
- `python -m ruff check .` → clean; `python tools/check_boundaries.py` → clean (the
  probe now allows `sensor.py` to import Home Assistant at module level, since a
  sensor entity *is* an HA object; the values it exposes are computed in `pricing/`).
- New tests: 13 in `tests/unit/test_price_sources.py` (precedence, staleness,
  divergence tolerance, missing periods, TTL cache, request counting), 10 in
  `tests/unit/test_price_publisher.py` (forecast shape, provenance, hold-last value,
  authority precedence, examples), 5 in `tests/schema/test_profile_schema.py`
  (authority enum, cloud provider slug, export multiplier arity).
- The review-register test caught the `RL-06` reference in the new sensor docstring
  the moment it stopped being true — the entry was removed rather than reworded.

## Not done

- **No cloud fetcher exists** (RL-20): no vendor credentials, no quota contract, so
  `cloud=` is always `None` in production and an authority of `cloud` degrades to the
  user schedule with a warning. The seat is built; the adapter is not.
- **Divergences do not raise a repair yet** (RL-22); they appear in attributes and
  diagnostics only.
- **`user_unless_stale` is exercised only in tests**: with one source there is
  nothing to be stale against.
- The price sensor's `forecast` attribute name is still unconfirmed against a live
  HAEO (OQ-007), so `forecast_format_verified` is `False` on every published sensor.
