"""Home Assistant implementation of the bridge's flow port.

This is the only place that touches Home Assistant's flow managers for HAEO
provisioning. It is deliberately thin: every method is one call into a public
manager (``config_entries.flow``, ``config_entries.options``,
``config_entries.subentries``), which are the same managers the REST endpoints
and the UI use.

Verification status: the manager signatures were read from Home Assistant
2026.1.1 source and the developer docs (FACTS F-031..F-038), but this module has
not yet run against a live instance, so ``HA_PORT_LIVE_VERIFIED`` stays false and
the live contract test is the gate that flips it.

Threading model: every method is **synchronous** and blocks on a future scheduled
onto ``hass.loop``. That is deliberate. The bridge's driver is synchronous
(``apply_plan``), and Home Assistant must never have a blocking call inside its
event loop, so ``runtime.py`` runs the apply in an executor thread and the port
bridges back to the loop. Calling these methods from the event loop itself would
deadlock — the runtime's executor hop is what prevents that.
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER, ConfigEntry, SubentryFlowContext
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from . import contracts
from .flows import EntryRecord, SubentryRecord

#: Flipped only by the live contract test (tests/contract/ha/test_live_ha_port.py).
HA_PORT_LIVE_VERIFIED = False


def _record(entry: ConfigEntry) -> EntryRecord:
    subentries = tuple(
        SubentryRecord(
            subentry_id=subentry.subentry_id,
            subentry_type=subentry.subentry_type,
            title=subentry.title,
            data=dict(subentry.data),
        )
        for subentry in entry.subentries.values()
    )
    return EntryRecord(entry_id=entry.entry_id, title=entry.title, options=dict(entry.options), subentries=subentries)


class HomeAssistantFlowPort:
    """Drive HAEO's flows through ``hass``."""

    def __init__(self, hass: HomeAssistant, *, timeout: float = 60.0) -> None:
        self.hass = hass
        self.timeout = timeout

    def _call(self, coro: Coroutine[Any, Any, Any]) -> Any:
        """Run one manager coroutine on Home Assistant's loop and wait for it."""
        return asyncio.run_coroutine_threadsafe(coro, self.hass.loop).result(self.timeout)

    def haeo_version(self) -> str | None:
        if not self.hass.config_entries.async_entries(contracts.HAEO_DOMAIN):
            return None
        return self._call(self._haeo_version())

    async def _haeo_version(self) -> str | None:
        integration = await async_get_integration(self.hass, contracts.HAEO_DOMAIN)
        return integration.version

    def entries(self, domain: str) -> list[EntryRecord]:
        return [_record(entry) for entry in self.hass.config_entries.async_entries(domain)]

    def init_config_flow(self, handler: str) -> dict[str, Any]:
        return self._call(self.hass.config_entries.flow.async_init(handler, context={"source": SOURCE_USER}))

    def configure(self, flow_id: str, user_input: dict[str, Any]) -> dict[str, Any]:
        return self._call(self.hass.config_entries.flow.async_configure(flow_id, user_input=user_input))

    def init_options_flow(self, entry_id: str) -> dict[str, Any]:
        return self._call(self.hass.config_entries.options.async_init(entry_id))

    def configure_options(self, flow_id: str, user_input: dict[str, Any]) -> dict[str, Any]:
        return self._call(self.hass.config_entries.options.async_configure(flow_id, user_input=user_input))

    def init_subentry_flow(
        self,
        entry_id: str,
        subentry_type: str,
        *,
        subentry_id: str | None = None,
    ) -> dict[str, Any]:
        source = SOURCE_USER if subentry_id is None else SOURCE_RECONFIGURE
        context = SubentryFlowContext(source=source)
        if subentry_id is not None:
            context["subentry_id"] = subentry_id  # type: ignore[typeddict-unknown-key]
        return self._call(self.hass.config_entries.subentries.async_init((entry_id, subentry_type), context=context))

    def configure_subentry(self, flow_id: str, user_input: dict[str, Any]) -> dict[str, Any]:
        return self._call(self.hass.config_entries.subentries.async_configure(flow_id, user_input=user_input))

    def remove_subentry(self, entry_id: str, subentry_id: str) -> None:
        entry = self.hass.config_entries.async_get_entry(entry_id)
        if entry is None:
            return
        self.hass.config_entries.subentries.async_remove_subentry(entry, subentry_id)
