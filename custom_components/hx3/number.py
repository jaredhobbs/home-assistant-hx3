"""Support for Johnson Controls Hx 3 Thermostat humidify/dehumidify setpoints"""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.const import PERCENTAGE

from hx3 import api

from .const import _LOGGER, DOMAIN


async def async_setup_entry(hass, config, async_add_entities):
    """Set up the Hx 3 humidify/dehumidify setpoints."""
    data = hass.data[DOMAIN][config.entry_id]
    entities = []
    for controller in data.controllers:
        if controller.humidification:
            entities.append(Hx3HumidifySetpoint(data, controller))
        if controller.dehumidification:
            entities.append(Hx3DehumidifySetpoint(data, controller))
    async_add_entities(entities, True)


class Hx3HumidifySetpoint(NumberEntity):
    """The target humidity to maintain when humidifying.

    HA's ClimateEntity only models a single target_humidity, which can't
    represent this and the independent dehumidify setpoint at the same
    time, so both are exposed as their own entities on the same device
    instead. Only meaningful while humidification_mode is MANUAL -- the
    official app hides this setpoint entirely while it's AUTO, which HA
    has no equivalent for at the entity level, so this goes unavailable
    instead.
    """

    _attr_device_class = NumberDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, data, controller):
        """Initialize the humidify setpoint."""
        self._data = data
        self._controller = controller

        self._attr_unique_id = f"{controller.id}_humidify_setpoint"
        self._attr_name = f"{controller.name} Humidify Setpoint"

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
        return (
            self._data.is_available()
            and self._controller.humidification_mode == api.HumidificationMode.MANUAL
        )

    @property
    def native_min_value(self) -> float:
        return round(self._controller.humidification["min"] * 100)

    @property
    def native_max_value(self) -> float:
        return round(self._controller.humidification["max"] * 100)

    @property
    def native_value(self) -> float | None:
        return round(self._controller.humidify_setpoint * 100)

    def set_native_value(self, value: float) -> None:
        """Set the humidify setpoint."""
        try:
            self._controller.humidify_setpoint = value / 100
        except api.HxError as err:
            _LOGGER.error("Invalid humidify setpoint %s: %s", value, err)

    async def async_update(self):
        """Get the latest data from the service."""
        await self._data.async_update()


class Hx3DehumidifySetpoint(NumberEntity):
    """The target humidity to maintain when dehumidifying.

    Only meaningful while dehumidification_mode is MANUAL -- see
    Hx3HumidifySetpoint's docstring for why this goes unavailable in
    AUTO rather than disappearing the way the official app's field does.
    """

    _attr_device_class = NumberDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, data, controller):
        """Initialize the dehumidify setpoint."""
        self._data = data
        self._controller = controller

        self._attr_unique_id = f"{controller.id}_dehumidify_setpoint"
        self._attr_name = f"{controller.name} Dehumidify Setpoint"

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
        return (
            self._data.is_available()
            and self._controller.dehumidification_mode == api.HumidificationMode.MANUAL
        )

    @property
    def native_min_value(self) -> float:
        return round(self._controller.dehumidification["min"] * 100)

    @property
    def native_max_value(self) -> float:
        return round(self._controller.dehumidification["max"] * 100)

    @property
    def native_value(self) -> float | None:
        return round(self._controller.dehumidify_setpoint * 100)

    def set_native_value(self, value: float) -> None:
        """Set the dehumidify setpoint."""
        try:
            self._controller.dehumidify_setpoint = value / 100
        except api.HxError as err:
            _LOGGER.error("Invalid dehumidify setpoint %s: %s", value, err)

    async def async_update(self):
        """Get the latest data from the service."""
        await self._data.async_update()
