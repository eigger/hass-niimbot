"""Test configuration.

Protocol and model tests do not start Home Assistant. Integration tests request
the ``hass`` fixture; custom integrations are enabled only for those.
"""

from __future__ import annotations

# <!-- hass-standards:domain-fixtures:start -->
# Use pytest_homeassistant_custom_component.common.MockConfigEntry for
# mock_config_entry when the integration uses config entries.
# Define mock_client only when an external communication client is present.
# Mock external communication boundaries, never Home Assistant core modules.
# Keep integration-specific fixtures below this managed block.
# <!-- hass-standards:domain-fixtures:end -->

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.niimbot.const import DOMAIN

ADDRESS = "AA:BB:CC:DD:EE:01"
ADDRESS_2 = "AA:BB:CC:DD:EE:02"


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


@pytest.fixture
def mock_config_entry():
    """A real config entry with the address identity used by Niimbot setup."""
    return MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, title="Niimbot", data={})


@pytest.fixture
def mock_client(printer_response):
    """Responses from the external printer protocol client."""
    return printer_response


@pytest.fixture
async def payload_example_setup(hass, enable_bluetooth, mock_config_entry):
    """Load the real entry, platforms and actions without a nearby printer."""
    from homeassistant.helpers import entity_registry as er

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    # Give the YAML a reproducible real integration-owned target.
    registry = er.async_get(hass)
    entity = next(
        entity
        for entity in er.async_entries_for_config_entry(
            registry, mock_config_entry.entry_id
        )
        if entity.domain == "image"
    )
    registry.async_update_entity(entity.entity_id, new_entity_id="image.niimbot_label")
    yield
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()


@pytest.fixture
def payload_example_adapter():
    """Bind the same production renderer/context and real normalized HA data."""

    def adapter(hass, example_metadata, normalized_action, schema_data):
        from functools import partial
        import inspect
        from homeassistant.core import ServiceCall
        from hass_standards_payload import PreparedPayload
        from custom_components.niimbot.render import _make_context, render_image

        call = ServiceCall(
            domain=DOMAIN,
            service="print",
            data=schema_data,
            **(
                {"hass": hass}
                if "hass" in inspect.signature(ServiceCall).parameters
                else {}
            ),
        )
        return PreparedPayload(
            payload=schema_data.get("payload", ""),
            context=_make_context(
                hass, default_font="ppb.ttf", palette=["black", "white"]
            ),
            render_options={
                "width": schema_data.get("width", 400),
                "height": schema_data.get("height", 240),
                "rotate": schema_data.get("rotate", 0),
                "rotate_mode": "image",
                "background": schema_data.get("background", "white"),
                "dither": False,
            },
            prepare=partial(render_image, "image.niimbot_label", call, hass),
        )

    return adapter
