"""Button entities for Niimbot printer actions."""

from __future__ import annotations

import logging

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.components.button import ButtonEntity
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
from .niimprint import BLEData, NiimbotDevice, PrinterCommandUnsupported

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Niimbot button entities."""
    coordinator: DataUpdateCoordinator[BLEData] = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    device: NiimbotDevice = hass.data[DOMAIN][entry.entry_id]["device"]

    entities: list[ButtonEntity] = [
        NiimbotPrinterResetButton(coordinator, coordinator.data, device),
    ]

    if device.supports_print_test_page():
        entities.append(
            NiimbotPrintTestPageButton(coordinator, coordinator.data, device)
        )

    # B1-class ACKs 0x8E but feeds ~15 cm; hide there. Other models: paper calibration.
    if device.supports_label_position_calibration():
        entities.append(
            NiimbotCalibrateLabelPositionButton(coordinator, coordinator.data, device)
        )
    # 0x59 is separate from vendor isSupportCalibration; B1 NAKs it despite the flag.
    if device.supports_height_calibration():
        entities.append(
            NiimbotCalibrateHeightButton(coordinator, coordinator.data, device)
        )

    async_add_entities(entities)


def _reraise_action_error(action: str, err: Exception) -> None:
    """Map protocol errors to a clear HomeAssistantError."""
    if isinstance(err, HomeAssistantError):
        raise err
    if isinstance(err, PrinterCommandUnsupported):
        raise HomeAssistantError(
            f"This printer does not support {action}"
        ) from err
    raise HomeAssistantError(f"Failed to {action}: {err}") from err


class NiimbotBaseButton(
    CoordinatorEntity[DataUpdateCoordinator[BLEData]], ButtonEntity
):
    """Base class for Niimbot button entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        device: NiimbotDevice,
        key: str,
    ) -> None:
        super().__init__(coordinator)
        self._device = device
        self._attr_translation_key = key
        name = f"{ble_data.name} {ble_data.identifier}"
        self._attr_unique_id = f"{name}_{key}"
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, ble_data.address)},
            name=name,
            manufacturer="Niimbot",
            model=ble_data.model,
            hw_version=ble_data.hw_version,
            sw_version=ble_data.sw_version,
            serial_number=ble_data.serial_number,
        )

    def _get_ble_device(self):
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self._device.address
        )
        if ble_device is None:
            raise HomeAssistantError(
                f"Could not find printer with address {self._device.address}"
            )
        return ble_device


class NiimbotCalibrateLabelPositionButton(NiimbotBaseButton):
    """Button to run paper/gap sensor calibration (may feed several labels)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        device: NiimbotDevice,
    ) -> None:
        super().__init__(coordinator, ble_data, device, "calibrate_label_position")

    async def async_press(self) -> None:
        ble_dev = self._get_ble_device()
        try:
            ok = await self._device.calibrate_label_position(ble_dev)
            if not ok:
                raise HomeAssistantError("Printer rejected paper calibration")
        except Exception as err:
            _reraise_action_error("paper calibration", err)


class NiimbotCalibrateHeightButton(NiimbotBaseButton):
    """Button to calibrate roll feed height."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        device: NiimbotDevice,
    ) -> None:
        super().__init__(coordinator, ble_data, device, "calibrate_roll_feed")

    async def async_press(self) -> None:
        ble_dev = self._get_ble_device()
        try:
            ok = await self._device.calibrate_height(ble_dev)
            if not ok:
                raise HomeAssistantError("Printer rejected roll feed calibration")
        except Exception as err:
            _reraise_action_error("calibrate roll feed", err)


class NiimbotPrinterResetButton(NiimbotBaseButton):
    """Button to reset printer settings."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        device: NiimbotDevice,
    ) -> None:
        super().__init__(coordinator, ble_data, device, "reset_printer_settings")

    async def async_press(self) -> None:
        ble_dev = self._get_ble_device()
        try:
            ok = await self._device.printer_reset(ble_dev)
            if not ok:
                raise HomeAssistantError("Printer rejected settings reset")
        except Exception as err:
            _reraise_action_error("reset printer settings", err)


class NiimbotPrintTestPageButton(NiimbotBaseButton):
    """Button to print a test page."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        device: NiimbotDevice,
    ) -> None:
        super().__init__(coordinator, ble_data, device, "print_test_page")

    async def async_press(self) -> None:
        ble_dev = self._get_ble_device()
        try:
            ok = await self._device.print_test_page(ble_dev)
            if not ok:
                raise HomeAssistantError("Printer rejected test page print")
        except Exception as err:
            _reraise_action_error("print test page", err)
