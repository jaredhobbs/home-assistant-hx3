"""Support for Johnson Controls Hx 3 Thermostat humidification mode selects"""

from __future__ import annotations

from homeassistant.components.select import SelectEntity

from hx3 import api

from .const import DOMAIN

MODE_AUTO = "auto"
MODE_MANUAL = "manual"

MODE_TO_HW = {
    MODE_AUTO: api.HumidificationMode.AUTO,
    MODE_MANUAL: api.HumidificationMode.MANUAL,
}
HW_MODE_TO_HA = {v: k for k, v in MODE_TO_HW.items()}


async def async_setup_entry(hass, config, async_add_entities):
    """Set up the Hx 3 humidification/dehumidification mode selects."""
    data = hass.data[DOMAIN][config.entry_id]
    entities = []
    for controller in data.controllers:
        if controller.humidification:
            entities.append(Hx3HumidificationModeSelect(data, controller))
        if controller.dehumidification:
            entities.append(Hx3DehumidificationModeSelect(data, controller))
    async_add_entities(entities, True)


class Hx3HumidificationModeSelect(SelectEntity):
    """AUTO/MANUAL mode governing the humidify setpoint."""

    _attr_options = [MODE_AUTO, MODE_MANUAL]

    def __init__(self, data, controller):
        """Initialize the humidification mode select."""
        self._data = data
        self._controller = controller

        self._attr_unique_id = f"{controller.id}_humidification_mode"
        self._attr_name = f"{controller.name} Humidification Mode"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._controller.id)},
            "name": self._controller.name,
            "manufacturer": self._controller.brand,
            "model": self._controller.model,
            "sw_version": self._controller.version,
            "suggested_area": self._controller.location_name,
        }

    @property
    def available(self) -> bool:
        return self._data.is_available()

    @property
    def current_option(self) -> str | None:
        return HW_MODE_TO_HA.get(self._controller.humidification_mode)

    def select_option(self, option: str) -> None:
        """Set the humidification mode."""
        self._controller.humidification_mode = MODE_TO_HW[option]

    async def async_update(self):
        """Get the latest data from the service."""
        await self._data.async_update()


class Hx3DehumidificationModeSelect(SelectEntity):
    """AUTO/MANUAL mode governing the dehumidify setpoint."""

    _attr_options = [MODE_AUTO, MODE_MANUAL]

    def __init__(self, data, controller):
        """Initialize the dehumidification mode select."""
        self._data = data
        self._controller = controller

        self._attr_unique_id = f"{controller.id}_dehumidification_mode"
        self._attr_name = f"{controller.name} Dehumidification Mode"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._controller.id)},
            "name": self._controller.name,
            "manufacturer": self._controller.brand,
            "model": self._controller.model,
            "sw_version": self._controller.version,
            "suggested_area": self._controller.location_name,
        }

    @property
    def available(self) -> bool:
        return self._data.is_available()

    @property
    def current_option(self) -> str | None:
        return HW_MODE_TO_HA.get(self._controller.dehumidification_mode)

    def select_option(self, option: str) -> None:
        """Set the dehumidification mode."""
        self._controller.dehumidification_mode = MODE_TO_HW[option]

    async def async_update(self):
        """Get the latest data from the service."""
        await self._data.async_update()
