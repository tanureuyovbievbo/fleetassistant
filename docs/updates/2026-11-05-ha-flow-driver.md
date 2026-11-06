# 2026-11-05 — HA flow driver (bridge can now write, live gate still shut)

## What changed
- `haeo_bridge/flows.py`: `FlowHaeoDriver` implements the `HaeoDriver` protocol by
  answering HAEO's flows — config flow for hubs, options flow for hub settings,
  subentry flows for elements. No direct subentry creation, no HAEO storage writes.
- `haeo_bridge/ha_port.py`: `HomeAssistantFlowPort` is the only module that touches
  `hass` (`config_entries.flow`, `.options`, `.subentries`). `HA_PORT_LIVE_VERIFIED`
  stays `False` until the live contract test passes.
- `haeo_bridge/apply.py`: `DriverError`, status `partial`, a driver `preflight` hook,
  and one code path for dry-run and real runs. A failed write stops the apply and
  becomes a repair issue instead of a traceback.
- `haeo_bridge/contracts.py`: `NON_ELEMENT_SUBENTRY_TYPES`,
  `CONNECTION_SUBENTRY_TYPE`, `CONNECTION_FIELDS_UNRESOLVED`.
- `haeo_bridge/__init__.py` exports the flow layer (not `ha_port`, which imports HA).

## Why
OQ-016 asked how an integration can create HAEO subentries. The answer is: it starts
a subentry flow. The verified endpoint shapes are now in F-031..F-038, and the
provisioning rule is recorded as ADR-0014.

## Verification
- 122 tests pass offline; `ruff check .` clean; `python tools/check_boundaries.py`
  reports clean (no HA import outside the allowed modules, no `.storage`, no HAEO
  call outside the bridge).
- 8 new unit tests drive a fake flow port: hub creation through the sectioned
  creation data, idempotent re-apply, options-flow update, error form → repair issue,
  missing-field form → named `FlowError`, connections blocked before any flow starts,
  unknown element type refused by preflight, element removal through the subentry
  manager.
- Live gates still closed: OQ-017 (per-element fields), OQ-018 (HAEO's own
  switchboard subentry and connection field names), and the live port test.

## Not done
- The runtime does not call the flow driver yet: setup compiles and validates a plan
  but does not apply it, because OQ-017/OQ-018 would block every real profile.
- Meter/thermostat/relay mapping is still an open decision (ADR-0013, proposed).
