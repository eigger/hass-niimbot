"""DeviceInfo is built with keyword arguments only (TypedDict and dataclass)."""

from __future__ import annotations

import ast
from pathlib import Path

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo

from custom_components.niimbot.entity import device_info
from custom_components.niimbot.niimprint import BLEData

PACKAGE = Path(__file__).parents[3] / "custom_components" / "niimbot"

# Deprecated since HA 2026.12 (removed 2027.12); ATTR_NAME is not deprecated.
DEPRECATED_CONSTANTS = {
    "ATTR_CONFIGURATION_URL",
    "ATTR_CONNECTIONS",
    "ATTR_DEFAULT_NAME",
    "ATTR_HW_VERSION",
    "ATTR_IDENTIFIERS",
    "ATTR_MANUFACTURER",
    "ATTR_MODEL",
    "ATTR_MODEL_ID",
    "ATTR_SERIAL_NUMBER",
    "ATTR_SUGGESTED_AREA",
    "ATTR_SW_VERSION",
    "ATTR_VIA_DEVICE",
}

ADDRESS = "AA:BB:CC:DD:EE:FF"


def _base(**extra: str) -> DeviceInfo:
    return DeviceInfo(
        connections={(CONNECTION_BLUETOOTH, ADDRESS)},
        name="D110 1234",
        manufacturer="Niimbot",
        **extra,
    )


def test_known_values_are_present() -> None:
    data = BLEData(
        name="D110",
        identifier="1234",
        address=ADDRESS,
        model="D110",
        hw_version="1.2",
        sw_version="3.4",
        serial_number="SN1",
    )
    assert device_info(data) == _base(
        model="D110", hw_version="1.2", sw_version="3.4", serial_number="SN1"
    )


def test_unknown_and_empty_values_are_omitted() -> None:
    data = BLEData(name="D110", identifier="1234", address=ADDRESS)
    assert device_info(data) == _base()
    partial = BLEData(
        name="D110", identifier="1234", address=ADDRESS, sw_version="3.4", model=""
    )
    assert device_info(partial) == _base(sw_version="3.4")


def test_no_deprecated_device_info_constants_or_item_assignment() -> None:
    for path in PACKAGE.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "homeassistant.const"
            ):
                names = {alias.name for alias in node.names}
                assert not names & DEPRECATED_CONSTANTS, path
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Subscript)
                        and isinstance(target.value, ast.Name)
                        and target.value.id in {"info", "device_info"}
                    ):
                        raise AssertionError(f"{path}:{node.lineno} item assignment")
