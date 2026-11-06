# Sources register

Every cited source gets one row. Only list documents that were **actually fetched**. Cite inline as `[S-NNN]`.

| ID | Title / description | Publisher | URL | Accessed | Fetched by | Notes |
|----|---------------------|-----------|-----|----------|------------|-------|
| S-001 | HAEO `manifest.json` (main branch) | hass-energy/haeo (GitHub) | https://raw.githubusercontent.com/hass-energy/haeo/main/custom_components/haeo/manifest.json | 2026-11-05 | bootstrap session | Content at time of fetch: version "0.5.0". Re-fetch at the pinned tag. |
| S-002 | HAEO `hacs.json` (main branch) | hass-energy/haeo (GitHub) | https://raw.githubusercontent.com/hass-energy/haeo/main/hacs.json | 2026-11-05 | bootstrap session | |
| S-003 | HAEO releases list (GitHub REST API) | GitHub | https://api.github.com/repos/hass-energy/haeo/releases?per_page=3 | 2026-11-05 | bootstrap session | |
| S-004 | HAEO repository metadata (license field) | GitHub REST API | https://api.github.com/repos/hass-energy/haeo | 2026-11-05 | bootstrap session | `license.spdx_id` = MIT |
| S-005 | HAEO README (main branch) | hass-energy/haeo (GitHub) | https://github.com/hass-energy/haeo | 2026-11-05 | bootstrap session | Says HiGHS is used through "bundled `highspy` bindings". |
| S-006 | "Integration manifest" — §Requirements | Home Assistant Developer Docs | https://raw.githubusercontent.com/home-assistant/developers.home-assistant/master/docs/creating_integration_manifest.md | 2026-11-05 | bootstrap session | Published at https://developers.home-assistant.io/docs/creating_integration_manifest |

