"""The hx3 integration."""
from __future__ import annotations
import asyncio
from datetime import timedelta

from homeassistant.const import CONF_EMAIL, CONF_TOKEN, CONF_ACCESS_TOKEN, CONF_TTL
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.util import Throttle

from .hx3_api import api

from .const import _LOGGER, CONF_DEV_ID, CONF_LAST_REFRESH, CONF_LOC_ID, CONF_REFRESH_TOKEN, DOMAIN

UPDATE_LOOP_SLEEP_TIME = 5
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=300)
PLATFORMS = ["climate"]


async def async_setup_entry(hass, config):
    """Set up the Hx 3 thermostat."""
    email = config.data[CONF_EMAIL]
    token = config.data[CONF_TOKEN]
    access_token = config.data.get(CONF_ACCESS_TOKEN) or None
    refresh_token = config.data.get(CONF_REFRESH_TOKEN) or None
    ttl = config.data.get(CONF_TTL) or None
    last_refresh = config.data.get(CONF_LAST_REFRESH) or 0

    client = await hass.async_add_executor_job(
        get_hx3_client,
        email,
        token,
        access_token,
        refresh_token,
        ttl,
        last_refresh,
    )

    if client is None:
        return False

    loc_id = config.data.get(CONF_LOC_ID)
    dev_id = config.data.get(CONF_DEV_ID)

    controllers = []

    for location in client.locations_by_id.values():
        for device in location.controllers_by_id.values():
            if (not loc_id or location.id == loc_id) and (
                not dev_id or device.id == dev_id
            ):
                controllers.append(device)

    if not controllers:
        _LOGGER.debug("No devices found")
        return False

    data = Hx3Data(
        hass,
        config,
        client,
        controllers,
    )
    await data.async_update()
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config.entry_id] = data
    await hass.config_entries.async_forward_entry_setups(config, PLATFORMS)

    config.async_on_unload(config.add_update_listener(update_listener))

    return True


async def update_listener(hass, config) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(config.entry_id)


async def async_unload_entry(hass, config):
    """Unload the config config and platforms."""
    unload_ok = await hass.config_entries.async_unload_platforms(config, PLATFORMS)
    if unload_ok:
        hass.data.pop(DOMAIN)
    return unload_ok


def get_hx3_client(email: str, token: str, access_token: str = None, refresh_token: str = None, ttl: int = None, last_refresh: int = 0):
    """Initialize the hx3 client."""
    try:
        return api.Hx3Api(
            email,
            token=token,
            access_token=access_token,
            refresh_token=refresh_token,
            ttl=ttl,
            last_refresh=last_refresh,
        )
    except api.AuthError:
        _LOGGER.error("Failed to login to Hx 3 account %s", email)
        return None
    except api.HxError as ex:
        raise ConfigEntryNotReady(
            "Failed to initialize the Hx 3 client: "
            "Check your configuration (email, token), "
            "or maybe you have exceeded the API rate limit?"
        ) from ex


class Hx3Data:
    """Get the latest data and update."""

    def __init__(self, hass, config, client, controllers):
        """Initialize the data object."""
        self._hass = hass
        self._config = config
        self._client = client
        self.controllers = controllers

    async def _retry(self) -> bool:
        """Recreate a new hx client.

        When we get an error, the best way to be sure that the next query
        will succeed, is to recreate a new hx client.
        """
        client = self._client
        self._client = await self._hass.async_add_executor_job(
            get_hx3_client,
            client._email,
            client._token,
            client._access_token,
            client._refresh_token,
            client._ttl,
            client._last_refresh,
        )

        if self._client is None:
            return False

        controllers = [
            controller
            for location in self._client.locations_by_id.values()
            for controller in location.controllers_by_id.values()
        ]

        if not controllers:
            _LOGGER.error("Failed to find any controllers")
            return False

        self.controllers = controllers
        await self._hass.config_entries.async_reload(self._config.entry_id)
        return True

    async def _refresh_devices(self):
        """Refresh each enabled device."""
        for device in self.controllers:
            await self._hass.async_add_executor_job(device.refresh)
            await asyncio.sleep(UPDATE_LOOP_SLEEP_TIME)

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self) -> None:
        """Update the state."""
        retries = 3
        while retries > 0:
            try:
                await self._refresh_devices()
                client = self._client
                self._hass.config_entries.async_update_entry(
                    self._config,
                    data={
                        **self._config.data,
                        CONF_ACCESS_TOKEN: client._access_token,
                        CONF_REFRESH_TOKEN: client._refresh_token,
                        CONF_TTL: client._ttl,
                        CONF_LAST_REFRESH: client._last_refresh,
                    }
                )
                break
            except (
                api.APIRateLimited,
                api.ConnectionError,
                api.ConnectionTimeout,
                OSError,
            ) as exp:
                retries -= 1
                if retries == 0:
                    raise exp
                result = await self._retry()
                if not result:
                    raise exp
                _LOGGER.error("Hx 3 update failed, Retrying - Error: %s", exp)
