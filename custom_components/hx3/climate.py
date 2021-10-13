"""Support for Johnson Controls Hx 3 Thermostat"""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateEntity
from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    FAN_AUTO,
    FAN_ON,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    PRESET_AWAY,
    PRESET_NONE,
    SUPPORT_AUX_HEAT,
    SUPPORT_FAN_MODE,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_HUMIDITY,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_TARGET_TEMPERATURE_RANGE,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_PASSWORD,
    CONF_REGION,
    CONF_USERNAME,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)
import homeassistant.helpers.config_validation as cv

from hx3 import api

from .const import (
    _LOGGER,
    CONF_DEV_ID,
    CONF_LOC_ID,
    DOMAIN,
)

ATTR_FAN_ACTIVE = "fan_active"
ATTR_OUTDOOR_TEMPERATURE = "outdoor_temperature"

PLATFORM_SCHEMA = vol.All(
    cv.deprecated(CONF_REGION),
    PLATFORM_SCHEMA.extend(
        {
            vol.Required(CONF_USERNAME): cv.string,
            vol.Required(CONF_PASSWORD): cv.string,
            vol.Optional(CONF_DEV_ID): cv.string,
            vol.Optional(CONF_LOC_ID): cv.string,
        }
    ),
)

HVAC_MODE_TO_HW_MODE = {
    HVAC_MODE_OFF: api.Mode.OFF,
    HVAC_MODE_HEAT_COOL: api.Mode.AUTO,
    HVAC_MODE_COOL: api.Mode.COOL,
    HVAC_MODE_HEAT: api.Mode.HEAT,
}
HW_MODE_TO_HVAC_MODE = {
    api.Mode.OFF: HVAC_MODE_OFF,
    api.Mode.EHEAT: HVAC_MODE_HEAT,
    api.Mode.HEAT: HVAC_MODE_HEAT,
    api.Mode.COOL: HVAC_MODE_COOL,
    api.Mode.AUTO: HVAC_MODE_HEAT_COOL,
    api.Mode.MAXHEAT: HVAC_MODE_HEAT,
    api.Mode.MAXCOOL: HVAC_MODE_COOL,
}
HW_MODE_TO_HA_HVAC_ACTION = {
    api.ActiveDemand.OFF: CURRENT_HVAC_IDLE,
    api.ActiveDemand.HEAT: CURRENT_HVAC_HEAT,
    api.ActiveDemand.COOL: CURRENT_HVAC_COOL,
}
FAN_MODE_TO_HW = {
    FAN_ON: api.FanMode.ALWAYS,
    FAN_AUTO: api.FanMode.AUTO,
}
HW_FAN_MODE_TO_HA = {
    api.FanMode.ALWAYS: FAN_ON,
    api.FanMode.AUTO: FAN_AUTO,
    api.FanMode.FIFTEEN: FAN_AUTO,
    api.FanMode.THIRTY: FAN_AUTO,
    api.FanMode.FORTYFIVE: FAN_AUTO,
}


async def async_setup_entry(hass, config, async_add_entities):
    """Set up the Hx 3 thermostat."""
    data = hass.data[DOMAIN][config.entry_id]
    async_add_entities(
        [Hx3Thermostat(data, controller) for controller in data.controllers],
        True,
    )


