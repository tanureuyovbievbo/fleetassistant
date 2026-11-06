"""Forecast price sensors that HAEO reads (ADR-0019).

One entity per price input (import/export), published so the compiled plan's literal
entity references resolve to real state. Each carries the compiled series in a
``forecast`` attribute — the shape HAEO's horizon and price inputs consume (F-016)
— and the provenance of every period in its other attributes.

The entity id matters: the compiled plan references ``sensor.fleetassistant_<site>_
price_import`` literally, so the registry entry is created with that
``suggested_object_id`` instead of letting Home Assistant invent one and hoping the
two agree.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, NAME, PRICE_INPUTS, VERSION
from .pricing.compiler import price_entity_id
from .pricing.publisher import current_price, price_attributes

INPUT_LABELS = {"price_import": "Import price", "price_export": "Export price"}
PLATFORM = "sensor"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if runtime is None or not runtime.tariffs:
        return

    registry = er.async_get(hass)
    currency = str(runtime.profile.get("site", {}).get("currency") or "USD")
    entities: list[PriceSensor] = []
    for input_name in PRICE_INPUTS:
        tariff = runtime.tariffs.get(input_name)
        if tariff is None:
            continue
        desired = price_entity_id(runtime.site_id, input_name)
        unique_id = f"{entry.entry_id}_{input_name}"
        registry.async_get_or_create(
            PLATFORM,
            DOMAIN,
            unique_id,
            suggested_object_id=desired.removeprefix(f"{PLATFORM}."),
            config_entry=entry,
        )
        entities.append(
            PriceSensor(
                runtime=runtime,
                entry_id=entry.entry_id,
                input_name=input_name,
                unique_id=unique_id,
                currency=currency,
            )
        )
    async_add_entities(entities, update_before_add=True)


class PriceSensor(SensorEntity):
    """The merged price for one input, with provenance in the attributes."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_icon = "mdi:currency-usd"

    def __init__(
        self,
        *,
        runtime: Any,
        entry_id: str,
        input_name: str,
        unique_id: str,
        currency: str,
    ) -> None:
        self._runtime = runtime
        self._input_name = input_name
        self._attr_unique_id = unique_id
        self._attr_name = INPUT_LABELS.get(input_name, input_name)
        self._attr_native_unit_of_measurement = currency
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": NAME,
            "manufacturer": "fleetassistant",
            "model": runtime.profile.get("deployment", {}).get("profile", "unknown"),
            "sw_version": VERSION,
        }

    @property
    def _tariff(self) -> Any:
        return self._runtime.tariffs.get(self._input_name)

    @property
    def native_value(self) -> float | None:
        tariff = self._tariff
        if tariff is None:
            return None
        return current_price(tariff, dt_util.utcnow())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        tariff = self._tariff
        if tariff is None:
            return {}
        return price_attributes(tariff, now=dt_util.utcnow())

    @property
    def available(self) -> bool:
        tariff = self._tariff
        return tariff is not None and bool(tariff.points)
