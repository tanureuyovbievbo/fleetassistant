"""fleetassistant — Home Assistant custom integration.

HAEO is the site optimizer (compose, never fork: C-04). This integration only
*configures* HAEO through Home Assistant's config-flow API (C-06, C-07).

Import order matters: this module MUST NOT import Home Assistant at module
level, so the pure-Python core stays importable in tests without HA installed.
HA imports are deferred into the setup functions (see tests/test_package_hygiene.py).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .const import DOMAIN, NAME, VERSION

if TYPE_CHECKING:  # pragma: no cover - typing only
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

__version__ = VERSION

__all__ = [
    "DOMAIN",
    "NAME",
    "VERSION",
    "__version__",
    "async_setup",
    "async_setup_entry",
    "async_unload_entry",
]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration (YAML import is not supported: C-05)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one site from a config entry.

    Kept thin: real wiring lives in ``runtime.py`` so that this module stays
    importable without Home Assistant.
    """
    from .runtime import async_setup_entry as _setup

    return await _setup(hass, entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .runtime import async_unload_entry as _unload

    return await _unload(hass, entry)
