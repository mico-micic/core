"""V-ZUG sensors definition module."""

from __future__ import annotations

from vzug import DEVICE_TYPE_WASHING_MACHINE

from homeassistant.components.sensor import (
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL_INCREASING,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ENERGY_KILO_WATT_HOUR, VOLUME_LITERS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as dt_util

from .const import DOMAIN
from .vzug_sensors import VZugDevice, VZugSensor, VZugSensorEntryDescription

TIME_STR_FORMAT = "%H:%M"
ICON_PROGRAM = {True: "mdi:washing-machine", False: "mdi:washing-machine-off"}
ICON_PROGRAM_STATUS = {
    "idle": "mdi:stop-circle-outline",
    "active": "mdi:circle-double",
    "paused": "mdi:pause-circle-outline",
}
STATE_TEXT = {True: "active", False: "inactive"}


VZUG_DEVICE_DESCRIPTION = VZugSensorEntryDescription(
    key="machine",
    icon="mdi:washing-machine",
    value_func=lambda sensor: STATE_TEXT.get(sensor.device.is_active),
)

COMMON_MACHINE_DESCRIPTIONS: tuple[VZugSensorEntryDescription, ...] = (
    VZugSensorEntryDescription(
        key="status",
        name="Device Status",
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
        key="program_status",
        name="Program Status",
        icon_func=lambda sensor: ICON_PROGRAM_STATUS.get(sensor.device.program_status),
        value_attr="program_status",
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
