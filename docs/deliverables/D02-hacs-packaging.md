# D02 — HACS Packaging Specification

| Field | Value |
|-------|-------|
| ID | D02 |
| Epic | e02-hacs-packaging |
| Version | 0.0.0 (stub) |
| Status | in-progress |
| Owner role | architect |
| Last updated | 2026-11-05 |
| Depends on | D01, C-02, C-03, C-05, C-08, C-19, C-20, F-006, F-010, F-013, F-014, OQ-001, OQ-003, OQ-004, OQ-008, OQ-010 |

> **Implementation:** manifest.json, hacs.json, CI, and release zip exist. License decided 2026-11-06: **Apache-2.0** (ADR-0023) with `LICENSE`, `NOTICE`, and `tests/unit/test_licensing.py`; the HACS submission checklist is now blocked only on a release tag and store review.
>
> The outline below remains the acceptance contract; code lands against it.
>
> **Stub outline.** Required structure and acceptance criteria.

## Required outline

1. **Repository layout.** Final tree for `custom_components/fleetassistant/` (`__init__.py`, `manifest.json`, `config_flow.py`, `const.py`, `strings.json`, `translations/`, `diagnostics.py`, `repairs.py`, `haeo_bridge/`, `adapters/`, `pricing/`, `profile/`, `telemetry/`, `ledger/`, `audit/`). Root files: `hacs.json`, `LICENSE`, `info.md` or README rendering.
2. **`manifest.json` contents.** Specify every key with its value and the reason: `domain`, `name` ("fleetassistant"), `version`, `config_flow`, `integration_type`, `iot_class`, `dependencies` / `after_dependencies` (does fleetassistant declare `haeo`? weigh hard dependency against soft detection), `requirements` (C-08), `codeowners`, `documentation`, `issue_tracker`. Confirm each key against HA dev docs (C-23).
3. **`hacs.json` contents.** `name`, `homeassistant` (minimum version, OQ-004; floor 2026.1.1 per F-010), `zip_release`, `filename`, `render_readme`, `hacs`. Confirm the keys against HACS docs.
4. **Minimum HA version** and the reasoning for it.
5. **Config flow and options flow outline.** Steps, fields, validation, and the error → repair-issue mapping (C-05). Include a step that imports a site profile (file upload or paste). Include detection of HAEO presence and version.
6. **Dependency strategy.** Our own runtime dependencies (target: none beyond HA core). HAEO's highspy/numpy: how a user installs them on each install type (HAOS, Container, Core). Resolve OQ-001 and OQ-010 first. Write the user install docs (draft text included here).
7. **Release and zip mechanics.** Versioning (SemVer, tag `vX.Y.Z`), GitHub Actions workflow outline (lint, test, hassfest, HACS action, build zip, attach to release), and a changelog policy.
8. **HACS store submission checklist.** Each item cites the HACS docs (fetched).
9. **Brand and naming.** Brand asset policy (C-20) and the domain collision check (C-03).
10. **License decision (resolved).** Apache-2.0 for the repository (ADR-0023), decided by the human on 2026-11-06.
    - Why: §3 patent grant with retaliation and §5 inbound=outbound contributions are what utility procurement and
      an acquirer read; MIT is silent on both.
    - Fleet cloud: Apache-2.0 has no network-service clause, so the multi-tenant services stay closed. AGPL-3.0 was
      rejected for exactly that reason.
    - HAEO stays MIT (one-way compatible; reproduced in `NOTICE`); no HA/HACS/HAEO source is vendored, so §4(b)
      "modified file" markers apply to nothing.
    - GPL-3 exposure when shipping a modified HAOS appliance is unchanged (C-19): source availability applies to
      HAOS/Supervisor/CLI, not to this repository.
    - Enforced by `tests/unit/test_licensing.py` (licence text, NOTICE contents, no affiliation claim, pyproject
      agreement, no vendored upstream source, device-pack licence fields).
11. Open questions · Constraint compliance · Change log.

## Acceptance criteria

- [ ] Every manifest and hacs.json key is backed by a fetched source (S-ID).
- [ ] Install docs cover HAOS, Container, and Core, or explicitly mark an install type unsupported.
- [ ] OQ-001 and OQ-010 are resolved, or the install docs carry a clear UNVERIFIED warning.
- [ ] A human has signed the license decision (recorded as an ADR).
- [ ] Human review gate passed.
