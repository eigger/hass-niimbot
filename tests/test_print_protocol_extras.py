"""Tests for print pacing, 0xE0 completion, CheckLine, status data, ribbon RFID."""

import asyncio
import struct

from PIL import Image

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
    RequestCodeEnum,
)
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
        transport = FakeTransport(
            [NiimbotPacket(PRINTER_STATUS_DATA_RESP, payload)]
        )
        client = PrinterClient(transport=transport)
        data = await client.get_printer_status_data()
        assert data["support_color"] == 1
        assert data["protocol_version"] == 5
        assert data["raw_version"] == 305

    run(_test())


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
        transport = FakeTransport(
            [NiimbotPacket(PAGE_INDEX_CMD, struct.pack(">H", 1))]
        )
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
        transport = FakeTransport(
            [NiimbotPacket(PRINTER_CHECK_LINE_RESP, b"\x01")]
        )
        client = PrinterClient(transport=transport)
        await client.set_image(
            img, wait_between_print_lines=0, print_line_batch_size=32, printhead_pixels=96
        )
        types = [p.type for p in transport.written_packets]
        assert RequestCodeEnum.PRINTER_CHECK_LINE in types
        check = next(
            p for p in transport.written_packets if p.type == RequestCodeEnum.PRINTER_CHECK_LINE
        )
        line, flag = struct.unpack(">HB", check.data)
        assert line == CHECK_LINE_INTERVAL - 1
        assert flag == 0x01

    run(_test())
