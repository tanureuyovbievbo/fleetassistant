# 2026-11-06 - First CI run, packaging fixes, PR #1 merged

Model: pi (this session). Started from a green local tree at `7576260`; ended at `a6cbfbc`
on `main`.

## Why this entry exists

Until this session, every check had passed on one Windows machine. Pushing the branch turned
"it works here" into "a clean Ubuntu runner agrees", which is a different claim.

## What the first runs found

| Run | Commit | Result |
| --- | --- | --- |
| 1 | `b292a3a` | Core pass, hassfest fail, HACS fail (repository was private) |
| 2 | `60bf8f3` | hassfest pass, HACS 3/10 checks failed |
| 3 | `f1c7f91` | HACS 2/10 checks failed (topics, licence) |
| 4 | `a6cbfbc` (merge of PR #1) | **all four jobs pass** |

Defects the remote runner caught that the local run could not:

1. `manifest.json` keys were not sorted, which hassfest rejects outright.
2. `__init__.py` defined `async_setup` without a module-level `CONFIG_SCHEMA`. hassfest
   requires one; importing it would have broken the "package imports without Home
   Assistant" rule (C-08). The function was dead code (config-entry-only, C-05), so it was
   deleted rather than satisfied.
3. `LICENSE` carried an edit-later note above the licence text. GitHub's licence detector
   reads the whole file and reported **no license**; moving the note to `NOTICE` fixed
   detection. `LICENSE` now differs from `api.github.com/licenses/apache-2.0` by whitespace
   only (verified: 169/169 normalised lines identical).
4. No brand assets. `brand/icon.png` (256x256) and `brand/logo.png` (512x256) are generated
   deterministically by a zlib PNG writer, so they can be regenerated without an image
   library or a binary blob of unknown provenance.
5. CI only ran on `push: branches: [main]` and `pull_request`, so a pushed feature branch
   produced no signal at all. It now runs on every branch push.

Two remaining HACS checks were metadata, not code: repository topics (set by the owner:
`home-assistant`, `hacs-custom`) and licence detection, which reads the **default branch** -
so it only passed once PR #1 was merged.

## State after the merge

```
main                a6cbfbc  Merge pull request #1 from tanureuyovbievbo/feat/v1-site-layer
remote tree         72fc5e87ea84 == local HEAD tree (identical content)
GET /license        Apache-2.0
CI (a6cbfbc)        Core, hassfest, HACS validation, pins - all success
local               316 passed, 7 deselected; ruff clean; probes clean; 0 broken md links
```

## Not verified

- `pytest -m live` has still never run. The three `*_LIVE_VERIFIED` booleans remain `False`
  and `.github/workflows/haeo-contract.yml` remains unexecuted.
- `release.yml` has never run (no tag), so the zip-building assertion is untested.
- The version scheme is still a recommendation, not a decision (see `next_action`).
