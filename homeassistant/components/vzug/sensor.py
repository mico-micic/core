"""V-ZUG sensors module."""

from __future__ import annotations

from datetime import tzinfo
from enum import Enum

from vzug import DEVICE_TYPE_WASHING_MACHINE

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ENERGY_KILO_WATT_HOUR, VOLUME_LITERS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as dt_util

from .const import DOMAIN
from .vzug_poller import VZugPoller

TIME_STR_FORMAT = "%H:%M"
ICON_PROGRAM = {True: "mdi:washing-machine", False: "mdi:washing-machine-off"}
STATE_TEXT = {True: "active", False: "inactive"}


class EnumOptiDos(Enum):
    """Enum used for the optiDos A/B sensor."""

    A = "A"
    B = "B"


class EnumAvgTotal(Enum):
    """Enum used for the power and water consumption sensors."""

    AVG = "Average"
    TOTAL = "Total"


# This function is called as part of the __init__.async_setup_entry (via the
# hass.config_entries.async_forward_entry_setup call)
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add device and sensors for passed config_entry in HA."""

    timezone = dt_util.get_time_zone(hass.config.time_zone)

    # Get poller from hass.data entry created in __init__.async_setup_entry function
    sensors: list[SensorBase] = []
    for poller in hass.data[DOMAIN].values():
        sensors.append(VZugDevice(poller))

        if DEVICE_TYPE_WASHING_MACHINE in poller.device.device_type:
            sensors.append(ProgramSensor(poller))
            sensors.append(ProgramEndSensor(poller, timezone))
            sensors.append(WaterConsumptionSensor(poller, EnumAvgTotal.TOTAL))
            sensors.append(WaterConsumptionSensor(poller, EnumAvgTotal.AVG))
            sensors.append(PowerConsumptionSensor(poller, EnumAvgTotal.TOTAL))
            sensors.append(PowerConsumptionSensor(poller, EnumAvgTotal.AVG))
            sensors.append(OptiDosSensor(poller, EnumOptiDos.A))
            sensors.append(OptiDosSensor(poller, EnumOptiDos.B))

    async_add_entities(sensors)


class SensorBase(Entity):
    """This base class for all sensors including the device entity."""

    should_poll = False

    def __init__(self, poller: VZugPoller, id_suffix: str, name_suffix: str) -> None:
        """Use predefined prefix for id and name and set sensor specific suffix."""
        self._poller = poller

        self.entity_id = f"{self._entity_id_prefix}.{id_suffix}"
        self._attr_unique_id = f"{self.device.uuid}_{id_suffix}"
        self._attr_name = f"{self._get_device_name()} {name_suffix}"

    # To link this entity to the VZug device, this property must return an
    # identifiers value matching that used in the VZugDevice class
    @property
    def device_info(self):
        """Return information to link this entity with the correct device."""
        return {"identifiers": {(DOMAIN, self.device.uuid)}}

    @property
    def available(self) -> bool:
        """Forward call to VZugPoller::is_online."""
        return self._poller.is_online

    def _get_device_name(self) -> str:
        """Return the user readable device name."""
        name = self.device.device_name
        if len(name) == 0:
            name = self.device.model_desc

        return name

    @property
    def device(self):
        """Return the device reference."""
        return self._poller.device

    @property
    def _entity_id_prefix(self) -> str:
        return f"{DOMAIN}.{self.device.device_type}.{self.device.uuid}"

    async def async_added_to_hass(self):
        """Register callback to get notfied when the device data was updated."""
        self._poller.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Don't forget to remove the callback."""
        self._poller.remove_callback(self.async_write_ha_state)


class VZugDevice(SensorBase):
    """Representation of a V-ZUG device."""

    # Enable polling only for the device class. In this way we use the hass
    # scheduler to trigger the poller.
    should_poll = True

    def __init__(self, poller: VZugPoller) -> None:
        """Set id and name so that all other sensors can be referenced to this device."""
        super().__init__(poller, "", "")

        # https://developers.home-assistant.io/docs/entity_registry_index/#unique-id-requirements
        self._attr_unique_id = f"{self.device.uuid}_machine"
        self.entity_id = super()._entity_id_prefix
        self._attr_name = super()._get_device_name()

    # Information about the devices that is sible in the UI.
    # https://developers.home-assistant.io/docs/device_registry_index/#device-properties
    @property
    def device_info(self):
        """Information about this entity/device."""
        return {
            "identifiers": {(DOMAIN, self.device.uuid)},
            # If desired, the name for the device could be different to the entity
            "name": super()._get_device_name(),
            "sw_version": "",
            "model": self.device.model_desc,
            "manufacturer": "V-ZUG",
            "configuration_url": f"http://{self._poller.hostname}",
            "hw_version": self.device.serial,
        }

    @property
    def icon(self):
        """Set washing-maschine icon."""
        return "mdi:washing-machine"

    @property
    def state(self):
        """Return whether the device is active or not."""
        return STATE_TEXT.get(self.device.is_active)

    async def async_update(self):
        """Poll for device data."""
        await self._poller.async_poll()


