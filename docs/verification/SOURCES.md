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

## Sources to fetch (queued, NOT yet citable)

These are candidate primary sources. Do not cite them until they are fetched and given an S-ID above.

| Topic | Candidate URL | Needed by |
|-------|---------------|-----------|
| HAEO installation guide | https://haeo.io/latest/user-guide/installation/ | D02, OQ-001, OQ-010 |
| HAEO hub / elements / connections docs | https://haeo.io/latest/ | D01, D04 |
| HAEO config-flow source at pinned tag | https://github.com/hass-energy/haeo/tree/v0.5.0/custom_components/haeo | D04 |
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
