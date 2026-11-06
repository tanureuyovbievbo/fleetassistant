# e02 — HACS packaging spec (D02)

| Field | Value |
|-------|-------|
| Deliverable | `docs/deliverables/D02-hacs-packaging.md` |
| Depends on | e01 accepted |
| Constraints | C-02, C-03, C-05, C-08, C-19, C-20, C-21 |
| Human decision | none left: OQ-003 is closed by ADR-0023 (Apache-2.0). OQ-008 is resolved by ADR-0011. |

## Goal
A packaging spec plus a minimal scaffold that loads in HA: repo layout, `manifest.json` and `hacs.json` contents, minimum HA version, config flow and options flow outline, dependency strategy for highspy/numpy with install docs, release zip mechanics, HACS store submission checklist, and the license decision with its consequences for the fleet cloud.

## Stories
| ID | Story | Owner role |
|----|-------|-----------|
| S1 | Fetch the HACS docs (integration requirements, hacs.json keys, store inclusion) and the HA manifest docs. Resolve OQ-001 (dependency install behavior) with fetched sources. | source-verifier |
| S2 | Draft D02 sections (layout, manifest, hacs.json, minimum HA, flows outline, dependency strategy, release, checklist). | architect |
| S3 | License options memo for OQ-003 and the consequences for the fleet cloud → decided Apache-2.0 by the human (ADR-0023); `LICENSE` + `NOTICE` + `tests/unit/test_licensing.py` in place. | architect, human — **done** |
| S4 | Scaffold: `manifest.json`, `hacs.json`, a minimal `__init__.py` and `config_flow.py` that loads with zero entities. CI: hassfest and HACS validation. | engineer |
| S5 | Install docs: HAEO install path (including highspy/numpy notes as verified in S1), then fleetassistant. | architect |
| S6 | Reviews and human gate. | reviewer, claims-auditor, human |

## Acceptance criteria
- [ ] The domain is `fleetassistant`. The display name is "fleetassistant". No collision with `haeo`, HA core, or the HACS default list (check before release).
- [ ] `manifest.json` lists `haeo` in dependencies or after_dependencies. The choice is justified with a fetched source.
- [ ] Every manifest and hacs.json key is backed by a fetched doc (C-23).
- [ ] OQ-001 is resolved or kept explicitly open, with the conservative policy applied.
- [ ] The scaffold passes hassfest and the HACS action in CI.
- [ ] The license decision is recorded as an ADR, including the GPL-3 implications for any HAOS appliance (C-19).
