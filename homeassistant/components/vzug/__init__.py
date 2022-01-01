"""The VZUG integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import DEVICE_TYPE_CONF, DOMAIN
from .vzug_poller import VZugPoller

# List of platforms to support. There should be a matching .py file for each
PLATFORMS: list[str] = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Create device poller for every VZUG device."""

    hostname = entry.data[CONF_HOST]
    username = entry.data.get(CONF_USERNAME, "")
    password = entry.data.get(CONF_PASSWORD, "")
    dev_type = entry.data.get(DEVICE_TYPE_CONF, "")

    vzug_updater = VZugPoller(hostname, username, password, dev_type)

    # Run first poll
    await vzug_updater.async_poll()

    # Store an instance of the poller so that it can be used by the sensors
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = vzug_updater

    # This creates each HA object for each platform and calls the async_setup_entry function in sensors.py
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Stop polling and unload poller."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
