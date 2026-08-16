"""Tests for Niimbot BLE config flow."""

import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import CONF_ADDRESS, CONF_SCAN_INTERVAL
from custom_components.niimbot.config_flow import (
    NiimbotConfigFlow,
    Discovery,
    NIIMBOT_NAME_PREFIXES,
)
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


def test_name_prefixes_stay_in_sync_with_manifest():
    """manifest.json의 local_name 매처가 전부 config_flow 프리픽스에 반영돼 있어야 한다."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    manifest_prefixes = set()
    for entry in manifest.get("bluetooth", []):
        if local_name := entry.get("local_name"):
            assert local_name.endswith("*"), f"예상치 못한 패턴 형태: {local_name}"
            manifest_prefixes.add(local_name[:-1])

    missing = manifest_prefixes - set(NIIMBOT_NAME_PREFIXES)
    assert not missing, f"config_flow 프리픽스에 누락된 모델: {sorted(missing)}"


def test_name_looks_like_niimbot_guards_mac_address_and_avoids_false_positives():
    """Test that _name_looks_like_niimbot matches true Niimbot devices and rejects false positives/MACs."""
    from custom_components.niimbot.config_flow import _name_looks_like_niimbot

    # MAC address starting with B1 / C1 / A8 should NOT match model prefix
    assert _name_looks_like_niimbot("B1:22:33:44:55:66", "B1:22:33:44:55:66") is False
    assert _name_looks_like_niimbot("C1:22:33:44:55:66", "C1:22:33:44:55:66") is False
    assert _name_looks_like_niimbot("A8:3F:11:22:33:44", "A8:3F:11:22:33:44") is False

    # Real model names (with hyphens or underscores) should match
    assert _name_looks_like_niimbot("D11_BF25_BLE", "AA:BB:CC:DD:EE:01") is True
    assert _name_looks_like_niimbot("D11-1234", "AA:BB:CC:DD:EE:02") is True
    assert _name_looks_like_niimbot("B1-G723040259", "AA:BB:CC:DD:EE:03") is True
    assert _name_looks_like_niimbot("B1_PRO", "AA:BB:CC:DD:EE:04") is True
    assert _name_looks_like_niimbot("B2_Pro-9999", "AA:BB:CC:DD:EE:05") is True
    assert _name_looks_like_niimbot("B2-0001", "AA:BB:CC:DD:EE:06") is True
    assert _name_looks_like_niimbot("B18_0001", "AA:BB:CC:DD:EE:07") is True
    assert _name_looks_like_niimbot("A63_0001", "AA:BB:CC:DD:EE:08") is True
    assert _name_looks_like_niimbot("T2S_0001", "AA:BB:CC:DD:EE:09") is True
    assert _name_looks_like_niimbot("B21-123456", "AA:BB:CC:DD:EE:10") is True
    assert _name_looks_like_niimbot("B3S-1234", "AA:BB:CC:DD:EE:11") is True
    assert _name_looks_like_niimbot("NIIMBOT-D11", "AA:BB:CC:DD:EE:12") is True

    # False positives from generic non-Niimbot devices must be rejected
    assert _name_looks_like_niimbot("S1 Earbuds", "11:22:33:44:55:66") is False
    assert _name_looks_like_niimbot("P1 Mouse", "11:22:33:44:55:67") is False
    assert _name_looks_like_niimbot("M2 Tracker", "11:22:33:44:55:68") is False
    assert _name_looks_like_niimbot("C1 Sensor", "11:22:33:44:55:69") is False
    assert _name_looks_like_niimbot("JCB-Terminal", "11:22:33:44:55:70") is False
    assert _name_looks_like_niimbot("[TV] Samsung", "11:22:33:44:55:71") is False
    assert _name_looks_like_niimbot("LYWSD03MMC", "11:22:33:44:55:72") is False


def test_async_step_user_filters_by_service_uuid_and_name():
    """Test that async_step_user includes valid Niimbot devices and excludes non-Niimbot devices."""
    async def _test():
        flow = NiimbotConfigFlow()
        flow.hass = MagicMock()

        d11_clone = _make_discovery_info(
            "AA:BB:CC:DD:EE:01",
            name="D11_BF25_BLE",
            service_uuids=[],
        )
        b1_underscore = _make_discovery_info(
            "AA:BB:CC:DD:EE:02",
            name="B1_G723040259",
            service_uuids=[],
        )
        b21_printer = _make_discovery_info(
            "AA:BB:CC:DD:EE:03",
            name="B21-123456",
            service_uuids=[],
        )
        uuid_matched_device = _make_discovery_info(
            "AA:BB:CC:DD:EE:04",
            name=None,
            service_uuids=[NIIMBOT_SERVICE_UUID],
        )
        random_nameless_mac = _make_discovery_info(
            "23:07:04:37:39:E5",
            name=None,
            service_uuids=[],
        )
        s1_earbuds = _make_discovery_info(
            "11:22:33:44:55:66",
            name="S1 Earbuds",
            service_uuids=[],
        )
        samsung_tv = _make_discovery_info(
            "11:22:33:44:55:67",
            name="[TV] Samsung",
            service_uuids=["00001800-0000-1000-8000-00805f9b34fb"],
        )
        xiaomi_sensor = _make_discovery_info(
            "22:33:44:55:66:77",
            name="LYWSD03MMC",
            service_uuids=[],
        )

        discovered = [
            d11_clone,
            b1_underscore,
            b21_printer,
            uuid_matched_device,
            random_nameless_mac,
            s1_earbuds,
            samsung_tv,
            xiaomi_sensor,
        ]

        with patch(
            "custom_components.niimbot.config_flow.async_discovered_service_info",
            return_value=discovered,
        ), patch.object(flow, "_async_current_ids", return_value=set()):
            result = await flow.async_step_user()

        assert result["type"] == "form"
        assert result["step_id"] == "user"

        # Valid Niimbot devices should be discovered
        assert "AA:BB:CC:DD:EE:01" in flow._discovered_devices
        assert flow._discovered_devices["AA:BB:CC:DD:EE:01"].name == "D11_BF25_BLE"

        assert "AA:BB:CC:DD:EE:02" in flow._discovered_devices
        assert flow._discovered_devices["AA:BB:CC:DD:EE:02"].name == "B1_G723040259"

        assert "AA:BB:CC:DD:EE:03" in flow._discovered_devices
        assert flow._discovered_devices["AA:BB:CC:DD:EE:03"].name == "B21-123456"

        assert "AA:BB:CC:DD:EE:04" in flow._discovered_devices
        assert flow._discovered_devices["AA:BB:CC:DD:EE:04"].name == "Niimbot (AA:BB:CC:DD:EE:04)"

        # Random nameless rotating MACs and non-Niimbot devices must be filtered out
        assert "23:07:04:37:39:E5" not in flow._discovered_devices
        assert "11:22:33:44:55:66" not in flow._discovered_devices
        assert "11:22:33:44:55:67" not in flow._discovered_devices
        assert "22:33:44:55:66:77" not in flow._discovered_devices

    asyncio.run(_test())


def test_async_step_user_no_devices_found():
    """Test abort when no Niimbot devices match."""
    async def _test():
        flow = NiimbotConfigFlow()
        flow.hass = MagicMock()

        samsung_tv = _make_discovery_info(
            "11:22:33:44:55:66",
            name="[TV] Samsung",
            service_uuids=["00001800-0000-1000-8000-00805f9b34fb"],
        )
        random_nameless_mac = _make_discovery_info(
            "23:07:04:37:39:E5",
            name=None,
            service_uuids=[],
        )

        with patch(
            "custom_components.niimbot.config_flow.async_discovered_service_info",
            return_value=[samsung_tv, random_nameless_mac],
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


