# Facts ledger

This file holds verified technical facts about HAEO, Home Assistant, HACS, and vendor APIs. Each fact has an ID, a source, and an access date. Deliverables cite facts as `[F-NNN]`.

**Rules**
- A fact is `verified` only when the source was fetched and the exact value was read from it.
- A fact can go stale. Re-verify each fact at the **pinned** HAEO version (see ADR-0004) before code depends on it.
- If a fact conflicts with the brief, record the conflict in `OPEN_QUESTIONS.md`. Do not silently pick one.

| ID | Fact | Value | Source | Accessed | Status | Used by |
|----|------|-------|--------|----------|--------|---------|
| F-001 | HAEO domain | `haeo` | S-001 | 2026-11-05 | verified | C-03, D02 |
| F-002 | HAEO config_flow | `true` | S-001 | 2026-11-05 | verified | D04 |
| F-003 | HAEO integration_type | `hub` | S-001 | 2026-11-05 | verified | D01, D04 |
| F-004 | HAEO iot_class | `local_push` | S-001 | 2026-11-05 | verified | D01 |
| F-005 | HAEO quality_scale | `platinum` | S-001 | 2026-11-05 | verified | D02 |
| F-006 | HAEO requirements | `["highspy>=1.15.1", "numpy>=2.3.2"]` | S-001 | 2026-11-05 | verified | C-08, D02 |
| F-007 | HAEO manifest version on `main` | `"0.5.0"` | S-001 | 2026-11-05 | verified | ADR-0004 |
| F-008 | HAEO after_dependencies | `["calendar", "frontend", "http", "recorder"]` | S-001 | 2026-11-05 | verified | D02 |
| F-009 | HAEO manifest `dependencies` | `[]` | S-001 | 2026-11-05 | verified | D02 |
| F-010 | HAEO hacs.json | `{"name": "HAEO", "hacs": "2.0.5", "homeassistant": "2026.1.1", "filename": "haeo.zip", "render_readme": true, "zip_release": true}` | S-002 | 2026-11-05 | verified | D02 (minimum HA version floor; zip-release pattern) |
| F-011 | Latest HAEO release | `v0.5.0`, published 2026-10-27 (previous: `v0.5.0rc3`, 2026-10-23) | S-003 | 2026-11-05 | verified | ADR-0004 |
| F-012 | HAEO license | MIT | S-004 | 2026-11-05 | verified | C-19, D02 |
| F-013 | HAEO uses the HiGHS solver through highspy | README: "bundled `highspy` bindings" | S-005 | 2026-11-05 | verified (wording only; packaging mechanism not verified) | D02, OQ-010 |
| F-014 | HA installs integration `requirements` | HA dev docs: "Home Assistant will try to install the requirements into the `deps` subdirectory of the Home Assistant configuration directory if you are not using a `venv`…" If installation fails, the integration fails to load. | S-006 | 2026-11-05 | verified | C-08, OQ-001 |
| F-015 | HAEO element types at v0.5.0 | `battery, battery_section, buffer, connection, deferrable_load, ev, grid, inverter, junction, load, node, solar, policy` (13) | S-009 | 2026-11-05 | verified (source) | C-23, D04 |
| F-016 | HAEO has no element named `meter`, `thermostat`, or `relay` | Confirmed by the complete `ElementType` enum | S-009 | 2026-11-05 | verified (source) | OQ-002, D04 |
| F-017 | HAEO hub creation data | `{integration_type: "hub", common: {name, horizon}, advanced: {debounce_seconds: 2, advanced_mode: bool}}` | S-012 | 2026-11-05 | verified (source; live-unverified) | D04 |
| F-018 | HAEO elements/connections are config **subentries** of the hub entry | `subentry_type` equals the element type; subentry data starts `{name, element_type}`; element flows filtered by `advanced` flag | S-012 | 2026-11-05 | verified (source; live-unverified) | D04, OQ-009 |
| F-019 | HAEO hub unique_id | `haeo_hub_<hub name lowercased, spaces → underscore>`; duplicate hub names rejected with `name_exists` | S-012 | 2026-11-05 | verified (source) | D04 |
| F-020 | New HAEO hub is created with two subentries | a `network` subentry and a switchboard `junction` | S-012, S-007 | 2026-11-05 | verified (source) | D04 |
| F-021 | HAEO stored field values are tagged | `{"type": "entity", "value": [ids]}` (+optional `on_states`/`off_states`) or `{"type": "constant", "value": float|bool}` | S-010 | 2026-11-05 | verified (source) | D04, OQ-002 |
| F-022 | HAEO horizon value shape | preset → `{"value": "5_days"}`; forecast sensor → `{"value": ["sensor.x"]}`; default `5_days` | S-011 | 2026-11-05 | verified (source; live-unverified) | D04, OQ-007 |
| F-023 | HAEO horizon presets | `2_days`, `3_days`, `5_days`, `7_days` (there is no 4-day or arbitrary-days preset) | S-008, S-011 | 2026-11-05 | verified (source) | D04 |
| F-024 | HAEO default period layout | tiers of 5×1 min, 11×5 min, 46×30 min, 48×60 min (≈72 h / 110 periods); presets derive their own layout | S-008 | 2026-11-05 | verified (source) | D04, OQ-007 |
| F-025 | HAEO "Relax impossible plans" | key `relax_infeasible`, in the hub **options** advanced section, default `False` | S-008, S-013 | 2026-11-05 | verified (source; live-unverified) | D04, ADR-0009 |
| F-026 | HAEO `record_forecasts` option | `record_forecasts`, hub options advanced section, default `False` | S-008, S-013 | 2026-11-05 | verified (source) | D07 |
| F-027 | HAEO forecast attribute boundary key | `time` (ISO 8601; tz-less read in HA time zone); values under `value`; n+1 boundaries = n periods; ≥2 increasing times required | S-014 | 2026-11-05 | verified (source) | D05, OQ-007 |
| F-028 | HAEO hub setup form fields | only `name`, `horizon`, `advanced_mode`; there is no relax flag at creation | S-013 | 2026-11-05 | verified (source) | D04 |
| F-029 | HAEO element form shows "policy pricing" fields for battery and load | `ELEMENT_SURFACED_PRICE_HINTS = {battery, load}` | S-015 | 2026-11-05 | verified (source) | D05, OQ-011 |
| F-030 | HAEO element config fields are sectioned and type-specific | e.g. grid `power_limits` → `CONF_MAX_POWER_SOURCE_TARGET`; defaults live on `FieldHint`; optionality from `NotRequired` | S-016 | 2026-11-05 | verified (source; per-type key list still open) | D04, OQ-017 |

