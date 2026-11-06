# ADR-0014 — Provision HAEO by answering its flows, never by writing its records

| Field | Value |
|-------|-------|
| Status | accepted |
| Date | 2026-11-05 |
| Source | `tests/contract/ha/test_live_ha_port.py`, `docs/verification/FACTS_LEDGER.md` F-031..F-038 |
| Constraints | C-05, C-06, C-07, C-17, C-23 |
| Relates to | ADR-0003, ADR-0004, ADR-0012, OQ-016, OQ-017, OQ-018 |
| Amended by | — |

## Context
HAEO has no YAML configuration. A hub, its elements and its connections exist only
as a config entry plus config subentries, and every field is validated by HAEO's
own flow steps [F-015, F-018, F-031]. HAEO also writes things of its own at creation time
(a `network` subentry and a switchboard junction) [F-020].

There are three ways to provision that state from our integration:

1. answer HAEO's config/options/subentry flows;
2. write the entry and subentries directly with `async_add_subentry` /
   `async_update_subentry`, bypassing the flows;
3. write HAEO's stored state ourselves.

Option 2 looks cheaper — it skips the flow round-trips — but it fabricates data
HAEO never validated, and it hard-codes field names that HAEO derives from its
schemas at flow time. Option 3 is forbidden outright (C-06).

## Decision
1. **All HAEO writes go through flows**: `config_entries.flow` for the hub,
   `config_entries.options` for hub settings, `config_entries.subentries` for
   elements and connections. Implemented as `haeo_bridge/flows.py`
   (`FlowHaeoDriver`) over a narrow `FlowPort` interface.
2. **The port, not Home Assistant, is the seam.** `ha_port.py` is the only module
   that touches `hass`; every other module stays importable and testable without
   Home Assistant, which is what lets the bridge be contract-tested offline.
3. **A form we cannot answer is a stop, not a retry.** `FlowError` names the step
   and the fields that are still missing, and becomes a repair issue. Retrying
   with invented values would defeat the point of the flow.
4. **Direct subentry CRUD is allowed for exactly one thing: deletion.** Removing
   a subentry has no flow in any HA version we target (the WebSocket
   `config_entries/subentries/update` renames only) [F-038].
5. **Partial applies are reported as partial.** A failed write stops the run with
   status `partial` and a per-item issue; the bridge never claims `applied` for
   work that did not land (ADR-0012).
6. **Unrecorded fields block instead of guessing.** Connections raise
   `BridgeUnverified` while `CONNECTION_FIELDS_UNRESOLVED` is true, so a plan with
   links is refused before any flow starts (OQ-017, OQ-018).

## Consequences
- Provisioning is as slow as HAEO's flows (a few round-trips per element), which
  is irrelevant at site scale (tens of elements) and keeps us inside HAEO's
  contract.
- Every HAEO version bump can change a flow's steps; the pin (ADR-0004) plus the
  live contract matrix is what catches it, and the failure mode is a clear
  `haeo_flow_incomplete` issue rather than corrupted state.
- Headless provisioning (C-17) has a verified REST path with the same semantics:
  `/api/config/config_entries/{flow,options/flow,subentries/flow}` [F-034..F-036].
- A hub created through a flow does not yet carry our options, so the driver
  settles hub settings immediately after creation instead of leaving a "changed"
  hub behind for the next apply.
- We remain dependent on HAEO keeping `relax_infeasible` in the options flow; if
  it moves, `update_hub` fails loudly instead of silently writing a stale record.

## Rejected
- **Direct `async_add_subentry` for creation**: skips validation, duplicates
  HAEO's schema knowledge in our code, and silently breaks when HAEO adds a
  required field.
- **Writing HAEO's stored state or `.storage` files**: forbidden by C-06 and
  breaks on every HAEO release.
- **Answering flows with best-guess defaults when a step asks for unknown
  fields**: turns a clear stop into a corrupt hub (C-23).
- **A generic "create anything" flow walker**: we drive the three flows we need
  and assert their shape; a generic walker would hide which fields we depend on.
