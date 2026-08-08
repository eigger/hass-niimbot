"""Select entities for Niimbot printer settings."""

from __future__ import annotations

import logging

from homeassistant import config_entries
from homeassistant.components.select import SelectEntity
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
from homeassistant.components import bluetooth

from .const import DOMAIN
from .niimprint import BLEData, NiimbotDevice
from .niimprint.model import (
    AUTO_SHUTDOWN_OPTIONS,
    auto_shutdown_index,
    auto_shutdown_label,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Niimbot select entities."""
    coordinator: DataUpdateCoordinator[BLEData] = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    device: NiimbotDevice = hass.data[DOMAIN][entry.entry_id]["device"]
    async_add_entities(
        [NiimbotAutoShutdownSelect(coordinator, coordinator.data, device)]
    )


class NiimbotAutoShutdownSelect(
    CoordinatorEntity[DataUpdateCoordinator[BLEData]], SelectEntity
):
    """Select for printer auto-shutdown time."""

    _attr_has_entity_name = True
    _attr_name = "Auto Shutdown"
    _attr_icon = "mdi:timer-outline"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(AUTO_SHUTDOWN_OPTIONS.values())

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        device: NiimbotDevice,
    ) -> None:
        super().__init__(coordinator)
        self._device = device
        name = f"{ble_data.name} {ble_data.identifier}"
        self._attr_unique_id = f"{name}_auto_shutdown"
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
    def current_option(self) -> str | None:
        return auto_shutdown_label(self._device.ble_data.autoshutdowntime)

    async def async_select_option(self, option: str) -> None:
        index = auto_shutdown_index(option)
        if index is None:
            raise HomeAssistantError(f"Unknown auto shutdown option: {option}")
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self._device.address
        )
        if ble_device is None:
            raise HomeAssistantError(
                f"Could not find printer with address {self._device.address}"
            )
        try:
            data = await self._device.set_auto_shutdown(ble_device, index)
        except Exception as err:
            raise HomeAssistantError(f"Failed to set auto shutdown: {err}") from err
        self.coordinator.async_set_updated_data(data)
