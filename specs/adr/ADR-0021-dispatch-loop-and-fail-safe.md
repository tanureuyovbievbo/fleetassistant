# ADR-0021 — Dispatch loop: fresh plans only, fail-safe once, on a timer

- **Status:** accepted
- **Date:** 2026-11-06
- **Deciders:** architect, reviewer
- **Related:** C-11 (tiered authority), C-12 (never over-promise), C-20 (local
  autonomy and hardware fail-safe), ADR-0018 (write physics fields explicitly),
  ADR-0020 (references and adapter glue), RL-23, RL-26..RL-28

## Context

The pieces existed but were not connected: `executor.py` could apply a plan and
fall back, `adapters/` could write a real entity, `haeo_bridge` could provision the
optimizer — and nothing turned the optimizer's output into a timestamped,
dispatched, expired, audited sequence of device writes.

Three failure modes decide the design, and all three are ordinary, not exotic:

1. **A plan that is late.** A plan computed for 15:00 is not a plan for 16:00. A
   setpoint held past its window is how a battery ends up empty at the evening
   peak — the site would have been better off with its own defaults.
2. **A plan that never arrives.** HAEO restarts, the network drops, the supervisor
   updates. Silence is not an instruction to keep doing the last thing.
3. **A plan that cannot be written.** No consent, a value outside the envelope, a
   rate limit, a dead adapter. The dispatcher must not bypass the safety pipeline
   to "make the plan work" — the pipeline is the thing that decides.

## Decision

**One dispatcher per site, on a timer, and it is the only code that calls the
executor.** `dispatch.Dispatcher.tick(source, now)`:

- **Freshness.** A plan older than `max_plan_age` (default 15 min) is discarded and
  the site fails safe, with the age in the reason (`plan is 1200s old (max 900s)`).
  The same window is passed to the executor as `valid_for`, so a plan that expires
  between ticks is refused twice, not once.
- **Grace.** Silence is tolerated for `fail_safe_after` (default 30 min) measured
  from the last successful apply. One missed cycle is normal; ten minutes of
  silence is an outage.
- **Once.** The fail-safe is written **once per outage** and then the loop reports
  `idle` with `already failed safe`. Re-writing the same fallback every minute
  would spam the device and the audit log, and would hide the fact that the
  optimizer is down.
- **Recovery.** A good plan clears the outage marker; the next outage fails safe
  again.
- **Unload.** `async_unload_entry` forces the fail-safe. Leaving devices on the
  optimizer's last instruction while we go away is exactly what a fail-safe exists
  to prevent.
- **Sources.** A plan arrives through `PlanSource`. `MappedPlanSource` reads the
  entities an installer mapped in each control's `plan_entity`; a value that is not
  a number is **skipped, never coerced to zero** — a zero export limit at noon is a
  real instruction, not a missing reading. A control with no `plan_entity`
  contributes nothing, and HAEO's own entity ids are never guessed (ADR-0012,
  OQ-022).
- **Off by default.** `dispatch_enabled` is `False`. A site with no mapped plan
  entity has nothing to dispatch, and a timer that fails safe every minute is worse
  than no timer.

Every tick that acts writes an audit record: `dispatch.apply` (plan id, age,
applied capabilities, rejected capabilities with reasons) or `dispatch.fail_safe`
(reason, setpoint count). The last ten outcomes are exposed in diagnostics.

## Rejected alternatives

| Alternative | Why not |
| --- | --- |
| Dispatch on every optimizer update, no timer | HAEO's update cadence is not a contract (OQ-006); a missed update would silently stop dispatch, and nothing would notice the silence |
| Apply whatever plan exists, however old | Holds a stale setpoint through a price change; the site loses money and blames the optimizer |
| Fail safe on the first missed plan | Ordinary solver runs and restarts would flap devices several times an hour |
| Fail safe repeatedly while the source is down | Device spam, audit noise, and a fail-safe that looks like normal operation |
| Read HAEO's plan entities by convention | Guessing entity ids is the failure ADR-0012 exists to prevent; the mapping is explicit and a missing mapping is visible |
| Let adapters write directly from the optimizer callback | Bypasses consent, clamping, rate limits, hysteresis, and the audit chain |
| Keep the last plan on unload | Leaves the house following instructions from an integration that is gone |

## Consequences

- A site can be in four states: `applied`, `rejected` (plan arrived, nothing
  written), `idle` (no plan yet, or already failed safe), `failed_safe`. Diagnostics
  show the sequence, so "why is the battery at 50%" has an answer.
- The fail-safe setpoints are the ones declared per capability in the profile. They
  are static — RL-26 records that a household-level safety net (contactor plus local
  automations) is still the gateway-primary requirement, not this loop.
- Read-back now comes from the state machine (closing RL-23), but a read value
  carries no timestamp or quality: RL-27.
- The interval is a fixed 60 s; aligning it to HAEO's plan boundaries is RL-28.
