"""Support for niimbot ble binary sensors."""

import logging
import dataclasses

from .niimprint import NiimbotDevice, BLEData

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .entity import NiimbotBleEntity
from .types import NiimbotConfigEntry

_LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class NiimbotBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Binary sensor description with inversion flag."""

    inverted: bool = False


BINARY_SENSORS: list[NiimbotBinarySensorEntityDescription] = [
    NiimbotBinarySensorEntityDescription(
        key="closingstate",
        translation_key="cover",
        icon="mdi:tray",
        entity_category=EntityCategory.DIAGNOSTIC,
        # closingstate != 0 means open (label cover). Custom name — not a door.
    ),
    NiimbotBinarySensorEntityDescription(
        key="paperstate",
        translation_key="paper",
        icon="mdi:label-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        # Protocol (Advanced1/2): paperstate == 0 means inserted. Confirmed on B1
        # with stock loaded reporting Off when not inverted.
        inverted=True,
    ),
    NiimbotBinarySensorEntityDescription(
        key="rfidreadstate",
        translation_key="rfid",
        icon="mdi:nfc-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        # rfidreadstate != 0 means readable
    ),
    NiimbotBinarySensorEntityDescription(
        key="ribbonstate",
        translation_key="ribbon_paper",
        icon="mdi:filmstrip",
        entity_category=EntityCategory.DIAGNOSTIC,
        # Protocol: ribbonstate == 0 means inserted
        inverted=True,
    ),
    NiimbotBinarySensorEntityDescription(
        key="ribbon_rfidreadstate",
        translation_key="ribbon_rfid",
        icon="mdi:nfc-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        # ribbon_rfidreadstate != 0 means readable
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NiimbotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Niimbot BLE binary sensors."""
    coordinator = entry.runtime_data.coordinator
    device = entry.runtime_data.device

    entities: list[BinarySensorEntity] = [
        NiimbotConnectionBinarySensor(coordinator, coordinator.data, device),
    ]
    created_keys: set[str] = set()

    for description in BINARY_SENSORS:
        if description.key in coordinator.data.sensors:
            entities.append(
                NiimbotStateBinarySensor(coordinator, coordinator.data, description)
            )
            created_keys.add(description.key)

    async_add_entities(entities)

    if len(created_keys) < len(BINARY_SENSORS):

        @callback
        def _on_coordinator_update() -> None:
            new_entities: list[BinarySensorEntity] = []
            for description in BINARY_SENSORS:
                if (
                    description.key not in created_keys
                    and description.key in coordinator.data.sensors
                ):
                    new_entities.append(
                        NiimbotStateBinarySensor(
                            coordinator, coordinator.data, description
                        )
                    )
                    created_keys.add(description.key)
            if new_entities:
                async_add_entities(new_entities)
            if len(created_keys) == len(BINARY_SENSORS) or (
                device.heartbeat_variant not in (None, "advanced2")
            ):
                unsub()

        unsub = coordinator.async_add_listener(_on_coordinator_update)


class NiimbotStateBinarySensor(
    NiimbotBleEntity,
    CoordinatorEntity[DataUpdateCoordinator[BLEData]],
    BinarySensorEntity,
):
    """Binary sensor for printer state values (lid, paper, RFID)."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        description: NiimbotBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._bind_printer(ble_data, description.key)

    @property
    def is_on(self) -> bool | None:
        value = self.coordinator.data.sensors.get(self.entity_description.key)
        if value is None:
            return None
        is_on = value != 0
        if self.entity_description.inverted:
            return not is_on
        return is_on


class NiimbotConnectionBinarySensor(
    NiimbotBleEntity,
    CoordinatorEntity[DataUpdateCoordinator[BLEData]],
    BinarySensorEntity,
):
    """Niimbot BLE connection binary sensor."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:bluetooth-connect"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        device: NiimbotDevice,
    ) -> None:
        """Populate the niimbot entity with relevant data."""
        super().__init__(coordinator)

        self._device = device
        self._id = ble_data.address
        self._bind_printer(ble_data, "connection")

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
