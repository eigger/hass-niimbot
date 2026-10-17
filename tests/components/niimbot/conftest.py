"""Test configuration.

Protocol and model tests do not start Home Assistant. Integration tests request
the ``hass`` fixture; custom integrations are enabled only for those.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.niimbot.const import DOMAIN

ADDRESS = "AA:BB:CC:DD:EE:01"
ADDRESS_2 = "AA:BB:CC:DD:EE:02"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(request: pytest.FixtureRequest) -> None:
    """Load custom_components/niimbot only for tests that start Home Assistant."""
    if "hass" in request.fixturenames:
        request.getfixturevalue("enable_custom_integrations")


async def setup_entry(
    hass: HomeAssistant,
    *,
    address: str = ADDRESS,
    data: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> MockConfigEntry:
    """Create and load a config entry. No advertisement is required: setup
    continues with the last-known (empty) data when the printer is absent."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=address,
        title=f"Niimbot {address[-5:]}",
        data=data or {},
        options=options or {},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def device_of(
    hass: HomeAssistant, address: str = ADDRESS, *, entry_id: str
) -> dr.DeviceEntry:
    """The HA device created from the printer's entity device info."""
    devices = [
        device
        for device in dr.async_entries_for_config_entry(dr.async_get(hass), entry_id)
        if (CONNECTION_BLUETOOTH, address) in device.connections
    ]
    assert len(devices) == 1, address
    device = devices[0]
    return device


@pytest.fixture
def printer_response():
    """External printer client responses; retain polling and entity logic."""
    from unittest.mock import AsyncMock, MagicMock
    from custom_components.niimbot.niimprint.printer import PrinterClient, InfoEnum

    printer = MagicMock(spec=PrinterClient)
    printer.get_info = AsyncMock(
        side_effect=lambda key: {
            InfoEnum.DEVICESERIAL: "TEST00001",
            InfoEnum.HARDVERSION: 1,
            InfoEnum.SOFTVERSION: 1,
            InfoEnum.DEVICETYPE: 32,
            InfoEnum.DENSITY: 3,
            InfoEnum.PRINTSPEED: 2,
            InfoEnum.LABELTYPE: 1,
            InfoEnum.AUTOSHUTDOWNTIME: 1,
            InfoEnum.BATTERY: 4,
        }.get(key)
    )
    printer.get_printer_status_data = AsyncMock(return_value=None)
    printer.get_sound = AsyncMock(return_value=True)
    printer.heartbeat = AsyncMock(
        return_value={
            "powerlevel": 4,
            "closingstate": 0,
            "paperstate": 0,
            "rfidreadstate": 0,
        }
    )
    printer.heartbeat_payload = None
    return printer


def make_ble_device(address: str = ADDRESS):
    """Build an external BLE response for old and current Bleak signatures."""
    import inspect
    from bleak.backends.device import BLEDevice

    kwargs = {"rssi": -60} if "rssi" in inspect.signature(BLEDevice).parameters else {}
    return BLEDevice(address, "Niimbot", {}, **kwargs)
