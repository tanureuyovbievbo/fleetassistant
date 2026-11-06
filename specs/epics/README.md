# Epic capsules

Each epic directory `eNN-slug/` holds:

| File | Purpose |
|------|---------|
| `epic.md` | Goal, deliverable link, stories, acceptance criteria, gate checklist |
| `eNN-tasks.yaml` | Runnable task list (id, story, owner role, inputs, outputs, verify command, status) |
| `notes/` | Optional working notes. Not authoritative. |

Rules:
- An epic starts only after the previous epic's gate is accepted by a human (see `specs/release-plan.yaml`).
- Status is tracked in `specs/execution-status.yaml`, not in this file.
- Accepted epics move to `archive/` only after the release that contains them ships.
- Task `owner` is a **role** (`architect`, `source-verifier`, `engineer`, `reviewer`, `claims-auditor`, `human`), never a model.

| Epic | Deliverable | Kind |
|------|-------------|------|
| [e00-bootstrap](e00-bootstrap/epic.md) | — | done |
| [e01-architecture-spec](e01-architecture-spec/epic.md) | D01 | design |
| [e02-hacs-packaging](e02-hacs-packaging/epic.md) | D02 | design + scaffold |
| [e03-site-profile-schema](e03-site-profile-schema/epic.md) | D03 | schema |
| [e04-haeo-bridge](e04-haeo-bridge/epic.md) | D04 | spike + code (highest risk) |
| [e05-price-target-model](e05-price-target-model/epic.md) | D05 | code |
| [e06-control-adapters](e06-control-adapters/epic.md) | D06 | code |
| [e07-telemetry-schema](e07-telemetry-schema/epic.md) | D07 | schema + code |
| [e08-fleet-services](e08-fleet-services/epic.md) | D08 | spec + scaffold |
| [e09-aggregation-services](e09-aggregation-services/epic.md) | D09 | spec |
| [e10-rule-pack-california](e10-rule-pack-california/epic.md) | D10 | research + spec |
| [e11-phased-plan](e11-phased-plan/epic.md) | D11 | plan |
| [e12-risk-register](e12-risk-register/epic.md) | D12 | register |
