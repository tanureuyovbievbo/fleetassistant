# ADR-0023: Apache-2.0 for this repository

- **Status:** accepted
- **Date:** 2026-11-06
- **Deciders:** project owner (human, m01965)
- **Closes:** OQ-003
- **Supersedes:** none

## Context

D02 could not recommend a HACS submission without a licence. The candidates were
MIT, Apache-2.0, AGPL-3.0, and a split (open integration, closed fleet). The
repository composes two upstream works that it does not own: Home Assistant Core
and Frontend (Apache-2.0) and HAEO (MIT). Nothing is vendored, so the choice binds
only our own code — but it also sets what a contributor, an acquirer, and a
procurement reviewer can rely on.

## Decision

The repository is licensed **Apache-2.0**. `LICENSE` holds the unmodified licence
text; `NOTICE` names the product, the upstream works it composes, and the
trademark and certification disclaimers required by C-21.

Consequences that are part of the decision, not commentary:

1. **Patent grant and retaliation (§3).** Every contributor grants a patent
   licence that terminates if they sue over the work. MIT is silent on patents.
   This is the single asymmetry that matters for a product sold to utilities.
2. **Contribution clause (§5).** Contributions are inbound=outbound unless stated
   otherwise, so no CLA is needed to keep provenance clean. MIT has no such
   clause.
3. **Redistribution duties (§4).** Ship a copy of the licence, keep notices, and
   reproduce `NOTICE`. Modified upstream files must carry a "modified" marker —
   we modify none, because C-05 forbids writing into HAEO and we never fork
   Home Assistant. Our own original files carry no per-file header; adding one to
   every module would be noise without changing any obligation.
4. **No trademark rights (§6).** Reinforces C-21: "fleetassistant" is our name,
   Home Assistant and HAEO are theirs.
5. **The hosted fleet is unaffected.** Apache-2.0 has no network-service clause,
   so the fleet cloud stays closed-source. AGPL-3.0 was rejected precisely
   because it would have forced publication of the multi-tenant services.
6. **HAEO stays MIT.** MIT code may be incorporated into an Apache-2.0 work
   one-way; we do not relicense HAEO, and the MIT notice is reproduced in
   `NOTICE`. Composing HAEO over its config flows (C-05) creates no derivative
   work of HAEO.
7. **GPL-3 exposure is unchanged.** A modified HAOS appliance still triggers
   source availability for HAOS, Supervisor, and CLI (C-19); our Apache-2.0 code
   neither adds nor removes that obligation, and a GPL-3 device integration
   remains usable only if audited for a paid fleet.

## Rejected alternatives

- **MIT.** Simplest text, best match to HAEO, but no patent grant, no
  contribution clause, and no explicit trademark clause. For a product that will
  be audited by a utility, the missing patent grant is the wrong risk to carry
  silently.
- **AGPL-3.0.** Would force publication of the fleet services to any tenant
  interacting over the network. Kills the commercial model for no benefit to
  site owners, who already get the integration's source.
- **Split licence (Apache-2.0 integration, proprietary fleet in one repo).** A
  single repository cannot carry two licences without a per-directory licence
  map that HACS, GitHub, and every downstream scanner will misread. If the fleet
  later needs a different licence, it moves to its own repository; that is a
  future ADR.
- **No licence (all rights reserved).** Blocks HACS listing and outside
  contribution entirely.

## Verification

- `LICENSE` holds the canonical Apache-2.0 text (11,358 bytes;
  https://www.apache.org/licenses/LICENSE-2.0.txt, fetched 2026-11-05) preceded by a
  `#`-prefixed note that says it must be edited later and deleted (RL-33). The note
  is outside the licence, so the text stays canonical; the appendix's
  `[yyyy] [name of copyright owner]` sample is untouched on purpose.
- The copyright holder in `NOTICE` is deliberately **blank** (an underscore
  placeholder) until a legal entity is chosen — naming one now would be an
  invented fact (RL-33).
- `NOTICE` exists and names Home Assistant and HAEO with their licences.
- `pyproject.toml` declares `license = "Apache-2.0"` (PEP 639 SPDX expression)
  and `license-files = ["LICENSE", "NOTICE"]`.
- `tests/unit/test_licensing.py` fails if `LICENSE` loses the Apache header, if
  `NOTICE` stops naming HAEO's MIT licence, or if `pyproject.toml` disagrees with
  the ADR.
