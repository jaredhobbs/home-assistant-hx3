"""The hx3 integration."""
from __future__ import annotations
import asyncio
import time
from datetime import timedelta

from homeassistant.const import CONF_EMAIL, CONF_TOKEN, CONF_ACCESS_TOKEN, CONF_TTL
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.util import Throttle

from hx3 import api

from .const import _LOGGER, CONF_DEV_ID, CONF_LAST_REFRESH, CONF_LOC_ID, CONF_REFRESH_TOKEN, DOMAIN

UPDATE_LOOP_SLEEP_TIME = 5
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=300)
PLATFORMS = ["climate", "sensor", "switch", "number", "select"]

# Backoff schedule (seconds) between retries of a single update after a
# transient failure (e.g. the API returning 503). The current client/auth
# token is reused as-is for each retry -- transient failures are a server
# problem, not a token problem, so there's no need to rebuild the client.
TRANSIENT_RETRY_DELAYS = (30, 60, 120, 300)

# Extra time, beyond the normal MIN_TIME_BETWEEN_UPDATES cadence, that
# entities keep reporting their last-known state as available after a
# failed refresh, while retries continue in the background. HA marks an
# entity unavailable the moment its async_update() raises, which would
# otherwise happen on every single failed attempt (including ones a retry
# a few seconds later quietly fixes). Entities instead check
# Hx3Data.is_available(), so a brief blip doesn't surface as Unavailable
# unless refreshes have actually been failing for this long. This is
# added on top of MIN_TIME_BETWEEN_UPDATES (not a replacement for it) --
# a successful refresh is only ever attempted that often, so the grace
# window has to cover that normal gap too, not just the retry time.
AVAILABILITY_GRACE_PERIOD = MIN_TIME_BETWEEN_UPDATES.total_seconds() + 120


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
        raise ConfigEntryAuthFailed(
            "Failed to authenticate with the Hx Thermostat API; a new share "
            "code is required"
        )

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

    return True


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
        self._last_success = float("-inf")

    def is_available(self) -> bool:
        """Whether entities should still report available.

        True as long as a refresh has succeeded within the last
        AVAILABILITY_GRACE_PERIOD seconds, even if the most recent attempt
        failed and is currently being retried.
        """
        return time.monotonic() - self._last_success < AVAILABILITY_GRACE_PERIOD

    async def _refresh_devices(self):
        """Refresh each enabled device."""
        for device in self.controllers:
            await self._hass.async_add_executor_job(device.refresh)
            await asyncio.sleep(UPDATE_LOOP_SLEEP_TIME)

    def _persist_tokens(self) -> None:
        """Persist the client's (possibly rotated) tokens on the config entry.

        This is a plain data write for durability across restarts only --
        there's deliberately no update listener registered on this entry,
        because HA reloads a whole entry (tearing down and recreating every
        entity, briefly showing them all as Unavailable) whenever a
        listener-bearing entry's data actually changes. The token/ttl/
        last_refresh values only actually change when the hx3 client
        rotates the access token near TTL expiry (every few hours), which
        would otherwise reload the integration on that same cadence for no
        reason -- the new token still works fine in the existing client,
        nothing needs to be rebuilt.
        """
        client = self._client
        self._hass.config_entries.async_update_entry(
            self._config,
            data={
                **self._config.data,
                CONF_ACCESS_TOKEN: client._access_token,
                CONF_REFRESH_TOKEN: client._refresh_token,
                CONF_TTL: client._ttl,
                CONF_LAST_REFRESH: client._last_refresh,
            },
        )

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self) -> None:
        """Update the state.

        Transient failures (the API returning 503, connection drops, etc.)
        are retried on the existing client/token with a growing backoff,
        rather than tearing down and rebuilding the client -- the token is
        still fine, the server is just having a bad moment. If the token
        itself is no longer valid, retrying won't help, so we raise
        ConfigEntryAuthFailed instead, which prompts the user to
        reauthenticate (enter a new share code) without deleting and
        re-adding the integration.
        """
        for delay in (*TRANSIENT_RETRY_DELAYS, None):
            try:
                await self._refresh_devices()
            except api.AuthError as exp:
                raise ConfigEntryAuthFailed(
                    "Hx 3 authentication failed; a new share code is required"
                ) from exp
            except (
                api.APIError,
                api.ConnectionError,
                api.ConnectionTimeout,
                OSError,
            ) as exp:
                if delay is None:
                    raise exp
                _LOGGER.warning(
                    "Hx 3 update failed, retrying in %ss - Error: %s", delay, exp
                )
                await asyncio.sleep(delay)
            else:
                self._persist_tokens()
                self._last_success = time.monotonic()
                return
