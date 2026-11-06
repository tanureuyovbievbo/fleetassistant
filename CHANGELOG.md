# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning follows [Semantic Versioning](https://semver.org/). Integration releases use the same version as `manifest.json` (see D02).

## [Unreleased]

### Added
- Telemetry producer (`telemetry/producer.py`): envelopes are grouped per
  `(quality, source, authority)` so a commanded setpoint is never laundered into a
  measured value; dispatch rejections become flags, never zero metrics.
- Device packs (`device_packs/`, ADR-0022): data-only brand contracts with a
  per-capability entity binding and safety envelope. A cloud integration binding
  full authority is an error; an unverified or unsourced pack says so in the
  issue list.
- Commitments ledger wired into dispatch: `CommitmentsLedger.conflicts()` /
  `headroom()` and `Dispatcher._conflict()` refuse a dispatch that would deliver a
  capability another program already holds, audit it as `dispatch.refused`, and
  leave the devices untouched.
- Price repairs: `price_divergence` (worst period, both values, chosen value) and
  `price_degraded` (stale, fallback and missing period counts) (closes RL-22).
- Reference re-check: referenced entities are subscribed and re-validated on every
  state change (closes RL-24).
- Fleet allocation (`fleet/allocation.py`): merit order with availability,
  opt-out, comfort reserve, battery-life and share caps, simultaneous capacity from
  declared windows, `dispatch_delta` with hysteresis, bounded `feedback_trim`.
- `tools/preflight.py`: offline validate → compile → prevalidate → tariffs →
  references, human or JSON output, exit code 1 when blocked.
- `docs/ops/VERSION_MATRIX.md`: HA × HAEO × integration pins, the one (unverified)
  supported combination, the procedure that verifies it, and the per-tenant
  rollback table (D08 item 4).
- Dispatch loop (`dispatch.py`, ADR-0021): a plan older than 15 minutes is
  discarded, 30 minutes of optimizer silence writes the per-capability fail-safe
  **once** per outage, a good plan clears the lockout, and unloading the entry
  forces the fallback. Diagnostics expose the last ten outcomes; the audit chain
  records `dispatch.apply` / `dispatch.fail_safe`.
- `MappedPlanSource`: a plan is built from the entities each control names in
  `plan_entity`. A non-numeric state is skipped, never coerced to zero; a missing
  mapping produces a repair, not a guess at HAEO's entity ids (OQ-022).
- Options toggle `dispatch_enabled` (default off) and the `dispatch_failed_safe`
  repair, cleared automatically when a plan is applied again.
- `HaServiceAdapter.read_state` now reads the state machine through an injected
  reader and falls back to the last write only when the entity is missing or
  unreadable (closes RL-23; residual gaps RL-26..RL-28).
- Review register `docs/verification/REVIEW_LATER.md` (18 deliberate gaps, each with
  file, trigger and owner) plus `tests/unit/test_review_register.py`, which fails when
  a code reference `RL-xx` has no row or a row has no trigger/owner.
- Live write path behind the options flag `apply_haeo_plan` (default off):
  `runtime.py` runs `apply_plan` with `FlowHaeoDriver(HomeAssistantFlowPort(hass))`
  in an executor thread, stores the report on `SiteRuntime`, appends a `haeo.apply`
  audit record and raises/clears the `haeo_apply_incomplete` repair issue.
- `HomeAssistantFlowPort` bridges each flow call onto `hass.loop` and blocks, so the
  synchronous bridge driver can run outside the event loop; the driver accepts a
  blocking port (regression test `test_a_blocking_port_is_accepted`).
- Options flow toggle for provisioning, with description text; `SiteRuntime`
  diagnostics now expose the last apply's operations and issues.

### Added
- Setup-time verification of every entity a profile names (forecast sensors, price
  entities, calendars, control entities, the HAEO horizon sensor) with error/warning
  repairs instead of a plan that silently optimises against `unknown` (ADR-0020).
- Local-backed control adapters: `number`/`climate`/`switch` bindings driven through
  an injected service caller, so a gateway site can write export limits, battery
  targets, charger amps, thermostat setpoints and shed circuits (ADR-0020).
- `entity_id` and `scale` on profile controls, so a local control names the entity it
  drives and can convert our unit into the entity's unit.