class WaterConsumptionSensor(SensorBase):
    """Sensor for the water consumption."""

    def __init__(self, poller: VZugPoller, avg_total: EnumAvgTotal) -> None:
        """Initialize the sensor with id and name suffix."""

        if EnumAvgTotal.TOTAL is avg_total:
            super().__init__(
                poller, "total_water_consumption", "Total Water Consumption"
            )
        else:
            super().__init__(
                poller, "avg_water_consumption", "Average Water Consumption"
            )

        self._avg_total = avg_total

    @property
    def icon(self):
        """Set water icon."""
        return "mdi:water"

    @property
    def unit_of_measurement(self) -> str:
        """Set unit to liter."""
        return VOLUME_LITERS

    @property
    def state(self):
        """Return water consumption in liter."""
        if EnumAvgTotal.TOTAL is self._avg_total:
            return self.device.water_consumption_l_total
        else:
            return self.device.water_consumption_l_avg


class PowerConsumptionSensor(SensorBase):
    """Sensor for the power consumption."""

    def __init__(self, poller: VZugPoller, avg_total: EnumAvgTotal) -> None:
        """Initialize the sensor with id and name suffix."""

        if EnumAvgTotal.TOTAL is avg_total:
            super().__init__(
                poller, "total_power_consumption", "Total Power Consumption"
            )
        else:
            super().__init__(
                poller, "avg_power_consumption", "Average Power Consumption"
            )

        self._avg_total = avg_total

    @property
    def icon(self):
        """Set lightnin-bolt icon."""
        return "mdi:lightning-bolt"

    @property
    def unit_of_measurement(self) -> str:
        """Set unit to kWh."""
        return ENERGY_KILO_WATT_HOUR

    @property
    def state(self):
        """Return power consumption in kWh."""
        if EnumAvgTotal.TOTAL is self._avg_total:
            return self.device.power_consumption_kwh_total
        else:
            return self.device.power_consumption_kwh_avg


class ProgramSensor(SensorBase):
    """Sensor for the active washing machine program."""

    def __init__(self, poller: VZugPoller) -> None:
        """Initialize the sensor with id and name suffix."""
        super().__init__(poller, "program", "Program")

    @property
    def icon(self):
        """Return washing machine icon depending if program is active or not."""
        return ICON_PROGRAM.get(self.device.is_active)

    @property
    def state(self):
        """Return program name if available."""
        if len(self.device.program) == 0:
            return "-"
        else:
            return self.device.program


class ProgramEndSensor(SensorBase):
    """Sensor for the active washing machine program."""

    def __init__(self, poller: VZugPoller, timezone: tzinfo | None) -> None:
        """Initialize the sensor with id and name suffix."""
        super().__init__(poller, "program_end", "Program End")
        self._timezone = timezone

    def _to_time_formatted(self) -> str:
        if self.device.is_active:
            return self.device.get_date_time_end(self._timezone).strftime(
                TIME_STR_FORMAT
            )
        else:
            return "-"

    @property
    def icon(self):
        """Set calendar-clock icon."""
        return "mdi:calendar-clock"

    @property
    def state(self):
        """Return end time."""
        return self._to_time_formatted()


class OptiDosSensor(SensorBase):
    """Sensor for the optiDos status."""

    def __init__(self, poller: VZugPoller, opti_dos: EnumOptiDos) -> None:
        """Initialize the sensor with id and name suffix."""
        super().__init__(
            poller, f"optidos_{opti_dos.value}", f"optiDos {opti_dos.value} Status"
        )
        self._opti_dos_letter = opti_dos

    @property
    def icon(self):
        """Set format-color-fill icon."""
        return "mdi:format-color-fill"

    @property
    def state(self):
        """Return optiDos status text."""
        if EnumOptiDos.A is self._opti_dos_letter:
            return self.device.optidos_a_status
        else:
            return self.device.optidos_b_status
