# ADR-0018 — Write physics fields explicitly; never inherit a HAEO default

Status: accepted (2026-11-06)
Supersedes: —
Superseded by: —

## Context

Reading HAEO v0.5.0 for OQ-021 produced an uncomfortable pair of facts:

- the efficiency segment computes `output = input * efficiency` (F-058), and
  `OutputType.EFFICIENCY` is documented as a "ratio (0-1, displayed as %)" (F-057);
- the field's own declared default is `95.0` (F-059).

Those cannot both be right. If a battery is created with its efficiency untouched, the
model would multiply energy by 95 — creating energy out of nothing. Whatever upstream
concludes, we cannot ship a payload that leaves the question open.

## Decision

1. Every field whose units we are certain of is **written explicitly** by the plan
   compiler in the unit HAEO's model consumes — ratios for `*_percentage` and
   `*efficiency`, kW for power, currency/kWh for prices.
2. A field is omitted only when omitting it is provably harmless: HAEO's schema marks
   it optional *and* its default is in the same unit we would write.
3. Where a HAEO default disagrees with HAEO's own model maths, we treat the default as
   a bug in HAEO, write our own value, and record the discrepancy (RL-19) rather than
   copying it.
4. The site profile speaks percent for human-facing quantities (`min_soc_pct`,
   `charge_efficiency_pct`); the bridge converts. Profiles are read by installers;
   payloads are read by a solver.
5. A profile value outside its physical range is a validation error, not a clamp: a
   silent clamp turns a data-entry mistake into a modelled battery.

## Consequences

- Payloads are longer and diffs are noisier: a plan carries 0.95 where an "empty"
  element would carry nothing. That is the price of not guessing.
- We cannot rely on HAEO defaults improving our behaviour; a HAEO release that fixes
  the 95.0 default changes nothing for us, and one that changes units breaks our
  payloads loudly (a value of 0.95 read as a percentage is 0.95 %, visible immediately).
- Upgrading HAEO now requires re-reading these fields, which is exactly the version
  pin discipline C-09 already demands.

## Rejected alternatives

- **Omit efficiency and let HAEO default.** Ships a plan that creates energy.
- **Write `95.0` to match HAEO's default.** Matches a default we believe is wrong, and
  makes our payload look correct while the model is nonsense.
- **Write both a percentage and a ratio key.** HAEO has one field; inventing a second
  would be rejected by its flows.
- **Clamp out-of-range values.** Hides the mistake; a 0.925 % efficiency would silently
  become 50 %.