| F-031 | Subentry flows are started in-process with `hass.config_entries.subentries.async_init((entry_id, subentry_type), context=SubentryFlowContext(source=SOURCE_USER))` and answered with `async_configure(flow_id, user_input)` | verified (source) | S-018, S-020 | 2026-11-05 | D04, OQ-016 |
| F-032 | Subentry CRUD is `hass.config_entries.async_add_subentry(entry, subentry)` / `async_update_subentry(entry, subentry, data=..., title=..., unique_id=...)` / `async_remove_subentry(entry, subentry_id)`; entries expose `entry.subentries` and `entry.get_subentries_of_type(type)` | verified (source) | S-018, S-019 | 2026-11-05 | D04 |
| F-033 | A subentry flow supports only the `user` and `reconfigure` steps and can reach its parent entry through `self._get_entry()`; `ConfigSubentry` carries `subentry_id`, `subentry_type`, `title`, `data`, `unique_id` | verified (source) | S-018 | 2026-11-05 | D04 |
| F-034 | `POST /api/config/config_entries/flow` starts a config flow with `{"handler": "<domain>", "show_advanced_options": bool}`; `POST /api/config/config_entries/flow/{flow_id}` takes the **raw user-input dict as the body** (not wrapped); `GET` re-shows the step, `DELETE` aborts | verified (source) | S-019 | 2026-11-05 | D04, D08 |
| F-035 | The options flow is `POST /api/config/config_entries/options/flow` with `{"handler": "<entry_id>"}`, then `POST .../options/flow/{flow_id}` with the user input | verified (source) | S-019 | 2026-11-05 | D04 |
| F-036 | The subentry flow is `POST /api/config/config_entries/subentries/flow` with `{"handler": [entry_id, subentry_type], "show_advanced_options": bool}`, then `POST .../subentries/flow/{flow_id}` with the user input; passing `subentry_id` switches the flow context to `reconfigure` | verified (source) | S-019 | 2026-11-05 | D04, OQ-016 |
| F-037 | Config entries are read with `GET /api/config/config_entries/entry?domain=<domain>` and managed with `DELETE /entry/{entry_id}` and `POST /entry/{entry_id}/reload`; every config-entry view requires an admin token | verified (source) | S-019 | 2026-11-05 | D04, D08 |
| F-038 | The WebSocket API has `config_entries/get`, `config_entries/subentries/list`, `config_entries/subentries/update` (title only) and `config_entries/subentries/delete`; there is **no** command that creates a subentry | verified (source) | S-019 | 2026-11-05 | D04, D08, OQ-016 |
| F-039 | HA 2026.1.1 is the Home Assistant version HAEO v0.5.0 declares in `hacs.json`, so it is the version the contract matrix pins | verified | S-002 | 2026-11-05 | D02, D04 |

## Brief claims still awaiting verification

