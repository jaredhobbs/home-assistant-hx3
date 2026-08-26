"""Support for Johnson Controls Hx 3 Thermostat emergency heat switch"""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity

from hx3 import api

from .const import DOMAIN


async def async_setup_entry(hass, config, async_add_entities):
    """Set up the Hx 3 emergency heat switch."""
    data = hass.data[DOMAIN][config.entry_id]
    async_add_entities(
        [
            Hx3EmergencyHeatSwitch(data, controller)
            for controller in data.controllers
            if api.Mode.EHEAT in controller.system_modes
        ],
        True,
    )


class Hx3EmergencyHeatSwitch(SwitchEntity):
    """Switch to force emergency (aux) heat.

    Home Assistant removed aux-heat support from the climate entity model
    (ClimateEntityFeature.AUX_HEAT / is_aux_heat / turn_aux_heat_on/off),
    and HVACMode has no distinct "emergency heat" member, so EHEAT can
    never appear as its own entry in the thermostat card's mode dropdown
    -- it only ever shows as HEAT there. This switch, on the same device,
    is HA's recommended replacement for making emergency heat controllable.
    """

    _attr_icon = "mdi:heat-wave"

    def __init__(self, data, controller):
        """Initialize the emergency heat switch."""
        self._data = data
        self._controller = controller

        self._attr_unique_id = f"{controller.id}_emergency_heat"
        self._attr_name = f"{controller.name} Emergency Heat"

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
    def is_on(self) -> bool:
        """Return True if emergency heat is currently active."""
        return self._controller.system_mode == api.Mode.EHEAT

    def turn_on(self, **kwargs) -> None:
        """Turn emergency heat on."""
        self._controller.system_mode = api.Mode.EHEAT

    def turn_off(self, **kwargs) -> None:
        """Turn emergency heat off, falling back to normal heat if available."""
        if api.Mode.HEAT in self._controller.system_modes:
            self._controller.system_mode = api.Mode.HEAT
        else:
            self._controller.system_mode = api.Mode.OFF

    async def async_update(self):
        """Get the latest data from the service."""
        await self._data.async_update()
