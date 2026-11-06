# e05 — Generic price/target model (D05)

| Field | Value |
|-------|-------|
| Deliverable | `docs/deliverables/D05-price-target-model.md` |
| Depends on | e04 accepted |
| Constraints | C-08, C-13, C-14, C-16, C-23, C-24 |
| ADR | ADR-0006 |
| Output paths | `custom_components/fleetassistant/pricing/`, `custom_components/fleetassistant/ledger/`, `rule_packs/` |

## Goal
Pluggable rate providers (flat, TOU block schedules, dynamic feeds: Nord Pool, Tibber, Octopus, EPEX, Electricity Maps) and a generic incentive/target overlay. These compile into the forecast sensors and pricing inputs that HAEO consumes, including the priced degradation term. Define the rule-pack interface and prove that v1 works with zero rule packs. Ship the commitments ledger.

## Stories
| ID | Story | Owner role |
|----|-------|-----------|
| S1 | Verify the HAEO price input shapes (forecast attribute format, pricing segments / policy pricing / Tagged Power names and units). Verify how each dynamic feed exposes prices in HA (existing integrations vs direct API). Record ToS notes. | source-verifier |
| S2 | Provider interface + flat + TOU block providers. | engineer |
| S3 | Dynamic feed providers that read existing HA integration entities where available. No new pip dependencies (C-08). | engineer |
| S4 | Target overlay + degradation term compiler → forecast-sensor outputs. | engineer |
| S5 | Rule-pack interface (rate schedules, export value curves, event targets, regulatory constraints) with provenance fields. Empty registry by default. | architect, engineer |
| S6 | Commitments ledger data structure and API (C-16). | engineer |
| S7 | Tests T-06, T-07, T-11. Reviews and human gate. | engineer, reviewer, claims-auditor, human |

## Acceptance criteria
- [ ] Zero rule packs installed → HAEO receives valid price inputs (T-06).
- [ ] The degradation term is present and never silently zero (T-07).
- [ ] No regional numbers in core code.
- [ ] The ledger rejects over-commitment (T-11).
- [ ] Every sensor and attribute name written for HAEO is verified (C-23).
