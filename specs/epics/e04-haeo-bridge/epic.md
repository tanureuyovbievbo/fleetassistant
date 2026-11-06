# e04 — HAEO provisioning bridge (D04) — HIGHEST RISK, SPIKE FIRST

| Field | Value |
|-------|-------|
| Deliverable | `docs/deliverables/D04-haeo-provisioning-bridge.md` |
| Depends on | e03 accepted (S1 spike may run early with human approval: SPIKE-PULL-AHEAD) |
| Constraints | C-04, C-05, C-06, C-07, C-10, C-11, C-23 |
| ADRs | ADR-0003, ADR-0004, ADR-0007 |
| Skill | `.pi/skills/haeo-bridge-contract` |
| Output paths | `custom_components/fleetassistant/haeo_bridge/`, `tests/contract/haeo/` |

## Goal
Code that compiles a site profile into HAEO hub, element, and connection entries through HA's config-flow API. It includes referential-integrity pre-validation with clear repair output, a horizon strategy (preset or forecast sensor), "Relax impossible plans" defaults, HAEO version pinning, and contract tests against a live HAEO.

## Stories
| ID | Story | Owner role |
|----|-------|-----------|
| S1 | **Spike** (throwaway, `spike-prototype` skill): in a disposable HA container with pinned HAEO, record every flow step, field, subentry flow, and option key for hub, element types, and connections. Answer OQ-002, OQ-005, OQ-006, OQ-007, OQ-009. Output `specs/archive/spikes/SPIKE-haeo-config-flow.md` with transcripts. | engineer, source-verifier |
| S2 | Design the HAEO network plan (intermediate representation) and the profile → plan mapping table. | architect |
| S3 | Pre-validator: element names, connection endpoints, units, required inputs → fleetassistant repair issues. | engineer |
| S4 | Applier: drives config flows (in-process first; REST/WebSocket for headless, per OQ-009). Idempotent diff: create, update, remove. | engineer |
| S5 | Version guard: `SUPPORTED_HAEO_VERSIONS` and a repair on mismatch. | engineer |
| S6 | Horizon strategy and the "Relax impossible plans" default per ADR-0007. | architect, engineer |
| S7 | Contract tests T-02..T-05 against live pinned HAEO in CI. | engineer |
| S8 | Reviews and human gate. | reviewer, claims-auditor, human |

## Acceptance criteria
- [ ] The spike report exists, and every flow step and field is recorded from observation, not from guesses.
- [ ] Only `haeo_bridge/` imports or calls HAEO. A CI boundary check proves it.
- [ ] No writes to `.storage` or to HAEO files (C-06). A CI check proves it.
- [ ] Re-apply is a no-op (T-03).
- [ ] An invalid reference produces a repair and applies nothing (T-04).
- [ ] A version mismatch produces a repair and applies nothing (T-05).
- [ ] Headless capability is documented with evidence. If it is not possible, an escalation exists in OPEN_QUESTIONS and D12.
