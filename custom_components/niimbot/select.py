"""Select entities for Niimbot printer settings."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.components import bluetooth

from .entity import NiimbotBleEntity
from .niimprint import BLEData, NiimbotDevice
from .types import NiimbotConfigEntry
from .niimprint.model import (
    AUTO_SHUTDOWN_OPTIONS,
    auto_shutdown_index,
    auto_shutdown_option,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NiimbotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Niimbot select entities."""
    coordinator = entry.runtime_data.coordinator
    device = entry.runtime_data.device
    async_add_entities(
        [NiimbotAutoShutdownSelect(coordinator, coordinator.data, device)]
    )


class NiimbotAutoShutdownSelect(
    NiimbotBleEntity, CoordinatorEntity[DataUpdateCoordinator[BLEData]], SelectEntity
):
    """Select for printer auto-shutdown time."""

    _attr_translation_key = "auto_shutdown"
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
        self._bind_printer(ble_data, "auto_shutdown")

    @property
    def current_option(self) -> str | None:
        return auto_shutdown_option(self._device.ble_data.autoshutdowntime)

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
