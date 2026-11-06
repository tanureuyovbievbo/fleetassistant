# ADR-0006 — Generic, pluggable pricing with rule packs and a priced degradation term

| Field | Value |
|-------|-------|
| Status | accepted |
| Date | 2026-11-05 |
| Source | Project brief |
| Constraints | C-13, C-14, C-16 |

## Context
v1 must work everywhere without regional logic. California logic is a later deliverable. Unpriced battery cycling destroys warranty life.

## Decision
Core ships flat, TOU block, and dynamic feed providers, plus a generic target overlay. Regional rates, export curves, event targets, and regulatory constraints are rule packs, and every number in a pack has provenance. A priced degradation term is a required model input when a battery exists. v1 MUST work with zero rule packs.

## Consequences
The rule-pack interface must be stable before D10. The degradation cost default needs an explicit user choice; it is never silently zero.

## Rejected alternatives
- **Hard-coding California tariffs in v1:** violates C-13.
- **Leaving degradation to the optimizer's defaults:** violates C-14.
