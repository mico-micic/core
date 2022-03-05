"""V-ZUG device sensor tests."""

from vzug.const import (
    DEVICE_TYPE_DRYER,
    DEVICE_TYPE_UNKNOWN,
    DEVICE_TYPE_WASHING_MACHINE,
)

from homeassistant.helpers import entity_registry as ent_reg

from .device_mocks import (
    CONFIG_ENTRY_BASIC_DEVICE,
    CONFIG_ENTRY_DRYER,
    CONFIG_ENTRY_WASHING_MACHINE,
    UUID_BASIC_DEVICE,
    UUID_DRYER,
    UUID_WASHING_MACHINE,
    MockBasicDevice,
    MockDryer,
    MockWashingMachine,
)
from .setup_helpers import setup_vzug_integration


async def test_device_entity_registry(hass):
    """Test device entity is created correctly."""

    await setup_vzug_integration(hass, MockBasicDevice(), CONFIG_ENTRY_BASIC_DEVICE)

    entity_registry = ent_reg.async_get(hass)
    dev_prefix = f"sensor.{DEVICE_TYPE_UNKNOWN.lower()}_{UUID_BASIC_DEVICE}"

    assert f"{dev_prefix}" in entity_registry.entities
    assert f"{dev_prefix}_status" in entity_registry.entities

    assert hass.states.get(f"{dev_prefix}_status").state == "testing"


async def test_washing_machine_sensors(hass):
    """Test all washing machine sensors."""

    await setup_vzug_integration(
        hass, MockWashingMachine(), CONFIG_ENTRY_WASHING_MACHINE
    )

    entity_registry = ent_reg.async_get(hass)

    dev_prefix = f"sensor.{DEVICE_TYPE_WASHING_MACHINE.lower()}_{UUID_WASHING_MACHINE}"

    assert dev_prefix in entity_registry.entities
    assert hass.states.get(f"{dev_prefix}").state == "active"
    assert hass.states.get(f"{dev_prefix}_status").state == "washing-tests"
    assert hass.states.get(f"{dev_prefix}_program").state == "Testing at 60°"
    assert hass.states.get(f"{dev_prefix}_program_end").state == "04:42"
    assert hass.states.get(f"{dev_prefix}_optidos_a").state == "full"
    assert hass.states.get(f"{dev_prefix}_optidos_b").state == "empty"

    total_water = hass.states.get(f"{dev_prefix}_total_water_consumption")
    assert total_water.state == "3000"
    assert total_water.attributes.get("unit_of_measurement") == "L"

    avg_water = hass.states.get(f"{dev_prefix}_avg_water_consumption")
    assert avg_water.state == "55.5"
    assert avg_water.attributes.get("unit_of_measurement") == "L"

    total_power = hass.states.get(f"{dev_prefix}_total_power_consumption")
    assert total_power.state == "500.5"
    assert total_power.attributes.get("unit_of_measurement") == "kWh"

    avg_power = hass.states.get(f"{dev_prefix}_avg_power_consumption")
    assert avg_power.state == "0.5"
    assert avg_power.attributes.get("unit_of_measurement") == "kWh"


async def test_dryer_sensors(hass):
    """Test all dryer sensors."""

    await setup_vzug_integration(hass, MockDryer(), CONFIG_ENTRY_DRYER)

    entity_registry = ent_reg.async_get(hass)

    dev_prefix = f"sensor.{DEVICE_TYPE_DRYER.lower()}_{UUID_DRYER}"

    assert dev_prefix in entity_registry.entities
    assert hass.states.get(f"{dev_prefix}").state == "active"
    assert hass.states.get(f"{dev_prefix}_status").state == "drying-tests"
    assert hass.states.get(f"{dev_prefix}_program").state == "Drying at 42°"
    assert hass.states.get(f"{dev_prefix}_program_end").state == "04:42"

    total_power = hass.states.get(f"{dev_prefix}_total_power_consumption")
    assert total_power.state == "500.5"
    assert total_power.attributes.get("unit_of_measurement") == "kWh"

    avg_power = hass.states.get(f"{dev_prefix}_avg_power_consumption")
    assert avg_power.state == "0.5"
    assert avg_power.attributes.get("unit_of_measurement") == "kWh"
