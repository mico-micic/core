"""V-ZUG device mocks used for testing."""

from datetime import datetime

from vzug import (
    DEVICE_TYPE_DRYER,
    DEVICE_TYPE_UNKNOWN,
    DEVICE_TYPE_WASHING_MACHINE,
    BasicDevice,
    DeviceError,
    Dryer,
    WashingMachine,
)

from homeassistant.components.vzug.const import DEVICE_TYPE_CONF

UUID_BASIC_DEVICE = "basic_uuid"
UUID_WASHING_MACHINE = "washing_uuid"
UUID_DRYER = "dryer_uuid"

CONFIG_ENTRY_BASIC_DEVICE = {
    "host": "1.1.1.1",
    "username": "test-username",
    "password": "test-password",
    DEVICE_TYPE_CONF: DEVICE_TYPE_UNKNOWN,
}

CONFIG_ENTRY_WASHING_MACHINE = {
    "host": "1.1.1.1",
    "username": "test-username",
    "password": "test-password",
    DEVICE_TYPE_CONF: DEVICE_TYPE_WASHING_MACHINE,
}

CONFIG_ENTRY_DRYER = {
    "host": "2.2.2.2",
    "username": "test-username",
    "password": "test-password",
    DEVICE_TYPE_CONF: DEVICE_TYPE_DRYER,
}


class MockBasicDevice(BasicDevice):
    """Device mock simulating a successful device connection."""

    def __init__(self) -> None:
        """Initialize mock device with some default values."""
        super().__init__("")
        self._device_name = "MockDevice Name"
        self._uuid = UUID_BASIC_DEVICE
        self._status = "testing"
        self._device_type = DEVICE_TYPE_UNKNOWN

    async def load_device_information(self):
        """Simulate successful operation."""
        return True

    async def load_all_information(self):
        """Simulate successful operation."""
        return True


class MockDeviceAuthException(DeviceError):
    """Device error mock returning an authentication problem."""

    @property
    def is_auth_problem(self) -> bool:
        """Simulate authentication problem."""
        return True


class MockDeviceAuthProblem(BasicDevice):
    """Device mock simulating an authentication error."""

    def __init__(self) -> None:
        """Initialize mock device without values."""
        super().__init__("")

    async def load_device_information(self):
        """Simulate failed operation."""
        return False

    @property
    def error_exception(self):
        """Return mocked device authentication exception."""
        return MockDeviceAuthException("Test-Err", "Test-Code")


class MockDeviceConnectionProblem(BasicDevice):
    """Device mock simulating a connection error."""

    def __init__(self) -> None:
        """Initialize mock device without values."""
        super().__init__("")

    async def load_device_information(self):
        """Simulate failed operation."""
        return False

    @property
    def error_exception(self):
        """Return mocked device exception."""
        return DeviceError("Test-Err", "Test-Code")


class MockWashingMachine(WashingMachine):
    """Washing machine mock simulating a successful connection."""

    def __init__(self) -> None:
        """Initialize mock device with some default values."""
        super().__init__("")
        self._device_name = "MockDevice Name"
        self._uuid = UUID_WASHING_MACHINE
        self._status = "washing-tests"
        self._device_type = DEVICE_TYPE_WASHING_MACHINE

    async def load_device_information(self):
        """Simulate successful operation."""
        return True

    async def load_all_information(self):
        """Simulate successful operation."""
        return True

    @property
    def is_active(self) -> bool:
        """Mock device is active by default."""
        return True

    @property
    def program(self) -> str:
        """Return static program."""
        return "Testing at 60°"

    def get_date_time_end(self, tz=None) -> datetime:
        """Return static end date / time."""
        return datetime(2000, 1, 1, 4, 42, 0, 0)

    @property
    def water_consumption_l_total(self) -> float:
        """Return static consumption value."""
        return 3000

    @property
    def water_consumption_l_avg(self) -> float:
        """Return static consumption value."""
        return 55.5

    @property
    def power_consumption_kwh_total(self) -> float:
        """Return static consumption value."""
        return 500.5

    @property
    def power_consumption_kwh_avg(self) -> float:
        """Return static consumption value."""
        return 0.5

    @property
    def optidos_a_status(self) -> str:
        """Return static optidos value."""
        return "full"

    @property
    def optidos_b_status(self) -> str:
        """Return static optidos value."""
        return "empty"


class MockDryer(Dryer):
    """Dryer mock simulating a successful connection."""

    def __init__(self) -> None:
        """Initialize mock device with some default values."""
        super().__init__("")
        self._device_name = "MockDevice Name"
        self._uuid = UUID_DRYER
        self._status = "drying-tests"
        self._device_type = DEVICE_TYPE_DRYER

    async def load_device_information(self):
        """Simulate successful operation."""
        return True

    async def load_all_information(self):
        """Simulate successful operation."""
        return True

    @property
    def is_active(self) -> bool:
        """Mock device is active by default."""
        return True

    @property
    def program(self) -> str:
        """Return static program value."""
        return "Drying at 42°"

    def get_date_time_end(self, tz=None) -> datetime:
        """Return static end date / time."""
        return datetime(2000, 1, 1, 4, 42, 0, 0)

    @property
    def power_consumption_kwh_total(self) -> float:
        """Return static consumption value."""
        return 500.5

    @property
    def power_consumption_kwh_avg(self) -> float:
        """Return static consumption value."""
        return 0.5
