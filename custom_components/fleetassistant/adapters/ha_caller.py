"""Home Assistant glue for the service-call seam (C-09).

``adapters/ha_services.py`` turns capabilities into service calls but must stay
importable without Home Assistant, so the call itself is injected. This module is
the one place that knows how to make a *blocking* call from an adapter thread: it
hands the coroutine to the event loop and waits, because adapters run inside the
executor where blocking is allowed (and is the only thing that works).

Keeping it inside ``adapters/`` is deliberate: the constraint probe forbids
``services.async_call`` outside the adapter layer, so the knowledge of *how* a
device is driven — including "through HA services" — never leaks upward.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from homeassistant.core import HomeAssistant

from .ha_services import ServiceCaller

DEFAULT_TIMEOUT_SECONDS = 30.0


def service_caller(hass: HomeAssistant, *, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> ServiceCaller:
    """Return a caller that blocks the calling (executor) thread until HA answers."""

    def call(domain: str, service: str, data: Mapping[str, Any]) -> Any:
        future = asyncio.run_coroutine_threadsafe(
            hass.services.async_call(domain, service, dict(data), blocking=True), hass.loop
        )
        return future.result(timeout=timeout)

    return call