| S-007 | HAEO `const.py` (v0.5.0) | hass-energy/haeo (GitHub) | https://raw.githubusercontent.com/hass-energy/haeo/v0.5.0/custom_components/haeo/const.py | 2026-11-05 | e04 spike | `DOMAIN="haeo"`, `ELEMENT_TYPE_NETWORK="network"`, `CONF_INTEGRATION_TYPE="integration_type"`, `CONF_RECORD_FORECASTS="record_forecasts"`, `INTEGRATION_TYPE_HUB="hub"`. |
| S-008 | HAEO `core/const.py` (v0.5.0) | hass-energy/haeo (GitHub) | https://raw.githubusercontent.com/hass-energy/haeo/v0.5.0/custom_components/haeo/core/const.py | 2026-11-05 | e04 spike | Hub section keys `common`/`advanced`/`tiers`; `CONF_HORIZON="horizon"`, `CONF_HORIZON_PRESET="horizon_preset"`, `CONF_DEBOUNCE_SECONDS="debounce_seconds"`, `CONF_ADVANCED_MODE="advanced_mode"`, `CONF_RELAX_INFEASIBLE="relax_infeasible"`; `DEFAULT_DEBOUNCE_SECONDS=2`; presets `2_days/3_days/5_days/7_days`; default tier layout (1/5/30/60 min). |
| S-009 | HAEO `core/schema/elements/element_type.py` (v0.5.0) | hass-energy/haeo (GitHub) | https://raw.githubusercontent.com/hass-energy/haeo/v0.5.0/custom_components/haeo/core/schema/elements/element_type.py | 2026-11-05 | e04 spike | Complete `ElementType` enum: battery, battery_section, buffer, connection, deferrable_load, ev, grid, inverter, junction, load, node, solar, policy. |
| S-010 | HAEO `core/schema/entity_value.py` + `constant_value.py` (v0.5.0) | hass-energy/haeo (GitHub) | https://raw.githubusercontent.com/hass-energy/haeo/v0.5.0/custom_components/haeo/core/schema/entity_value.py | 2026-11-05 | e04 spike | Stored field values are tagged: `{"type": "entity", "value": [entity_id, ...]}` (optional `on_states`/`off_states`) or `{"type": "constant", "value": <float|bool>}`. |
| S-011 | HAEO `core/schema/horizon_value.py` + `flows/horizon.py` (v0.5.0) | hass-energy/haeo (GitHub) | https://raw.githubusercontent.com/hass-energy/haeo/v0.5.0/custom_components/haeo/flows/horizon.py | 2026-11-05 | e04 spike | Horizon is a tagged value, not a bare string: preset → `{"value": "5_days"}`, forecast sensor → `{"value": ["sensor.x"]}`; default `5_days`; a horizon entity must publish at least two increasing forecast times and must not come from the same hub. |
| S-012 | HAEO `flows/hub.py` (v0.5.0) | hass-energy/haeo (GitHub) | https://raw.githubusercontent.com/hass-energy/haeo/v0.5.0/custom_components/haeo/flows/hub.py | 2026-11-05 | e04 spike | Hub creation data is sectioned; elements/connections are **config subentries** of the hub entry (`subentry_type` = element type), created through `async_get_supported_subentry_types`; hub unique_id `haeo_hub_<name>`; a new hub also gets a `network` subentry and a switchboard `junction`. |
| S-013 | HAEO `flows/__init__.py` (v0.5.0) | hass-energy/haeo (GitHub) | https://raw.githubusercontent.com/hass-energy/haeo/v0.5.0/custom_components/haeo/flows/__init__.py | 2026-11-05 | e04 spike | Hub setup form carries only name + horizon (+ advanced_mode); `relax_infeasible` and `record_forecasts` appear in the hub **options** form's advanced section, default `False`. |
| S-014 | HAEO `core/data/forecast_times.py` (v0.5.0) | hass-energy/haeo (GitHub) | https://raw.githubusercontent.com/hass-energy/haeo/v0.5.0/custom_components/haeo/core/data/forecast_times.py | 2026-11-05 | e04 spike | A `forecast` attribute point names its boundary `time` (any other keys ignored); n+1 boundaries describe n periods; tz-less times are read in the HA time zone; fewer than two increasing times is an error. |
| S-015 | HAEO `core/schema/elements/__init__.py` (v0.5.0) | hass-energy/haeo (GitHub) | https://raw.githubusercontent.com/hass-energy/haeo/v0.5.0/custom_components/haeo/core/schema/elements/__init__.py | 2026-11-05 | e04 spike | Per-type `*ConfigSchema`/`*ConfigData` pairs; `ELEMENT_SURFACED_PRICE_HINTS` for battery and load ("policy pricing" fields on the element form); `ELEMENT_REFERENCE_MAPPERS` for buffer and policy. |
| S-016 | HAEO `core/adapters/registry.py` + `.agents/skills/elements/SKILL.md` (v0.5.0) | hass-energy/haeo (GitHub) | https://raw.githubusercontent.com/hass-energy/haeo/v0.5.0/.agents/skills/elements/SKILL.md | 2026-11-05 | e04 spike | `ELEMENT_TYPES` registry per type with `advanced`, `connectivity`, `can_source`, `can_sink`, `device_names`; element fields are `Annotated` with `SectionHints` (units, direction, time-series, defaults), e.g. grid `power_limits` → `CONF_MAX_POWER_SOURCE_TARGET`. |

## Sources to fetch (queued, NOT yet citable)

These are candidate primary sources. Do not cite them until they are fetched and given an S-ID above.

| Topic | Candidate URL | Needed by |
|-------|---------------|-----------|
| HAEO installation guide | https://haeo.io/latest/user-guide/installation/ | D02, OQ-001, OQ-010 |
| HA config entries and config flow | https://developers.home-assistant.io/docs/config_entries_config_flow_handler | D02, D04 |
| HA config subentries | https://developers.home-assistant.io/docs/config_entries_config_flow_handler (subentries section) | D04, OQ-009 |
| HA REST API | https://developers.home-assistant.io/docs/api/rest | D04, D08 |
| HA WebSocket API | https://developers.home-assistant.io/docs/api/websocket | D04, D08 |
| HA repairs / issue registry | https://developers.home-assistant.io/docs/core/platform/repairs | D02, D04 |
| HA Application Credentials | https://developers.home-assistant.io/docs/core/platform/application_credentials | D08 |
| HA integration quality scale | https://developers.home-assistant.io/docs/core/integration-quality-scale/ | D02 |
| HACS publish requirements | https://hacs.xyz/docs/publish/start | D02 |
| HACS integration requirements | https://hacs.xyz/docs/publish/integration | D02 |
| HA Core license | https://github.com/home-assistant/core/blob/dev/LICENSE.md | D02 |
| HA Supervisor license | https://github.com/home-assistant/supervisor/blob/main/LICENSE | D02 |
| CPUC / CEC / CAISO / IOU program pages | (per D10 item) | D10 |
| OpenADR Alliance certification | https://www.openadr.org/ | D10 |
