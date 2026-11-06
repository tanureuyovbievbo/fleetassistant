# 2026-11-06 - First CI run on GitHub

## What happened

The work was pushed to `feat/v1-site-layer` (18 commits, `main` untouched). CI had never
run before, so its first run was the first real test of assumptions made on Windows.

Run 1 (`b292a3a`) - 2 of 4 jobs failed:

| Job | Result | Cause |
| --- | --- | --- |
| Core (ruff, probes, pytest) | pass | the suite is portable; 316 tests pass on `ubuntu-latest` |
| Dependency and version pins | pass | `requirements: []` and the HAEO pin survive |
| hassfest | fail | `[MANIFEST] Manifest keys are not sorted correctly`; `[CONFIG_SCHEMA]` warning for an `async_setup` with no `CONFIG_SCHEMA` |
| HACS validation | fail | the repository was private at run time |

## Fixes

1. `manifest.json` keys re-sorted (`domain`, `name`, then alphabetical) and `categories`
   added (`energy.energy_prices`, `energy.solar_batteries`, after checking the list at
   `contributors.home-assistant.io/core/integrations/categories/`).
2. `async_setup` deleted from `__init__.py`. hassfest demands a module-level
   `CONFIG_SCHEMA` from any integration that defines `async_setup`, and that import would
   break the hygiene rule that the package imports without Home Assistant (C-08). This is
   a config-entry-only integration (C-05), so the function had no purpose.
3. `LICENSE` reduced to the canonical Apache-2.0 text; the "edit later" note moved to the
   top of `NOTICE`. GitHub's licence detector reads the whole file, so the note prefix made
   it report **no license**, which is exactly what HACS' licence check tests.
4. Brand assets generated: `custom_components/fleetassistant/brand/icon.png` (256x256) and
   `logo.png` (512x256), valid PNGs built deterministically (no image library needed).

Run 2 (`60bf8f3`) - hassfest passes, HACS is down to one failure: **no repository topics**.
Topics are repository metadata, not files: they need `home-assistant` and `hacs` set in the
repository settings (or via the API with a token, which this environment does not have).

## Not verified

- HACS validation cannot pass until topics are set; the remaining checks (brands, licence)
  are satisfied locally but unconfirmed on GitHub.
- `hassfest` accepts `quality_scale: custom` for a custom integration (verified in
  `home-assistant/core@2026.1.1` `script/hassfest/manifest.py`), so the field stays.
