"""Tests for Niimbot BLE config flow."""

import asyncio
import json
import os
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

MANIFEST_PATH = os.path.join(
    os.path.dirname(__file__), "..", "custom_components", "niimbot", "manifest.json"
)


def _make_discovery_info(
    address: str,
    name: str | None = None,
    service_uuids: list[str] | None = None,
):
    info = MagicMock()
    info.address = address
    info.name = name or address
    info.advertisement = MagicMock()
    info.advertisement.local_name = name
    info.device = MagicMock()
    info.device.name = name
    info.device.address = address
    info.service_uuids = service_uuids if service_uuids is not None else []
    return info


def test_manifest_local_name_matchers_have_no_wildcard_in_first_3_chars():
    """Test that all local_name matchers in manifest.json obey HA's 3-char prefix rule.

    Home Assistant's bluetooth indexer (_local_name_to_index_key) raises ValueError
    if '*' or '[' appears in the first 3 characters of any local_name matcher.
    """
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for entry in manifest.get("bluetooth", []):
        if local_name := entry.get("local_name"):
            assert len(local_name) >= 3, f"Matcher too short: {local_name}"
            prefix = local_name[:3]
            assert "*" not in prefix and "[" not in prefix, (
                f"Invalid matcher '{local_name}': first 3 chars '{prefix}' cannot contain wildcards"
            )


def test_async_step_user_filters_by_service_uuid_and_name():
    """Test that async_step_user prioritises devices matching NIIMBOT_SERVICE_UUID or known prefixes."""
    async def _test():
        flow = NiimbotConfigFlow()
        flow.hass = MagicMock()

        d11_clone = _make_discovery_info(
            "AA:BB:CC:DD:EE:01",
            name="D11_BF25_BLE",
            service_uuids=[NIIMBOT_SERVICE_UUID],
        )
        nameless_niimbot = _make_discovery_info(
            "AA:BB:CC:DD:EE:02",
            name=None,
            service_uuids=[NIIMBOT_SERVICE_UUID],
        )
        b21_printer_no_uuid = _make_discovery_info(
            "AA:BB:CC:DD:EE:03",
            name="B21-123456",
            service_uuids=[],
        )
        samsung_tv = _make_discovery_info(
            "11:22:33:44:55:66",
            name="[TV] Samsung",
            service_uuids=["00001800-0000-1000-8000-00805f9b34fb"],
        )
        random_beacon = _make_discovery_info(
            "77:88:99:AA:BB:CC",
            name=None,
            service_uuids=[],
        )

        discovered = [d11_clone, nameless_niimbot, b21_printer_no_uuid, samsung_tv, random_beacon]

        with patch(
            "custom_components.niimbot.config_flow.async_discovered_service_info",
            return_value=discovered,
        ), patch.object(flow, "_async_current_ids", return_value=set()):
            result = await flow.async_step_user()

        assert result["type"] == "form"
        assert result["step_id"] == "user"

        # The 3 Niimbot-matching devices should be discovered
        assert "AA:BB:CC:DD:EE:01" in flow._discovered_devices
        assert flow._discovered_devices["AA:BB:CC:DD:EE:01"].name == "D11_BF25_BLE"

        assert "AA:BB:CC:DD:EE:02" in flow._discovered_devices
        assert flow._discovered_devices["AA:BB:CC:DD:EE:02"].name == "Niimbot (AA:BB:CC:DD:EE:02)"

        assert "AA:BB:CC:DD:EE:03" in flow._discovered_devices
        assert flow._discovered_devices["AA:BB:CC:DD:EE:03"].name == "B21-123456"

        # Non-Niimbot devices must be filtered out when candidates match
        assert "11:22:33:44:55:66" not in flow._discovered_devices
        assert "77:88:99:AA:BB:CC" not in flow._discovered_devices

    asyncio.run(_test())


def test_async_step_user_fallback_when_no_candidates_matched():
    """Test fallback to all unconfigured devices when no candidate matches Niimbot filters."""
    async def _test():
        flow = NiimbotConfigFlow()
        flow.hass = MagicMock()

        unknown_raw_device = _make_discovery_info(
            "99:88:77:66:55:44",
            name=None,
            service_uuids=[],
        )

        with patch(
            "custom_components.niimbot.config_flow.async_discovered_service_info",
            return_value=[unknown_raw_device],
        ), patch.object(flow, "_async_current_ids", return_value=set()):
            result = await flow.async_step_user()

        assert result["type"] == "form"
        assert result["step_id"] == "user"

        # Fallback should list the device so user can pick by MAC
        assert "99:88:77:66:55:44" in flow._discovered_devices
        assert flow._discovered_devices["99:88:77:66:55:44"].name == "Niimbot (99:88:77:66:55:44)"

    asyncio.run(_test())


def test_async_step_user_no_devices_found():
    """Test abort when no BLE devices exist at all."""
    async def _test():
        flow = NiimbotConfigFlow()
        flow.hass = MagicMock()

        with patch(
            "custom_components.niimbot.config_flow.async_discovered_service_info",
            return_value=[],
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
            name="D11_BF25_BLE",
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
            name="D11_BF25_BLE",
            service_uuids=[NIIMBOT_SERVICE_UUID],
        )

        result = await flow.async_step_bluetooth(info)

        flow.async_set_unique_id.assert_awaited_once_with("AA:BB:CC:DD:EE:01")
        assert flow.context["title_placeholders"] == {"name": "D11_BF25_BLE"}
        assert result["type"] == "form"
        assert result["step_id"] == "bluetooth_confirm"

    asyncio.run(_test())


