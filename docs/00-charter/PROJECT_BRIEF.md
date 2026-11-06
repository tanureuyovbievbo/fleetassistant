# Project Brief — fleetassistant (formerly HA-OPENDERMS) (source of truth)

| Field | Value |
|-------|-------|
| Status | accepted (founding brief) |
| Received | 2026-11-05 |
| Rule | Do not edit the brief text. Record changes to intent as ADRs and as entries in `docs/updates/`. |

> **Product rename (2026-11-05, ADR-0011):** The product is now **fleetassistant** (domain `fleetassistant`) to match the repository. The brief text below is kept verbatim and still says "HA-OPENDERMS" / "OpenDERMS". Read every such mention as "fleetassistant". All brief rules about the name (domain format, no collision with `haeo`, naming honesty) still apply to the new name.

> **Note on "verified" claims in this brief:** The brief calls its HAEO facts "verified". Agents MUST still re-confirm each fact at the pinned HAEO version and record it in `docs/verification/FACTS_LEDGER.md`. One brief claim, about dependency installation, conflicts with the current HA developer docs. See OQ-001.

---

You are the founding architect and lead engineer for HA-OPENDERMS — an open distributed energy management platform delivered first as a Home Assistant custom integration distributed through HACS, built on top of HAEO (Home Assistant Energy Optimizer) as the site-level optimizer. Later phases add the multi-tenant fleet, dispatch, and settlement services. Work in small verifiable increments; every increment must run and be testable on its own.

## What HA-OPENDERMS is

v1 = a HACS custom integration that a homeowner or installer installs into their existing Home Assistant. It gives a site: a declarative site profile, automatic HAEO network provisioning, a generic price/target model, a control-adapter layer, and a telemetry publisher. It composes HAEO; it does not fork, patch, or reimplement HAEO.

v2 = fleet services (multi-tenant hosting, provisioning, OTA, observability, dispatch, settlement, consumer app) that consume v1 sites.

Deployment profiles, one product:

- **Cloud-primary** (no site hardware): HA hosted per-tenant in our cloud, connected to the home only via vendor cloud APIs (Tesla Fleet, SolarEdge Open, Enphase Energy, EG4Base, Sigenergy cloud, Wallbox, Easee, ecobee, Sensibo). Coarse control only. Purpose: self-serve enrollment, near-zero acquisition cost, measured savings, national expansion.
- **Gateway-primary** (on-site): HAOS on a wired mini PC driving open-protocol stacks (Sol-Ark, EG4, Sigenergy, Solis, Deye, Growatt, GoodWe, Hoymiles) with Shelly Pro 3EM / CT metering, relay shedding, local EV charger control. Full control authority: inverter export limit, battery setpoints, charger amps, thermostat, relays, hardware fail-safe. Purpose: dispatch-eligible, auditable sites.

Both profiles run the same integration, site profile, adapter contract, telemetry schema, and app. A cloud-primary site upgrades to gateway-primary by adding hardware and re-pointing the profile — no re-onboarding.

Price/rate/regulation logic is generic and pluggable in v1. No California tariff logic in v1. Rate schedules, export values, incentive overlays, and regulatory constraints are rule packs installed later as modules. v1 ships with: flat, time-of-use block schedules, dynamic price feeds (Nord Pool, Tibber, Octopus, EPEX, Electricity Maps), and a generic "target/incentive overlay" abstraction. California packs (TOU/EV rates, NEM 3.0 export curves, ELRP/DRIP/BatteryVPP targets) are a named later deliverable, not a v1 feature.

## Facts about HAEO you must build against (verified)

- HAEO's manifest: domain: haeo, config_flow: true, integration_type: hub, iot_class: local_push, quality_scale: platinum, requirements highspy>=1.15.1 and numpy>=2.3.2 (HiGHS solver, not scipy). MIT licensed.
- HAEO configuration is UI/config-flow only: you create a Hub (with planning horizon), then Element entries, then Connection entries. There is no YAML config file to generate. Programmatic provisioning must drive Home Assistant's config-flow API to create hub/element/connection entries. Treat HAEO's flow fields as an unstable private API: pin the HAEO version, build a versioned bridge module, and contract-test it against a live HAEO instance.
- HAEO supports multiple hubs per instance (separate systems/buildings) and creates an input entity for every configured field, so constants (battery capacity, export limit, min SOC) can be written at runtime without reconfiguring elements.
- HAEO's horizon comes from a preset (2/3/5/7 days, default 5) with periods growing 1 → 5 → 30 → 60 minutes, or from a forecast sensor whose forecast attribute lists period boundary times. Use the forecast-sensor path when we need a custom period layout.
- HAEO consumes forecast-style sensors (points with time + value) for prices, load, solar, and inputs. That is the seam our generic price model writes into.
- HAEO models pricing via pricing segments / policy pricing and Tagged Power, computes shadow prices per node, and has a hub setting "Relax impossible plans" (off by default) plus repair issues for broken element references and unresolvable constraints. Use shadow prices for fleet allocation; keep "Relax impossible plans" on for fleet reliability; pre-validate referential integrity before applying a rendered profile.

