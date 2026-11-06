# D09 — Aggregation Services

| Field | Value |
|-------|-------|
| ID | D09 |
| Epic | e09-aggregation-services |
| Version | 0.0.0 (stub) |
| Status | not-started |
| Owner role | architect |
| Last updated | 2026-11-05 |
| Depends on | D05, D06, D07, D08, C-11, C-12, C-16, C-21, OQ-011 |

> **Stub.** Required outline and acceptance criteria only.

## Required outline

1. **Capability ledger.** Per-site advertised capabilities with their authority tier, availability windows, and consent. It is the fleet-level view of the per-site commitments ledger (C-16).
2. **Qualified-capacity model.** Firm compared with best-effort capacity (C-12: cloud-only kW is never firm). Simultaneity math: diversity factor, coincident availability, SOC-dependent capacity, and confidence intervals. Show the formulas.
3. **Allocation solver.**
   - Input: HAEO shadow prices per site as site marginal cost (OQ-011 for names and units). Do NOT re-optimize site internals (C-11).
   - Fleet LP: minimize the cost to meet the aggregate target, subject to availability, opt-outs, comfort floors, battery-life caps (degradation, C-14), and fairness (define the metric).
   - Output: per-site target overlays delivered through the D05 overlay mechanism.
   - Solver choice: must satisfy the fleet-side dependency rules (fleet services run outside HA).
4. **Feedback trim loop.** Telemetry-driven re-allocation during an event, cadence, and stability.
5. **Settlement and payout pipeline.** Reconciled performance record (D07) → claim → partner/utility settlement → customer payout. Audit trail. Dispute handling.
6. **Honesty rules.** No firm offer exceeds qualified firm capacity. Non-performance is reported (C-12, C-21).
7. Open questions · Constraint compliance · Change log.

## Acceptance criteria

- [ ] The allocation uses shadow prices and does not run a second site optimizer.
- [ ] Simultaneity math is written out with worked numbers marked illustrative.
- [ ] The settlement pipeline is traceable from payout back to the telemetry records.
- [ ] Human review gate passed.
