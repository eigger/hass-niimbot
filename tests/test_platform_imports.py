"""Smoke imports for Home Assistant platform modules."""

import importlib

import pytest


PLATFORM_MODULES = (
    "custom_components.niimbot.sensor",
    "custom_components.niimbot.binary_sensor",
    "custom_components.niimbot.button",
    "custom_components.niimbot.switch",
    "custom_components.niimbot.select",
    "custom_components.niimbot.image",
)


@pytest.mark.parametrize("module_name", PLATFORM_MODULES)
def test_platform_module_imports(module_name: str) -> None:
    """Platform modules must import under the conftest HA stubs."""
    mod = importlib.import_module(module_name)
    assert hasattr(mod, "async_setup_entry")


def test_button_module_defines_action_entities() -> None:
    button = importlib.import_module("custom_components.niimbot.button")
    for name in (
        "NiimbotCancelPrintButton",
        "NiimbotPrinterResetButton",
        "NiimbotCalibrateHeightButton",
        "NiimbotCalibrateLabelPositionButton",
        "NiimbotPrintTestPageButton",
    ):
        assert hasattr(button, name), f"missing {name}"