### Added
- Published price sensors: one sensor per price input (`price_import`, `price_export`),
  carrying the compiled series in a HAEO-shaped `forecast` attribute plus the
  provenance of every period (ADR-0019).
- Dual tariff sources: `pricing/sources.py` merges a user-entered schedule with a
  cloud quote under a per-site authority (`cloud`, `user`, `user_unless_stale`),
  marks lapsed quotes `stale`, prefers a fresh secondary, and records every
  divergence with both values and the applied one.
- `CloudTariffSource`: an injected fetcher, a TTL cache and a request counter, so a
  vendor adapter (when one exists) cannot hide its quota from us (C-22).
- Profile keys `pricing.authority`, `pricing.cloud.stale_after_minutes` and
  `pricing.export.{currency_per_kwh,hour_multipliers}`, plus a `price_authority`
  options-flow selector.

### Added
- Charger modelling: `ev_charger` compiles to HAEO's `deferrable_load`
  (`schedule.window_calendar`, `power.max_power`, `deficit_price`/`overage_price`),
  with `window_calendar` now required by the site-profile schema (ADR-0016). HAEO's
  `ev` element, which models a vehicle, stays unused and recorded.
- Degradation pricing: a battery's `degradation_cost` compiles into a `policy`
  element whose rule prices the battery's discharge (`{source: [battery], target:
  ["*"]}`), because HAEO places a rule's price on the source's outbound edges for a
  single source and a wildcard destination (ADR-0017, F-056).
- Ratio conversion: HAEO's `*_percentage` fields are 0..1 ratios, so profile
  percentages leave as `value / 100` (F-052); the previous payload would have meant
  2000 % for a 20 % floor.
- `policy` payload support (`flat` keys on `ElementPlan`, `contracts.POLICY_*`) and
  policy pre-validation: `policy_rules_missing`, `policy_price_invalid`,
  `policy_connected`, plus rule endpoints checked for dangling names.
- Site-profile schema: element keys for the HAEO fields we now fill
  (`window_calendar`, `initial_soc_pct`, `import_price_entity`, `export_price_entity`,
  `deficit_price`, …).

### Added
- HAEO element field table (`haeo_bridge/fields.py`) recorded from the pinned v0.5.0
  schemas: tagged `entity`/`constant` values, section names (`power_limits`,
  `pricing`, `forecast`, `curtailment`, `storage`, `limits`, `efficiency`,
  `advanced`, `vehicle`, `charging`), and the required/optional key per element.
  Evidence: SOURCES S-021..S-028, FACTS F-040..F-049, `ELEMENT_FIELDS_LIVE_VERIFIED`
  still `False`.
- Topology renders into a per-element `connection` field (`connection_target`) with a
  synthesised `<system>_bus` junction per system; the driver no longer has connection
  read/write operations (ADR-0015).
- `haeo_bridge/prevalidate.py` learns `haeo_field_missing`, `element_unconnected`,
  `dangling_connection` (now also for a bad `connection` target) and the warning
  `profile_key_unmapped`, so a profile key with no HAEO field is reported instead of
  written.
- `pricing.compiler.price_entity_id()` and `compile_plan(price_entities=...)`: grid
  price fields are filled from the price sensors we publish, overridable per site.
- `contracts.NON_ELEMENT_SUBENTRY_TYPES`, `CONNECTIONS_ARE_ELEMENT_FIELDS`,
  `PRUNE_UNKNOWN_ELEMENTS` (False): HAEO's own switchboard junction is never deleted.

### Added
- HAEO flow driver (`haeo_bridge/flows.py`) that provisions hubs, elements and
  hub options by answering HAEO's config/options/subentry flows, plus its Home
  Assistant port (`haeo_bridge/ha_port.py`) which is the only module touching `hass`
  for HAEO writes. Live verification is still gated (`HA_PORT_LIVE_VERIFIED`).
- `DriverError` with stable issue codes, apply status `partial`, and a driver
  `preflight` hook so unsupported plans block before any write.


### Added
- e04 spike, source half: HAEO v0.5.0's configuration surface read from the pinned tag and recorded in `haeo_bridge/contracts.py`.
  - Hub creation data is sectioned (`common`/`advanced`) and its horizon is a tagged value (`{"value": "5_days"}` or `{"value": ["sensor.x"]}`); `relax_infeasible` is options-only and defaults to `False`.
  - Elements and connections are config **subentries** of the hub entry, not config entries. HAEO registers 13 element types; none is `meter`, `thermostat`, or `relay`.
  - Element field values are tagged `entity`/`constant` values; a forecast point names its boundary `time`.
  - Pre-validation now separates `haeo_type_unverified` (live gate), `haeo_kind_unmapped` (modelling gap), `haeo_type_unknown`, and `horizon_preset_unsupported`.
  - New offline regression suite `tests/unit/test_haeo_contract_surface.py`; live `xfail(strict=True)` tests reshaped to fail the moment a live instance confirms the surface.
  - Evidence: SOURCES S-007..S-016, FACTS F-015..F-030, OQ-002/006/007/009 narrowed, OQ-016/OQ-017 opened, ADR-0013 proposed, spike note in `specs/archive/spikes/`.
- v1 core implementation (pure Python, no Home Assistant required at import time):
  - `profile/` — versioned site-profile schema (v1) with codes for dangling references, HAEO-name leaks, capability/unit mismatches, and cloud-primary authority violations; JSON/YAML loader and migration hook.
  - `haeo_bridge/` — plan compiler, referential-integrity pre-validation, version pin gate, and an idempotent applier that diffs hubs/elements/connections. Element type names and hub option keys stay unverified, so applying is blocked by design (C-23).
  - `pricing/` — flat, TOU block, and dynamic-series providers; generic target/incentive overlays; compiler that emits forecast-series price inputs plus a required priced battery-degradation term.
  - `adapters/` — capability descriptors (limits, rate limit, hysteresis, consent, backing, authority, fail-safe), safety pipeline, and API-backed plus Modbus-backed stub adapters behind one contract.
  - `executor.py`, `audit.py`, `ledger.py`, `telemetry.py` — plan execution with staleness and fail-safe, SHA-256 hash-chained audit log, commitments ledger that rejects over-commitment, telemetry envelope v1 with dedupe and firm/estimated separation.
  - Home Assistant glue: `config_flow.py` (config + options), `runtime.py` (repairs on validation failure), `manifest.json` with zero pip requirements, `hacs.json`.
- Tests: 288 passing (schema examples and broken variants, bridge plan/apply/idempotency/version gate, element field table and connectivity, flow driver against a fake port, pricing, adapters, executor, ledger, telemetry, boundary probes).
- CI: `ci.yml` (ruff, boundary probes, pytest, hassfest, HACS validation, manifest pin check), `release.yml` (zip + release), `haeo-contract.yml` (manual live-HAEO contract run).

### Added
- Repository bootstrap: README, AGENTS.md (model-agnostic agent instructions), CONVENTIONS.md.
- Planning spine: `specs/` (state, release plan with epics e00–e12, execution status, product vision/scope/glossary, ADR-0001 to ADR-0010, tech-architecture plans).
- Documentation: project brief, constraints C-01 to C-24, deliverable stubs D01 to D12 with required outlines and acceptance criteria, facts ledger, sources register, open questions, update log.
- Agentic harness in `.pi/`: generic agent roles, project skills, and orchestration prompts.
- Placeholder directories for the integration, site profiles, rule packs, fleet services, and tests. No implementation code.

### Changed
- Review register: RL-23 closed; RL-26 (fail-safe is not a hardware net), RL-27
  (read-back has no quality flag) and RL-28 (fixed 60 s cadence) opened.
- **Efficiency units closed (OQ-021).** HAEO's segment computes `output = input *
  efficiency` and documents the field as a 0..1 ratio, while its own default is
  `95.0`. The bridge now always writes efficiency as a ratio (`92.5` → `0.925`,
  default `0.95`) instead of passing percentages through, and the site-profile
  validator rejects values outside 1..100 with a warning below 50 (F-057..F-060,
  ADR-0018, RL-19).
- Product renamed from HA-OPENDERMS (domain `openderms`) to fleetassistant (domain `fleetassistant`) to match the repository (ADR-0011). Resolves OQ-008.
