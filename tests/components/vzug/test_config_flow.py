"""Test the V-ZUG config flow."""

from unittest.mock import patch

from vzug import DEVICE_TYPE_WASHING_MACHINE

from homeassistant import config_entries
from homeassistant.components.vzug.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import RESULT_TYPE_CREATE_ENTRY, RESULT_TYPE_FORM

from .device_mocks import (
    MockDeviceAuthProblem,
    MockDeviceConnectionProblem,
    MockWashingMachine,
)

DEVICE_MOCK_PATH = "homeassistant.components.vzug.config_flow.BasicDevice"

DEFAULT_USER_INPUT = {
    "host": "1.1.1.1",
    "username": "test-username",
    "password": "test-password",
}


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""

    init_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert init_result["type"] == RESULT_TYPE_FORM
    assert bool(init_result["errors"]) is False

    with patch(DEVICE_MOCK_PATH, return_value=MockWashingMachine()) as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            init_result["flow_id"], DEFAULT_USER_INPUT
        )
        await hass.async_block_till_done()

    assert len(mock_setup_entry.mock_calls) == 1
    assert result["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == "MockDevice Name"
    assert result["data"] == {
        "host": "1.1.1.1",
        "username": "test-username",
        "password": "test-password",
        "vzug.device_type": DEVICE_TYPE_WASHING_MACHINE,
    }


async def test_form_invalid_auth(hass: HomeAssistant) -> None:
    """Test we handle invalid auth."""

    init_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        DEVICE_MOCK_PATH,
        return_value=MockDeviceAuthProblem(),
    ):
        result = await hass.config_entries.flow.async_configure(
            init_result["flow_id"],
            DEFAULT_USER_INPUT,
        )

    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""

    init_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        DEVICE_MOCK_PATH,
        return_value=MockDeviceConnectionProblem(),
    ):
        result = await hass.config_entries.flow.async_configure(
            init_result["flow_id"],
            DEFAULT_USER_INPUT,
        )

    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_invalid_host(hass: HomeAssistant) -> None:
    """Test we handle invalid host error."""

    init_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        DEVICE_MOCK_PATH,
        return_value=MockDeviceConnectionProblem(),
    ):
        result = await hass.config_entries.flow.async_configure(
            init_result["flow_id"],
            {"host": "e"},
        )

    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] == {"host": "cannot_connect"}
