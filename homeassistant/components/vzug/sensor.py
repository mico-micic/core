"""V-ZUG sensors module."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import tzinfo
import logging

from vzug import DEVICE_TYPE_WASHING_MACHINE
from vzug.basic_device import BasicDevice

from homeassistant.components.sensor import (
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL_INCREASING,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ENERGY_KILO_WATT_HOUR, VOLUME_LITERS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as dt_util

from .const import DOMAIN
from .vzug_poller import VZugPoller

TIME_STR_FORMAT = "%H:%M"
ICON_PROGRAM = {True: "mdi:washing-machine", False: "mdi:washing-machine-off"}
STATE_TEXT = {True: "active", False: "inactive"}

_LOGGER = logging.getLogger(__name__)


@dataclass
class VZugSensorEntryDescription(SensorEntityDescription):
    """Entry description class for V-ZUG sensors."""

    value_attr: str | None = None
    value_func: Callable | None = None
    icon_func: Callable | None = None


VZUG_DEVICE_DESCRIPTION = VZugSensorEntryDescription(
    key="machine",
    icon="mdi:washing-machine",
    value_func=lambda sensor: STATE_TEXT.get(sensor.device.is_active),
)

COMMON_MACHINE_DESCRIPTIONS: tuple[VZugSensorEntryDescription, ...] = (
    VZugSensorEntryDescription(
        key="status",
        name="Status",
        icon="mdi:information-outline",
        value_attr="status",
    ),
)

WASHING_MACHINE_DESCRIPTIONS: tuple[VZugSensorEntryDescription, ...] = (
    VZugSensorEntryDescription(
        key="total_water_consumption",
        name="Water Consumption Total",
        icon="mdi:water",
        native_unit_of_measurement=VOLUME_LITERS,
        state_class=STATE_CLASS_TOTAL_INCREASING,
        value_attr="water_consumption_l_total",
    ),
    VZugSensorEntryDescription(
        key="avg_water_consumption",
        name="Water Consumption Average",
        icon="mdi:water",
        native_unit_of_measurement=VOLUME_LITERS,
        state_class=STATE_CLASS_MEASUREMENT,
        value_attr="water_consumption_l_avg",
    ),
    VZugSensorEntryDescription(
        key="total_power_consumption",
        name="Power Consumption Total",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        state_class=STATE_CLASS_TOTAL_INCREASING,
        value_attr="power_consumption_kwh_total",
    ),
    VZugSensorEntryDescription(
        key="avg_power_consumption",
        name="Power Consumption Average",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
        state_class=STATE_CLASS_MEASUREMENT,
        value_attr="power_consumption_kwh_avg",
    ),
    VZugSensorEntryDescription(
        key="optidos_a",
        name="optiDos A Status",
        icon="mdi:format-color-fill",
        value_attr="optidos_a_status",
    ),
    VZugSensorEntryDescription(
        key="optidos_b",
        name="optiDos B Status",
        icon="mdi:format-color-fill",
        value_attr="optidos_b_status",
    ),
    VZugSensorEntryDescription(
        key="program",
        name="Program",
        icon_func=lambda sensor: ICON_PROGRAM.get(sensor.device.is_active),
        value_attr="program",
    ),
    VZugSensorEntryDescription(
        key="program_end",
        name="Program End",
        icon="mdi:calendar-clock",
        value_func=lambda sensor: sensor.device.get_date_time_end(
            sensor.timezone
        ).strftime(TIME_STR_FORMAT)
        if sensor.device.is_active
        else "-",
    ),
)


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
    sensors: list[SensorEntity] = []
    for poller in hass.data[DOMAIN].values():
        sensors.append(VZugDevice(poller, VZUG_DEVICE_DESCRIPTION))
        sensors.extend(
            [VZugSensor(poller, desc, timezone) for desc in COMMON_MACHINE_DESCRIPTIONS]
        )

        if DEVICE_TYPE_WASHING_MACHINE is poller.device.device_type:
            sensors.extend(
                [
                    VZugSensor(poller, desc, timezone)
                    for desc in WASHING_MACHINE_DESCRIPTIONS
                ]
            )

    async_add_entities(sensors)


def _to_default_if_empty(value):
    """Return a predefined string if input is a string type but empty."""
    ret = value
    if isinstance(value, str) and len(value) == 0:
        ret = "-"
    return ret


class VZugSensor(SensorEntity):
    """Basic class for all V-ZUG device sensors."""

    should_poll = False

    def __init__(
        self,
        poller: VZugPoller,
        description: VZugSensorEntryDescription,
        timezone: tzinfo | None,
    ) -> None:
        """Set entity id and name so that this sensor will be mapped to the corresponding device."""

        self._poller = poller
        self._timezone = timezone

        self.entity_id = f"{self.get_entity_id_prefix()}.{description.key}"
        self._attr_unique_id = f"{self.device.uuid}_{description.key}"
        self._attr_name = f"{self.get_device_name()} {description.name}"
        self._vzug_entity_description = description
        self.entity_description = description

    def get_entity_id_prefix(self) -> str:
        """Return the entity id prefix."""
        return f"{DOMAIN}.{self.device.device_type}.{self.device.uuid}"

    def get_device_name(self) -> str:
        """Return the user readable device name."""
        if len(self.device.device_name) == 0:
            return self.device.model_desc

        return self.device.device_name

    @property
    def timezone(self) -> tzinfo | None:
        """Return current timezone used for date / time values."""
        return self._timezone

    @property
    def device(self) -> BasicDevice:
        """Return the device reference."""
        return self._poller.device

    @property
    def available(self) -> bool:
        """Forward call to VZugPoller::is_online."""
        return self._poller.is_online

    @property
    def icon(self) -> str | None:
        """Return the icon by calling the icon_func if defined."""
        if self._vzug_entity_description.icon_func is not None:
            return self._vzug_entity_description.icon_func(self)
        else:
            return super().icon

    # To link this entity to the VZug device, this property must return an
    # identifiers value matching that used in the VZugDevice class
    @property
    def device_info(self):
        """Return information to link this entity with the correct device."""
        return {"identifiers": {(DOMAIN, self.device.uuid)}}

    @property
    def native_value(self):
        """Read device data as defined by the entry description (from value_attr / value_func)."""

        if self._vzug_entity_description.value_func is not None:
            return self._vzug_entity_description.value_func(self)

        attr = self._vzug_entity_description.value_attr
        if hasattr(self.device, attr):
            return _to_default_if_empty(getattr(self.device, attr))

        _LOGGER.error(
            "Error reading device attribute! No or invalid value_func / value_attr defined for sensor with key %s",
            self.entity_description.key,
        )

    async def async_added_to_hass(self):
        """Register callback to get notfied when the device data was updated."""
        self._poller.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Don't forget to remove the callback."""
        self._poller.remove_callback(self.async_write_ha_state)


class VZugDevice(VZugSensor):
    """Representation of a V-ZUG device."""

    # Enable polling only for the device class. In this way we use the hass
    # scheduler to trigger the poller.
    should_poll = True

    def __init__(self, poller: VZugPoller, desc: VZugSensorEntryDescription) -> None:
        """Set id and name so that all other sensors can be referenced to this device."""

        super().__init__(poller, desc, None)

        # https://developers.home-assistant.io/docs/entity_registry_index/#unique-id-requirements
        self.entity_id = self.get_entity_id_prefix()
        self._attr_name = self.get_device_name()

    # Information about the devices that is sible in the UI.
    # https://developers.home-assistant.io/docs/device_registry_index/#device-properties
    @property
    def device_info(self):
        """Information about this entity/device."""
        return {
            "identifiers": {(DOMAIN, self.device.uuid)},
            "name": self.get_device_name(),
            "sw_version": "",
            "model": self.device.model_desc,
            "manufacturer": "V-ZUG",
            "configuration_url": f"http://{self._poller.hostname}",
            "hw_version": self.device.serial,
        }

    async def async_update(self):
        """Poll for device data."""
        await self._poller.async_poll()
