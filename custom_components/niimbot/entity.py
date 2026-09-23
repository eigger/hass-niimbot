"""Shared device binding for Niimbot entities."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import DeviceInfo

from .niimprint import BLEData


def device_info(ble_data: BLEData) -> DeviceInfo:
    """Device registry info shared by every platform."""
    name = f"{ble_data.name} {ble_data.identifier}"
    return DeviceInfo(
        connections={(CONNECTION_BLUETOOTH, ble_data.address)},
        name=name,
        manufacturer="Niimbot",
        model=ble_data.model,
        hw_version=ble_data.hw_version,
        sw_version=ble_data.sw_version,
        serial_number=ble_data.serial_number,
    )


class NiimbotBleEntity:
    """Bind the unique id and device info from a BLE snapshot.

    Unique ids stay ``{name} {identifier}_{key}``, which existing entities
    already use. This mixin has no ``__init__`` so it can sit in front of a
    Home Assistant entity base that does not always call ``super().__init__``.
    """

    _attr_has_entity_name = True

    def _bind_printer(self, ble_data: BLEData, key: str) -> None:
        """Set unique id and device info. ``key`` is the unique-id suffix."""
        name = f"{ble_data.name} {ble_data.identifier}"
        self._attr_unique_id = f"{name}_{key}"
        self._attr_device_info = device_info(ble_data)
