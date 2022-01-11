"""Tests for RTSPtoWebRTC inititalization."""

from __future__ import annotations

import base64
from typing import Any, AsyncGenerator, Awaitable, Callable
from unittest.mock import patch

import aiohttp
import pytest
import rtsp_to_webrtc

from homeassistant.components import camera
from homeassistant.components.rtsp_to_webrtc import DOMAIN
from homeassistant.components.websocket_api.const import TYPE_RESULT
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker

STREAM_SOURCE = "rtsp://example.com"
# The webrtc component does not inspect the details of the offer and answer,
# and is only a pass through.
OFFER_SDP = "v=0\r\no=carol 28908764872 28908764872 IN IP4 100.3.6.6\r\n..."
ANSWER_SDP = "v=0\r\no=bob 2890844730 2890844730 IN IP4 host.example.com\r\n..."

SERVER_URL = "http://127.0.0.1:8083"

CONFIG_ENTRY_DATA = {"server_url": SERVER_URL}


@pytest.fixture(autouse=True)
async def webrtc_server() -> None:
    """Patch client library to force usage of RTSPtoWebRTC server."""
    with patch(
        "rtsp_to_webrtc.client.WebClient.heartbeat",
        side_effect=rtsp_to_webrtc.exceptions.ResponseError(),
    ):
        yield


@pytest.fixture
async def mock_camera(hass) -> AsyncGenerator[None, None]:
    """Initialize a demo camera platform."""
    assert await async_setup_component(
        hass, "camera", {camera.DOMAIN: {"platform": "demo"}}
    )
    await hass.async_block_till_done()
    with patch(
        "homeassistant.components.demo.camera.Path.read_bytes",
        return_value=b"Test",
    ), patch(
        "homeassistant.components.camera.Camera.stream_source",
        return_value=STREAM_SOURCE,
    ), patch(
        "homeassistant.components.camera.Camera.supported_features",
        return_value=camera.SUPPORT_STREAM,
    ):
        yield


async def async_setup_rtsp_to_webrtc(hass: HomeAssistant) -> None:
    """Set up the component."""
    return await async_setup_component(hass, DOMAIN, {})


async def test_setup_success(hass: HomeAssistant) -> None:
    """Test successful setup and unload."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=CONFIG_ENTRY_DATA)
    config_entry.add_to_hass(hass)

    with patch("rtsp_to_webrtc.client.Client.heartbeat"):
        assert await async_setup_rtsp_to_webrtc(hass)
        await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.data.get(DOMAIN)
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_invalid_config_entry(hass: HomeAssistant) -> None:
    """Test a config entry with missing required fields."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={})
    config_entry.add_to_hass(hass)

    assert await async_setup_rtsp_to_webrtc(hass)

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].state is ConfigEntryState.SETUP_ERROR


async def test_setup_server_failure(hass: HomeAssistant) -> None:
    """Test server responds with a failure on startup."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=CONFIG_ENTRY_DATA)
    config_entry.add_to_hass(hass)

    with patch(
        "rtsp_to_webrtc.client.Client.heartbeat",
        side_effect=rtsp_to_webrtc.exceptions.ResponseError(),
    ):
        assert await async_setup_rtsp_to_webrtc(hass)
        await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].state is ConfigEntryState.SETUP_RETRY

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_communication_failure(hass: HomeAssistant) -> None:
    """Test unable to talk to server on startup."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=CONFIG_ENTRY_DATA)
    config_entry.add_to_hass(hass)

    with patch(
        "rtsp_to_webrtc.client.Client.heartbeat",
        side_effect=rtsp_to_webrtc.exceptions.ClientError(),
    ):
        assert await async_setup_rtsp_to_webrtc(hass)
        await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].state is ConfigEntryState.SETUP_RETRY

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_offer_for_stream_source(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    hass_ws_client: Callable[[...], Awaitable[aiohttp.ClientWebSocketResponse]],
    mock_camera: Any,
) -> None:
    """Test successful response from RTSPtoWebRTC server."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=CONFIG_ENTRY_DATA)
    config_entry.add_to_hass(hass)

    with patch("rtsp_to_webrtc.client.Client.heartbeat"):
        assert await async_setup_rtsp_to_webrtc(hass)
        await hass.async_block_till_done()

    aioclient_mock.post(
        f"{SERVER_URL}/stream",
        json={"sdp64": base64.b64encode(ANSWER_SDP.encode("utf-8")).decode("utf-8")},
    )

    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "camera/web_rtc_offer",
            "entity_id": "camera.demo_camera",
            "offer": OFFER_SDP,
        }
    )
    response = await client.receive_json()
    assert response.get("id") == 1
    assert response.get("type") == TYPE_RESULT
    assert response.get("success")
    assert "result" in response
    assert response["result"].get("answer") == ANSWER_SDP
    assert "error" not in response


async def test_offer_failure(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    hass_ws_client: Callable[[...], Awaitable[aiohttp.ClientWebSocketResponse]],
    mock_camera: Any,
) -> None:
    """Test a transient failure talking to RTSPtoWebRTC server."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=CONFIG_ENTRY_DATA)
    config_entry.add_to_hass(hass)

    with patch("rtsp_to_webrtc.client.Client.heartbeat"):
        assert await async_setup_rtsp_to_webrtc(hass)
        await hass.async_block_till_done()

    aioclient_mock.post(
        f"{SERVER_URL}/stream",
        exc=aiohttp.ClientError,
    )

    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 2,
            "type": "camera/web_rtc_offer",
            "entity_id": "camera.demo_camera",
            "offer": OFFER_SDP,
        }
    )
    response = await client.receive_json()
    assert response.get("id") == 2
    assert response.get("type") == TYPE_RESULT
    assert "success" in response
    assert not response.get("success")
    assert "error" in response
    assert response["error"].get("code") == "web_rtc_offer_failed"
    assert "message" in response["error"]
    assert "RTSPtoWebRTC server communication failure" in response["error"]["message"]
