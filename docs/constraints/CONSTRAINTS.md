# Non-negotiable constraints (C-01 to C-24)

| Field | Value |
|-------|-------|
| Source | [`docs/00-charter/PROJECT_BRIEF.md`](../00-charter/PROJECT_BRIEF.md) § Non-negotiable constraints and § Verification discipline |
| Status | accepted |
| Rule | Every deliverable ends with a "Constraint compliance" table that lists each relevant C-ID as `met`, `n/a`, or `violated`, with the reason. A `violated` row blocks acceptance. |

Each constraint has a **Check**. The reviewer agent applies the check (see `.pi/skills/constraints-check/SKILL.md`).

## Platform and form factor

### C-01 — No multi-tenant fork of Home Assistant Core
- **Rule:** NEVER fork HA Core. HA single-tenancy is the tenant boundary: one tenant per container, never one tenant per config entry in a shared core.
- **Why:** A site has about 200–600 entities. HA degrades past tens of thousands of entities in one event loop. HAEO solves inside that loop.
- **Check:** No design puts more than one tenant in one HA process. Fleet sizing (D08) shows entities per container.

### C-02 — Integration form factor
- **Rule:** Ship as `custom_components/fleetassistant/`, distributed through HACS. It is not an HAOS add-on and not a core fork.
- **Check:** The repository layout and `hacs.json` match D02.

### C-03 — Domain and display name
- **Rule:** The domain is `fleetassistant`: lowercase, a valid Python identifier, no dashes. The display name is "fleetassistant" (ADR-0011; renamed from "HA-OPENDERMS" / `openderms`). NEVER collide with `haeo` or any other existing domain.
- **Check:** `manifest.json` has `"domain": "fleetassistant"`. Search the HA core and HACS default lists for a collision before release.

### C-04 — Compose HAEO; do not fork, patch, or reimplement it
- **Rule:** HAEO is the optimizer. We generate its configuration and feed its input sensors. We do not copy, patch, or re-solve its model.
- **Check:** No HAEO source is vendored. No LP solver runs per site in our code (see also C-11).

### C-05 — UI config flow and repairs
- **Rule:** Setup uses a config entry and an options flow. YAML-only setup is not allowed. Import and validation errors appear as HA repair issues.
- **Check:** `config_flow: true` in the manifest. Every validation error path maps to a repair issue ID listed in D02 and D04.

## HAEO composition

### C-06 — HAEO configured through the config-flow API only
- **Rule:** Create HAEO hub, element, and connection entries only through HA's config-flow API. NEVER write HAEO files, `.storage` entries, or private internals.
- **Check:** The bridge uses only documented HA config-flow interfaces (internal flow manager or REST/WebSocket flow endpoints). Grep finds no `.storage` path and no `haeo.` private import.

### C-07 — One versioned bridge module
- **Rule:** All HAEO interaction goes through `custom_components/fleetassistant/haeo_bridge/`. It pins a HAEO version and is contract-tested against a live HAEO at that version.
- **Check:** Only the bridge imports or calls anything about HAEO. A contract-test job exists for each supported HAEO version.

### C-08 — Dependency policy
- **Rule:** Allowed dependencies are (a) packages already in HA core requirements, (b) pure-Python code vendored in our component, or (c) documented user/ops install steps. NEVER assume a dependency exists.
- **Note:** The brief's statement on how HA installs custom-integration requirements conflicts with current HA developer docs. See **OQ-001**. Until OQ-001 is resolved, apply the conservative rule above.
- **Check:** `manifest.json` `requirements` is empty or contains only HA-core packages. D02 documents the highspy/numpy path for HAEO.

## Control and data model

### C-09 — Single control-adapter interface
- **Rule:** All device access goes through one interface: `set_export_limit(kW)`, `set_battery_target(%)`, `set_charger_amps(A)`, `set_thermostat_setpoint(°F)`, `set_charging_schedule(...)`, `shed_circuit(id, bool)`. Each capability declares safe min/max, rate limit, hysteresis, consent requirement, and backing (`api` or `local`). API adapters come first and Modbus adapters later, with the identical contract.
- **Check:** Only `adapters/` makes device calls (service calls to device entities, HTTP calls to vendors, Modbus). All other code calls the interface.

### C-10 — Site profile is the source of truth
- **Rule:** The versioned site profile (stack type, metering topology, controllable loads, control limits, consent flags, deployment profile, rule-pack references) is the input to a renderer. The renderer emits config entries, helpers, automations, and the HAEO network. No hand-edited per-site config in fleet mode.
- **Check:** Rendering is deterministic: the same profile gives the same artifacts. A profile diff produces a change plan.

### C-11 — One authoritative optimizer per site
- **Rule:** HAEO on the site's HA instance is the only optimizer. The cloud mirror is deliberately degraded (telemetry, monitoring, coarse control). A design that needs two optimizers for one site is a **defect**.
- **Check:** Fleet allocation (D09) uses HAEO shadow prices as input. It does not re-optimize site internals.

