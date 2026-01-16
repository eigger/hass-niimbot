"""Support for niimbot ble binary sensors."""

import logging

from .niimprint import NiimbotDevice, BLEData

from homeassistant import config_entries
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Niimbot BLE binary sensors."""
    coordinator: DataUpdateCoordinator[BLEData] = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    device: NiimbotDevice = hass.data[DOMAIN][entry.entry_id]["device"]

    entities = [
        NiimbotConnectionBinarySensor(coordinator, coordinator.data, device),
    ]

    async_add_entities(entities)


class NiimbotConnectionBinarySensor(
    CoordinatorEntity[DataUpdateCoordinator[BLEData]], BinarySensorEntity
):
    """Niimbot BLE connection binary sensor."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:bluetooth-connect"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        device: NiimbotDevice,
    ) -> None:
        """Populate the niimbot entity with relevant data."""
        super().__init__(coordinator)

        self._device = device

        name = f"{ble_data.name} {ble_data.identifier}"

        self._attr_unique_id = f"{name}_connection"
        self._attr_name = "Connection"

        self._id = ble_data.address
        self._attr_device_info = DeviceInfo(
            connections={
                (
                    CONNECTION_BLUETOOTH,
                    ble_data.address,
                )
            },
            name=name,
            manufacturer="Niimbot",
            model=ble_data.model,
            hw_version=ble_data.hw_version,
            sw_version=ble_data.sw_version,
            serial_number=ble_data.serial_number,
        )

    async def async_added_to_hass(self) -> None:
        """Register callback when entity is added."""
        await super().async_added_to_hass()
        self._device.callback_connection = self._handle_connection_update

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callback when entity is removed."""
        await super().async_will_remove_from_hass()
        self._device.callback_connection = None

    @callback
    def _handle_connection_update(self) -> None:
        """Handle connection state update."""
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return true if the device is connected."""
        return self._device.is_connected
