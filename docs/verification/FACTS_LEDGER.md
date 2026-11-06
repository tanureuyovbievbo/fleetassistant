# Facts ledger

This file holds verified technical facts about HAEO, Home Assistant, HACS, and vendor APIs. Each fact has an ID, a source, and an access date. Deliverables cite facts as `[F-NNN]`.

**Rules**
- A fact is `verified` only when the source was fetched and the exact value was read from it.
- A fact can go stale. Re-verify each fact at the **pinned** HAEO version (see ADR-0004) before code depends on it.
- If a fact conflicts with the brief, record the conflict in `OPEN_QUESTIONS.md`. Do not silently pick one.

| ID | Fact | Value | Source | Accessed | Status | Used by |
|----|------|-------|--------|----------|--------|---------|
| F-001 | HAEO domain | `haeo` | S-001 | 2026-11-05 | verified | C-03, D02 |
| F-002 | HAEO config_flow | `true` | S-001 | 2026-11-05 | verified | D04 |
| F-003 | HAEO integration_type | `hub` | S-001 | 2026-11-05 | verified | D01, D04 |
| F-004 | HAEO iot_class | `local_push` | S-001 | 2026-11-05 | verified | D01 |
| F-005 | HAEO quality_scale | `platinum` | S-001 | 2026-11-05 | verified | D02 |
| F-006 | HAEO requirements | `["highspy>=1.15.1", "numpy>=2.3.2"]` | S-001 | 2026-11-05 | verified | C-08, D02 |
| F-007 | HAEO manifest version on `main` | `"0.5.0"` | S-001 | 2026-11-05 | verified | ADR-0004 |
| F-008 | HAEO after_dependencies | `["calendar", "frontend", "http", "recorder"]` | S-001 | 2026-11-05 | verified | D02 |
| F-009 | HAEO manifest `dependencies` | `[]` | S-001 | 2026-11-05 | verified | D02 |
| F-010 | HAEO hacs.json | `{"name": "HAEO", "hacs": "2.0.5", "homeassistant": "2026.1.1", "filename": "haeo.zip", "render_readme": true, "zip_release": true}` | S-002 | 2026-11-05 | verified | D02 (minimum HA version floor; zip-release pattern) |
| F-011 | Latest HAEO release | `v0.5.0`, published 2026-10-27 (previous: `v0.5.0rc3`, 2026-10-23) | S-003 | 2026-11-05 | verified | ADR-0004 |
| F-012 | HAEO license | MIT | S-004 | 2026-11-05 | verified | C-19, D02 |
| F-013 | HAEO uses the HiGHS solver through highspy | README: "bundled `highspy` bindings" | S-005 | 2026-11-05 | verified (wording only; packaging mechanism not verified) | D02, OQ-010 |
| F-014 | HA installs integration `requirements` | HA dev docs: "Home Assistant will try to install the requirements into the `deps` subdirectory of the Home Assistant configuration directory if you are not using a `venv`…" If installation fails, the integration fails to load. | S-006 | 2026-11-05 | verified | C-08, OQ-001 |

## Brief claims still awaiting verification

These claims appear in the brief. They are treated as **UNVERIFIED** until an F-ID exists for them.

| Brief claim | Tracked as |
|-------------|-----------|
| HAEO setup order: Hub (with horizon) → Element entries → Connection entries; config-flow only, no YAML | OQ-002, OQ-009 |
| HAEO supports multiple hubs per HA instance | OQ-002 |
| HAEO creates an input entity for every configured field (runtime-writable constants) | OQ-002 |
| Horizon presets 2/3/5/7 days (default 5); periods grow 1 → 5 → 30 → 60 min | OQ-007 |
| Custom horizon from a forecast sensor whose `forecast` attribute lists period boundaries | OQ-007 |
| HAEO consumes forecast-style sensors (time + value points) | OQ-007 |
| Pricing segments / policy pricing / Tagged Power; per-node shadow prices | OQ-011 |
| Hub setting "Relax impossible plans" (default off); repair issues for broken references and unresolvable constraints | OQ-006 |
| HAOS Supervisor "Python packages" setting is the path for highspy/numpy | OQ-001, OQ-010 |
