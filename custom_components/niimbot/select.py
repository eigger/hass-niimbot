"""Select entities for Niimbot printer settings."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .ble import require_ble_device
from .entity import NiimbotBleEntity, NiimbotKeepLastKnown
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
    NiimbotBleEntity,
    NiimbotKeepLastKnown,
    CoordinatorEntity[DataUpdateCoordinator[BLEData]],
    SelectEntity,
    RestoreEntity,
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

    def _has_known_value(self) -> bool:
        return self.current_option is not None

    async def async_added_to_hass(self) -> None:
        """Load the last stored option for use until the printer reports one."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        option = state.state if state else None
        if option in self._attr_options and self._accept_restored(option):
            self._restored_value = option

    @property
    def current_option(self) -> str | None:
        live = auto_shutdown_option(self._device.ble_data.autoshutdowntime)
        return self._restored_value if live is None else live

    async def async_select_option(self, option: str) -> None:
        index = auto_shutdown_index(option)
        if index is None:
            raise HomeAssistantError(f"Unknown auto shutdown option: {option}")
        ble_device = require_ble_device(self.hass, self._device.address)
        try:
            data = await self._device.set_auto_shutdown(ble_device, index)
        except Exception as err:
            raise HomeAssistantError(f"Failed to set auto shutdown: {err}") from err
        self.coordinator.async_set_updated_data(data)
