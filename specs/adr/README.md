# Architecture Decision Records

Format: Context · Decision · Consequences · Rejected alternatives. New ADRs take the next number. To supersede an ADR, add a new ADR and set the old one's status to `superseded by ADR-NNNN`. Never delete an ADR.

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-0001](ADR-0001-tenant-per-container.md) | Tenant per container; never fork HA Core | accepted |
| [ADR-0002](ADR-0002-single-control-adapter-interface.md) | Single control-adapter interface | accepted |
| [ADR-0003](ADR-0003-haeo-via-config-flow-bridge.md) | HAEO only through the config-flow API, through one versioned bridge | accepted |
| [ADR-0004](ADR-0004-pin-haeo-version.md) | Pin HAEO version (working target v0.5.0) | accepted |
| [ADR-0005](ADR-0005-site-profile-source-of-truth.md) | Site profile as code is the source of truth | accepted |
| [ADR-0006](ADR-0006-generic-pricing-rule-packs.md) | Generic pricing, rule packs, priced degradation | accepted |
| [ADR-0007](ADR-0007-relax-impossible-plans-and-prevalidation.md) | "Relax impossible plans" ON in fleet mode; pre-validation | accepted |
| [ADR-0008](ADR-0008-integration-not-addon.md) | HACS integration, not an HAOS add-on | accepted |
| [ADR-0009](ADR-0009-provisioning-security.md) | Provisioning and connectivity security baseline | accepted |
| [ADR-0010](ADR-0010-model-agnostic-agentic-workflow.md) | Model-agnostic agentic workflow | accepted |
| [ADR-0011](ADR-0011-product-rename-fleetassistant.md) | Product renamed to fleetassistant | accepted |
| [ADR-0012](ADR-0012-unverified-facts-block-apply.md) | Unverified external facts block an apply | accepted |
| [ADR-0013](ADR-0013-element-per-kind-mapping.md) | One HAEO element per profile kind; unmapped kinds block | proposed |
| [ADR-0014](ADR-0014-flow-driven-provisioning.md) | Provision HAEO by answering its flows, never by writing its records | accepted |

Next ADRs expected: license decision (D02, OQ-003), per-element field map (D04, OQ-017), Modbus access path (D06, OQ-013), fleet stack (D08).
| [ADR-0015](ADR-0015-topology-as-connection-fields.md) | Topology is a per-element `connection` field; the bridge never prunes | accepted | 2026-11-05 |
