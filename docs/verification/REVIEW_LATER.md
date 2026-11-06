# Review later — open modelling decisions and known sharp edges

A register, not a promise. Every entry is a place where the code currently does
something defensible **with a known gap**, and where a reviewer should look again
once the blocking questions close. Code refers to these as `RL-xx`.

Rules for this file:

- An entry is opened when the code ships a deliberate simplification.
- An entry closes only when the gap is either fixed or recorded as a decision.
- `Trigger` says what makes the review urgent; `Owner` says which deliverable
  answers it.

| ID | Where | What is deliberately unfinished | Trigger | Owner |
| --- | --- | --- | --- | --- |
| RL-01 | `haeo_bridge/plan.py:_degradation_policies` | Only **discharge** wear is priced. Charging-side wear is unpriced, so a plan may cycle a battery through cheap-hours arbitrage without paying for the wear that causes. | Any site whose plan charges from the grid at negative or near-zero prices | D05 / OQ-020 |
| RL-02 | `haeo_bridge/plan.py:_degradation_policies` | The rule's price is a **constant** snapshot of `degradation_cost`. A future cost series (temperature- or SOC-dependent) would need a per-period entity instead of a constant. | First profile that wants degradation cost to vary | D05 |
| RL-03 | `haeo_bridge/plan.py:_degradation_policies` | The rule targets the wildcard `["*"]`. With one battery per system that is exact; with two batteries, each battery's rule prices **the other battery's discharge** too (both wildcard rules cover one flow). | First multi-battery system | D04 / D05 |
| RL-05 | `telemetry.py`, `haeo_bridge/fields.py` | SOC is declared in `%` but HAEO stores 0..1 ratios (F-053). Telemetry capture of SOC must divide by 100; not implemented yet. | First plan/performance capture | D07 |
| RL-07 | `site_profiles/examples/solark_gateway_primary.yaml` | `window_calendar` is a placeholder entity id. Nothing in the integration creates or maintains the calendar a deferrable load needs. | First gateway site | D03 / OQ-022 |
| RL-08 | `haeo_bridge/fields.py` (`meter`/`thermostat`/`relay`) | Three profile kinds still have **no** HAEO carrier; they carry controls only, and their energy hides inside another element. | First profile that needs them for optimisation rather than control | D04 / ADR-0013 |
| RL-09 | `haeo_bridge/plan.py`, `flows._switchboard` | **done 2026-11-06 (ADR-0025).** Elements target HAEO's own switchboard junction, resolved from the hub's subentries at apply time; we no longer create a junction. What remains unproven is that HAEO accepts a translated switchboard name as a connection target — a live check, OQ-018 | first live apply | D04 / OQ-018 |
| RL-10 | `haeo_bridge/apply.py` (`PRUNE_UNKNOWN_ELEMENTS = False`) | Elements we do not know about are reported, never deleted. Corollary: a **removed** profile element stays in HAEO until someone deletes it by hand. | First profile edit after a live apply | D04 / OQ-018 |
| RL-11 | `profile/schema.py` (`degradation_cost.currency`) | The degradation currency is not compared to `site.currency`; a profile mixing EUR and USD passes validation. | First multi-currency fleet | D03 |
| RL-12 | `haeo_bridge/fields.py:DEFERRABLE_LOAD_FIELDS` | `deficit_price`/`overage_price` are left at HAEO's defaults (10.0/0.0), which encode a hard preference for meeting the window. That is a policy choice we inherited, not one we made. | First charger profile whose owner wants softer behaviour | D05 |
| RL-13 | `haeo_bridge/ha_port.py` | The port blocks on `run_coroutine_threadsafe`, so it must never be called from the event loop. One accidental `await`-free call from `async_setup_entry` would deadlock the loop for the timeout. | Any new caller of the bridge | D04 |
| RL-14 | `runtime.py:_apply_profile` | Provisioning runs once per setup when the flag is on; there is no re-apply on option change, no debounce, no daily reconcile. Two HA restarts in a row re-run the diff (cheap: it no-ops) but nothing repairs drift. | First site with the flag enabled | D04 / D08 |
| RL-15 | `adapters/stubs.py` | Both adapters are stubs. Their capabilities exist so the contract is exercised, not because any device is spoken to. | First real vendor adapter | D06 / D08 |
| RL-16 | `pricing/providers.py:DynamicSeries` | Dynamic prices use hold-last for gaps; a stale feed therefore looks like a flat price rather than a missing one. | First dynamic-price site | D05 / D07 |
| RL-17 | `ledger.py` | Exposure math is a sweep over commitment boundaries; it assumes kW is constant across each interval. Program rules that define energy (kWh) rather than power need a different model. | First real program enrolment | D09 / D10 |
| RL-18 | `haeo_bridge/contracts.py` | `HAEO_SURFACE_LIVE_VERIFIED`, `HAEO_SURFACE_COMMIT`, `ELEMENT_FIELDS_LIVE_VERIFIED` and `HA_PORT_LIVE_VERIFIED` are hand-maintained booleans. Nothing forces them to be re-read after a HAEO release. | Any HAEO version bump | D04 / D08 |
| RL-19 | `haeo_bridge/fields.py:BATTERY_FIELDS` (`efficiency`) | HAEO v0.5.0's own field default for efficiency is `95.0` against a `0..1` ratio whose segment computes `output = input * efficiency` (F-057..F-059) — the default would create energy. We therefore always write efficiency; the upstream default is a suspected HAEO bug worth reporting. | Any HAEO version bump, or an element created outside this bridge | D04 |
| RL-20 | `custom_components/fleetassistant/runtime.py` (`_resolve_tariffs`) | The cloud tariff seat is empty: no vendor fetcher, credentials or quota contract exists yet, so `cloud=` is always `None` and authority `cloud` degrades to the user schedule | when a vendor tariff adapter is added, measure its quota against C-22 first | adapter owner |
| RL-21 | `custom_components/fleetassistant/sensor.py` | The price sensor's entity id is pinned through `suggested_object_id`; a user who renames the entity breaks the plan's literal reference (`price_import`) silently | before the first live apply, or on any rename | integration owner |
| RL-22 | `custom_components/fleetassistant/pricing/sources.py` (`merge_tariffs`) | **done 2026-11-06.** `runtime._publish_price_repairs` raises `price_divergence` (with the worst period and both values) and `price_degraded`; the repair is informational and does not switch authority — that stays a human decision (ADR-0019) | if a divergence should auto-escalate to a different authority | integration owner |