### C-12 — Tiered control authority, no over-promising
- **Rule:** Cloud path = coarse and best-effort, never claimed as firm. Gateway path = full. Both unreachable = local defaults, and we report non-performance and opt out. NEVER over-promise to a utility, ISO, or aggregator.
- **Check:** Each capability and each telemetry record carries an authority tier. Qualified capacity (D09) excludes cloud-only kW from firm offers.

### C-13 — Generic, pluggable pricing
- **Rule:** v1 ships flat, TOU block, dynamic feeds (Nord Pool, Tibber, Octopus, EPEX, Electricity Maps), and a generic target/incentive overlay. v1 has no California tariff logic. v1 MUST work with zero rule packs installed.
- **Check:** There is a test that runs with an empty rule-pack registry. There are no region-specific constants in core code.

### C-14 — Priced battery degradation
- **Rule:** The price model includes a priced battery-degradation term as a model input (currency per kWh of throughput or equivalent). It is not a regional rule.
- **Check:** The site profile schema has the field. The price compiler emits it into a HAEO input. The default is not zero unless the user sets zero explicitly.

### C-15 — Local autonomy and hardware fail-safe
- **Rule:** Gateway-primary sites have a contactor and local automations. The home stays safe and comfortable when our cloud is unreachable.
- **Check:** D06 defines fail-safe states for each capability and the loss-of-comms timeout behavior.

### C-16 — Commitments ledger
- **Rule:** v1 ships a per-site commitments ledger that records which kW is committed to which program. The structure prevents double-counting.
- **Check:** The ledger rejects an overlapping commitment that exceeds qualified capacity. A unit test proves this.

## Security, privacy, provisioning

### C-17 — Headless, least-privilege provisioning
- **Rule:** Provisioning is headless-capable through the HA config-flow REST API. Each site has its own device identity and client certificate. WireGuard is client-only, with no inbound ports. OAuth2 is scoped, through HA Application Credentials. NEVER ship shared admin tokens.
- **Check:** No long-lived admin token appears in any artifact or image. The network design opens no inbound port.

### C-18 — Security and privacy baseline
- **Rule:** Per-tenant secret isolation, encryption at rest, telemetry minimization, CCPA/CPRA-conscious retention and deletion, and an append-only audit log of every dispatch and control write. Design for SOC 2 scope from day one.
- **Check:** `specs/tech-architecture/SECURITY_PLAN_LATEST.md` maps each item to a control. Every adapter write emits an audit record.

## Legal, brand, honesty

### C-19 — Licensing hygiene

*Settled 2026-11-06: this repository is Apache-2.0 (ADR-0023).*
- **Rule:** Respect upstream licenses: HA Core/Frontend Apache-2.0; HAOS/Supervisor/CLI GPL-3; HAEO MIT. Audit every community device integration's license before it enters a paid fleet.
- **Check:** D02 records the license decision. `docs/verification/LICENSE_AUDIT.md` (created in D08) lists each third-party integration and its license.

### C-20 — Branding
- **Rule:** Market as "powered by Home Assistant · built on HAEO". NEVER present the Home Assistant brand as ours. Nabu Casa's cloud is not our relay.
- **Check:** No HA logo or "Home Assistant" product name is used as our brand. The remote-access design uses our own WireGuard path.

### C-21 — Naming honesty and certification claims
- **Rule:** The product name (fleetassistant, formerly HA-OPENDERMS; ADR-0011) and the term "open DERMS" describe a product and an architecture. They MUST NOT imply OpenADR Alliance membership or certification, CEC-AC SPARc, ISO registration, or any compliance status. Certification claims are explicit, dated, and evidence-backed.
- **Check:** Search every doc and UI string for "certified", "compliant", "OpenADR", "SPARc", and "registered". Each hit has a date and a source, or a negation.

## Verification

### C-22 — Primary sources or UNVERIFIED
- **Rule:** Cite primary sources (CEC, CPUC, CAISO, IOU program pages, OpenADR Alliance, CEC-AC, UL, IEEE, NIST) with URL and date. Mark everything else UNVERIFIED and list it in open questions. Do not invent rates, minimums, amounts, costs, or timelines. Do not cite unfetched documents.
- **Check:** `/verify-claims` passes with no uncited regulatory, rate, market, or certification statement.

### C-23 — Never guess HAEO or HA names
- **Rule:** Confirm HAEO element/segment names, config-flow fields, sensor names, and units against haeo.io and the `hass-energy/haeo` source at the pinned version. Confirm HA API shapes against developers.home-assistant.io.
- **Check:** Every HAEO or HA identifier in a deliverable has an F-ID in `FACTS_LEDGER.md` or is marked UNVERIFIED.

### C-24 — Vendor ToS risk and quota math
- **Rule:** Name the terms-of-service risk for every adapter that targets a closed ecosystem. Show the quota math before promising telemetry cadence.
- **Check:** Each vendor adapter section has a "ToS risk" paragraph and a "Quota math" table, with sources or UNVERIFIED marks.

### C-25 — Discover before you create
- **Rule:** Read the target before writing it. Reuse a pre-existing hub record. Delete only what our own previous plan created.
- **Check:** No `create_*` call for a target absent from the preceding `list_*` read. A pre-existing switchboard is adopted, never duplicated. A foreign subentry is reported, never removed.
- **Where:** `specs/adr/ADR-0024-discover-before-create.md`
