"""Unit tests for the optional cloud label info sensor."""

from custom_components.niimbot.niimprint.parser import NiimbotDevice
from custom_components.niimbot.sensor import (
    CLOUD_LABEL_INFO_DESCRIPTION,
    NiimbotCloudLabelInfoSensor,
)


class _FakeCoordinator:
    def __init__(self, data):
        self.data = data
        self.last_update_success = True
        self.config_entry = None


def test_cloud_label_info_sensor_exposes_status_and_requested_at():
    device = NiimbotDevice("11:22:33:44:55:66")
    device._cloud_lookup_state = {
        "status": "found",
        "barcode": "10262260",
        "requested_at": "2026-08-09T05:45:00+00:00",
        "source": "network",
        "label_name": None,
        "label_width_mm": 30,
        "label_height_mm": 50,
        "preview_url": "https://example.com/p.png",
    }
    coordinator = _FakeCoordinator(device.ble_data)
    sensor = NiimbotCloudLabelInfoSensor(
        coordinator, device.ble_data, CLOUD_LABEL_INFO_DESCRIPTION, device
    )

    assert sensor.native_value == "found"
    attrs = sensor.extra_state_attributes
    assert attrs["barcode"] == "10262260"
    assert attrs["requested_at"] == "2026-08-09T05:45:00+00:00"
    assert attrs["label_width_mm"] == 30
    assert attrs["status"] == "found"


def test_cloud_label_info_sensor_prefers_label_name_as_state():
    device = NiimbotDevice("11:22:33:44:55:66")
    device._cloud_lookup_state = {
        "status": "found",
        "barcode": "1",
        "requested_at": "2026-08-09T05:45:00+00:00",
        "label_name": "White 50x30",
    }
    coordinator = _FakeCoordinator(device.ble_data)
    sensor = NiimbotCloudLabelInfoSensor(
        coordinator, device.ble_data, CLOUD_LABEL_INFO_DESCRIPTION, device
    )
    assert sensor.native_value == "White 50x30"


def test_cloud_label_info_sensor_empty_before_lookup():
    device = NiimbotDevice("11:22:33:44:55:66")
    coordinator = _FakeCoordinator(device.ble_data)
    sensor = NiimbotCloudLabelInfoSensor(
        coordinator, device.ble_data, CLOUD_LABEL_INFO_DESCRIPTION, device
    )
    assert sensor.native_value is None
    assert sensor.extra_state_attributes is None
