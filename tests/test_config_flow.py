"""Tests for Niimbot BLE config flow."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import CONF_ADDRESS, CONF_SCAN_INTERVAL
from custom_components.niimbot.config_flow import NiimbotConfigFlow, Discovery
from custom_components.niimbot.const import (
    CONF_CONFIRM_EVERY_NTH_PRINT_LINE,
    CONF_KEEP_CONNECTION,
    CONF_USE_CLOUD_LABEL_INFO,
    CONF_WAIT_BETWEEN_EACH_PRINT_LINE,
    DEFAULT_CONFIRM_EVERY_NTH_PRINT_LINE,
    DEFAULT_KEEP_CONNECTION,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USE_CLOUD_LABEL_INFO,
    DEFAULT_WAIT_BETWEEN_EACH_PRINT_LINE,
    NIIMBOT_SERVICE_UUID,
)


def _make_discovery_info(
    address: str,
    local_name: str | None = None,
    device_name: str | None = None,
    service_uuids: list[str] | None = None,
):
    info = MagicMock()
    info.address = address
    info.advertisement = MagicMock()
    info.advertisement.local_name = local_name
    info.device = MagicMock()
    info.device.name = device_name
    info.service_uuids = service_uuids if service_uuids is not None else []
    return info


def test_async_step_user_filters_by_service_uuid():
    """Test that async_step_user only lists devices containing NIIMBOT_SERVICE_UUID."""
    async def _test():
        flow = NiimbotConfigFlow()
        flow.hass = MagicMock()

        d11_clone = _make_discovery_info(
            "AA:BB:CC:DD:EE:01",
            local_name="D11_BF25_BLE",
            service_uuids=[NIIMBOT_SERVICE_UUID],
        )
        nameless_niimbot = _make_discovery_info(
            "AA:BB:CC:DD:EE:02",
            local_name=None,
            device_name=None,
            service_uuids=[NIIMBOT_SERVICE_UUID],
        )
        samsung_tv = _make_discovery_info(
            "11:22:33:44:55:66",
            local_name="[TV] Samsung",
            service_uuids=["00001800-0000-1000-8000-00805f9b34fb"],
        )
        random_beacon = _make_discovery_info(
            "77:88:99:AA:BB:CC",
            local_name=None,
            service_uuids=[],
        )

        discovered = [d11_clone, nameless_niimbot, samsung_tv, random_beacon]

        with patch(
            "custom_components.niimbot.config_flow.async_discovered_service_info",
            return_value=discovered,
        ), patch.object(flow, "_async_current_ids", return_value=set()):
            result = await flow.async_step_user()

        assert result["type"] == "form"
        assert result["step_id"] == "user"

        # Only the 2 Niimbot devices should be discovered
        assert "AA:BB:CC:DD:EE:01" in flow._discovered_devices
        assert flow._discovered_devices["AA:BB:CC:DD:EE:01"].name == "D11_BF25_BLE"

        assert "AA:BB:CC:DD:EE:02" in flow._discovered_devices
        assert flow._discovered_devices["AA:BB:CC:DD:EE:02"].name == "Niimbot (AA:BB:CC:DD:EE:02)"

        # Non-Niimbot devices must be filtered out
        assert "11:22:33:44:55:66" not in flow._discovered_devices
        assert "77:88:99:AA:BB:CC" not in flow._discovered_devices

    asyncio.run(_test())


def test_async_step_user_no_devices_found():
    """Test abort when no Niimbot devices are found."""
    async def _test():
        flow = NiimbotConfigFlow()
        flow.hass = MagicMock()

        samsung_tv = _make_discovery_info(
            "11:22:33:44:55:66",
            local_name="[TV] Samsung",
            service_uuids=["00001800-0000-1000-8000-00805f9b34fb"],
        )

        with patch(
            "custom_components.niimbot.config_flow.async_discovered_service_info",
            return_value=[samsung_tv],
        ), patch.object(flow, "_async_current_ids", return_value=set()):
            result = await flow.async_step_user()

        assert result["type"] == "abort"
        assert result["reason"] == "no_devices_found"

    asyncio.run(_test())


def test_async_step_user_creates_entry():
    """Test user selecting a device creates config entry."""
    async def _test():
        flow = NiimbotConfigFlow()
        flow.hass = MagicMock()
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})

        info = _make_discovery_info(
            "AA:BB:CC:DD:EE:01",
            local_name="D11_BF25_BLE",
            service_uuids=[NIIMBOT_SERVICE_UUID],
        )
        flow._discovered_devices = {"AA:BB:CC:DD:EE:01": Discovery("D11_BF25_BLE", info)}

        user_input = {
            CONF_ADDRESS: "AA:BB:CC:DD:EE:01",
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_WAIT_BETWEEN_EACH_PRINT_LINE: DEFAULT_WAIT_BETWEEN_EACH_PRINT_LINE,
            CONF_CONFIRM_EVERY_NTH_PRINT_LINE: DEFAULT_CONFIRM_EVERY_NTH_PRINT_LINE,
            CONF_KEEP_CONNECTION: DEFAULT_KEEP_CONNECTION,
            CONF_USE_CLOUD_LABEL_INFO: DEFAULT_USE_CLOUD_LABEL_INFO,
        }

        result = await flow.async_step_user(user_input=user_input)

        flow.async_set_unique_id.assert_awaited_once_with("AA:BB:CC:DD:EE:01", raise_on_progress=False)
        flow.async_create_entry.assert_called_once_with(title="D11_BF25_BLE", data=user_input)
        assert result == {"type": "create_entry"}

    asyncio.run(_test())


def test_async_step_bluetooth():
    """Test bluetooth automatic discovery step."""
    async def _test():
        flow = NiimbotConfigFlow()
        flow.hass = MagicMock()
        flow.context = {}
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_show_form = MagicMock(return_value={"type": "form", "step_id": "bluetooth_confirm"})

        info = _make_discovery_info(
            "AA:BB:CC:DD:EE:01",
            local_name="D11_BF25_BLE",
            service_uuids=[NIIMBOT_SERVICE_UUID],
        )

        result = await flow.async_step_bluetooth(info)

        flow.async_set_unique_id.assert_awaited_once_with("AA:BB:CC:DD:EE:01")
        assert flow.context["title_placeholders"] == {"name": "D11_BF25_BLE"}
        assert result["type"] == "form"
        assert result["step_id"] == "bluetooth_confirm"

    asyncio.run(_test())

