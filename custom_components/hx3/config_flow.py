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

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle reauthentication, e.g. after the stored token is rejected."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Prompt for a fresh share code and apply it to the existing entry."""
        errors = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            client = await self.hass.async_add_executor_job(
                get_hx3_client, reauth_entry.data[CONF_EMAIL], user_input[CONF_TOKEN]
            )
            if client is not None:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={
                        CONF_TOKEN: user_input[CONF_TOKEN],
                        CONF_ACCESS_TOKEN: client._access_token,
                        CONF_REFRESH_TOKEN: client._refresh_token,
                        CONF_TTL: client._ttl,
                        CONF_LAST_REFRESH: client._last_refresh,
                    },
                )
            errors["base"] = "invalid_auth"

        schema = vol.Schema({vol.Required(CONF_TOKEN): str})
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={"email": reauth_entry.data[CONF_EMAIL]},
        )
