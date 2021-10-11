"""Config flow for hx3 integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_TOKEN
from homeassistant.data_entry_flow import FlowResult

from . import get_hx3_client
from .const import DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_TOKEN): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for hx3."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Create config entry. Show the setup form to the user."""
        errors = {}

        if user_input is not None:
            valid = await self.is_valid(**user_input)
            if valid:
                return self.async_create_entry(
                    title=DOMAIN,
                    data=user_input,
                )
            errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def is_valid(self, **kwargs) -> bool:
        """Check if login credentials are valid."""
        client = await self.hass.async_add_executor_job(
            get_hx3_client, kwargs[CONF_EMAIL], kwargs[CONF_TOKEN]
        )

        return client is not None

    async def async_step_import(self, import_data):
        """Import entry from configuration.yaml."""
        return await self.async_step_user(
            {
                CONF_EMAIL: import_data[CONF_EMAIL],
                CONF_TOKEN: import_data[CONF_TOKEN],
            }
        )
