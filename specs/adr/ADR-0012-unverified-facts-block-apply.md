# ADR-0012 — Unverified external facts block an apply; they are never guessed

| Field | Value |
|-------|-------|
| Status | accepted |
| Date | 2026-11-05 |
| Source | Verification discipline in the brief; C-06, C-07, C-23 |
| Constraints | C-06, C-07, C-14, C-23 |
| Relates to | OQ-002, OQ-006, OQ-007, OQ-012, ADR-0003, ADR-0004 |
| Amended by | — |

## Context
The HAEO bridge must drive HAEO's config-flow API. Element type names, hub option
keys, forecast payload shapes, and the input that carries a degradation cost are all
HAEO facts we have not read from HAEO itself at the pinned version. Guessing any of
them produces a plan that fails on a customer site, at install time, with an error
message the customer cannot act on.

## Decision
1. Unverified facts are represented in code as `None` / `False` plus an explicit flag
   (`HaeoTypeMap.verified`, `FORECAST_FORMAT_VERIFIED`, `INPUT_NAMES_VERIFIED`,
   `representation_verified`). No plausible default values.
2. `haeo_bridge/prevalidate.py` emits a blocking issue (`haeo_type_unverified`) while any
   kind maps to `None`, so `apply_plan` returns `status="blocked"` before calling the
   driver, and `runtime.py` surfaces one repair issue per blocking problem.
3. Emitted price payloads carry `format_verified: false`. A downstream consumer that
   ignores it is a defect in the consumer, not a hidden assumption in ours.
4. Each unverified fact has an owning OQ and a `xfail(strict=True)` contract test, so
   closing the OQ forces the code and the test to move together.

## Consequences
- A fresh install cannot provision HAEO. That is intentional and visible: the user sees
  "HAEO element type names are not verified for kinds: …" and the release notes say why.
- The e04 spike is the only way to unblock v1. It is scheduled first in the build order.
- Reviewers can grep for `verified` and enumerate the entire unverified surface.

## Rejected alternatives
- **Guess the names and correct later:** silent wrongness, and a config-flow call that
  creates half a network is worse than no call (C-07 requires referential pre-validation).
- **Read HAEO's source and paste what looks right without a live test:** source reading
  proves a name exists, not that the flow accepts it in that sequence with those options.
- **Fail only when HAEO rejects the call:** errors arrive after partial writes; the site is
  left in an undefined state and a repair issue cannot be precise.