## How an entry closes

1. Fix the code, or record an ADR that accepts the gap.
2. Delete the row and the corresponding `RL-xx` comment.
3. Note the closure in `CHANGELOG.md` under "Changed".

A row that reaches its trigger **without** being reviewed is a defect against
C-08/C-14/C-23, not a stale note.
| RL-24 | `references.py:check_references` | **done 2026-11-06.** `runtime._watch_references` subscribes to every referenced entity and re-runs the check on change; a rename is now caught within one state event. Deeper re-check (calendar contents, forecast depth) is still only at setup | if a rename is missed because the entity id itself changed | D07 / D08 |
| RL-25 | `adapters/ha_services.py` (`SwitchBinding`, `ClimateBinding`) | `SwitchBinding` treats "shed" as "turn off" and `ClimateBinding` converts °F→°C. Both are conventions, not verified vendor semantics: a heat-pump switch that is *on* when not shedding inverts the safety direction. | First relay or thermostat under contract | D06 |
| RL-26 | `custom_components/fleetassistant/dispatch.py` (`Executor.fail_safe`) | The fail-safe writes each capability's declared fallback setpoint. It is not the household safety net C-20 requires for gateway-primary sites: no contactor, no local automation, no proof that the fallback is reachable when the integration itself is the thing that failed. | Before the first gateway-primary dispatch-eligible site | D06 / D11 |
| RL-27 | `custom_components/fleetassistant/adapters/ha_services.py` (`read_state`) | A read value is a bare float: no timestamp, no quality flag, and climate modes are optimistically mapped (`heat`/`cool` → 1.0). A stale or `unknown` state is indistinguishable from a measurement. | First telemetry capture (D07) | D07 |
| RL-28 | `custom_components/fleetassistant/runtime.py` (`_start_dispatch`) | The loop ticks on a fixed 60 s interval, not on HAEO's plan boundaries or the site's price-step length. A plan published at 15:00:59 is dispatched at 15:01:00 and expires 15 minutes later regardless of the horizon's granularity. | First site with a sub-hourly price feed | D05 / D06 |
| RL-29 | `tools/preflight.py` | Offline preflight cannot see the entity registry, so it prints the reference inventory instead of checking it. A profile can be READY here and then raise repairs in HA | first operator run on a real site | D03 / D08 |
| RL-30 | `custom_components/fleetassistant/telemetry/transport.py` | **partly done 2026-11-06.** Producer + publisher + HTTP/MQTT sinks + bounded disk spool exist and are tested, but `runtime.py` still constructs none of them: there is no collector endpoint, no credentials and no `seq` persistence across restarts (a replay would be rejected by the dedupe registry). Wiring needs an ops decision, not code | first fleet onboarding | D07 / D08 |
| RL-31 | `fleet/allocation.py` (`Allocator`) | The share cap is a share of the target, chosen to spread an event; it is not derived from a program's fairness rule, site consent class, or a regulatory constraint. Clearing cost is the marginal offer, not a market price | before any payout is computed | D09 |
| RL-32 | `fleet/allocation.py` (`simultaneity_factor`) | Coincidence is computed from declared windows only. Real coincidence depends on weather and behaviour; the factor is an upper bound on qualified capacity, not a measured value | before a qualified-capacity number reaches a utility or aggregator | D09 / D10 |
| RL-33 | `LICENSE` (note block) and `NOTICE` (copyright line) | The copyright holder is a blank placeholder and `LICENSE` carries an edit-later note so the gap stays visible; Apache-2.0 §4(d) makes the NOTICE part of redistribution, and an unnamed holder weakens an infringement claim | Before the first public release or the first paid contract, whichever comes first | owner |
| RL-34 | `custom_components/fleetassistant/haeo_bridge/fields.py` (`HUB_SWITCHBOARD`) | **done 2026-11-06 (ADR-0025).** Symbolic target resolved at apply time; `_bus_element` and `fields.bus_name` deleted. Residual: the sentinel is a string in the plan, so a plan diff cannot show topology changes — diagnostics print the resolved name after an apply | before fleet-scale plan storage | D04 |
