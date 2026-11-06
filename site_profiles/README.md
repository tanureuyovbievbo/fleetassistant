# site_profiles

Owned by D03 / e03. Status: implemented (schema v1 + examples + invalid fixtures).

| Path | Contains |
|------|----------|
| `schema/site-profile.v1.schema.json` | Published JSON Schema (draft 2020-12). Both YAML and JSON profiles validate against it. |
| `examples/tesla_cloud_primary.yaml` | Tesla home, cloud-primary (PV + Powerwall + EV + thermostat, coarse control only) |
| `examples/solark_gateway_primary.yaml` | Sol-Ark + Shelly Pro 3EM + AC + EV, gateway-primary with hardware fail-safe |
| `examples/multi_hub_adu.json` | Main house + ADU: two systems → two HAEO hubs in one instance |
| `examples/invalid/` | Fixtures that MUST fail validation (dangling reference, unpriced battery, HAEO name leak, cloud site with local control) |

The profile is HAEO-agnostic: no HAEO field names may appear (C-06). The bridge
(`custom_components/fleetassistant/haeo_bridge/`) maps profile → HAEO network plan.

## Authority, in order

1. `custom_components/fleetassistant/profile/schema.py` — the executable validator.
2. `site_profiles/schema/site-profile.v1.schema.json` — the published contract.
3. This README.

`tests/schema/test_schema_file.py` fails when (1) and (2) disagree about versions, top-level
keys, element kinds, capabilities, or units.

## Schema rules worth knowing

- `degradation_cost.currency_per_kwh` must be **greater than zero** and must name a `source`.
  A battery without a priced degradation term is rejected, not warned (C-14).
- `consent.granted: false` is valid; controls then reject writes with `consent_missing`.
- `cloud_primary` may not declare `backing: local` or `authority: full` controls (tiered authority, C-12).
- `deployment.fail_safe` is required by policy for `gateway_primary` (C-15). The validator emits a
  **warning** when it is absent so a gateway can be staged before the contactor is wired; the
  published schema therefore does not require it.
