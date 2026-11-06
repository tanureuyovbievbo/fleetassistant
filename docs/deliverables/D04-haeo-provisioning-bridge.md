# D04 — HAEO Provisioning Bridge

| Field | Value |
|-------|-------|
| ID | D04 |
| Epic | e04-haeo-bridge |
| Version | 0.0.0 (stub) |
| Status | in-progress (source-verified, live gate closed) |
| Owner role | architect (design) → engineer (code) |
| Last updated | 2026-11-05 |
| Depends on | D01, D03, C-04, C-05, C-06, C-07, C-10, C-23, ADR-0003, ADR-0004, ADR-0007, OQ-002, OQ-006, OQ-007, OQ-009 |
| Risk | **Highest-risk item. Spike first** (see `specs/epics/e04-haeo-bridge/epic.md`, story S1). |

> **Implementation:** plan compile, pre-validation, version gate, and idempotent apply exist. The HAEO v0.5.0 surface is now read from the pinned source and recorded in `haeo_bridge/contracts.py` (spike: `specs/archive/spikes/SPIKE-2026-11-05-haeo-v050-surface.md`); apply stays blocked until a live instance confirms it (ADR-0012 + `contracts.HAEO_SURFACE_LIVE_VERIFIED`).
>
> **Design correction (source-verified):** HAEO models elements and connections as config **subentries** of the hub entry, not as separate config entries. The runtime `HaeoDriver` therefore drives subentry flows; the `ElementPlan`/`ConnectionPlan` data model is unaffected. `meter`, `thermostat`, and `relay` have no HAEO element — see ADR-0013 (proposed).
>
> **Flow driver (implemented):** `haeo_bridge/flows.py` answers HAEO's config flow (hub), options flow (hub settings) and subentry flows (elements) through a narrow `FlowPort`; `haeo_bridge/ha_port.py` is the only module touching `hass`. A refused write stops the apply as `partial` with a repair issue. Rule: ADR-0014.
>
> **Still open:** the live run (accept HAEO's payloads — OQ-017), how our `_bus` junction relates to HAEO's own switchboard junction and whether pruning may ever be enabled (OQ-018), who supplies the run-window calendar a charger needs (OQ-022), HAEO's efficiency units (OQ-021), OQ-011 (shadow prices), OQ-007 (price/load sensor formats).
>
> **Resolved 2026-11-06:** a charger is a `deferrable_load` (ADR-0016, OQ-019) and battery degradation is a `policy` rule (ADR-0017, OQ-020); profile percentages are written as 0..1 ratios (F-052).
>
> **Field table (2026-11-05):** element payloads are built from `haeo_bridge/fields.py`, which records each section and key against a primary source (S-021..S-028). Topology is a per-element `connection` field pointing at a synthesised `<system>_bus` junction (ADR-0015); the bridge never prunes elements it did not create.
>
> The outline below remains the acceptance contract; code lands against it.
>
> **Stub outline.** Required structure and acceptance criteria.

## Stage 1 — Spike (throw-away)

- Goal: prove that a headless process can create one HAEO hub, two elements, and one connection on a live HA + HAEO (pinned version), through the HA config-flow API only.
- Output: `specs/archive/spikes/SPIKE-haeo-bridge.md` with the observed flow step IDs, field keys, entry/subentry model, error payloads, and timing. Every observation becomes an F-ID.
- Use the `spike-prototype` skill. Spike code is not merged into `custom_components/`.

## Stage 2 — Design (this document)

1. **Mechanism.** In-process (`hass.config_entries.flow` / subentry flow manager) or out-of-process (REST `/api/config/config_entries/flow` or WebSocket). Choose per use case: the in-integration renderer compared with headless fleet provisioning (C-17). Confirm the API shapes (C-23).
2. **Compile pipeline.** Site profile → `HaeoNetworkPlan` (hubs, elements, connections, horizon, options) → ordered flow operations → apply.
3. **Referential-integrity pre-validation.** Element name uniqueness, connection endpoints exist, every hub has the required nodes, units are valid. Produce a list of validation errors. Each error maps to an `fleetassistant` repair issue with a translation key and a fix hint.
4. **Idempotency and drift.** Ownership marker for entries we create (how, without writing HAEO storage?), diff against existing entries, create/update/delete plan, a dry-run mode, and drift detection with a repair issue.
5. **Runtime constants.** Writing to HAEO input entities (battery capacity, export limit, min SOC) without reconfiguring. Confirm entity naming (OQ-002).
6. **Horizon strategy.** Preset compared with forecast-sensor (OQ-007). Default = preset unless the price model needs a custom period layout.
7. **"Relax impossible plans".** Default ON for fleet mode, per the brief (ADR-0007). Confirm the option key (OQ-006).
8. **HAEO repair passthrough.** How HAEO's own repair issues appear in our diagnostics.
9. **Version pinning.** `SUPPORTED_HAEO_VERSIONS`, detection at setup, behavior on mismatch (repair issue, no apply), and the upgrade procedure.
10. **Contract tests.** Test harness: HA + pinned HAEO in a container. Scenarios: create, idempotent re-apply, update a constant, delete an element, invalid reference rejected before apply, version mismatch. CI matrix per supported HAEO version.
11. Open questions · Constraint compliance · Change log.

## Stage 3 — Code (engineer, TDD)

- Path: `custom_components/fleetassistant/haeo_bridge/` (versioned submodule, for example `v0_5/`).
- Tests: `tests/unit/haeo_bridge/` and `tests/contract/haeo/`.

## Acceptance criteria

- [ ] Spike notes exist and every observed identifier is an F-ID.
- [ ] No write to HAEO files or storage. Grep check in CI (C-06).
- [ ] Contract tests pass against a live, pinned HAEO.
- [ ] An invalid profile never reaches the apply step. A repair issue is raised instead.
- [ ] Re-applying the same profile produces zero operations.
- [ ] Human review gate passed (design gate, then code gate).
