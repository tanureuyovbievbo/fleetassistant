"""Live HAEO contract tests (manual workflow only).

These require a running Home Assistant with HAEO installed at the pinned
version. They are skipped unless ``HAEO_VERSION`` is set (the
``haeo-contract.yml`` workflow sets it).

Everything asserted here is a fact we currently only believe. When an assertion
flips, the corresponding OQ is resolved and the code constant must change with
it — that is the whole point of pinning.
"""

from __future__ import annotations

import os

import pytest

from custom_components.fleetassistant.const import SUPPORTED_HAEO_VERSIONS

pytestmark = pytest.mark.live

HAEO_VERSION = os.environ.get("HAEO_VERSION", "")

requires_live = pytest.mark.skipif(not HAEO_VERSION, reason="live HAEO instance required (set HAEO_VERSION)")


@requires_live
def test_pinned_version_is_the_one_under_test() -> None:
    assert HAEO_VERSION in SUPPORTED_HAEO_VERSIONS


@requires_live
@pytest.mark.xfail(strict=True, reason="OQ-002: meter/thermostat/relay have no recorded HAEO element")
def test_element_type_names_are_verified() -> None:
    from custom_components.fleetassistant.haeo_bridge.plan import DEFAULT_TYPE_MAP, HaeoTypeMap

    type_map = HaeoTypeMap(types=dict(DEFAULT_TYPE_MAP), verified=True)
    assert None not in type_map.types.values()


@requires_live
@pytest.mark.xfail(strict=True, reason="OQ-006: hub record shape is source-verified, not live-verified")
def test_hub_record_shape_is_verified() -> None:
    """The hub must be created by the config-flow API and read back as here.

    Source-verified at v0.5.0 (``flows/hub.py``): creation data is sectioned and
    the horizon is a tagged value, and ``relax_infeasible`` lives in the hub's
    options rather than its creation data.
    """
    from custom_components.fleetassistant.haeo_bridge import contracts
    from custom_components.fleetassistant.haeo_bridge.plan import HubPlan

    plan = HubPlan(system_id="s", hub="h", horizon_mode="preset", preset_days=5)
    data = plan.config_data()
    assert set(data) == {contracts.CONF_INTEGRATION_TYPE, "common", "advanced"}
    assert data["common"][contracts.CONF_HORIZON] == {contracts.HORIZON_VALUE_KEY: "5_days"}
    assert plan.options_data()["advanced"][contracts.CONF_RELAX_INFEASIBLE] is True
    # what a live instance must show us
    assert contracts.HAEO_SURFACE_LIVE_VERIFIED is True


@requires_live
@pytest.mark.xfail(strict=True, reason="OQ-007: forecast payload shape is unverified")
def test_forecast_payload_shape_is_verified() -> None:
    from custom_components.fleetassistant.pricing.series import FORECAST_FORMAT_VERIFIED

    assert FORECAST_FORMAT_VERIFIED is True