These claims appear in the brief. They are treated as **UNVERIFIED** until an F-ID exists for them.

| Brief claim | Status after the e04 source spike | Tracked as |
|-------------|----------------------------------|-----------|
| Setup order: Hub (with horizon) → Element entries → Connection entries; config-flow only, no YAML | Corrected: hub first, then elements/connections as **subentries**, not config entries (F-018). Still config-flow only. | OQ-009 |
| HAEO supports multiple hubs per HA instance | Consistent with the source (one config entry per hub, subentries scoped to it); live confirmation pending. | OQ-002 |
| HAEO creates an input entity for every configured field | Partly: each field stores an `entity` or `constant` tagged value (F-021); which fields get input entities is derived from field hints (F-030). Live confirmation pending. | OQ-002 |
| Horizon presets 2/3/5/7 days (default 5); periods grow 1 → 5 → 30 → 60 min | Verified (F-023, F-024). | closed |
| Custom horizon from a forecast sensor whose `forecast` attribute lists period boundaries | Verified in shape (F-022, F-027); which sensor formats HAEO accepts as price/load inputs is still open. | OQ-007 |
| HAEO consumes forecast-style sensors (time + value points) | Verified for boundary times (F-027); value units/semantics per input still open. | OQ-007 |
| Pricing segments / policy pricing / Tagged Power; per-node shadow prices | Partly: `policy` element type exists and battery/load carry surfaced price hints (F-029); segment/tagged-power field names and shadow-price outputs still open. | OQ-011 |
| Hub setting "Relax impossible plans" (default off) | Verified: `relax_infeasible`, options-only, default `False` (F-025). Repair issue IDs still open. | OQ-006 |
| HAOS Supervisor "Python packages" setting is the path for highspy/numpy | Unresolved; conflicts with F-014. | OQ-001, OQ-010 |

| F-040 | Every HAEO element value is a tagged union: `{"type": "entity", "value": [entity_id], on_states?, off_states?}`, `{"type": "constant", "value": number|bool}` or `{"type": "none"}` | verified (source) | S-023 | 2026-11-05 | D04 |
| F-041 | Topology is a per-element field, not a connection entry: `CommonConfig {name, connection?}` / `ConnectedCommonConfig {name, connection}`, with `connection = {"type": "connection_target", "value": "<element name>"}`; HAEO rewrites targets when the target element is renamed | verified (source) | S-025 | 2026-11-05 | D04, OQ-018 |
| F-042 | Grid element fields: `pricing.price_source_target` and `pricing.price_target_source` are **required** (`PRICE`, time series); `power_limits.max_power_source_target` / `max_power_target_source` default to 100.0 kW with no entity required | verified (source) | S-021 | 2026-11-05 | D04 |
| F-043 | Battery sections and keys: `storage.capacity`, `storage.initial_charge_percentage`, `limits.min_charge_percentage` (0.0), `limits.max_charge_percentage` (100.0), `power_limits.*`, `pricing.salvage_value` (0.0), `efficiency.efficiency_source_target/target_source` (95.0), `advanced.charge_limit_cost` (100.0, min 0.0) | verified (source) | S-022 | 2026-11-05 | D04, D05 |
| F-044 | Battery surfaces two pricing hints: `charge_cost` (default -0.001, `source_is_wildcard`) and `discharge_cost` (default 0.0) — priced cycling is a policy/surfaced-price concern, not a battery config field | verified (source) | S-022 | 2026-11-05 | D05, OQ-020 |
| F-045 | `load` fields: `forecast.forecast` (POWER, direction "-") and `curtailment.curtailment` (STATUS, force-required, default False); it surfaces a `consumption_cost` hint (wildcard, negated) | verified (source) | S-024 | 2026-11-05 | D04, D05 |
| F-046 | `solar` fields: `forecast.forecast` (direction "+") and `curtailment.curtailment` | verified (source) | S-024 | 2026-11-05 | D04 |
| F-047 | `ev` models a vehicle, not a charger: `vehicle.capacity`, `vehicle.energy_per_distance`, `vehicle.current_soc` (entity only), `charging.max_charge_rate`, `charging.connected` (entity only), optional trip calendar and `public_charging_price` (0.6) | verified (source) | S-027 | 2026-11-05 | D04, OQ-019 |
| F-048 | `policy` element = `{element_type: "policy", name, rules: [{name, enabled, source, target, price}]}` where `source`/`target` are element names or `["*"]`; rules compile into policy pricing and HAEO rewrites element references on rename | verified (source) | S-028 | 2026-11-05 | D05, OQ-020 |
| F-049 | A hub creates its own `network` and `switchboard` (junction) subentries at creation time, so an external driver must never prune elements it did not create | verified (source) | S-016 | 2026-11-05 | D04, OQ-018 |
