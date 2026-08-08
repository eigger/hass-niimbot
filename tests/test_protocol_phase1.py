"""Phase 1 protocol correctness tests."""

import asyncio
import struct

import pytest

from custom_components.niimbot.niimprint.packet import NiimbotPacket
from custom_components.niimbot.niimprint.printer import (
    HEARTBEAT_RESP_ADVANCED1,
    HEARTBEAT_RESP_ADVANCED2,
    PrinterClient,
    PrinterTimeout,
    RequestCodeEnum,
)
from custom_components.niimbot.niimprint.parser import _battery_percentage
from tests.fake_transport import FakeTransport


def run(coro):
    return asyncio.run(coro)


def _rfid_payload(
    uuid: bytes,
    barcode: str,
    serial: str,
    total: int,
    used: int,
    type_: int,
    capacity: int | None = None,
) -> bytes:
    data = bytearray(uuid)
    barcode_b = barcode.encode()
    serial_b = serial.encode()
    data.append(len(barcode_b))
    data.extend(barcode_b)
    data.append(len(serial_b))
    data.extend(serial_b)
    data.extend(total.to_bytes(2, "big"))
    data.extend(used.to_bytes(2, "big"))
    data.append(type_)
    if capacity is not None:
        data.extend(capacity.to_bytes(2, "big"))
    return bytes(data)


def test_packet_roundtrip():
    original = NiimbotPacket(RequestCodeEnum.HEARTBEAT, b"\x01")
    rebuilt = NiimbotPacket.from_bytes(original.to_bytes())
    assert rebuilt.type == original.type
    assert rebuilt.data == original.data
    assert len(original.to_bytes()) == len(original.data) + 7


def test_get_rfid_no_tag():
    async def _test():
        transport = FakeTransport(
            [NiimbotPacket(RequestCodeEnum.GET_RFID + 1, b"\x00")]
        )
        client = PrinterClient(transport=transport)
        assert await client.get_rfid() is None

    run(_test())


def test_get_rfid_uuid_starting_with_zero():
    async def _test():
        payload = _rfid_payload(
            uuid=bytes.fromhex("00aabbccddeeff01"),
            barcode="ABC123",
            serial="S1",
            total=100,
            used=12,
            type_=1,
        )
        transport = FakeTransport(
            [NiimbotPacket(RequestCodeEnum.GET_RFID + 1, payload)]
        )
        client = PrinterClient(transport=transport)
        info = await client.get_rfid()
        assert info is not None
        assert info["uuid"] == "00aabbccddeeff01"
        assert info["barcode"] == "ABC123"
        assert info["serial"] == "S1"
        assert info["total_len"] == 100
        assert info["used_len"] == 12
        assert info["type"] == 1
        assert info["capacity"] is None

    run(_test())


def test_get_rfid_with_capacity():
    async def _test():
        payload = _rfid_payload(
            uuid=bytes.fromhex("1122334455667788"),
            barcode="SKU",
            serial="BATCH",
            total=200,
            used=50,
            type_=2,
            capacity=150,
        )
        transport = FakeTransport(
            [NiimbotPacket(RequestCodeEnum.GET_RFID + 1, payload)]
        )
        client = PrinterClient(transport=transport)
        info = await client.get_rfid()
        assert info["capacity"] == 150
        assert info["total_len"] == 200
        assert info["used_len"] == 50

    run(_test())


def test_heartbeat_advanced1_length_13():
    async def _test():
        data = bytes([0] * 9 + [0, 3, 0, 1])
        transport = FakeTransport([NiimbotPacket(HEARTBEAT_RESP_ADVANCED1, data)])
        client = PrinterClient(transport=transport)
        result = await client.heartbeat()
        assert result["closingstate"] == 0
        assert result["powerlevel"] == 3
        assert result["paperstate"] == 0
        assert result["rfidreadstate"] == 1
        assert result["variant"] == "advanced1"
        assert client.heartbeat_payload == b"\x01"

    run(_test())


