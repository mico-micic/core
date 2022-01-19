"""V-ZUG API poller module."""

from typing import Callable, Set

from vzug import (
    DEVICE_TYPE_DRYER,
    DEVICE_TYPE_WASHING_MACHINE,
    BasicDevice,
    Dryer,
    WashingMachine,
)


class VZugPoller:
    """Class that uses the vzug-api to poll for device data."""

    def __init__(
        self, hostname: str, username: str, password: str, dev_type: str
    ) -> None:
        """Initialize device api."""

        self._hostname = hostname
        self._username = username
        self._password = password
        self._device = None
        self._online = False
        self._callbacks: Set[Callable] = set()

        if DEVICE_TYPE_WASHING_MACHINE in dev_type:
            self._device = WashingMachine(hostname, username, password)
        elif DEVICE_TYPE_DRYER in dev_type:
            self._device = Dryer(hostname, username, password)
        else:
            self._device = BasicDevice(hostname, username, password)

    async def async_poll(self) -> None:
        """Poll for device information and notify all registered callbacks."""
        if self._device is not None:
            self._online = await self._device.load_all_information()
            for callback in self._callbacks:
                callback()

    def remove_callback(self, callback: Callable[[], None]) -> None:
        """Remove previously registered callback."""
        self._callbacks.discard(callback)

    @property
    def device(self):
        """Return the device reference."""
        return self._device

    @property
    def is_online(self):
        """Return whether the device is online or not."""
        return self._online

    @property
    def hostname(self):
        """Return the devices hostname."""
        return self._hostname

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register callback, called when Roller changes state."""
        self._callbacks.add(callback)
