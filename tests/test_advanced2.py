"""Tests for Advanced2 heartbeat handling and sensor parsing."""

import asyncio

from custom_components.niimbot.niimprint.packet import NiimbotPacket
from custom_components.niimbot.niimprint.parser import NiimbotDevice
from custom_components.niimbot.niimprint.printer import (
    HEARTBEAT_RESP_ADVANCED2,
    PrinterClient,
)
from tests.fake_transport import FakeTransport


def run(coro):
    return asyncio.run(coro)


def test_heartbeat_advanced2_length_boundaries():
    async def _test():
        # Short payload (< 9 bytes)
        adv2_short = bytearray(5)
        transport = FakeTransport(
            [NiimbotPacket(HEARTBEAT_RESP_ADVANCED2, bytes(adv2_short))]
        )
        client = PrinterClient(transport=transport, heartbeat_payload=b"\x04")
        res_short = await client.heartbeat()
        assert "temperature" not in res_short
        assert "ribbonstate" not in res_short

        # 9-byte payload
        adv2_9 = bytearray(9)
        adv2_9[2] = 4  # powerlevel
        adv2_9[3] = 35  # temperature
        adv2_9[7] = 1  # ribbon_rfidreadstate
        adv2_9[8] = 0  # ribbonstate
        transport = FakeTransport(
            [NiimbotPacket(HEARTBEAT_RESP_ADVANCED2, bytes(adv2_9))]
        )
        client = PrinterClient(transport=transport, heartbeat_payload=b"\x04")
        res_9 = await client.heartbeat()
        assert res_9["temperature"] == 35
        assert res_9["ribbon_rfidreadstate"] == 1
        assert res_9["ribbonstate"] == 0
        assert "wifi_rssi" not in res_9
        assert "lighting_error" not in res_9
        assert "voltage_state" not in res_9

        # 11-byte payload
        adv2_11 = bytearray(11)
        adv2_11[3] = 35
        adv2_11[9:11] = (-65).to_bytes(2, "big", signed=True)
        transport = FakeTransport(
            [NiimbotPacket(HEARTBEAT_RESP_ADVANCED2, bytes(adv2_11))]
        )
        client = PrinterClient(transport=transport, heartbeat_payload=b"\x04")
        res_11 = await client.heartbeat()
        assert res_11["wifi_rssi"] == -65
        assert "lighting_error" not in res_11

        # 13-byte payload
        adv2_13 = bytearray(13)
        adv2_13[12] = 2
        transport = FakeTransport(
            [NiimbotPacket(HEARTBEAT_RESP_ADVANCED2, bytes(adv2_13))]
        )
        client = PrinterClient(transport=transport, heartbeat_payload=b"\x04")
        res_13 = await client.heartbeat()
        assert res_13["lighting_error"] == 2
        assert "voltage_state" not in res_13

        # 14-byte payload
        adv2_14 = bytearray(14)
        adv2_14[13] = 5
        transport = FakeTransport(
            [NiimbotPacket(HEARTBEAT_RESP_ADVANCED2, bytes(adv2_14))]
        )
        client = PrinterClient(transport=transport, heartbeat_payload=b"\x04")
        res_14 = await client.heartbeat()
        assert res_14["voltage_state"] == 5

    run(_test())


def test_parser_apply_heartbeat_advanced2_keys():
    device = NiimbotDevice("AA:BB:CC:DD:EE:FF")

    # Advanced1 heartbeat: should only update closingstate, paperstate, rfidreadstate
    hb_adv1 = {
        "closingstate": 0,
        "paperstate": 0,
        "rfidreadstate": 1,
        "variant": "advanced1",
    }
    device._apply_heartbeat(hb_adv1)
    assert device.heartbeat_variant == "advanced1"
    assert device.ble_data.sensors["closingstate"] == 0
    assert device.ble_data.sensors["paperstate"] == 0
    assert device.ble_data.sensors["rfidreadstate"] == 1
    assert "printhead_temperature" not in device.ble_data.sensors
    assert "ribbonstate" not in device.ble_data.sensors
    assert "wifi_rssi" not in device.ble_data.sensors

    # Advanced2 heartbeat: updates extra sensor keys when present
    hb_adv2 = {
        "closingstate": 0,
        "paperstate": 0,
        "rfidreadstate": 1,
        "temperature": 42,
        "ribbonstate": 0,
        "ribbon_rfidreadstate": 1,
        "wifi_rssi": -70,
        "lighting_error": 0,
        "voltage_state": 12,
        "variant": "advanced2",
    }
    device._apply_heartbeat(hb_adv2)
    assert device.heartbeat_variant == "advanced2"
    assert device.ble_data.sensors["printhead_temperature"] == 42
    assert device.ble_data.sensors["ribbonstate"] == 0
    assert device.ble_data.sensors["ribbon_rfidreadstate"] == 1
    assert device.ble_data.sensors["wifi_rssi"] == -70
    assert device.ble_data.sensors["lighting_error"] == 0
    assert device.ble_data.sensors["voltage_state"] == 12
