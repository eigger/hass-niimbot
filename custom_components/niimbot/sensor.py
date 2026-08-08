"""Support for niimbot ble sensors."""

import logging
from datetime import timedelta

from .niimprint import NiimbotDevice, BLEData

from homeassistant import config_entries
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSORS_MAPPING_TEMPLATE: dict[str, SensorEntityDescription] = {
    "battery": SensorEntityDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        name="Battery",
    ),
    "last_error": SensorEntityDescription(
        key="last_error",
        name="Last Error",
        icon="mdi:alert-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "density": SensorEntityDescription(
        key="density",
        name="Print Density",
        icon="mdi:printer-3d-nozzle",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "printspeed": SensorEntityDescription(
        key="printspeed",
        name="Print Speed",
        icon="mdi:speedometer",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "labeltype": SensorEntityDescription(
        key="labeltype",
        name="Label Type",
        icon="mdi:tag-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "autoshutdowntime": SensorEntityDescription(
        key="autoshutdowntime",
        name="Auto Shutdown",
        icon="mdi:timer-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}

RFID_SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    "labels_remaining": SensorEntityDescription(
        key="labels_remaining",
        name="Labels Remaining",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:label-multiple",
    ),
    "labels_used": SensorEntityDescription(
        key="labels_used",
        name="Labels Used",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:label-off",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "labels_total": SensorEntityDescription(
        key="labels_total",
        name="Labels Total",
        icon="mdi:label",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "consumable_usage": SensorEntityDescription(
        key="consumable_usage",
        name="Consumable Usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:percent",
    ),
    "label_sku": SensorEntityDescription(
        key="label_sku",
        name="Label SKU",
        icon="mdi:barcode",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "consumable_type": SensorEntityDescription(
        key="consumable_type",
        name="Consumable Type",
        icon="mdi:tag-text",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "tag_uuid": SensorEntityDescription(
        key="tag_uuid",
        name="Tag UUID",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
}


def _device_info(ble_data: BLEData) -> DeviceInfo:
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Niimbot BLE sensors."""
    coordinator: DataUpdateCoordinator[BLEData] = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    device: NiimbotDevice = hass.data[DOMAIN][entry.entry_id]["device"]

    sensors_mapping = SENSORS_MAPPING_TEMPLATE.copy()
    entities: list[SensorEntity] = []
    created_keys: set[str] = set()

    # Core sensors from capability / known keys (not only first-refresh data).
    for key, description in sensors_mapping.items():
        if key == "last_error":
            entities.append(
                NiimbotLastErrorSensor(
                    coordinator, coordinator.data, description, device
                )
            )
        elif key == "battery":
            entities.append(
                NiimbotBatterySensor(
                    coordinator, coordinator.data, description, device
                )
            )
        else:
            entities.append(NiimbotSensor(coordinator, coordinator.data, description))
        created_keys.add(key)

    entities.append(NiimbotPrintDurationSensor(coordinator, coordinator.data, device))
    entities.append(NiimbotPrintProgressSensor(coordinator, coordinator.data, device))

    def _add_rfid_entities() -> list[SensorEntity]:
        added: list[SensorEntity] = []
        if not device.supports_label_rfid():
            return added
        for key, description in RFID_SENSOR_DESCRIPTIONS.items():
            if key in created_keys:
                continue
            added.append(
                NiimbotRfidSensor(coordinator, coordinator.data, description, device)
            )
            created_keys.add(key)
        return added

    entities.extend(_add_rfid_entities())
    async_add_entities(entities)

    # Model may be unknown until the first successful poll.
    if not device.supports_label_rfid():

        @callback
        def _on_coordinator_update() -> None:
            new_entities = _add_rfid_entities()
            if new_entities:
                async_add_entities(new_entities)
                unsub()

        unsub = coordinator.async_add_listener(_on_coordinator_update)


class NiimbotSensor(CoordinatorEntity[DataUpdateCoordinator[BLEData]], SensorEntity):
    """Niimbot BLE sensors for the device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Populate the niimbot entity with relevant data."""
        super().__init__(coordinator)
        self.entity_description = entity_description

        name = f"{ble_data.name} {ble_data.identifier}"
        self._attr_unique_id = f"{name}_{entity_description.key}"
        self._attr_device_info = _device_info(ble_data)

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        try:
            return self.coordinator.data.sensors[self.entity_description.key]
        except KeyError:
            return None


class NiimbotBatterySensor(NiimbotSensor):
    """Battery sensor with optional charge-bucket attribute."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        entity_description: SensorEntityDescription,
        device: NiimbotDevice,
    ) -> None:
        super().__init__(coordinator, ble_data, entity_description)
        self._device = device

    @property
    def extra_state_attributes(self) -> dict | None:
        bucket = self.coordinator.data.sensors.get("battery_bucket")
        if bucket is None and self._device._info_battery_bucket is None:
            return None
        return {
            "charge_bucket": bucket
            if bucket is not None
            else self._device._info_battery_bucket
        }


class NiimbotLastErrorSensor(NiimbotSensor):
    """Diagnostic sensor for the last printer error code."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        entity_description: SensorEntityDescription,
        device: NiimbotDevice,
    ) -> None:
        super().__init__(coordinator, ble_data, entity_description)
        self._device = device

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._device.callback_error = self._handle_error_update

    async def async_will_remove_from_hass(self) -> None:
        await super().async_will_remove_from_hass()
        self._device.callback_error = None

    @callback
    def _handle_error_update(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> StateType:
        return self._device.last_error or self.coordinator.data.sensors.get(
            "last_error"
        )

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._device.last_error_time is None:
            return None
        return {"timestamp": self._device.last_error_time}


class NiimbotRfidSensor(NiimbotSensor):
    """RFID consumable sensor with optional attributes on remaining labels."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        entity_description: SensorEntityDescription,
        device: NiimbotDevice,
    ) -> None:
        super().__init__(coordinator, ble_data, entity_description)
        self._device = device

    @property
    def extra_state_attributes(self) -> dict | None:
        if self.entity_description.key != "labels_remaining":
            return None
        return dict(self._device._rfid_attrs) if self._device._rfid_attrs else None


class NiimbotPrintDurationSensor(
    CoordinatorEntity[DataUpdateCoordinator[BLEData]], SensorEntity
):
    """Niimbot print duration sensor."""

    _attr_has_entity_name = True
    _attr_name = "Print Duration"
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        device: NiimbotDevice,
    ) -> None:
        """Initialize the print duration sensor."""
        super().__init__(coordinator)

        self._device = device
        self._unsub_timer = None

        name = f"{ble_data.name} {ble_data.identifier}"
        self._attr_unique_id = f"{name}_print_duration"
        self._attr_device_info = _device_info(ble_data)

    async def async_added_to_hass(self) -> None:
        """Register callback when entity is added."""
        await super().async_added_to_hass()
        self._device.callback_printing = self._handle_printing_update

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callback when entity is removed."""
        await super().async_will_remove_from_hass()
        self._device.callback_printing = None
        self._stop_timer()

    def _start_timer(self) -> None:
        """Start the timer for real-time updates."""
        if self._unsub_timer is None:
            self._unsub_timer = async_track_time_interval(
                self.hass,
                self._update_elapsed_time,
                timedelta(seconds=1),
            )

    def _stop_timer(self) -> None:
        """Stop the timer."""
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None

    @callback
    def _update_elapsed_time(self, now=None) -> None:
        """Update elapsed time every second."""
        self.async_write_ha_state()

    @callback
    def _handle_printing_update(self) -> None:
        """Handle printing state update."""
        if self._device.is_printing:
            self._start_timer()
        else:
            self._stop_timer()
        self.async_write_ha_state()

    @property
    def native_value(self) -> float:
        """Return the print duration in seconds."""
        return round(self._device.print_duration, 1)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        duration = self._device.print_duration
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        return {
            "formatted": f"{minutes:02d}:{seconds:01d}",
            "is_printing": self._device.is_printing,
        }


class NiimbotPrintProgressSensor(
    CoordinatorEntity[DataUpdateCoordinator[BLEData]], SensorEntity
):
    """Live print progress percentage from GET_PRINT_STATUS polls."""

    _attr_has_entity_name = True
    _attr_name = "Print Progress"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:progress-helper"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        device: NiimbotDevice,
    ) -> None:
        super().__init__(coordinator)
        self._device = device
        name = f"{ble_data.name} {ble_data.identifier}"
        self._attr_unique_id = f"{name}_print_progress"
        self._attr_device_info = _device_info(ble_data)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._device.callback_progress = self._handle_progress_update

    async def async_will_remove_from_hass(self) -> None:
        await super().async_will_remove_from_hass()
        self._device.callback_progress = None

    @callback
    def _handle_progress_update(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> float:
        return round(self._device.print_progress, 1)

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "page": self._device.print_page,
            "page_print_progress": self._device.print_page_print_progress,
            "page_feed_progress": self._device.print_page_feed_progress,
            "is_printing": self._device.is_printing,
        }
