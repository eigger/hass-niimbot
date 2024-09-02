"""Support for niimbot ble sensors."""
import logging
import dataclasses

from .niimprint import BLEData

from homeassistant import config_entries
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
    LIGHT_LUX,
    PERCENTAGE,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util.unit_system import METRIC_SYSTEM

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSORS_MAPPING_TEMPLATE: dict[str, SensorEntityDescription] = {
    "address": SensorEntityDescription(
        key="address",
        #device_class=SensorDeviceClass.MEASUREMENT,
        #native_unit_of_measurement=UnitOfPressure.VOLT,
        name="MAC",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Niimbot BLE sensors."""
    coordinator: DataUpdateCoordinator[BLEData] = hass.data[DOMAIN][entry.entry_id]

    # we need to change some units
    sensors_mapping = SENSORS_MAPPING_TEMPLATE.copy()

    entities = []
    _LOGGER.debug("got sensors: %s", coordinator.data.sensors)
    for sensor_type, sensor_value in coordinator.data.sensors.items():
        if sensor_type not in sensors_mapping:
            _LOGGER.debug(
                "Unknown sensor type detected: %s, %s",
                sensor_type,
                sensor_value,
            )
            continue
        entities.append(
            NiimbotSensor(coordinator, coordinator.data, sensors_mapping[sensor_type])
        )

    async_add_entities(entities)


class NiimbotSensor(CoordinatorEntity[DataUpdateCoordinator[BLEData]], SensorEntity):
    """Niimbot BLE sensors for the device."""
    #_attr_state_class = None
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        ble_data: BLEData,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Populate the niimbot entity with relevant data."""
        super().__init__(coordinator)
        self.entity_description = entity_description

        name = f"{ble_data.name} {ble_data.identifier}"

        self._attr_unique_id = f"{name}_{entity_description.key}"

        self._id = ble_data.address
        self._attr_device_info = DeviceInfo(
            connections={
                (
                    CONNECTION_BLUETOOTH,
                    ble_data.address,
                )
            },
            name=name,
            manufacturer="Niimbot Co., LTD.",
            model=ble_data.model,
            hw_version=ble_data.hw_version,
            sw_version=ble_data.sw_version,
        )

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        try:
            return self.coordinator.data.sensors[self.entity_description.key]
        except KeyError:
            return None
