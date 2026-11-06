# fleet — placeholder (v2)

Owned by D08 (fleet services) and D09 (aggregation). Nothing here runs inside Home Assistant.

Fixed requirements: tenant per container (C-01), WireGuard client-only (C-17), per-site identity and certificates, no shared admin tokens, per-tenant secret isolation, encryption at rest, append-only audit (C-18), license audit before any integration enters the paid fleet (C-19).

## Implemented

- `allocation.py` — the aggregation math: `Allocator` (merit order by marginal
  cost, then site id; availability, opt-out, comfort reserve, battery-life cap and
  share cap; a short fleet reports its shortfall instead of scaling up),
  `simultaneity_factor` / `simultaneous_capacity` (window-based coincidence, an
  upper bound — RL-32), `dispatch_delta` (only changes above hysteresis, explicit
  zero for a site that stops) and `feedback_trim` (bounded fraction of the
  measured error, deadbanded).

Not implemented: site marginal cost intake from HAEO shadow prices, settlement and
payout, per-tenant identity, and the orchestration described above.
