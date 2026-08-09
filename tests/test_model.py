"""Tests for niimprint model utilities."""

from custom_components.niimbot.niimprint.model import material_name, consumable_type_name


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
