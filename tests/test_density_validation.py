"""Tests for print density range resolution used by the print service."""

import pytest

from custom_components.niimbot.niimprint.model import (
    density_range,
    get_printer_meta_by_id,
    resolve_density,
)


def test_density_range_falls_back_when_model_unknown():
    assert density_range(None) == (1, 5, 3)


def test_density_range_reads_vendor_table():
    assert density_range(get_printer_meta_by_id(4096)) == (1, 5, 3)  # B1
    assert density_range(get_printer_meta_by_id(2049)) == (1, 15, 10)  # B21 Pro
    assert density_range(get_printer_meta_by_id(53250)) == (1, 20, 15)


def test_resolve_density_rejects_out_of_range():
    meta = get_printer_meta_by_id(4096)
    with pytest.raises(ValueError, match="supported range: 1-5"):
        resolve_density(meta, 6)
    with pytest.raises(ValueError, match="supported range: 1-5"):
        resolve_density(meta, 0)


def test_resolve_density_accepts_in_range_and_model_maximum():
    assert resolve_density(get_printer_meta_by_id(4096), 5) == 5
    assert resolve_density(get_printer_meta_by_id(53250), 20) == 20


def test_resolve_density_defaults_to_model_default():
    # Models whose range does not include 3 must not be handed the old
    # hard-coded default.
    meta = get_printer_meta_by_id(51457)
    assert density_range(meta) == (6, 15, 10)
    assert resolve_density(meta, None) == 10
    assert resolve_density(None, None) == 3