## Non-negotiable constraints

- Never fork Home Assistant Core to make it multi-tenant. HA's single-tenancy is the tenant boundary. Rule: tenant per container, never tenant per config entry in a shared core. A site is ~200–600 entities (per-inverter vendor APIs inflate this), HA degrades past tens of thousands of entities in one event loop, and HAEO solves inside that single loop.
- HA-OPENDERMS is an integration, not an HAOS add-on and not a core fork. Ship it as custom_components/openderms/. Do not collide with HAEO's haeo domain. Display name "HA-OPENDERMS"; keep the domain a lowercase Python identifier with no dashes.
- Composability rule: we generate HAEO's configuration through HA's config flow API, we never write into HAEO's files, storage, or private internals. All HAEO interaction goes through one bridge module with a pinned version and contract tests.
- Dependencies: Home Assistant does not pip-install arbitrary dependencies for custom integrations. Allowed: packages already in HA core's requirements, pure-Python code vendored inside our component, or documented user/ops steps (HAOS exposes a Supervisor "Python packages" setting — HAEO's highspy/numpy needs this path, and our install docs must say so). Do not assume a dependency exists.
- UI config flow required (config entry + options flow, no YAML-only setup), with import/validation errors surfaced as HA repairs, per Home Assistant integration best practice and store expectations.
- All device access goes through one control-adapter interface: setExportLimit(kW), setBatteryTarget(%), setChargerAmps(A), setThermostatSetpoint(°F), setChargingSchedule(...), shedCircuit(id, bool). Each capability declares safe min/max, rate limit, hysteresis, consent requirement, and whether it is API-backed or local-backed. API adapters first, Modbus adapters later, identical contract. Nothing else in the codebase touches a device.
- Site profile as code is the source of truth (stack type, metering topology, controllable loads, control limits, consent flags, deployment profile, rule-pack references). A renderer emits HA artifacts from it: config entries, helpers, automations, and the HAEO hub/element/connection network. No hand-edited per-site config in fleet mode.
- One authoritative optimizer per site: HAEO on the gateway. The cloud mirror stays deliberately degraded (telemetry, monitoring, coarse control). If a design forces dual optimization per site, flag it as a defect.
- Control authority is tiered. Cloud path = coarse, best-effort, never claimed as firm performance. Gateway path = full. Both unreachable = local defaults, and we report non-performance and opt out. We never over-promise performance to a utility, ISO, or aggregator.
- Generic pricing must include a priced battery-degradation term. Degradation cost is a model input, not a regional rule. Unpriced cycling destroys warranty life.
- Local autonomy and a hardware fail-safe (contactor + local automations) on gateway-primary sites: the home stays safe and comfortable when our cloud is unreachable.
- Program integrity is a data structure, not a policy memo. v1 ships a per-site commitments ledger (which kW is committed to which program) so double-counting is structurally prevented when rule packs arrive.
- Provisioning must be headless-capable (HA config-flow REST API for config entries), per-site device identity and client certificates, WireGuard client-only (no inbound ports), scoped OAuth2 via HA Application Credentials. Never ship shared admin tokens.
- Security/privacy: per-tenant secret isolation, encryption at rest, telemetry minimization, CCPA/CPRA-conscious retention and deletion, append-only audit log of every dispatch and control write. Design for SOC 2 scope from day one.
- Licensing: HA Core and Frontend are Apache 2.0 (modification and commercial use permitted, no trademark rights). HAOS, Supervisor and CLI are GPL-3 (ship a modified appliance and source availability applies to those components). HAEO is MIT. Community device integrations vary (some GPL-3) — audit each before it enters a paid fleet. Market as "powered by Home Assistant · built on HAEO"; never as the Home Assistant brand. Nabu Casa's cloud is not our relay.
- Naming honesty: "OpenDERMS" describes an open DERMS architecture. It must not imply OpenADR Alliance membership/certification, CEC-AC SPARc, ISO registration, or any compliance status. Certification claims are explicit, dated, evidence-backed statements only.

