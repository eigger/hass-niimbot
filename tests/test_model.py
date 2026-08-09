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


def test_missing_model_ids_resolution():
    from custom_components.niimbot.niimprint.model import (
        PrinterModel,
        PrintDirection,
        RfidClass,
        LabelType,
        get_printer_meta_by_id,
        modelsLibrary,
    )

    new_models_expected = [
        (3840, PrinterModel.H1, 203, PrintDirection.LEFT, 96, RfidClass.LABEL, 1, 3, 2),
        (4098, PrinterModel.B1_SE, 203, PrintDirection.TOP, 384, RfidClass.LABEL, 1, 5, 3),
        (4352, PrinterModel.H1S, 203, PrintDirection.LEFT, 96, RfidClass.LABEL, 1, 3, 2),
        (4610, PrinterModel.EP2M_H, 300, PrintDirection.TOP, 591, RfidClass.LABEL_RIBBON, 1, 5, 3),
        (4868, PrinterModel.K3_ITD, 203, PrintDirection.TOP, 656, RfidClass.LABEL, 1, 5, 3),
        (5120, PrinterModel.C1, 300, PrintDirection.LEFT, 178, RfidClass.RIBBON, 1, 5, 3),
        (5121, PrinterModel.EP1C, 300, PrintDirection.LEFT, 178, RfidClass.RIBBON, 1, 5, 3),
        (6144, PrinterModel.K2, 203, PrintDirection.TOP, 480, RfidClass.LABEL, 1, 5, 3),
        (6400, PrinterModel.M3, 300, PrintDirection.TOP, 851, RfidClass.LABEL_RIBBON, 1, 5, 3),
        (6402, PrinterModel.EP3M, 300, PrintDirection.TOP, 851, RfidClass.LABEL_RIBBON, 1, 5, 3),
        (6656, PrinterModel.B4, 203, PrintDirection.TOP, 832, RfidClass.LABEL, 1, 5, 3),
        (6657, PrinterModel.B4_PRO, 300, PrintDirection.TOP, 1248, RfidClass.LABEL, 1, 5, 3),
        (7168, PrinterModel.K4, 203, PrintDirection.TOP, 656, RfidClass.LABEL, 1, 15, 7),
        (7424, PrinterModel.A1_PRO, 300, PrintDirection.LEFT, 178, RfidClass.NONE, 1, 5, 3),
    ]

    for model_id, exp_model, exp_dpi, exp_dir, exp_px, exp_rfid, exp_min, exp_max, exp_def in new_models_expected:
        meta = get_printer_meta_by_id(model_id)
        assert meta is not None, f"Model ID {model_id} failed to resolve"
        assert meta["model"] == exp_model
        assert meta["dpi"] == exp_dpi
        assert meta["printDirection"] == exp_dir
        assert meta["printheadPixels"] == exp_px
        assert meta["rfid"] == exp_rfid
        assert meta["densityMin"] == exp_min
        assert meta["densityMax"] == exp_max
        assert meta["densityDefault"] == exp_def
        assert meta.get("printheadPixelsEstimated") is True

    # Assert exactly 14 models in modelsLibrary have printheadPixelsEstimated == True
    estimated_entries = [m for m in modelsLibrary if m.get("printheadPixelsEstimated") is True]
    assert len(estimated_entries) == 14

