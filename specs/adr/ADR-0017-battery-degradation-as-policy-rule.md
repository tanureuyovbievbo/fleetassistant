# ADR-0017 — Battery degradation is a priced `policy` rule

Status: accepted (2026-11-06)
Supersedes: the "degradation is a profile-only key" note in ADR-0013
Superseded by: —

## Context

C-14 requires a priced battery-degradation term: cycling a battery has a cost, and
an optimizer that does not pay it will cycle for pennies. HAEO has no degradation
field. Its battery element offers three nearby things:

| Field | What it actually is |
| --- | --- |
| `advanced.charge_limit_cost` | a penalty for approaching the charge/discharge limit (default 100.0) |
| `pricing.salvage_value` | residual value of stored energy at the horizon end |
| surfaced hints `charge_cost` / `discharge_cost` | prices applied to the battery's own flows |

`core/adapters/policy_compilation.py` (S-031) describes a general mechanism: a
policy rule names `sources` and `destinations` and a `price` in currency per kWh;
the compiler places that price on the *sink-side minimum cut* of the flow from the
sources to the destinations, once per unit of flow. Its own docstring records the
degenerate case we need:

> wildcard target with a single-outbound source: cut collapses to the source's
> outbound edges (the natural discharge / production gate)

So `{source: [battery], target: ["*"], price: X}` charges every kWh that leaves the
battery exactly X (F-056), and `{source: ["*"], target: [battery], price: Y}` would
charge every kWh that enters it.

## Decision

1. The plan compiler synthesises one `policy` element per battery that declares a
   `degradation_cost`, named `<battery>_degradation`, with a single enabled rule
   `{source: [<battery>], target: ["*"], price: <currency_per_kwh>}`.
2. The term stays a **profile input** (`element.degradation_cost`), never a rule-pack
   constant: it is a model input, not a regional rule (C-14).
3. A battery with no `degradation_cost` remains a blocking error
   (`degradation_missing`); the policy element does not replace that check — it is
   what makes the check meaningful.
4. Policy elements are created through the same subentry flow as any element; they
   have no connection target and carry `rules` next to `name`, not inside a section.
5. Charging-side wear is **not** priced in v1: it is a second rule
   (`*` → battery) that changes dispatch materially, and no source yet says at what
   rate. Recorded as open work in OQ-020 rather than guessed.

## Consequences

- Degradation cost now influences the optimizer's dispatch, not just our ledger.
- Every profile with a battery produces one extra HAEO subentry, so an element count
  in the plan is one lower than the subentry count. Diagnostics state both.
- Because the rule's price is a constant in the payload, changing a degradation cost
  is an element update, not a re-optimisation of the hub.
- A rule naming an element that does not exist blocks the apply
  (`dangling_connection`), so a renamed battery cannot leave a pricing rule pointing
  at nothing.

## Rejected alternatives

- **`charge_limit_cost`.** A limit penalty, not a throughput cost; using it would
  price proximity to the SOC bound instead of wear.
- **`salvage_value`.** Prices stored energy at the horizon end, which is a terminal
  condition, not cycling wear.
- **Folding degradation into the import price.** Contaminates the price signal that
  also feeds reporting and settlement; a battery-only rule keeps the two separate.
- **Leaving it as a profile-only key.** Then the optimizer never pays it, which is
  the failure C-14 exists to prevent.