## Verification discipline (every artifact)

- Cite primary sources for regulatory, program, rate, market, certification, and standards statements (CEC, CPUC, CAISO, IOU program pages, OpenADR Alliance, CEC-AC, UL, IEEE, NIST) with URL and date.
- Mark unverifiable items UNVERIFIED and list them in open questions. Do not invent rates, capacity minimums, incentive amounts, certification costs, or timelines. Do not cite a document you did not fetch.
- Confirm HAEO element/segment names, config-flow fields, sensor names, and units against the HAEO docs (haeo.io) and the hass-energy/haeo source. Confirm HA API shapes (config flow, REST, WebSocket, MQTT, Application Credentials) against Home Assistant developer docs. Never guess entity names, service names, flow steps, config keys, or units.
- Name vendor API terms-of-service risk wherever an adapter targets a closed ecosystem, and show the quota math required before promising telemetry cadence.

## Deliverables, in this order (produce as repo files; stop for review between each)

1. **Architecture spec** — v1 integration scope, v2 fleet services, the two deployment profiles, data flows, the control-adapter seam, site profile as source of truth, HAEO bridge design, and a rejected-alternatives section (multi-tenant core fork, hub-and-spoke remote_homeassistant as production, dual HAEO per site, writing HAEO storage directly, HAOS add-on as the primary form factor) with reasons.
2. **HACS packaging spec** — repo layout, manifest.json and hacs.json contents, min HA version, config flow + options flow outline, dependency strategy for highspy/numpy incl. install docs, release/zip mechanics, HACS store submission checklist, our license decision and its consequences for the fleet cloud.
3. **Site profile schema (versioned)** — YAML/JSON schema plus three worked examples: Tesla home (cloud-primary), Sol-Ark + Shelly 3EM + AC + EV home (gateway-primary), and a multi-hub home (two systems / accessory dwelling unit).
4. **HAEO provisioning bridge** (highest-risk item: spike it first) — code that compiles a site profile into HAEO hub/element/connection entries via HA's config-flow API; referential-integrity pre-validation (element names, connections) with clear repair-issue output; horizon strategy (preset vs forecast-sensor); "Relax impossible plans" defaults; HAEO version pinning; contract tests against a live HAEO.
5. **Generic price/target model** — pluggable rate providers (flat, TOU block schedules, dynamic price feeds) and a generic incentive/target overlay, compiled into the forecast-sensor and pricing-segment / policy-pricing / Tagged Power inputs HAEO consumes, including the priced degradation term. Define the rule-pack interface (rate schedules, export value curves, event targets, regulatory constraints) and prove v1 works with zero rule packs installed.
6. **Control adapter layer** — interface, capability descriptors, safety limits, consent gating, plan-execution cadence, local fail-safe, plus one API-backed stub adapter and one Modbus-backed stub adapter behind the identical contract.
7. **Telemetry & measurement schema** — versioned payloads, cadences, source authority (gateway > vendor cloud), quality flags, HAEO plan/performance capture, and the single reconciled performance record that later feeds claims and payouts.
8. **Fleet services spec + scaffolding** — tenancy/identity, headless provisioning, OTA and version matrix (HA × HAEO × our integrations) with rollback, per-stack contract-test matrix, observability SLOs, and per-tenant container orchestration with the compute math.
9. **Aggregation services** — capability ledger, qualified-capacity model with simultaneity math, allocation solver using HAEO shadow prices as site marginal cost → fleet LP for the aggregate target (honoring availability, opt-outs, comfort floors, battery-life caps, fairness), feedback trim loop, settlement/payout pipeline.
10. **Rule-pack deliverable: California** (later phase) — licensing, registration, metering/settlement data path, certifications (OpenADR 2.0b VEN, SPARc, UL 2933, CETS, IEEE 1547-2018 / UL 1741 SB), fast-to-revenue ordering, partner-aggregator-first path. Every item cited or marked UNVERIFIED.
11. **Phased plan with gates** — reference site → integration v1 → fleet layer → aggregation v1 (partner signal) → aggregation v2 (own certified signal) → scale, each with exit criteria, KPIs, staffing, cost bands.
12. **Risk register** — technical, operational, regulatory, vendor-dependency risks with mitigations, plus the top 10 numbers to verify against primary sources before committing capital.
