# D05 — Generic Price / Target Model

| Field | Value |
|-------|-------|
| ID | D05 |
| Epic | e05-price-target-model |
| Version | 0.0.0 (stub) |
| Status | implemented (representation unverified) |
| Owner role | architect (design) → engineer (code) |
| Last updated | 2026-11-05 |
| Depends on | D03, D04, C-04, C-13, C-14, C-16, ADR-0006, OQ-007, OQ-011, OQ-012 |

> **Implementation:** flat/TOU/dynamic providers, overlays, compiler, priced degradation term; HAEO input representation unverified (OQ-012).
>
> The outline below remains the acceptance contract; code lands against it.
>
> **Stub outline.** Required structure and acceptance criteria.

## Required outline

1. **Domain model.** `PriceSeries` (import, export), `TargetOverlay` (incentive or penalty over a time window, per node), `DegradationCost`, `ForecastPoint(time, value, unit)`.
2. **Rate provider interface.** Methods, refresh cadence, and failure behavior (keep the last good value with a staleness flag). Built-in providers:
   - `flat`
   - `tou_block` (weekday/weekend/season blocks, generic; no regional constants)
   - Dynamic feeds via existing HA integrations: Nord Pool, Tibber, Octopus, EPEX, Electricity Maps. For each feed: the source HA integration, the entity/attribute shape (F-ID or UNVERIFIED), and the license and ToS of the data (C-24).
3. **Target/incentive overlay.** A generic abstraction for events, targets, and incentives. It composes with prices. It is checked against the commitments ledger (C-16).
4. **Degradation term (C-14).** Units (currency/kWh throughput), defaults policy, and how it enters HAEO (native input or a price adjustment; OQ-012). Show that it is never silently zero.
5. **Compilation to HAEO inputs.** Forecast-sensor entities (names, attributes, units — all F-ID-backed), pricing segments, policy pricing, and Tagged Power mapping (OQ-011). Align with the horizon (D04 §6).
6. **Rule-pack interface.** Package layout under `rule_packs/<id>/`, manifest (id, version, region, effective dates, sources[]), extension points (rate schedules, export value curves, event targets, regulatory constraints), validation, sandboxing (data-only and declarative preferred over code), and the provenance requirement: every number in a rule pack carries an S-ID.
7. **Zero-rule-pack proof.** A test scenario where an empty registry still produces valid HAEO inputs from the flat, TOU, or dynamic providers.
8. Open questions · Constraint compliance · Change log.

## Acceptance criteria

- [ ] There are no California constants or region-specific logic in core (C-13).
- [ ] The zero-rule-pack test is defined (and passes once implemented).
- [ ] The degradation term is present end to end (C-14).
- [ ] Every HAEO input name and unit is F-ID-backed (C-23).
- [ ] Human review gate passed.
