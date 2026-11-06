# e03 — Site profile schema (D03)

| Field | Value |
|-------|-------|
| Deliverable | `docs/deliverables/D03-site-profile-schema.md` |
| Depends on | e02 accepted |
| Constraints | C-09, C-10, C-12, C-13, C-14, C-16, C-23 |
| Output paths | `site_profiles/schema/`, `site_profiles/examples/` |

## Goal
A versioned YAML/JSON schema for the site profile, with a validator and three worked examples:
1. Tesla home (cloud-primary)
2. Sol-Ark + Shelly Pro 3EM + AC + EV home (gateway-primary)
3. Multi-hub home (main house + ADU, two systems)

## Stories
| ID | Story | Owner role |
|----|-------|-----------|
| S1 | Define the field list: identity, deployment profile, systems (→ HAEO hubs), stack type, metering topology, controllable loads, control limits, consent flags, rule-pack references, degradation cost, horizon strategy. | architect |
| S2 | Write the JSON Schema `site_profiles/schema/site-profile.v1.schema.json` and a versioning and migration policy. | engineer |
| S3 | Write the three examples. Device facts (capacities, register maps, API scopes) cite sources or are UNVERIFIED. | architect, source-verifier |
| S4 | Add invalid fixtures (dangling reference, out-of-range limit, missing consent) for T-01. | engineer |
| S5 | Pure-Python validator using only an HA-core-available or vendored library (C-08). | engineer |
| S6 | Reviews and human gate. | reviewer, claims-auditor, human |

## Acceptance criteria
- [ ] The schema has `schema_version` and a documented migration rule.
- [ ] Upgrading the cloud-primary example to gateway-primary is a diff of the profile only.
- [ ] Every load and limit maps to an adapter capability (C-09).
- [ ] A battery without `degradation_cost` fails validation (C-14).
- [ ] T-01 passes.
- [ ] No HAEO field names appear in the profile. The profile is HAEO-agnostic; the bridge maps it.
