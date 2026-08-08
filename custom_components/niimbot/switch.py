"""Switch entities for Niimbot printer settings."""

from __future__ import annotations

import logging

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN
from .niimprint import BLEData, NiimbotDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Niimbot switch entities."""
    coordinator: DataUpdateCoordinator[BLEData] = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    device: NiimbotDevice = hass.data[DOMAIN][entry.entry_id]["device"]
    async_add_entities(
        [NiimbotConnectionSoundSwitch(coordinator, coordinator.data, device)]
    )


class NiimbotConnectionSoundSwitch(
    CoordinatorEntity[DataUpdateCoordinator[BLEData]], SwitchEntity
):
    """Switch for Bluetooth connection beep."""

    _attr_has_entity_name = True
    _attr_name = "Connection Sound"
    _attr_icon = "mdi:volume-high"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        device: NiimbotDevice,
    ) -> None:
        super().__init__(coordinator)
        self._device = device
        name = f"{ble_data.name} {ble_data.identifier}"
        self._attr_unique_id = f"{name}_connection_sound"
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, ble_data.address)},
            name=name,
            manufacturer="Niimbot",
            model=ble_data.model,
            hw_version=ble_data.hw_version,
            sw_version=ble_data.sw_version,
            serial_number=ble_data.serial_number,
        )

    @property
    def is_on(self) -> bool:
        value = self.coordinator.data.sensors.get("connection_sound")
        if value is None:
            return bool(self._device.connection_sound)
        return bool(value)

    async def async_turn_on(self, **kwargs) -> None:
        await self._set_sound(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._set_sound(False)

    async def _set_sound(self, on: bool) -> None:
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self._device.address
        )
        if ble_device is None:
            raise HomeAssistantError(
                f"Could not find printer with address {self._device.address}"
            )
        try:
            data = await self._device.set_connection_sound(ble_device, on)
        except Exception as err:
            raise HomeAssistantError(
                f"Failed to set connection sound: {err}"
            ) from err
        self.coordinator.async_set_updated_data(data)
