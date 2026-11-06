# ADR-0022 — Home Assistant's own integrations are the device transport

- **Status:** proposed (accept before the first vendor adapter is written)
- **Date:** 2026-11-06
- **Deciders:** architect, source-verifier, reviewer
- **Related:** C-05 (HAEO happens only through one bridge), C-09 (one control-adapter
  interface), C-19 (licence audit), C-24 (ToS and quota math), ADR-0020 (adapter
  glue), D06, D08, OQ-023

## Context

Home Assistant Core ships integrations for many inverters, batteries, chargers and
thermostats, and HACS ships many more. The obvious question is whether the site layer
should talk to those integrations instead of writing its own vendor clients.

The question is not "can it" — `adapters/ha_services.py` already drives whatever
entities exist, whether they come from a core integration, a HACS integration, or a
hand-written Modbus YAML. The question is what we are willing to *promise* on top of
code we do not control.

Three facts decide it:

1. **Coverage is uneven in a specific way.** A core integration that only produces
   `sensor.*` gives us observation and nothing else. Control requires the integration
   to expose writable entities (`number`, `select`, `switch`, `climate`) for the
   capability we need. Which integrations do that, for which models, in which HA
   version, is **UNVERIFIED per brand** (OQ-023) — it must be checked per device, per
   release, not assumed from the brand being "supported".
2. **Authority follows the integration's `iot_class`.** A `cloud_polling`
   integration means coarse authority, vendor ToS, and a quota (C-24); the same brand
   through `local_modbus` is full authority. The deployment profile and the
   integration's `iot_class` must agree, or the site is misdescribed.
3. **A paid fleet cannot inherit an unmaintained dependency.** Core integrations are
   Apache-2.0 (no licence problem) but they are maintained by volunteers, change
   entity ids and features between releases, and some HACS ones are GPL-3. C-19 asks
   for an audit *per brand*, not per repo.

## Decision

**Use HA's integrations as the transport; never as the contract.**

- **No vendor client is written while an accepted integration exposes the capability
  we need.** We do not reimplement a Modbus map or a cloud API that HA already
  speaks, because that is duplicated maintenance with no added safety.
- **A brand enters a site through a device pack**, not through code:
  `device_packs/<brand_id>/pack.json` declares, per capability,
  - the entity the pack binds to (`entity_id` or a pattern resolved at setup),
  - the capability's real limits, unit, rate limit, hysteresis and fail-safe value,
  - `authority` (`coarse`/`full`), the integration's `iot_class`, and whether the
    integration exposes control at all,
  - `sources`: the manual page or integration doc that proves the limits, with URL
    and date (C-23), plus a licence and ToS note (C-19, C-24).
  The pack is data. The site profile references a pack per element; the adapter layer
  consumes the resolved capability descriptor. Nothing brand-specific enters
  `adapters/`.
- **Control is claimed only where the pack proves a writable entity.** A read-only
  integration still qualifies for telemetry and for the load/solar forecast inputs —
  observation is valuable on its own and must not be blocked on control.
- **`iot_class` gates the promise.** A pack whose integration is `cloud_polling` is
  `coarse` authority by construction; a `gateway_primary` site that binds such a pack
  is a validation **error**, not a warning, because the profile would otherwise claim
  dispatch authority it cannot have (C-11, C-12).
- **Version coupling becomes a contract test.** Each pack lists the integration
  versions and HA versions it was verified against; the OTA version matrix (D08)
  carries that row, and a live test asserts the entities a pack binds to still exist
  with the expected domains after an HA upgrade. A pack without a version row is
  unusable in fleet mode.
- **The safety layer never depends on the integration.** C-20's contactor and local
  automations stay in the profile and in the site's own automations; a device pack
  can never be the thing that keeps a house safe.

## Consequences

- Adapter code stays brand-free; the work per brand is a pack plus a verification
  record, which is far cheaper than a client and far easier to audit.
- A brand we cannot verify is a brand we do not claim. `pack.json` must carry
  `"verified": false` with the open item in `sources` until someone checks the entity
  domain and the limits against a primary source — the same discipline ADR-0012
  applies to HAEO.
- Some capabilities will have no core path (e.g. `set_charging_schedule` on a charger
  whose integration only sets amps). The pack omits the capability, the profile
  validation reports it, and the site still dispatches the capabilities it does have.
- HACS-only integrations inherit HACS's stability and licensing variety; packs for
  them need the licence audit recorded before a paid fleet includes them.

## Rejected alternatives

| Alternative | Why not |
| --- | --- |
| Write our own Modbus/cloud clients per brand from day one | Duplicates maintained code, and the register maps and quotas still need the same citations; we would own every bug |
| Bind entity ids directly in the site profile with no pack | Limits, rate, hysteresis, authority and provenance would be re-derived per site by hand — the drift C-18's ledger exists to prevent |
| Treat "supported by HA" as "controllable" | Many core integrations are sensor-only; claiming control is the exact over-promise C-12 forbids |
| Fork or patch a core integration to add a writable entity | Violates the no-fork posture and would put us on the hook for a whole integration |
| Require local protocol for every brand | Excludes cloud-primary self-enrolment, which is the point of the second deployment profile |

## Open questions

- **OQ-023 (new):** per brand, which core/HACS integration exposes which writable
  entity, for which models, at HA 2026.1.1 — with the doc or source that proves it.
  Until this exists for a brand, its pack stays `verified: false`.
