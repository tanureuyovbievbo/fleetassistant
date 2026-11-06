# ADR-0025: The switchboard is HAEO's, referenced by sentinel

- **Status:** accepted and implemented
- **Date:** 2026-11-06
- **Deciders:** owner (chose option 1 after the OQ-018 analysis)
- **Related:** ADR-0015 (superseded in part), ADR-0024 (discover before create), C-25, OQ-018

## Context

HAEO creates a `junction` titled from the translated string
`common.switchboard_node_name` ("Switchboard" in English, F-062) when a hub is
created, and every connected element requires a `connection` target at creation
(F-061, F-063). A junction has no connection field of its own, so the graph is a
star with exactly one centre.

Our compiler, which runs before any hub exists, invented a centre of its own
(`<system_id>_bus`) and pointed every element at it. That produced hubs with two
junctions, an orphaned HAEO element, and an element list that depended on a name
we own rather than the name HAEO assigned.

## Decision

The plan carries a **symbolic** connection target, `fields.HUB_SWITCHBOARD`
(`"hub_switchboard"`), for every element in `CONNECTED_KINDS`.

- `FlowHaeoDriver` resolves it from the hub's own subentries — the first `junction`
  subentry, which is the one HAEO created with the hub — and substitutes the
  real name into the element payload it sends to the subentry flow.
- No junction is created by the plan. `_bus_element` and `fields.bus_name` are
  deleted; HAEO's switchboard is the only centre.
- Zero junctions is a **blocking** error (`switchboard_missing`): HAEO always
  creates one, so its absence means the entry is not a HAEO hub.
- More than one junction is legal (a user may add a sub-panel). The first one is
  the switchboard, and the apply reports `switchboard_ambiguous` as a warning
  rather than guessing silently or refusing.
- The diff ignores the `connection` field when the plan is symbolic: the plan and
  HAEO can never agree on a name they spell differently, so comparing it would
  report a change on every apply.
- Junction subentries are marked `managed: False` in `list_elements`, so the
  no-prune diff leaves them alone without producing an `element_not_pruned`
  warning (ADR-0024 rule 2/4).

## Consequences

- `preflight.py` prints `topology connected elements -> <hub switchboard>
  (resolved at apply)` because offline there is no name to print.
- A plan is no longer self-describing: applied topology needs the read-back. That
  is honest — the name belongs to HAEO.
- Renaming the switchboard in HAEO needs no replan: the target is resolved per
  apply. Renaming an element still breaks every connection that named it, which
  HAEO itself rewrites (F-041).
- Localized installs work without a translation table, and no string is guessed.
- Residual (RL-34): a stored plan cannot show a topology change, only the applied
  read-back can.

## Rejected alternatives

- **Deterministic private name (`<system>_bus`).** Two centres, dead element,
  topology fact hidden in a string.
- **Hardcode `"Switchboard"`.** English-only; the title is a translation key.
- **Delete HAEO's switchboard and own the centre.** Requires pruning — the flag
  that would delete user elements next.
- **Ask the user to name the switchboard in the profile.** Pushes an HAEO internal
  into the site profile, which must stay stack-agnostic (C-05).
