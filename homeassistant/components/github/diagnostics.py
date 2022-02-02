"""Diagnostics support for the GitHub integration."""
from __future__ import annotations

from typing import Any

from aiogithubapi import GitHubAPI, GitHubException

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import (
    SERVER_SOFTWARE,
    async_get_clientsession,
)

from .const import CONF_ACCESS_TOKEN, DOMAIN
from .coordinator import DataUpdateCoordinators


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = {"options": {**config_entry.options}}
    client = GitHubAPI(
        token=config_entry.data[CONF_ACCESS_TOKEN],
        session=async_get_clientsession(hass),
        **{"client_name": SERVER_SOFTWARE},
    )

    try:
        rate_limit_response = await client.rate_limit()
    except GitHubException as err:
        data["rate_limit"] = {"error": str(err)}
    else:
        data["rate_limit"] = rate_limit_response.data.as_dict

    repositories: dict[str, DataUpdateCoordinators] = hass.data[DOMAIN]
    data["repositories"] = {}

    for repository, coordinators in repositories.items():
        info = coordinators["information"].data
        data["repositories"][repository] = info.as_dict if info else None

    return data
