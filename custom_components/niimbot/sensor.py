"""Support for niimbot ble sensors."""

import logging
from datetime import timedelta

from .niimprint import NiimbotDevice, BLEData

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_USE_CLOUD_LABEL_INFO,
    DEFAULT_USE_CLOUD_LABEL_INFO,
)
from .entity import NiimbotBleEntity
from .types import NiimbotConfigEntry

_LOGGER = logging.getLogger(__name__)

SENSORS_MAPPING_TEMPLATE: dict[str, SensorEntityDescription] = {
    "battery": SensorEntityDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "last_error": SensorEntityDescription(
        key="last_error",
        translation_key="last_error",
        icon="mdi:alert-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "density": SensorEntityDescription(
        key="density",
        translation_key="density",
        icon="mdi:printer-3d-nozzle",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "printspeed": SensorEntityDescription(
        key="printspeed",
        translation_key="printspeed",
        icon="mdi:speedometer",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "labeltype": SensorEntityDescription(
        key="labeltype",
        translation_key="labeltype",
        icon="mdi:tag-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "protocol_version": SensorEntityDescription(
        key="protocol_version",
        translation_key="protocol_version",
        icon="mdi:numeric",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    "colour_support": SensorEntityDescription(
        key="colour_support",
        translation_key="colour_support",
        icon="mdi:palette",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    "print_area": SensorEntityDescription(
        key="print_area",
        translation_key="print_area",
        icon="mdi:resize",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
}

RFID_SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    "labels_remaining": SensorEntityDescription(
        key="labels_remaining",
        translation_key="labels_remaining",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:label-multiple",
    ),
    "labels_used": SensorEntityDescription(
        key="labels_used",
        translation_key="labels_used",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:label-off",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "labels_total": SensorEntityDescription(
        key="labels_total",
        translation_key="labels_total",
        icon="mdi:label",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "consumable_usage": SensorEntityDescription(
        key="consumable_usage",
        translation_key="consumable_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:percent",
    ),
    "label_sku": SensorEntityDescription(
        key="label_sku",
        translation_key="label_sku",
        icon="mdi:barcode",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "consumable_type": SensorEntityDescription(
        key="consumable_type",
        translation_key="consumable_type",
        icon="mdi:tag-text",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "tag_uuid": SensorEntityDescription(
        key="tag_uuid",
        translation_key="tag_uuid",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
}

RIBBON_RFID_SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    "ribbon_remaining": SensorEntityDescription(
        key="ribbon_remaining",
        translation_key="ribbon_remaining",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:filmstrip",
    ),
    "ribbon_used": SensorEntityDescription(
        key="ribbon_used",
        translation_key="ribbon_used",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:filmstrip-box",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "ribbon_total": SensorEntityDescription(
        key="ribbon_total",
        translation_key="ribbon_total",
        icon="mdi:film",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "ribbon_usage": SensorEntityDescription(
        key="ribbon_usage",
        translation_key="ribbon_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:percent",
    ),
    "ribbon_sku": SensorEntityDescription(
        key="ribbon_sku",
        translation_key="ribbon_sku",
        icon="mdi:barcode",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "ribbon_type": SensorEntityDescription(
        key="ribbon_type",
        translation_key="ribbon_type",
        icon="mdi:tag-text",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "ribbon_tag_uuid": SensorEntityDescription(
        key="ribbon_tag_uuid",
        translation_key="ribbon_tag_uuid",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
}

ADVANCED2_SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    "printhead_temperature": SensorEntityDescription(
        key="printhead_temperature",
        translation_key="printhead_temperature",
        icon="mdi:thermometer",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "wifi_rssi": SensorEntityDescription(
        key="wifi_rssi",
        translation_key="wifi_rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:wifi",
    ),
    "voltage_state": SensorEntityDescription(
        key="voltage_state",
        translation_key="voltage_state",
        icon="mdi:flash-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    "lighting_error": SensorEntityDescription(
        key="lighting_error",
        translation_key="lighting_error",
        icon="mdi:lightbulb-alert-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
}

CLOUD_LABEL_INFO_DESCRIPTION = SensorEntityDescription(
    key="cloud_label_info",
    translation_key="cloud_label_info",
    icon="mdi:cloud-search-outline",
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NiimbotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Niimbot BLE sensors."""
    coordinator = entry.runtime_data.coordinator
    device = entry.runtime_data.device

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
    entities.append(NiimbotLastFailureSensor(coordinator, coordinator.data, device))
    entities.append(NiimbotErrorCountSensor(coordinator, coordinator.data, device))

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

    def _add_ribbon_rfid_entities() -> list[SensorEntity]:
        added: list[SensorEntity] = []
        if not device.supports_ribbon_rfid():
            return added
        for key, description in RIBBON_RFID_SENSOR_DESCRIPTIONS.items():
            if key in created_keys:
                continue
            added.append(
                NiimbotRibbonRfidSensor(
                    coordinator, coordinator.data, description, device
                )
            )
            created_keys.add(key)
        return added

    def _add_advanced2_entities() -> list[SensorEntity]:
        added: list[SensorEntity] = []
        for key, description in ADVANCED2_SENSOR_DESCRIPTIONS.items():
            if key in created_keys:
                continue
            if key in coordinator.data.sensors:
                added.append(
                    NiimbotSensor(coordinator, coordinator.data, description)
                )
                created_keys.add(key)
        return added

    entities.extend(_add_rfid_entities())
    entities.extend(_add_ribbon_rfid_entities())
    entities.extend(_add_advanced2_entities())

    use_cloud = bool(
        entry.options.get(
            CONF_USE_CLOUD_LABEL_INFO,
            entry.data.get(CONF_USE_CLOUD_LABEL_INFO, DEFAULT_USE_CLOUD_LABEL_INFO),
        )
    )
    if use_cloud:
        entities.append(
            NiimbotCloudLabelInfoSensor(
                coordinator, coordinator.data, CLOUD_LABEL_INFO_DESCRIPTION, device
            )
        )

    async_add_entities(entities)

    # Model / RFID capability / Advanced2 sensors may be unknown at setup.
    # Keep listening until entities are created or capabilities settled.
    need_label = "labels_remaining" not in created_keys
    need_ribbon = "ribbon_remaining" not in created_keys
    need_adv2 = len(created_keys) < (
        len(sensors_mapping)
        + len(RFID_SENSOR_DESCRIPTIONS)
        + len(RIBBON_RFID_SENSOR_DESCRIPTIONS)
        + len(ADVANCED2_SENSOR_DESCRIPTIONS)
    )
    if need_label or need_ribbon or need_adv2:

        @callback
        def _on_coordinator_update() -> None:
            meta = device.get_model_meta()
            new_entities: list[SensorEntity] = []
            if "labels_remaining" not in created_keys:
                if meta is not None and not device.supports_label_rfid():
                    pass
                else:
                    new_entities.extend(_add_rfid_entities())
            if "ribbon_remaining" not in created_keys:
                if meta is not None and not device.supports_ribbon_rfid():
                    pass
                else:
                    new_entities.extend(_add_ribbon_rfid_entities())
            new_entities.extend(_add_advanced2_entities())

            if new_entities:
                async_add_entities(new_entities)
            label_done = (
                "labels_remaining" in created_keys
                or (meta is not None and not device.supports_label_rfid())
            )
            ribbon_done = (
                "ribbon_remaining" in created_keys
                or (meta is not None and not device.supports_ribbon_rfid())
            )
            adv2_done = all(
                k in created_keys for k in ADVANCED2_SENSOR_DESCRIPTIONS
            ) or (device.heartbeat_variant not in (None, "advanced2"))
            if label_done and ribbon_done and adv2_done:
                unsub()

        unsub = coordinator.async_add_listener(_on_coordinator_update)


class NiimbotSensor(
    NiimbotBleEntity, CoordinatorEntity[DataUpdateCoordinator[BLEData]], SensorEntity
):
    """Niimbot BLE sensors for the device."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Populate the niimbot entity with relevant data."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._bind_printer(ble_data, entity_description.key)

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
        """Printer error code plus the BLE session that produced it.

        The session breakdown (failed stage, radio, per-stage timings,
        likely_cause) is kept until the next print error, so a later status
        poll does not replace it.
        """
        attrs: dict = {}
        if self._device.last_error_time is not None:
            attrs["timestamp"] = self._device.last_error_time
        if self._device.last_error_report:
            attrs.update(self._device.last_error_report)
        return attrs or None


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
        if self.entity_description.key == "labels_remaining":
            return dict(self._device._rfid_attrs) if self._device._rfid_attrs else None
        if self.entity_description.key == "label_sku":
            attrs = self._device._cloud_label_attrs
            return dict(attrs) if attrs else None
        return None


class NiimbotCloudLabelInfoSensor(NiimbotSensor):
    """Cloud catalogue lookup result (status + request time)."""

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
    def native_value(self) -> StateType:
        state = self._device._cloud_lookup_state
        if not state:
            return None
        status = state.get("status")
        if status == "found":
            return state.get("label_name") or "found"
        return status

    @property
    def extra_state_attributes(self) -> dict | None:
        state = self._device._cloud_lookup_state
        if not state:
            return None
        return {key: value for key, value in state.items() if value is not None}


class NiimbotRibbonRfidSensor(NiimbotSensor):
    """Ribbon RFID sensor with optional attributes on remaining length."""

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
        if self.entity_description.key != "ribbon_remaining":
            return None
        attrs = self._device._ribbon_rfid_attrs
        return dict(attrs) if attrs else None


class NiimbotPrintDurationSensor(
    NiimbotBleEntity, CoordinatorEntity[DataUpdateCoordinator[BLEData]], SensorEntity
):
    """Niimbot print duration sensor."""

    _attr_translation_key = "print_duration"
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

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
        self._bind_printer(ble_data, "print_duration")

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
        """Elapsed time, plus the last print's BLE session breakdown.

        The breakdown (outcome, radio, per-stage timings such as connect_s /
        transfer_s / finish_s, and likely_cause on failure) is omitted while a
        job is running so the ticking state is not paired with the previous job.
        """
        duration = self._device.print_duration
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        attrs: dict = {
            "formatted": f"{minutes:02d}:{seconds:01d}",
            "is_printing": self._device.is_printing,
        }
        report = self._device.reports.last
        if not self._device.is_printing and report:
            attrs.update(report)
        return attrs


class NiimbotPrintProgressSensor(
    NiimbotBleEntity, CoordinatorEntity[DataUpdateCoordinator[BLEData]], SensorEntity
):
    """Live print progress percentage from GET_PRINT_STATUS polls."""

    _attr_translation_key = "print_progress"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:progress-helper"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        device: NiimbotDevice,
    ) -> None:
        super().__init__(coordinator)
        self._device = device
        self._bind_printer(ble_data, "print_progress")

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


class NiimbotLastFailureSensor(
    NiimbotBleEntity, CoordinatorEntity[DataUpdateCoordinator[BLEData]], SensorEntity
):
    """When a BLE session last failed, with that session's breakdown.

    The attributes are the same keys as Print Duration's report, kept until
    the next failure so a later success does not erase them. A status poll
    that never connects is left out: the printer is often asleep, and counting
    it would replace the last real failure on every scan.
    """

    _attr_translation_key = "last_failure"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-alert-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        device: NiimbotDevice,
    ) -> None:
        super().__init__(coordinator)
        self._device = device
        self._bind_printer(ble_data, "last_failure")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._device.add_session_listener(self._handle_session_update)

    async def async_will_remove_from_hass(self) -> None:
        await super().async_will_remove_from_hass()
        self._device.remove_session_listener(self._handle_session_update)

    @callback
    def _handle_session_update(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self):
        return self._device.last_failure_at

    @property
    def extra_state_attributes(self) -> dict | None:
        """The breakdown of the session that failed at this time.

        ``reports.last_failure`` is kept until the next counted failure. A
        later successful print replaces ``reports.last`` only.
        """
        return self._device.reports.last_failure


class NiimbotErrorCountSensor(
    NiimbotBleEntity, CoordinatorEntity[DataUpdateCoordinator[BLEData]], SensorEntity
):
    """How many BLE sessions have failed since this entry was loaded.

    The count starts over on every reload, so it is not a long-term statistic.
    A status poll that fails before the link is up is not counted. A print
    failure, or a poll that connected and then failed, is.
    """

    _attr_translation_key = "error_count"
    _attr_icon = "mdi:alert-circle-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[BLEData],
        ble_data: BLEData,
        device: NiimbotDevice,
    ) -> None:
        super().__init__(coordinator)
        self._device = device
        self._bind_printer(ble_data, "error_count")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._device.add_session_listener(self._handle_session_update)

    async def async_will_remove_from_hass(self) -> None:
        await super().async_will_remove_from_hass()
        self._device.remove_session_listener(self._handle_session_update)

    @callback
    def _handle_session_update(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> int:
        return self._device.error_count
