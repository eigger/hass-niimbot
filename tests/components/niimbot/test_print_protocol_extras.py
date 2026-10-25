"""Tests for print pacing, 0xE0 completion, CheckLine, status data, ribbon RFID."""

import asyncio
import struct

from PIL import Image
import pytest

from custom_components.niimbot.niimprint import printer as printer_module
from custom_components.niimbot.niimprint.model import (
    RfidClass,
    get_printer_meta_by_id,
    supports_ribbon_rfid,
)
from custom_components.niimbot.niimprint.packet import NiimbotPacket
from custom_components.niimbot.niimprint.printer import (
    CHECK_LINE_INTERVAL,
    PAGE_INDEX_CMD,
    PRINTER_CHECK_LINE_RESP,
    PRINTER_STATUS_DATA_RESP,
    PrinterClient,
    PrinterError,
    RequestCodeEnum,
)
from tests.components.niimbot.fake_transport import FakeTransport


def run(coro):
    return asyncio.run(coro)


def _rfid_payload(
    uuid: bytes,
    barcode: str,
    serial: str,
    total: int,
    used: int,
    type_: int,
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
    return bytes(data)


def test_protocol_version_buckets():
    assert PrinterClient._parse_protocol_version(250) == 3
    assert PrinterClient._parse_protocol_version(300) == 4
    assert PrinterClient._parse_protocol_version(301) == 4
    assert PrinterClient._parse_protocol_version(302) == 5
    assert PrinterClient._parse_protocol_version(100) == 0


def test_parse_print_area():
    assert PrinterClient._parse_print_area(struct.pack(">HH", 384, 960)) == "384x960"
    assert PrinterClient._parse_print_area(b"\x01") == "01"


def test_get_printer_status_data():
    async def _test():
        # 13+ bytes; colour at [10], version parts at [11]/[12]
        payload = bytes([0] * 10 + [1, 3, 5])  # raw = 3*100+5 = 305 => v5
        transport = FakeTransport([NiimbotPacket(PRINTER_STATUS_DATA_RESP, payload)])
        client = PrinterClient(transport=transport)
        data = await client.get_printer_status_data()
        assert data["support_color"] == 1
        assert data["protocol_version"] == 5
        assert data["raw_version"] == 305

    run(_test())


@pytest.mark.parametrize("length", [4, 8, 10])
async def test_print_status_response_lengths(length):
    payload = struct.pack(">HBB", 2, 80, 40) + bytes(length - 4)
    transport = FakeTransport(
        [NiimbotPacket(RequestCodeEnum.GET_PRINT_STATUS + 16, payload)]
    )
    status = await PrinterClient(transport=transport).get_print_status()
    assert status["page"] == 2
    assert status["progress"] == 80


async def test_truncated_print_status_is_a_clear_error():
    transport = FakeTransport(
        [NiimbotPacket(RequestCodeEnum.GET_PRINT_STATUS + 16, b"\x00\x01")]
    )
    with pytest.raises(ValueError, match="Invalid print status response"):
        await PrinterClient(transport=transport).get_print_status()


def test_get_rfid2_parses_like_rfid():
    async def _test():
        payload = _rfid_payload(
            uuid=bytes.fromhex("1122334455667788"),
            barcode="RIB001",
            serial="RS1",
            total=50,
            used=5,
            type_=1,
        )
        transport = FakeTransport(
            [NiimbotPacket(RequestCodeEnum.GET_RFID2 + 1, payload)]
        )
        client = PrinterClient(transport=transport)
        info = await client.get_rfid2()
        assert info["barcode"] == "RIB001"
        assert info["total_len"] == 50
        assert info["used_len"] == 5

    run(_test())


def test_ribbon_capability_helpers():
    # B1 = label only
    assert get_printer_meta_by_id(4096)["rfid"] == RfidClass.LABEL
    assert not supports_ribbon_rfid(RfidClass.LABEL)
    assert supports_ribbon_rfid(RfidClass.RIBBON)
    assert supports_ribbon_rfid(RfidClass.LABEL_RIBBON)


def test_wait_print_complete_via_page_index():
    async def _test():
        transport = FakeTransport([NiimbotPacket(PAGE_INDEX_CMD, struct.pack(">H", 1))])
        client = PrinterClient(transport=transport)
        status = await client.wait_print_complete(copies=1, timeout=2.0)
        assert status["page"] == 1
        assert status["progress"] == 100
        # No print-status poll should have been needed.
        assert not any(
            p.type == RequestCodeEnum.GET_PRINT_STATUS
            for p in transport.written_packets
        )

    run(_test())


def test_set_image_sends_check_line_every_200_rows():
    async def _test():
        height = CHECK_LINE_INTERVAL
        img = Image.new("L", (16, height), color=255)
        # Queue one CheckLine ACK (0xD3).
        transport = FakeTransport([NiimbotPacket(PRINTER_CHECK_LINE_RESP, b"\x01")])
        client = PrinterClient(transport=transport)
        await client.set_image(img, printhead_pixels=96)
        types = [p.type for p in transport.written_packets]
        assert RequestCodeEnum.PRINTER_CHECK_LINE in types
        check = next(
            p
            for p in transport.written_packets
            if p.type == RequestCodeEnum.PRINTER_CHECK_LINE
        )
        line, flag = struct.unpack(">HB", check.data)
        assert line == CHECK_LINE_INTERVAL - 1
        assert flag == 0x01

    run(_test())


def test_check_line_skips_data_error_reply():
    async def _test():
        # 0xDB error frame with DataError (0x06) instead of a 0xD3 ACK.
        transport = FakeTransport([NiimbotPacket(0xDB, b"\x06")])
        client = PrinterClient(transport=transport)
        await client.check_line(CHECK_LINE_INTERVAL - 1)
        assert transport.written_packets[0].type == RequestCodeEnum.PRINTER_CHECK_LINE

    run(_test())


def test_check_line_still_raises_other_printer_errors():
    async def _test():
        transport = FakeTransport([NiimbotPacket(0xDB, b"\x01")])
        client = PrinterClient(transport=transport)
        with pytest.raises(PrinterError):
            await client.check_line(CHECK_LINE_INTERVAL - 1)

    run(_test())


def _print_status(page: int, printed: int, fed: int) -> dict:
    active = [p for p in (printed, fed) if p > 0]
    return {
        "page": page,
        "page_print_progress": printed,
        "page_feed_progress": fed,
        "progress": max(active) if active else 0,
    }


async def test_wait_print_complete_waits_for_feed_after_print_progress(monkeypatch):
    """Print progress can reach 100 before the label is fed (D110).

    END_PRINT sent at that point is rejected and the job stops mid-label, so
    the single-copy fallback has to wait for the feed as well.
    """
    statuses = [
        _print_status(0, 19, 0),
        _print_status(0, 100, 0),
        _print_status(0, 100, 0),
        _print_status(0, 100, 100),
    ]
    client = PrinterClient(transport=FakeTransport())

    async def fake_status(await_for_response=True):
        return statuses.pop(0)

    monkeypatch.setattr(client, "get_print_status", fake_status)
    status = await client.wait_print_complete(copies=1, timeout=5.0, poll_interval=0)
    assert status["page_feed_progress"] == 100
    assert not statuses


async def test_wait_print_complete_settles_without_feed_progress(monkeypatch):
    """Models that report neither feed progress nor a page count still finish."""
    monkeypatch.setattr(printer_module, "PRINT_SETTLE_SECONDS", 0.05)
    polls = 0
    client = PrinterClient(transport=FakeTransport())

    async def fake_status(await_for_response=True):
        nonlocal polls
        polls += 1
        return _print_status(0, 50 if polls == 1 else 100, 0)

    monkeypatch.setattr(client, "get_print_status", fake_status)
    status = await client.wait_print_complete(copies=1, timeout=5.0, poll_interval=0.01)
    assert status["page_print_progress"] == 100
    assert polls > 2
