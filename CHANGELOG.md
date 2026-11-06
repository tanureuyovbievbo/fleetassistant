# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning follows [Semantic Versioning](https://semver.org/). Integration releases use the same version as `manifest.json` (see D02).

## [Unreleased]

### Added
- v1 core implementation (pure Python, no Home Assistant required at import time):
  - `profile/` — versioned site-profile schema (v1) with codes for dangling references, HAEO-name leaks, capability/unit mismatches, and cloud-primary authority violations; JSON/YAML loader and migration hook.
  - `haeo_bridge/` — plan compiler, referential-integrity pre-validation, version pin gate, and an idempotent applier that diffs hubs/elements/connections. Element type names and hub option keys stay unverified, so applying is blocked by design (C-23).
  - `pricing/` — flat, TOU block, and dynamic-series providers; generic target/incentive overlays; compiler that emits forecast-series price inputs plus a required priced battery-degradation term.
  - `adapters/` — capability descriptors (limits, rate limit, hysteresis, consent, backing, authority, fail-safe), safety pipeline, and API-backed plus Modbus-backed stub adapters behind one contract.
  - `executor.py`, `audit.py`, `ledger.py`, `telemetry.py` — plan execution with staleness and fail-safe, SHA-256 hash-chained audit log, commitments ledger that rejects over-commitment, telemetry envelope v1 with dedupe and firm/estimated separation.
  - Home Assistant glue: `config_flow.py` (config + options), `runtime.py` (repairs on validation failure), `manifest.json` with zero pip requirements, `hacs.json`.
- Tests: 93 passing (schema examples and broken variants, bridge plan/apply/idempotency/version gate, pricing, adapters, executor, ledger, telemetry, boundary probes).
- CI: `ci.yml` (ruff, boundary probes, pytest, hassfest, HACS validation, manifest pin check), `release.yml` (zip + release), `haeo-contract.yml` (manual live-HAEO contract run).

### Added
- Repository bootstrap: README, AGENTS.md (model-agnostic agent instructions), CONVENTIONS.md.
- Planning spine: `specs/` (state, release plan with epics e00–e12, execution status, product vision/scope/glossary, ADR-0001 to ADR-0010, tech-architecture plans).
- Documentation: project brief, constraints C-01 to C-24, deliverable stubs D01 to D12 with required outlines and acceptance criteria, facts ledger, sources register, open questions, update log.
- Agentic harness in `.pi/`: generic agent roles, project skills, and orchestration prompts.
- Placeholder directories for the integration, site profiles, rule packs, fleet services, and tests. No implementation code.

### Changed
- Product renamed from HA-OPENDERMS (domain `openderms`) to fleetassistant (domain `fleetassistant`) to match the repository (ADR-0011). Resolves OQ-008.
