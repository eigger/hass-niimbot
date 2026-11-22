"""Shared device binding for Niimbot entities."""

from __future__ import annotations

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import DeviceInfo

from .niimprint import BLEData


def device_info(ble_data: BLEData) -> DeviceInfo:
    """Device registry info shared by every platform."""
    name = f"{ble_data.name} {ble_data.identifier}"
    info = DeviceInfo(
        connections={(CONNECTION_BLUETOOTH, ble_data.address)},
        name=name,
        manufacturer="Niimbot",
    )
    # Unknown values are left out so a printer that is off at (re)load never
    # blanks what the registry already learned from an earlier connection.
    for field in _DEVICE_FIELDS:
        value = getattr(ble_data, field)
        if value:
            info[field] = value  # type: ignore[literal-required]
    return info


_DEVICE_FIELDS = ("model", "hw_version", "sw_version", "serial_number")


@callback
def async_sync_device_registry(hass: HomeAssistant, ble_data: BLEData) -> None:
    """Push newly learned model/firmware/serial into the device registry.

    The values only exist after the first successful connection, which may be
    long after the entities (and their DeviceInfo) were created. Empty values
    never overwrite known ones, and the registry is only touched on change.
    """
    registry = dr.async_get(hass)
    device = registry.async_get_device(
        connections={(CONNECTION_BLUETOOTH, ble_data.address)}
    )
    if device is None:
        return
    changes = {
        field: value
        for field in _DEVICE_FIELDS
        if (value := getattr(ble_data, field)) and value != getattr(device, field)
    }
    if changes:
        registry.async_update_device(device.id, **changes)


class NiimbotKeepLastKnown:
    """Stay available on the last known value while the printer is unreachable.

    A battery printer is off most of the day, so a failed poll would otherwise
    make every entity unavailable although the value has not changed. Put this
    mixin before ``CoordinatorEntity``. Entities whose state can change while
    the printer is off (lid, paper, progress) must not use it.
    """

    def _has_known_value(self) -> bool:
        """Return True when the entity has a value to show."""
        raise NotImplementedError

    @property
    def available(self) -> bool:
        """Available with a known value, otherwise follow the coordinator."""
        return self._has_known_value() or super().available  # type: ignore[misc]


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
