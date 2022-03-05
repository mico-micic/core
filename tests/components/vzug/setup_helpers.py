"""V-ZUG setup helper used to register devices in hass for testing."""

from unittest.mock import patch

from vzug import BasicDevice

from homeassistant.components.vzug.const import DOMAIN
from homeassistant.components.vzug.vzug_poller import VZugPoller
from homeassistant.setup import async_setup_component

from tests.common import MockConfigEntry

POLLER_MOCK_PATH = "homeassistant.components.vzug.VZugPoller"


class MockVZugPoller(VZugPoller):
    """Poller mock holding any mock device."""

    def __init__(self, device: BasicDevice) -> None:
        """Initialize mock poller with device given as parameter."""

        super().__init__("1.1.1.1", "", "", device.device_type)

        # Overwrite device with mock
        self._device = device


async def setup_vzug_integration(hass, device: BasicDevice, config: MockConfigEntry):
    """Create the V-ZUG instance."""

    assert await async_setup_component(hass, DOMAIN, {})

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=config,
        version=1,
    )

    with patch(POLLER_MOCK_PATH, return_value=MockVZugPoller(device)):
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    if config_entry.entry_id not in hass.data[DOMAIN]:
        return None

    return config_entry
