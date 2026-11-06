"""Config flow and options flow (C-05).

Config flow creates the config entry (one per site/tenant). Options flow edits
the site profile and the HAEO hub options. Import/validation errors surface as
repair issues raised by ``runtime.py`` — never as a silent failure.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_APPLY_HAEO_PLAN,
    CONF_PRICE_AUTHORITY,
    DEFAULT_APPLY_HAEO_PLAN,
    DEFAULT_RELAX_IMPOSSIBLE_PLANS,
    DOMAIN,
    NAME,
)
from .pricing.sources import AUTHORITIES
from .profile.schema import DEPLOYMENT_PROFILES, validate_profile
from .site import default_profile

DEFAULT_PRESET_DAYS = 5


class FleetassistantConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create one config entry per site."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            site_id = str(user_input["site_id"]).strip().lower().replace(" ", "_").replace("-", "_")
            await self.async_set_unique_id(site_id)
            self._abort_if_unique_id_configured()

            profile = default_profile(site_id, str(user_input["site_name"]).strip(), str(user_input["deployment_profile"]))
            issues = [i for i in validate_profile(profile) if i.is_error]
            if issues:
                errors["base"] = "invalid_profile"

            if not errors:
                return self.async_create_entry(
                    title=f"{NAME}: {user_input['site_name']}",
                    data={"profile": profile},
                    options={
                        "relax_impossible_plans": DEFAULT_RELAX_IMPOSSIBLE_PLANS,
                        "preset_days": DEFAULT_PRESET_DAYS,
                        CONF_APPLY_HAEO_PLAN: DEFAULT_APPLY_HAEO_PLAN,
                        "profile_json": "",
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("site_name"): str,
                    vol.Required("site_id"): str,
                    vol.Required("deployment_profile", default="cloud_primary"): vol.In(DEPLOYMENT_PROFILES),
                }
            ),
            errors=errors,
            description_placeholders={
                "docs": "https://github.com/tanureuyovbievbo/fleetassistant/blob/main/README.md",
            },
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> FleetassistantOptionsFlow:
        return FleetassistantOptionsFlow(config_entry)


class FleetassistantOptionsFlow(OptionsFlow):
    """Edit the site profile and HAEO hub options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        current = dict(self._entry.options)
        if user_input is not None:
            profile_json = str(user_input.get("profile_json") or "").strip()
            if profile_json:
                import json

                try:
                    candidate = json.loads(profile_json)
                except json.JSONDecodeError:
                    errors["base"] = "invalid_json"
                else:
                    if any(i.is_error for i in validate_profile(candidate)):
                        errors["base"] = "invalid_profile"
            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        "relax_impossible_plans": bool(user_input["relax_impossible_plans"]),
                        "preset_days": int(user_input["preset_days"]),
                        CONF_APPLY_HAEO_PLAN: bool(user_input.get(CONF_APPLY_HAEO_PLAN, DEFAULT_APPLY_HAEO_PLAN)),
                        CONF_PRICE_AUTHORITY: str(user_input.get(CONF_PRICE_AUTHORITY) or "").strip(),
                        "profile_json": str(user_input.get("profile_json") or ""),
                    },
                )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "relax_impossible_plans",
                        default=current.get("relax_impossible_plans", DEFAULT_RELAX_IMPOSSIBLE_PLANS),
                    ): bool,
                    vol.Required("preset_days", default=current.get("preset_days", DEFAULT_PRESET_DAYS)): vol.In(
                        [2, 3, 5, 7]
                    ),
                    vol.Required(
                        CONF_APPLY_HAEO_PLAN,
                        default=current.get(CONF_APPLY_HAEO_PLAN, DEFAULT_APPLY_HAEO_PLAN),
                    ): bool,
                    vol.Optional(
                        CONF_PRICE_AUTHORITY, default=current.get(CONF_PRICE_AUTHORITY, "")
                    ): vol.In(["", *AUTHORITIES]),
                    vol.Optional("profile_json", default=current.get("profile_json", "")): str,
                }
            ),
            errors=errors,
        )
