# fleetassistant

> An open distributed energy management platform. It ships first as a Home Assistant custom integration, distributed through HACS. It is built on HAEO (Home Assistant Energy Optimizer), which is the site-level optimizer.
>
> *Powered by Home Assistant · built on HAEO.* fleetassistant is not affiliated with, endorsed by, or certified by Nabu Casa, the Home Assistant project, the HAEO project, the OpenADR Alliance, or any utility, ISO, or certification body. The name describes a product, not a compliance status. "DERMS" in our docs describes an open architecture only.

**Status:** Early v1 implementation. The pure-Python core of the site layer exists and is tested without Home Assistant: site-profile schema and loader, HAEO bridge (plan → pre-validate → idempotent apply, plus a flow driver that provisions HAEO through HAEO's own config/options/subentry flows), generic price/target model with a priced degradation term, control-adapter contract with a safety pipeline, hash-chained audit log, commitments ledger, plan executor with fail-safe, and telemetry envelope v1. Apply against a real HAEO instance stays blocked until the pinned surface is confirmed live (ADR-0012). The per-element field table is now read from the pinned source (grid/battery/load/solar/`ev`/`policy`, plus `connection` as a per-element field — ADR-0015) and the bridge writes only recorded keys, so what remains is a live run: confirm HAEO accepts those payloads (OQ-017), settle how our bus relates to HAEO's own switchboard junction (OQ-018). The write path itself is wired: the `apply_haeo_plan` option (default off) provisions HAEO from the compiled plan in an executor thread and reports what happened through diagnostics, an audit record and a repair issue. Deliberate gaps are registered in [docs/verification/REVIEW_LATER.md](docs/verification/REVIEW_LATER.md) and referenced from the code as `RL-xx`. Chargers compile to a deferrable load and each battery's degradation cost compiles to a `policy` rule (ADR-0016, ADR-0017); efficiency is written as a ratio (OQ-021 closed, ADR-0018). Prices are now published: one sensor per price input, merging a user schedule with a cloud quote under an explicit per-site authority and staleness rule (ADR-0019). Controls bind to real entities (switch/number/climate through an injected service caller), every entity reference is checked at setup with a repair per gap, and a dispatch loop applies fresh plans through the safety pipeline and fails safe once when the optimizer goes quiet (ADR-0020, ADR-0021). Telemetry now has a producer as well as a schema — one envelope per quality/source/authority, so a commanded setpoint is never reported as a measurement — though nothing transports it yet (RL-30). Brand support is a data question: a device pack binds each capability to the entity an existing HA integration exposes, and a cloud integration cannot claim full authority (ADR-0022, OQ-023). The dispatch path consults the commitments ledger and refuses a double-booked capability before touching a device (C-16). Fleet allocation math (merit order, simultaneity, feedback trim) lives in `fleet/allocation.py`, `tools/preflight.py` reports offline what a live install would need, and the supported HA × HAEO × integration combination plus its rollback are pinned in [docs/ops/VERSION_MATRIX.md](docs/ops/VERSION_MATRIX.md) — currently UNVERIFIED pending a live run. Everything left on the roadmap needs either a human decision (licence OQ-003, meter/thermostat/relay carriers OQ-019) or a live instance (the `pytest -m live` gate).

The HAEO v0.5.0 configuration surface has been read from the pinned source and recorded (`custom_components/fleetassistant/haeo_bridge/contracts.py`), so the bridge writes HAEO's real shapes — sectioned hub data, tagged horizon, config subentries for elements. Applying a profile is still **blocked on purpose** until a live instance confirms that surface; three profile kinds (`meter`, `thermostat`, `relay`) still need a modelling decision (ADR-0013, proposed).

**Two gates are deliberately closed:** HAEO element type names (OQ-002) and hub option keys (OQ-006) are unverified, so the bridge refuses to apply a plan — see [docs/verification/OPEN_QUESTIONS.md](docs/verification/OPEN_QUESTIONS.md). Resolving them is the e04 spike, and it is the next honest step.

```bash
python -m pip install pytest pyyaml ruff
python -m pytest -q                 # core tests, no Home Assistant required
python tools/check_boundaries.py    # constraint probes C-06 / C-08 / C-09
```

## What it is

| Version | Form | Summary |
|---------|------|---------|
| **v1** | HACS custom integration `custom_components/fleetassistant/` | Declarative site profile, automatic HAEO network provisioning (config-flow API only), generic price/target model, control-adapter layer, telemetry publisher. It composes HAEO. It does not fork or patch HAEO. |
| **v2** | Fleet services | Multi-tenant hosting (tenant per container), headless provisioning, OTA, observability, dispatch, settlement, consumer app. These services consume v1 sites. |

There are two deployment profiles. Both run the same product:

- **Cloud-primary:** HA is hosted per tenant in our cloud. It reaches the home through vendor cloud APIs only. Control is coarse and best-effort.
- **Gateway-primary:** HAOS runs on a wired mini PC on site. It uses open-protocol device stacks and has a hardware fail-safe. Control authority is full.

## Repository map

| Path | Purpose |
|------|---------|
| [`AGENTS.md`](AGENTS.md) | Canonical instructions for **any** AI coding agent (model-agnostic). Read this first. |
| [`CONVENTIONS.md`](CONVENTIONS.md) | Engineering, documentation, and verification rules. |
| [`docs/`](docs/README.md) | Deliverable documents, constraints, verification ledgers, and the update log. |
| [`specs/`](specs/README.md) | Machine-readable plan state: release plan, epics, ADRs, and session state. |
| [`.pi/`](.pi/README.md) | Agentic workflow: generic agent roles, project skills, and orchestration prompts. |
| `custom_components/fleetassistant/` | v1 integration: profile schema, HAEO bridge, pricing, adapters, executor, audit, ledger, telemetry. |
| `site_profiles/` | Versioned site-profile schema plus three worked examples (Tesla cloud-primary, Sol-Ark gateway-primary, multi-hub ADU). |
| `fleet/` | v2 fleet and aggregation services (specs complete, no code yet; deliverables D08 and D09). |
| `rule_packs/` | Pluggable rate/target/regulatory rule packs (placeholder; interface in D05, California in D10). |
| `tests/` | Unit and schema tests (no HA needed), adapter contract suite, live HAEO contract suite (manual workflow). |

## How work happens

1. Each deliverable (D01 to D12) is an epic in [`specs/release-plan.yaml`](specs/release-plan.yaml), with a capsule in `specs/epics/`.
2. An agent runs `/deliver <Dnn>` ([`.pi/prompts/deliver.md`](.pi/prompts/deliver.md)). The chain is: draft (architect) → verify claims (source-verifier) → constraint and quality review (reviewer, claims-auditor) → **stop for human review**.
3. When the human approves, the epic is marked `accepted`. Then the next deliverable starts.
4. Every session appends an entry to [`docs/updates/`](docs/updates/README.md) and updates [`specs/state.yaml`](specs/state.yaml).

## Licensing notes

This repository is **Apache-2.0** ([ADR-0023](specs/adr/ADR-0023-apache-2-0-license.md)); the hosted fleet services stay closed, because Apache-2.0 imposes no source-release duty on a network service. [LICENSE](LICENSE) is the canonical text and [NOTICE](NOTICE) names the works we compose.

Upstream licenses to respect: HA Core and Frontend are Apache-2.0. HAOS, Supervisor, and CLI are GPL-3 — shipping a modified appliance triggers source availability for those components. HAEO is MIT and is not relicensed here. Community device integrations vary and need a per-integration audit before use in a paid fleet; a device pack must record the integration's licence and terms.

Nothing from Home Assistant, HAEO, HAOS, Supervisor, or HACS is vendored into this repository; `tests/unit/test_licensing.py` checks that and checks the NOTICE.
