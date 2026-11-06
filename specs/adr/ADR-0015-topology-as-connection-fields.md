# ADR-0015 — Topology is a per-element `connection` field; the bridge never prunes

Status: accepted (2026-11-05)
Supersedes: —
Superseded by: —

## Context

The site profile models a system as a set of elements plus explicit `connections`
(`[[source, target], ...]`). The HAEO bridge originally treated topology as a
separate HAEO object: a `connection` subentry created through its own flow, after
the element subentries.

Reading HAEO v0.5.0's element schemas at the pinned tag disproved that model:

- `core/schema/sections/common.py` defines `CommonConfig {name, connection?}` and
  `ConnectedCommonConfig {name, connection}`, where `connection` holds a single
  `{"type": "connection_target", "value": "<element name>"}` (F-041).
- No `connection` element type or subentry exists in
  `core/schema/elements/element_type.py`; `ElementType.CONNECTION` is a *model*
  concept produced by the optimizer, not a configured element (F-015, F-041).
- `flows/hub.py` creates a `network` subentry **and** a `switchboard` **junction**
  subentry when the hub is created, so a hub already owns elements we did not
  create (F-049).

Two failures follow from treating connections as entries: the plan invents an
object HAEO does not have, and a diff that deletes "elements not in the plan"
would delete HAEO's own switchboard junction on the first apply.

## Decision

1. Topology is rendered **into element payloads**: every connected element
   (`grid`, `battery`, `load`, `solar`, `ev_charger`) carries
   `connection = connection_target(<bus name>)`, and the plan synthesises one
   `junction` element per system as the bus (`<system_id>_bus`).
2. Profile `connections` are validated for referential integrity and must name an
   element of the same system; they are no longer applied as separate objects.
3. The driver has **no** connection read/write methods. `HaeoDriver` exposes only
   hub and element operations.
4. Element diffs are computed against what HAEO reports (`{"type", "data"}` with
   `name`/`element_type` excluded), because the subentry already stores those two
   fields in its title/type.
5. The bridge **does not prune** elements it did not create
   (`contracts.PRUNE_UNKNOWN_ELEMENTS = False`). An element present in HAEO but
   absent from the plan yields a warning issue `element_not_pruned`, never a
   `remove_subentry` call.

## Consequences

- Applying a plan is now possible without any unrecorded field: every payload key
  comes from a `FieldSpec` with a citation (F-040..F-048).
- Renaming a bus renames every element's `connection` target, because HAEO rewrites
  targets on rename — a plan rename is therefore a coordinated update, not a
  delete/create cycle.
- Pruning being off means a renamed or deleted profile element stays in HAEO until
  an operator removes it. Ownership tracking (recording created subentry ids in the
  config entry) is the follow-up that will allow safe pruning (OQ-018).
- Junction elements carry no fields, so a `profile_key_unmapped` warning — not an
  error — is the right output for a profile key HAEO has no field for.

## Rejected alternatives

- **Connection subentries.** Wrong model: HAEO has no such element type, and the
  flow would fail on a missing handler.
- **Deleting unknown elements to enforce convergence.** Deletes HAEO's switchboard
  junction and anything an operator added by hand; unrecoverable from the profile.
- **Pruning only names matching a pattern.** Guessing ownership from a naming
  convention hides the real gap (no ownership record) and would still delete a
  hand-created element that happens to match.
- **Keeping `connections` in `NetworkPlan` and trusting a future HAEO version to
  grow connection entries.** D04 must run against v0.5.0; a plan that models a
  future feature cannot be applied today.