class Hx3Thermostat(ClimateEntity):
    """Representation of a Johnson Controls Hx 3 Thermostat"""

    def __init__(self, data, controller):
        """Initialize the thermostat."""
        self._data = data
        self._controller = controller

        self._attr_unique_id = controller.id
        self._attr_name = controller.name
        self._attr_temperature_unit = (
            TEMP_CELSIUS if controller.temperature_unit == "C" else TEMP_FAHRENHEIT
        )
        self._attr_preset_modes = [PRESET_NONE, PRESET_AWAY]

        self._attr_hvac_modes = list(
            {
                HW_MODE_TO_HVAC_MODE[mode]
                for mode in controller.system_modes
                if mode in HW_MODE_TO_HVAC_MODE
            }
        )

        self._attr_supported_features = (
            SUPPORT_PRESET_MODE
            | SUPPORT_TARGET_TEMPERATURE
            | SUPPORT_TARGET_TEMPERATURE_RANGE
        )

        if controller.humidification:
            self._attr_supported_features |= SUPPORT_TARGET_HUMIDITY

        if api.Mode.EHEAT in controller.system_modes:
            self._attr_supported_features |= SUPPORT_AUX_HEAT

        if not controller._data["fan"]:
            return

        self._attr_fan_modes = list(
            {
                HW_FAN_MODE_TO_HA[mode]
                for mode in controller.fan_modes
                if mode in HW_FAN_MODE_TO_HA
            }
        )
        self._attr_supported_features |= SUPPORT_FAN_MODE

    @property
    def device_info(self):
        return {
            "identifiers": {
                (DOMAIN, self.unique_id)
            },
            "name": self.name,
            "manufacturer": self._controller.brand,
            "model": self._controller.model,
            "sw_version": self._controller.version,
            "suggested_area": self._controller.location_name,
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device specific state attributes."""
        data = {
            ATTR_FAN_ACTIVE: self._controller.fan_running,
            ATTR_OUTDOOR_TEMPERATURE: self._controller.outdoor_temperature,
        }
        return data

    @property
    def away(self):
        return self._controller.away

    @property
    def is_aux_heat(self) -> bool:
        return self._controller.system_mode == api.Mode.EHEAT

    @property
    def min_temp(self) -> float | None:
        """Return the minimum temperature."""
        if self.hvac_mode in [HVAC_MODE_COOL, HVAC_MODE_HEAT_COOL]:
            return self._controller._data["coolRange"]["min"]
        if self.hvac_mode == HVAC_MODE_HEAT:
            return self._controller._data["heatRange"]["min"]
        return None

    @property
    def max_temp(self) -> float | None:
        """Return the maximum temperature."""
        if self.hvac_mode == HVAC_MODE_COOL:
            return self._controller._data["coolRange"]["max"]
        if self.hvac_mode in [HVAC_MODE_HEAT, HVAC_MODE_HEAT_COOL]:
            return self._controller._data["heatRange"]["max"]
        return None

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        return self._controller.current_humidity

    @property
    def min_humidity(self) -> int:
        return self._controller.humidification["min"]

    @property
    def max_humidity(self) -> int:
        return self._controller.humidification["max"]

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode."""
        return HW_MODE_TO_HVAC_MODE[self._controller.system_mode]

    @property
    def hvac_action(self) -> str | None:
        """Return the current running hvac operation if supported."""
        if self.hvac_mode == HVAC_MODE_OFF:
            return None
        return HW_MODE_TO_HA_HVAC_ACTION[self._controller.active_demand]

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._controller.current_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        if self.hvac_mode == HVAC_MODE_COOL:
            return self._controller.setpoint_cool
        if self.hvac_mode == HVAC_MODE_HEAT:
            return self._controller.setpoint_heat
        return None

    @property
    def target_temperature_high(self) -> float | None:
        """Return the highbound target temperature we try to reach."""
        if self.hvac_mode == HVAC_MODE_HEAT_COOL:
            return self._controller.setpoint_cool
        return None

    @property
    def target_temperature_low(self) -> float | None:
        """Return the lowbound target temperature we try to reach."""
        if self.hvac_mode == HVAC_MODE_HEAT_COOL:
            return self._controller.setpoint_heat
        return None

    @property
    def preset_mode(self) -> str:
        """Return the current preset mode, e.g., home, away, temp."""
        return PRESET_AWAY if self.away else PRESET_NONE

    @property
    def fan_mode(self) -> str:
        """Return the fan setting."""
        return HW_FAN_MODE_TO_HA[self._controller.fan_mode]

    def _set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        try:
            # Get current mode
            mode = self._controller.system_mode.lower()
            # Set temperature
            setattr(self._controller, f"setpoint_{mode}", temperature)
        except api.HxError:
            _LOGGER.error("Temperature %.1f out of range", temperature)

    def set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if {HVAC_MODE_COOL, HVAC_MODE_HEAT} & set(self._attr_hvac_modes):
            self._set_temperature(**kwargs)

        temperature = None
        try:
            if HVAC_MODE_HEAT_COOL in self._attr_hvac_modes:
                temperature = kwargs.get(ATTR_TARGET_TEMP_HIGH)
                if temperature:
                    self._controller.setpoint_cool = temperature
                temperature = kwargs.get(ATTR_TARGET_TEMP_LOW)
                if temperature:
                    self._controller.setpoint_heat = temperature
        except api.HxError as err:
            _LOGGER.error("Invalid temperature %s: %s", temperature, err)

    def set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        self._controller.fan_mode = FAN_MODE_TO_HW[fan_mode]

    def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        self._controller.system_mode = HVAC_MODE_TO_HW_MODE[hvac_mode]

    def set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        self._controller.away = preset_mode == PRESET_AWAY

    def turn_aux_heat_on(self) -> None:
        """Turn auxiliary heater on."""
        self._controller.system_mode = api.Mode.EHEAT

    def turn_aux_heat_off(self) -> None:
        """Turn auxiliary heater off."""
        if HVAC_MODE_HEAT in self.hvac_modes:
            self.set_hvac_mode(HVAC_MODE_HEAT)
        else:
            self.set_hvac_mode(HVAC_MODE_OFF)

    async def async_update(self):
        """Get the latest state from the service."""
        await self._data.async_update()
