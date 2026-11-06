# ADR-0013 — One HAEO element per profile kind, and what to do where HAEO has none

| Field | Value |
|-------|-------|
| Status | proposed (3 kinds need a modelling decision before v1 apply is unblocked) |
| Date | 2026-11-05 |
| Source | e04 source spike, `specs/archive/spikes/SPIKE-2026-11-05-haeo-v050-surface.md` |
| Constraints | C-04, C-05, C-23 |
| Relates to | OQ-002, OQ-017, F-015, F-016, ADR-0012 |
| Amended by | — |

## Context
A site profile declares elements by *kind* (`grid`, `solar`, `battery`, `load`,
`meter`, `ev_charger`, `thermostat`, `relay`). HAEO v0.5.0 registers 13 element
types [F-015] and none of them is named `meter`, `thermostat`, or `relay` [F-016].
Four kinds map without ambiguity; three do not.

The profile is the source of truth (C-04), so the profile's vocabulary must not
bend to HAEO's. The bridge is the only place that translates.

## Decision
1. **Direct mapping** where HAEO has an element of that meaning: `grid → grid`,
   `solar → solar`, `battery → battery`, `load → load`, `ev_charger → ev`.
2. **No substitute may be invented silently.** A kind with no recorded decision
   stays `None` in the type map, and `prevalidate` emits `haeo_kind_unmapped`,
   which blocks the apply (ADR-0012).
3. **A meter is not an element.** HAEO computes power flows on a network; metering
   in the profile describes *where we measure*, not what the optimizer balances.
   The likely resolution is that a `meter` kind contributes no element and only
   constrains which sensor feeds the grid or load element — but that changes the
   profile's semantics, so it needs its own decision record.
4. **`thermostat` and `relay` are control surfaces, not optimizer elements.**
   Both are already modelled in the control-adapter layer (D06). HAEO needs a
   *load* representing the flexible energy behind them; which HAEO type carries it
   (`load`, `deferrable_load`, `ev`) depends on how the site is paid, so it is a
   per-rule-pack decision, not a global one.
5. The mapping is data, not code: `CANDIDATE_KIND_TO_TYPE` holds it, and a rule
   pack may supply an override (see `rule_packs/README.md`).

## Consequences
- v1 v1 apply cannot complete on a profile that declares `meter`, `thermostat`, or
  `relay` until items 3 and 4 are decided and recorded. This is visible as one
  repair issue per unmapped kind, not a crash.
- The two example profiles that use those kinds (`solark_gateway_primary.yaml`,
  `multi_hub_adu.json`) exercise the gap, so the block cannot regress unnoticed.
- Adding a kind to the profile forces a mapping entry: `tests/unit/test_haeo_contract_surface.py`
  asserts the type map covers exactly `ELEMENT_KINDS`.

## Rejected alternatives
- **Map `meter` to `junction` because it sounds similar.** A junction is a
  topology node that HAEO balances; a meter is a measurement point. The names
  would agree and the model would be wrong.
- **Drop `meter`, `thermostat`, `relay` from the schema.** Loses the control
  surface the site needs and pushes the distinction into per-site YAML, which C-04
  forbids.
- **Let the bridge emit whatever HAEO type is closest at runtime.** Makes the
  optimiser's behaviour depend on an install-time coincidence, and cannot be
  review-tested.
