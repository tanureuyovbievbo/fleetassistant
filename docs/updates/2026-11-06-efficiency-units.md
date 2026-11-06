# 2026-11-06 — OQ-021 closed: efficiency is a ratio, and HAEO's default is a trap

## The finding

Three facts in HAEO v0.5.0 do not fit together:

| Fact | Source |
| --- | --- |
| `EfficiencySegment.efficient_flows` returns `flow * efficiency` — no division by 100 | `core/model/elements/segments/efficiency.py` (S-034) |
| `OutputType` documents `EFFICIENCY` as a "ratio (0-1, displayed as %)" | `core/model/const.py` (S-035) |
| The battery's own field default is `95.0` | `core/schema/elements/battery.py` (S-036) |

Under the model's maths, a battery whose efficiency was left at the default would
multiply its input energy by 95 — creating energy. The battery flow
(`flows/elements/battery.py`, S-037) applies no percent→ratio conversion, so whatever
value is stored is what the segment uses.

We cannot fix HAEO and we will not fork it. We can refuse to reproduce the trap.

## What changed

- **Efficiency is compiled as a ratio.** `BATTERY_FIELDS` now declares both efficiency
  fields as `ratio` and **required**, so the payload always carries a value
  (`92.5 %` → `0.925`, default `0.95`). Previously the value was passed through as a
  constant, which would have written `95.0`.
- **The profile validates the percentage.** `charge_efficiency_pct` and
  `discharge_efficiency_pct` must lie in 1..100, with a warning below 50 % (a value of
  `0.925` is a person who wrote the ratio, and it must not silently clamp to 1 %).
- **The trap is registered.** `RL-19` records that any element created outside this
  bridge — by hand in the UI — inherits `95.0` and should be inspected; a HAEO release
  that fixes the default changes nothing for us.
- **ADR-0018** states the general rule: write physics fields explicitly, in the unit
  the model consumes, and never inherit a default whose unit we are unsure of.

## Verification

- `python -m pytest -q` → 136 passed, 7 live tests deselected. Two new tests:
  `test_battery_efficiency_is_a_ratio_and_never_omitted` (payload carries `0.925` and a
  `0.95` default) and `test_efficiency_outside_a_percentage_is_rejected` (`0.925` in a
  percentage field is a range error).
- `python -m ruff check .` → clean; `python tools/check_boundaries.py` → clean.
- The review-register integrity test failed the moment `fields.py` referenced `RL-19`
  before the row existed — the register is load-bearing, not documentation.

## Not done

- The live run still has to prove HAEO stores what we send (`ELEMENT_FIELDS_LIVE_VERIFIED`
  stays `False`); this change removes a modelling error, not the live gate.
- The upstream default is worth reporting. No issue has been filed — that is a decision
  for a human, and it does not block us.
