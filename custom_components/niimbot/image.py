"""Image platform for Niimbot.

Support for viewing last label printed or previewed.
"""

from __future__ import annotations

from propcache.api import cached_property
import logging

from homeassistant.components.image import ImageEntity, ImageEntityDescription, Image
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH

from .const import EMPTY_PNG, DOMAIN, ImageAndBLEData

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up image platform for Niimbot."""
    assert config_entry.unique_id
    image_coordinator = hass.data[DOMAIN][config_entry.entry_id]["image_coordinator"]
    desc = ImageEntityDescription(
        key="last_label_made",
        name="Last label made",
    )
    async_add_entities(
        [
            NiimbotImageEntity(
                hass,
                image_coordinator,
                desc,
                config_entry.unique_id,
            )
        ]
    )


class NiimbotImageEntity(
    CoordinatorEntity[DataUpdateCoordinator[ImageAndBLEData]], ImageEntity
):
    """Base representation of a Niimbot image."""

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator[ImageAndBLEData],
        entity_description: ImageEntityDescription,
        unique_id: str,
    ) -> None:
        """Initialize Image entity."""
        CoordinatorEntity.__init__(self, coordinator)
        ImageEntity.__init__(self, hass)
        self.entity_description = entity_description
        self._attr_unique_id = f"{unique_id}_{entity_description.key}"
        ble_data = coordinator.data[1]
        name = f"{ble_data.name} {ble_data.identifier}"
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
        self._cached_image = coordinator.data[0]

    @cached_property
    def available(self) -> bool:
        """Entity always either data or empty."""
        return True

    @property
    def data(self) -> ImageAndBLEData:
        """Return coordinator data for this entity."""
        return self.coordinator.data

    def image(self) -> bytes | None:
        """Return bytes of image."""
        return self._cached_image.content

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("Updated image data")
        self._cached_image = self.data[0]
        self._attr_image_last_updated = dt_util.now()
        super()._handle_coordinator_update()
