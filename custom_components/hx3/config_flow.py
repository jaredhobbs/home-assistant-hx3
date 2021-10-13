"""Config flow for hx3 integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_TOKEN, CONF_ACCESS_TOKEN, CONF_TTL
from homeassistant.data_entry_flow import FlowResult

from . import get_hx3_client
from .const import CONF_LAST_REFRESH, CONF_REFRESH_TOKEN, DOMAIN


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for hx3."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Create config entry. Show the setup form to the user."""
        errors = {}

        if user_input is not None:
            client = await self.hass.async_add_executor_job(
                get_hx3_client, user_input[CONF_EMAIL], user_input[CONF_TOKEN]
            )
            if client is not None:
                user_input[CONF_ACCESS_TOKEN] = client._access_token
                user_input[CONF_REFRESH_TOKEN] = client._refresh_token
                user_input[CONF_TTL] = client._ttl
                user_input[CONF_LAST_REFRESH] = client._last_refresh
                return self.async_create_entry(
                    title=DOMAIN,
                    data=user_input,
                )
            errors["base"] = "invalid_auth"

        schema = vol.Schema({
            vol.Required(CONF_EMAIL): str,
            vol.Required(CONF_TOKEN): str,
        })
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            last_step=True,
        )

    async def async_step_import(self, import_data):
        """Import entry from configuration.yaml."""
        return await self.async_step_user(
            {
                CONF_EMAIL: import_data[CONF_EMAIL],
                CONF_TOKEN: import_data[CONF_TOKEN],
            }
        )
