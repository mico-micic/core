"""Tests for Overkiz (by Somfy) config flow."""
from __future__ import annotations

from unittest.mock import Mock, patch

from aiohttp import ClientError
from pyoverkiz.exceptions import (
    BadCredentialsException,
    MaintenanceException,
    TooManyRequestsException,
)
import pytest

from homeassistant import config_entries, data_entry_flow
from homeassistant.components import dhcp
from homeassistant.components.overkiz.const import DOMAIN
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry

TEST_EMAIL = "test@testdomain.com"
TEST_EMAIL2 = "test@testdomain.nl"
TEST_PASSWORD = "test-password"
TEST_PASSWORD2 = "test-password2"
TEST_HUB = "somfy_europe"
TEST_HUB2 = "hi_kumo_europe"
TEST_GATEWAY_ID = "1234-5678-9123"
TEST_GATEWAY_ID2 = "4321-5678-9123"

MOCK_GATEWAY_RESPONSE = [Mock(id=TEST_GATEWAY_ID)]


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch("pyoverkiz.client.OverkizClient.login", return_value=True), patch(
        "pyoverkiz.client.OverkizClient.get_gateways", return_value=None
    ), patch(
        "homeassistant.components.overkiz.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": TEST_EMAIL, "password": TEST_PASSWORD, "hub": TEST_HUB},
        )

    assert result2["type"] == "create_entry"
    assert result2["title"] == TEST_EMAIL
    assert result2["data"] == {
        "username": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "hub": TEST_HUB,
    }

    await hass.async_block_till_done()

    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    "side_effect, error",
    [
        (BadCredentialsException, "invalid_auth"),
        (TooManyRequestsException, "too_many_requests"),
        (TimeoutError, "cannot_connect"),
        (ClientError, "cannot_connect"),
        (MaintenanceException, "server_in_maintenance"),
        (Exception, "unknown"),
    ],
)
async def test_form_invalid_auth(
    hass: HomeAssistant, side_effect: Exception, error: str
) -> None:
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("pyoverkiz.client.OverkizClient.login", side_effect=side_effect):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": TEST_EMAIL, "password": TEST_PASSWORD, "hub": TEST_HUB},
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": error}


async def test_abort_on_duplicate_entry(hass: HomeAssistant) -> None:
    """Test config flow aborts Config Flow on duplicate entries."""
    MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_GATEWAY_ID,
        data={"username": TEST_EMAIL, "password": TEST_PASSWORD, "hub": TEST_HUB},
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("pyoverkiz.client.OverkizClient.login", return_value=True), patch(
        "pyoverkiz.client.OverkizClient.get_gateways",
        return_value=MOCK_GATEWAY_RESPONSE,
    ), patch("homeassistant.components.overkiz.async_setup_entry", return_value=True):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": TEST_EMAIL, "password": TEST_PASSWORD},
        )

    assert result2["type"] == "abort"
    assert result2["reason"] == "already_configured"


async def test_allow_multiple_unique_entries(hass: HomeAssistant) -> None:
    """Test config flow allows Config Flow unique entries."""
    MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_GATEWAY_ID2,
        data={"username": "test2@testdomain.com", "password": TEST_PASSWORD},
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("pyoverkiz.client.OverkizClient.login", return_value=True), patch(
        "pyoverkiz.client.OverkizClient.get_gateways",
        return_value=MOCK_GATEWAY_RESPONSE,
    ), patch("homeassistant.components.overkiz.async_setup_entry", return_value=True):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": TEST_EMAIL, "password": TEST_PASSWORD, "hub": TEST_HUB},
        )

    assert result2["type"] == "create_entry"
    assert result2["title"] == TEST_EMAIL
    assert result2["data"] == {
        "username": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "hub": TEST_HUB,
    }


async def test_dhcp_flow(hass: HomeAssistant) -> None:
    """Test that DHCP discovery for new bridge works."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        data=dhcp.DhcpServiceInfo(
            hostname="gateway-1234-5678-9123",
            ip="192.168.1.4",
            macaddress="F8811A000000",
        ),
        context={"source": config_entries.SOURCE_DHCP},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == config_entries.SOURCE_USER


async def test_dhcp_flow_already_configured(hass: HomeAssistant) -> None:
    """Test that DHCP doesn't setup already configured gateways."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_GATEWAY_ID,
        data={"username": TEST_EMAIL, "password": TEST_PASSWORD, "hub": TEST_HUB},
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        data=dhcp.DhcpServiceInfo(
            hostname="gateway-1234-5678-9123",
            ip="192.168.1.4",
            macaddress="F8811A000000",
        ),
        context={"source": config_entries.SOURCE_DHCP},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "already_configured"
