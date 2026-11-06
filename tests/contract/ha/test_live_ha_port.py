"""Live contract tests for the Home Assistant flow port.

These run only inside a real Home Assistant test runtime with HAEO installed
(``pytest -m live``), which is what the ``haeo-contract`` workflow provisions.
Until they pass, ``HA_PORT_LIVE_VERIFIED`` stays false and the bridge refuses to
apply a plan that needs connections.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.live

try:  # pragma: no cover - exercised only in the live matrix
    from homeassistant.core import HomeAssistant  # type: ignore[import-not-found]

    HAVE_HA = True
except ImportError:  # pragma: no cover
    HomeAssistant = object  # type: ignore[assignment,misc]
    HAVE_HA = False

requires_ha = pytest.mark.skipif(not HAVE_HA, reason="Home Assistant is not installed")


@requires_ha
@pytest.mark.xfail(strict=True, reason="OQ-016: the flow port has not run against a live instance")
async def test_port_reads_a_live_haeo_hub(hass: HomeAssistant) -> None:
    from custom_components.fleetassistant.const import SUPPORTED_HAEO_VERSIONS
    from custom_components.fleetassistant.haeo_bridge import contracts
    from custom_components.fleetassistant.haeo_bridge.ha_port import HomeAssistantFlowPort

    port = HomeAssistantFlowPort(hass)
    entries = await port.entries(contracts.HAEO_DOMAIN)
    assert entries is not None
    version = await port.haeo_version()
    assert version in SUPPORTED_HAEO_VERSIONS


@requires_ha
@pytest.mark.xfail(strict=True, reason="OQ-016: subentry creation through the port is unverified")
async def test_port_creates_an_element_subentry(hass: HomeAssistant) -> None:
    from custom_components.fleetassistant.haeo_bridge.flows import interpret
    from custom_components.fleetassistant.haeo_bridge.ha_port import HomeAssistantFlowPort

    port = HomeAssistantFlowPort(hass)
    entries = await port.entries("haeo")
    assert entries, "a HAEO hub must exist in the live instance"
    step = interpret(await port.init_subentry_flow(entries[0].entry_id, "grid"))
    assert step.kind == "form"


@requires_ha
@pytest.mark.xfail(strict=True, reason="the port stays unverified until the two tests above pass")
async def test_port_is_marked_verified(hass: HomeAssistant) -> None:
    from custom_components.fleetassistant.haeo_bridge import ha_port

    assert ha_port.HA_PORT_LIVE_VERIFIED is True
