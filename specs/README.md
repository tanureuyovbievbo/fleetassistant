# specs/ — planning spine

These files hold machine-readable plan state. Agents read and update them. Humans approve the changes.

| Path | Purpose |
|------|---------|
| `state.yaml` | Session state: active epic, next action, decisions. **Read first.** |
| `release-plan.yaml` | Ordered epics (one per deliverable) with gates and dependencies. |
| `execution-status.yaml` | Status per epic and per story. |
| `planning-status.yaml` | Discover-phase checklist. |
| `product/` | `VISION_LATEST.yaml`, `SCOPE_LATEST.yaml`, `GLOSSARY_LATEST.yaml`, `snapshots/`. |
| `tech-architecture/` | `tech-stack.md`, `SECURITY_PLAN_LATEST.md`, `TEST_PLAN_LATEST.md`. |
| `adr/` | Architecture decision records (`ADR-NNNN-*.md`). |
| `epics/` | One capsule per epic: `eNN-slug/epic.md` (+ `*-tasks.yaml` added by `plan-work`). `archive/` holds finished epics. |
| `archive/spikes/` | Spike learning notes (throw-away code is not kept). |
| `bugs/registry.yaml` | Defect registry. |
| `verifications/` | Verification and UAT reports per epic. |

Status vocabulary (epics and stories): `not-started` · `in-progress` · `in-review` · `blocked` · `accepted` · `superseded`.
