# Version matrix and rollback

A fleet site is a stack of four independently released things. The matrix records
which combination we have tested; anything outside it is unsupported, not merely
unlucky.

| Layer | What it is | Where the pin lives |
| --- | --- | --- |
| Home Assistant Core | the host that owns the event loop and the config entries | `hacs.json` → `homeassistant`, image tag per tenant |
| HAEO | the site optimizer we configure through its flows | `SUPPORTED_HAEO_VERSIONS` in `custom_components/fleetassistant/const.py` |
| fleetassistant (this integration) | profile renderer, price model, adapters, dispatch, telemetry | `manifest.json` → `version`, release tag `v*` |
| Device integrations | the transports a device pack binds to | `device_packs/<brand>/pack.json` → `integration.domain` + verification row |

## Current support

| HA Core | HAEO | fleetassistant | Status | Evidence |
| --- | --- | --- | --- | --- |
| 2026.1.1 | 0.5.0 | 0.1.0 | **UNVERIFIED — pending live run** | source-verified only: `HAEO_SURFACE_LIVE_VERIFIED = False`, `ELEMENT_FIELDS_LIVE_VERIFIED = False` |

The single supported combination is deliberately narrow because neither HAEO's
flow surface nor our element fields have been confirmed against a running
instance (OQ-002, OQ-017, OQ-018). The contract tests in
`tests/contract/haeo/` and `tests/contract/ha/` are written as
`xfail(strict=True)`: they turn into failures the moment the stack starts
behaving as recorded, which is the signal to flip the verification booleans.

## How a combination becomes supported

1. Install HA 2026.1.1 and HAEO v0.5.0 on a scratch instance.
2. Run `pytest -m live` with `HAEO_VERSION=0.5.0` (`.github/workflows/haeo-contract.yml`).
3. When the three `xfail(strict=True)` tests start failing because the assertions
   now hold, flip `HAEO_SURFACE_LIVE_VERIFIED`, `ELEMENT_FIELDS_LIVE_VERIFIED` and
   `HA_PORT_LIVE_VERIFIED` in the same commit, and record the run in
   `docs/verification/`.
4. Add the row above with the date and the run's evidence link.

Never widen the matrix on the strength of a changelog.

## Rollback

| Failure | Rollback | Blast radius |
| --- | --- | --- |
| HAEO upgrade breaks the bridge | pin HAEO to the previous tag in the tenant image; `apply_plan` reports `blocked` on the version check rather than writing | the site keeps its last applied plan; dispatch continues on the last fresh plan until it ages out, then fails safe |
| fleetassistant upgrade regresses | install the previous release zip (HACS "Redownload" → choose tag); the config entry and profile are untouched | no re-onboarding: the profile is the source of truth and lives outside the integration |
| HA Core upgrade breaks a device integration | roll the tenant image back; the pack's `verified` row is invalidated until re-checked | adapters fail closed through `SafetyPipeline`; fail-safe values apply |
| Device integration removed | the pack binds nothing; `build_ha_adapters` emits `control_unbound` and the site runs optimizer-only | controls stop, the optimizer keeps planning |

Rollback is per tenant: one image tag, one HAEO pin, one integration version. A
site is never upgraded in place across all four layers at once.

## What this matrix does not cover

- **Add-ons.** We ship an integration, not an add-on (C-04), so Supervisor
  versions do not enter the matrix except as a host detail.
- **Python package versions.** `manifest.json` declares no requirements
  (`requirements: []`), so we never install anything into HA's `deps`
  directory. HAEO's `highspy`/`numpy` need a documented user/ops step (OQ-001).
- **Cloud-primary mirrors.** The cloud mirror is deliberately degraded (C-11):
  it runs no optimizer, so its row is "telemetry only" by design.
