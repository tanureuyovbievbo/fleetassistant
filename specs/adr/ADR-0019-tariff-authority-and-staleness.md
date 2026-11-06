# ADR-0019 — Two tariff sources, one explicit authority, provenance off the value

Status: accepted (2026-11-06)
Supersedes: —
Superseded by: —

## Context

A site can obtain prices two ways: the installer types a flat rate or a TOU block
schedule into the profile, or a cloud feed quotes them (a vendor API, or a HA
integration the homeowner already runs). Both are legitimate, and both can exist
at the same time — which raises four questions the code cannot dodge: which one
wins, what happens when one goes stale, who is told when they disagree, and where
the answer is recorded.

Nothing about this is HAEO-specific: HAEO reads one forecast series per price
input. The choice is entirely ours.

## Decision

1. **A per-site authority decides precedence**: `cloud`, `user`, or
   `user_unless_stale`. Defaults come from the deployment profile
   (`cloud_primary → cloud`, `gateway_primary → user`), overridable per site in the
   profile (`pricing.authority`) and per entry in the options flow, which wins over
   the profile.
2. **The non-primary source fills gaps.** A period the primary cannot price takes
   the secondary's value and is recorded as a *fallback*. A plan never has a hole
   where a price could exist.
3. **Staleness is a quality flag, not an error.** A quoted series carries
   `expires_at`; once it lapses the quote is marked `stale`. A fresh secondary beats
   a stale primary; if nothing better exists the stale value is still used, because
   planning on yesterday's price beats planning on `unknown`. Degraded periods are
   counted and reported.
4. **Disagreement is surfaced, never silently resolved.** When both sources price a
   period and differ by more than a tolerance (default 0.005 currency/kWh), a
   `Divergence` is recorded with both values and the applied one. It travels in the
   sensor's attributes and in diagnostics, and becomes a repair issue when repairs
   are next extended (RL-22).
5. **Provenance stays out of the value.** HAEO reads a number; the sensor's other
   attributes carry the source, quality, per-source counts and divergences. The
   optimizer's input never depends on who supplied it.
6. **Every tariff is published as a sensor.** One entity per price input, created
   with the object id the compiled plan references, so a plan cannot point at an
   entity nobody publishes.
7. **The cloud seat is a port, not an import.** `CloudTariffSource` takes an injected
   fetcher and counts requests, so a vendor adapter stays behind the adapter layer
   and the quota question (C-22) is answerable with a number.

## Consequences

- A site can be provisioned with only a typed tariff and later gain a cloud feed
  without re-onboarding: flip the authority, the secondary becomes primary.
- An authority of `cloud` with no cloud source configured is not an error; it emits
  a warning and uses the user schedule, so an entry never fails setup over pricing.
- Because divergences are recorded, a customer dispute has an answer: which price
  was applied, from where, and when it was fetched.
- The published sensor is now the only way HAEO learns a price, so a renamed entity
  breaks the plan silently — recorded as RL-21 rather than papered over.

## Rejected alternatives

- **Merging by taking the cheaper price.** Optimises against the vendor's error, not
  the bill.
- **Per-period "newest wins".** An entered schedule has no timestamp; recency is
  meaningless across source types and would let a cloud hiccup silently win.
- **Rejecting setup when sources disagree.** Blocks a working site over a data
  quality issue.
- **Putting provenance in the value** (e.g. a dict or a string). HAEO would fail to
  parse it, and the optimizer would lose its price.
- **Fetching inside `merge_tariffs`.** A merge is arithmetic; I/O belongs in the
  fetcher, which is why the cloud source is a separate object with a TTL and a
  counter.
