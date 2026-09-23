"""niimbot.print / niimbot.refresh_info through a real Home Assistant.

The renderer and the BLE transfer are the real call path up to print_image,
which is stubbed. Target resolution is the code under test.
"""

from __future__ import annotations

from unittest.mock import patch

from bleak.backends.device import BLEDevice
from conftest import ADDRESS, ADDRESS_2, device_of, setup_entry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import pytest

from custom_components.niimbot.const import DOMAIN
from custom_components.niimbot.niimprint.parser import NiimbotDevice
from custom_components.niimbot.services import SERVICE_PRINT, SERVICE_REFRESH_INFO

PAYLOAD = [{"type": "rectangle", "x_start": 0, "y_start": 0, "x_end": 10, "y_end": 10, "fill": "black"}]


def _ble_device(address: str) -> BLEDevice:
    return BLEDevice(address, "Niimbot", {})


async def test_print_targets_the_selected_printer(
    hass: HomeAssistant, enable_bluetooth: None
) -> None:
    """A device target prints on that printer and not the other."""
    first = await setup_entry(hass, address=ADDRESS)
    await setup_entry(hass, address=ADDRESS_2)
    printed: list[str] = []

    async def fake_print(self, ble_device, image, **kwargs):
        printed.append(self.address)
        return {"ok": True}

    with (
        patch.object(NiimbotDevice, "print_image", fake_print),
        patch(
            "custom_components.niimbot.services.bluetooth.async_ble_device_from_address",
            lambda hass, address, connectable=True: _ble_device(address),
        ),
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_PRINT,
            {
                "device_id": device_of(hass, ADDRESS, entry_id=first.entry_id).id,
                "payload": PAYLOAD,
                "width": 20,
                "height": 20,
            },
            blocking=True,
        )

    assert printed == [ADDRESS]


async def test_print_without_a_target_uses_the_only_printer(
    hass: HomeAssistant, enable_bluetooth: None
) -> None:
    """Existing automations that omit a target still reach the single printer."""
    await setup_entry(hass)
    printed: list[str] = []

    async def fake_print(self, ble_device, image, **kwargs):
        printed.append(self.address)
        return {"ok": True}

    with (
        patch.object(NiimbotDevice, "print_image", fake_print),
        patch(
            "custom_components.niimbot.services.bluetooth.async_ble_device_from_address",
            lambda hass, address, connectable=True: _ble_device(address),
        ),
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_PRINT,
            {"payload": PAYLOAD, "width": 20, "height": 20},
            blocking=True,
        )

    assert printed == [ADDRESS]


async def test_print_without_a_target_rejects_two_printers(
    hass: HomeAssistant, enable_bluetooth: None
) -> None:
    """Two printers and no target is an error instead of printing on the last one."""
    await setup_entry(hass, address=ADDRESS)
    await setup_entry(hass, address=ADDRESS_2)

    with pytest.raises(HomeAssistantError, match="More than one Niimbot printer"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_PRINT,
            {"payload": PAYLOAD, "width": 20, "height": 20},
            blocking=True,
        )


async def test_preview_does_not_open_a_connection(
    hass: HomeAssistant, enable_bluetooth: None
) -> None:
    """preview renders the image and skips the BLE print."""
    await setup_entry(hass)
    printed: list[str] = []

    async def fake_print(self, ble_device, image, **kwargs):
        printed.append(self.address)
        return {"ok": True}

    with patch.object(NiimbotDevice, "print_image", fake_print):
        response = await hass.services.async_call(
            DOMAIN,
            SERVICE_PRINT,
            {"payload": PAYLOAD, "width": 20, "height": 20, "preview": True},
            blocking=True,
            return_response=True,
        )

    assert printed == []
    assert response["image"].startswith("data:image/png;base64,")


async def test_refresh_info_targets_one_printer(
    hass: HomeAssistant, enable_bluetooth: None
) -> None:
    """refresh_info follows the same device target as print."""
    await setup_entry(hass, address=ADDRESS)
    second = await setup_entry(hass, address=ADDRESS_2)
    refreshed: list[str] = []

    async def fake_refresh(self, ble_device):
        refreshed.append(self.address)
        self.ble_data.density = 3
        return self.ble_data

    with (
        patch.object(NiimbotDevice, "refresh_info", fake_refresh),
        patch(
            "custom_components.niimbot.services.bluetooth.async_ble_device_from_address",
            lambda hass, address, connectable=True: _ble_device(address),
        ),
    ):
        response = await hass.services.async_call(
            DOMAIN,
            SERVICE_REFRESH_INFO,
            {"device_id": device_of(hass, ADDRESS_2, entry_id=second.entry_id).id},
            blocking=True,
            return_response=True,
        )

    assert refreshed == [ADDRESS_2]
    assert response["density"] == 3
