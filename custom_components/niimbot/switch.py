"""Switch entities for Niimbot printer settings."""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .ble import require_ble_device
from .entity import NiimbotBleEntity
from .niimprint import BLEData, NiimbotDevice
from .types import NiimbotConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NiimbotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Niimbot switch entities."""
    coordinator = entry.runtime_data.coordinator
    device = entry.runtime_data.device
    async_add_entities(
        [NiimbotConnectionSoundSwitch(coordinator, coordinator.data, device)]
    )


class NiimbotConnectionSoundSwitch(
    NiimbotBleEntity, CoordinatorEntity[DataUpdateCoordinator[BLEData]], SwitchEntity
):
    """Switch for Bluetooth connection beep."""

    _attr_translation_key = "connection_sound"
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
        self._bind_printer(ble_data, "connection_sound")

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
        ble_device = require_ble_device(self.hass, self._device.address)
        try:
            data = await self._device.set_connection_sound(ble_device, on)
        except Exception as err:
            raise HomeAssistantError(
                f"Failed to set connection sound: {err}"
            ) from err
        self.coordinator.async_set_updated_data(data)
