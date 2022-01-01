"""Config flow for the VZUG integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from vzug import BasicDevice

from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import DEVICE_TYPE_CONF, DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)

# This is the schema used to display the UI to the user.
DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """

    if len(data["host"]) < 3:
        raise InvalidHost

    dev = BasicDevice(data["host"])
    result = await dev.load_device_information()
    if not result:
        raise

    # TODO: Implement InvalidAuth exception handling
    # If the authentication is wrong:
    # InvalidAuth

    # It is stored internally in HA as part of the device config.
    return {"title": dev.device_name, DEVICE_TYPE_CONF: dev.device_type}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hello World."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                user_input[DEVICE_TYPE_CONF] = info[DEVICE_TYPE_CONF]
                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidHost:
                # Set the error on the `host` field, not the entire form.
                errors[CONF_HOST] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again.
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidHost(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid hostname."""