def test_heartbeat_advanced1_length_20_no_battery():
    async def _test():
        data = bytes([0] * 18 + [0, 1])
        transport = FakeTransport([NiimbotPacket(HEARTBEAT_RESP_ADVANCED1, data)])
        client = PrinterClient(transport=transport)
        result = await client.heartbeat()
        assert result["powerlevel"] is None
        assert result["paperstate"] == 0
        assert result["rfidreadstate"] == 1

    run(_test())


def test_heartbeat_advanced1_unknown_length():
    async def _test():
        data = bytes([1, 2, 3, 4, 5])
        transport = FakeTransport([NiimbotPacket(HEARTBEAT_RESP_ADVANCED1, data)])
        client = PrinterClient(transport=transport)
        result = await client.heartbeat()
        assert result["closingstate"] is None
        assert result["powerlevel"] is None
        assert result["variant"] == "advanced1"

    run(_test())


def test_heartbeat_falls_back_to_advanced2():
    async def _test():
        adv2 = bytearray(14)
        adv2[2] = 2
        adv2[3] = 40
        adv2[4] = 0
        adv2[5] = 0
        adv2[6] = 1
        adv2[7] = 0
        adv2[8] = 0
        adv2[12] = 0
        adv2[13] = 1

        transport = FakeTransport()
        client = PrinterClient(transport=transport)
        writes = {"n": 0}
        original_write = transport.write

        async def write_then_queue(data, response=True):
            await original_write(data, response=response)
            writes["n"] += 1
            if writes["n"] == 2:
                transport.queue(NiimbotPacket(HEARTBEAT_RESP_ADVANCED2, bytes(adv2)))

        transport.write = write_then_queue  # type: ignore[method-assign]

        result = await client.heartbeat()
        assert result["variant"] == "advanced2"
        assert result["powerlevel"] == 2
        assert result["temperature"] == 40
        assert result["closingstate"] == 0
        assert result["paperstate"] == 0
        assert client.heartbeat_payload == b"\x04"

    run(_test())


def test_heartbeat_prefers_cached_payload():
    async def _test():
        adv2 = bytearray(9)
        adv2[2] = 4
        adv2[4] = 1
        adv2[5] = 0
        adv2[6] = 1
        adv2[7] = 0
        adv2[8] = 0
        transport = FakeTransport(
            [NiimbotPacket(HEARTBEAT_RESP_ADVANCED2, bytes(adv2))]
        )
        client = PrinterClient(transport=transport, heartbeat_payload=b"\x04")
        result = await client.heartbeat()
        assert result["variant"] == "advanced2"
        assert transport.written_packets[0].data == b"\x04"

    run(_test())


def test_transceive_raises_printer_timeout():
    async def _test():
        transport = FakeTransport()
        client = PrinterClient(transport=transport)
        with pytest.raises(PrinterTimeout):
            await client._transceive(RequestCodeEnum.HEARTBEAT, b"\x01", timeout=0.05)

    run(_test())


def test_battery_percentage_none():
    assert _battery_percentage(None, "B1") is None


def test_battery_percentage_normal():
    assert _battery_percentage(3, "B1") == 75


def test_battery_percentage_b1_pro():
    assert _battery_percentage(60, "B1_PRO") == 60
    assert _battery_percentage(100, "B1_PRO") == 100


def test_battery_percentage_b1_pro_advanced2_is_bucket():
    # Advanced2 always uses the 0–4 bucket, even on B1 Pro.
    assert _battery_percentage(4, "B1_PRO", variant="advanced2") == 100
    assert _battery_percentage(2, "B1_PRO", variant="advanced2") == 50


def test_get_print_status_keeps_separate_progress_fields():
    async def _test():
        # page=1, print=80, feed=40
        payload = struct.pack(">HBB", 1, 80, 40)
        transport = FakeTransport(
            [NiimbotPacket(RequestCodeEnum.GET_PRINT_STATUS + 16, payload)]
        )
        client = PrinterClient(transport=transport)
        seen = {}

        def on_progress(status):
            seen.update(status)

        client.on_progress = on_progress
        status = await client.get_print_status()
        assert status["page"] == 1
        assert status["page_print_progress"] == 80
        assert status["page_feed_progress"] == 40
        assert status["progress"] == 80
        assert seen["progress"] == 80

    run(_test())
