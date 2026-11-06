---
name: haeo-bridge-contract
description: Rules and procedure for anything that touches HAEO from fleetassistant — the config-flow spike, the haeo_bridge module, version pinning, pre-validation, and contract tests against a live pinned HAEO. Use for D04/e04 work, any HAEO version bump, and any bug involving HAEO hubs, elements, connections, horizon, or price inputs.
---

# haeo-bridge-contract

## Invariants
- HAEO is configured **only** through HA's config-flow API: in-process flow manager, or REST/WebSocket for headless use (C-06).
- Only `custom_components/fleetassistant/haeo_bridge/` knows HAEO step IDs, field keys, element types, or entity names (C-07).
- The bridge declares `SUPPORTED_HAEO_VERSIONS`. Unknown version → repair issue and no apply (ADR-0004).
- Pre-validate before any apply. Invalid → fleetassistant repair issue and no partial apply (ADR-0007).
- Apply is idempotent: profile → network plan → diff against existing entries → create, update, or remove.
- One HAEO hub per profile `system`. Never two optimizers for one system (C-11).

## Spike procedure (e04 S1)
1. Start a disposable HA container at the minimum supported HA version. Install HAEO at the pinned tag (`v0.5.0` working target, F-011). Record the exact versions.
2. Through the config-flow REST/WebSocket API, start each flow (hub, every element type, connection). Record the raw JSON for each step: `flow_id`, `step_id`, `data_schema`, `errors`, and the result type. Also record subentry flows if HAEO uses them.
3. After creating entries, record the entities HAEO creates (input entities per field, outputs, shadow prices) with exact entity IDs, attributes, and units.
4. Test a forecast-sensor horizon and a preset horizon. Record the attribute format HAEO accepts.
5. Find the "Relax impossible plans" option key and the repair issue IDs.
6. Write `specs/archive/spikes/SPIKE-haeo-config-flow.md` with the transcripts. The source-verifier cross-checks the findings against the source at the pinned tag and adds F-IDs.

## Contract tests (`tests/contract/haeo/`)
- Run against a real HA + HAEO container at each version in `SUPPORTED_HAEO_VERSIONS`.
- Required: create network (T-02), idempotent re-apply (T-03), invalid reference blocked (T-04), version mismatch blocked (T-05), field-schema snapshot (fails when HAEO changes a flow schema).
- Snapshot files live in `tests/contract/haeo/snapshots/<haeo_version>/`.

## Version bump checklist
- [ ] New tag fetched. Release notes recorded as an S-ID.
- [ ] Spike step 2 re-run. Snapshot diff reviewed.
- [ ] Bridge mapping updated for the new version only. Old versions are kept until deprecated.
- [ ] Contract tests green on the old and new versions.
- [ ] OTA version matrix updated (D08).
