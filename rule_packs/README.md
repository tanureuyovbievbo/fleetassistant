# rule_packs

Owned by D05 (interface) and D10 (California pack). Status: interface implemented, **no packs shipped**.

v1 MUST work with zero rule packs installed. That is tested: `tests/unit/test_pricing.py::test_compile_works_with_zero_rule_packs` asserts it against the Tesla example.

## What a rule pack is

A rule pack is data plus a thin adapter, plugged into the generic model:

| Element | Generic seam | Module |
|---------|--------------|--------|
| Rate schedule | `RateProvider.price_at(ts)` | `custom_components/fleetassistant/pricing/providers.py` |
| Export value curve | `ExportValueCurve.currency_per_kwh` + hour multipliers | same |
| Event / incentive target | `TargetOverlay(label, start, end, price_delta_per_kwh, target_kw)` | `pricing/overlay.py` |
| Regulatory constraint | not modeled in v1 — declared, not guessed (OQ-014) | — |

## Pack layout (planned)

```text
rule_packs/<pack_id>/
  pack.json          # id, version, jurisdiction, effective_from, source URLs + fetch dates, license
  provider.py        # build_provider(profile) -> RateProvider
  README.md          # what the pack encodes and what it deliberately does not
```

## Non-negotiables

- Every number in a pack cites a primary source with URL and retrieval date. No pack ships with an
  UNVERIFIED rate, incentive amount, or capacity minimum.
- A pack never edits a site profile and never raises a site's control authority.
- Removing every pack must leave a working site (zero-pack baseline).
- Pack-level licensing is checked separately from the repository license: tariff data may carry
  redistribution terms.
