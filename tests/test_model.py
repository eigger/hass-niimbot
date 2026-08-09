"""Tests for niimprint model utilities and RFID parsing."""

from custom_components.niimbot.niimprint.model import consumable_type_name, material_name
from custom_components.niimbot.niimprint.parser import NiimbotDevice


def test_material_name_mapped():
    assert material_name(1) == "Thermal synthetic paper, general"
    assert material_name(19) == "Transparent thermal"
    assert material_name(129) == "PVC tag"


def test_material_name_unmapped():
    assert material_name(999) == "Unknown(999)"


def test_material_name_none():
    assert material_name(None) is None


def test_consumable_type_name_preserved():
    assert consumable_type_name(1) == "WithGaps"
    assert consumable_type_name(5) == "Transparent"
    assert consumable_type_name(19) == "Unknown(19)"


def test_rfid_apply_does_not_overwrite_labeltype():
    device = NiimbotDevice("AA:BB:CC:DD:EE:FF")
    # Simulate PrinterInfo set labeltype
    device.ble_data.labeltype = 1
    device.ble_data.sensors["labeltype"] = "WithGaps"

    rfid_info = {
        "uuid": "1122334455667788",
        "barcode": "SKU123",
        "total_len": 200,
        "used_len": 10,
        "type": 19,  # Transparent thermal
    }
    device._apply_rfid_info(rfid_info)

    # LabelType sensor and ble_data.labeltype should remain unchanged
    assert device.ble_data.labeltype == 1
    assert device.ble_data.sensors["labeltype"] == "WithGaps"

    # Consumable material sensor should map type 19 to Transparent thermal
    assert device.ble_data.sensors["consumable_type"] == "Transparent thermal"


def test_ribbon_rfid_apply_uses_material_name():
    device = NiimbotDevice("AA:BB:CC:DD:EE:FF")

    ribbon_rfid_info = {
        "uuid": "8877665544332211",
        "barcode": "RIBBON123",
        "total_len": 300,
        "used_len": 50,
        "type": 37,  # Satin ribbon
    }
    device._apply_ribbon_rfid_info(ribbon_rfid_info)

    # Ribbon material sensor should map type 37 to Satin ribbon
    assert device.ble_data.sensors["ribbon_type"] == "Satin ribbon"
