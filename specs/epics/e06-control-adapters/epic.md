# e06 — Control adapter layer (D06)

| Field | Value |
|-------|-------|
| Deliverable | `docs/deliverables/D06-control-adapter-layer.md` |
| Depends on | e05 accepted |
| Constraints | C-09, C-11, C-12, C-15, C-18, C-24 |
| ADR | ADR-0002 |
| Output paths | `custom_components/fleetassistant/adapters/`, `custom_components/fleetassistant/executor/`, `custom_components/fleetassistant/audit/` |

## Goal
The adapter interface, capability descriptors, safety limits, consent gating, plan-execution cadence, and local fail-safe. Plus one API-backed stub adapter and one Modbus-backed stub adapter behind the identical contract.

## Stories
| ID | Story | Owner role |
|----|-------|-----------|
| S1 | Interface and capability descriptor (min/max, unit, rate limit, hysteresis, consent, backing, authority, fail-safe value). | architect |
| S2 | Safety pipeline: clamp/reject → consent → rate limit → hysteresis → write → audit record. | engineer |
| S3 | Executor: read the HAEO plan through the bridge at a declared cadence and dispatch through adapters. Comms-loss → fail-safe. | engineer |
| S4 | API stub adapter (simulated vendor cloud, coarse tier). | engineer |
| S5 | Modbus stub adapter (simulated registers, full tier). Decide the Modbus access path without new pip deps (OQ-013). | engineer, source-verifier |
| S6 | Shared contract test suite (T-08, T-09, T-10). | engineer |
| S7 | Gateway fail-safe design: contactor wiring guidance plus local automations. Mark electrical items as needing a licensed electrician review. | architect |
| S8 | Reviews and human gate. | reviewer, claims-auditor, human |

## Acceptance criteria
- [ ] Only `adapters/` performs device writes. A CI boundary check proves it.
- [ ] Every write produces exactly one audit record, including rejected writes.
- [ ] Both stubs pass the same contract suite.
- [ ] A comms-loss test applies fail-safe values and emits a non-performance event.
- [ ] Vendor ToS risk and quota math are documented per API adapter target (C-24).
