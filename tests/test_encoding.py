"""Tests for row encoding and model capability helpers."""

import asyncio

from PIL import Image

from custom_components.niimbot.niimprint.model import (
    RfidClass,
    get_printer_meta_by_id,
    supports_label_rfid,
)
from custom_components.niimbot.niimprint.printer import (
    INDEXED_BLACK_PIXEL_LIMIT,
    PrinterClient,
    RequestCodeEnum,
)
from tests.fake_transport import FakeTransport


def run(coro):
    return asyncio.run(coro)


def test_meta_rfid_for_b1():
    meta = get_printer_meta_by_id(4096)
    assert meta is not None
    assert meta["rfid"] == RfidClass.LABEL
    assert meta["densityMin"] == 1
    assert meta["densityMax"] == 5
    assert supports_label_rfid(meta["rfid"])


def test_meta_rfid_none_for_t2s():
    meta = get_printer_meta_by_id(53250)
    assert meta is not None
    assert meta["rfid"] == RfidClass.NONE
    assert meta["densityMax"] == 20
    assert not supports_label_rfid(meta["rfid"])


def test_row_counters_split_mode_d11():
    client = PrinterClient(transport=FakeTransport())
    # 96px => 12 bytes => chunk_size 4
    row = bytes([0xFF, 0x00, 0x00, 0x00, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01])
    counters = client._row_counter_bytes(row, 96)
    assert counters[0] == 8
    assert counters[1] == 4
    assert counters[2] == 1


def test_row_counters_total_mode_wide():
    client = PrinterClient(transport=FakeTransport())
    # 384px => 48 bytes > chunk_size(16)*3? 384/8/3=16, 16*3=48, equal so still split.
    # Use 576px => 72 bytes > 24*3=72? 576/8/3=24, 24*3=72 equal.
    # 832px => 104 bytes, chunk=34, 34*3=102, 104>102 => total mode.
    row = bytes([0xFF]) + bytes(103)
    counters = client._row_counter_bytes(row, 832)
    total = 8
    assert counters == bytes((0x00, total & 0xFF, total >> 8))


def test_black_pixel_indices_and_limit():
    # One black pixel at column 0
    row = bytes([0x80, 0x00])
    indices = PrinterClient._black_pixel_indices(row, 16)
    assert indices == [0]

    # Exactly 6 black pixels
    row6 = bytes([0xFC, 0x00])  # bits 7..2 set => columns 0..5
    assert len(PrinterClient._black_pixel_indices(row6, 16)) == 6
    assert len(PrinterClient._black_pixel_indices(row6, 16)) <= INDEXED_BLACK_PIXEL_LIMIT

    # 7 black pixels
    row7 = bytes([0xFE, 0x00])
    assert len(PrinterClient._black_pixel_indices(row7, 16)) == 7


def test_set_image_coalesces_identical_rows_and_uses_indexed():
    async def _test():
        # 16x4 image: white background after invert becomes black in mode "1"?
        # ImageOps.invert(L).convert("1"): black in source -> white after invert -> 0 in "1"
        # We need black pixels in the final "1" image (pix != 0).
        # After invert: dark source becomes light. convert("1") uses threshold.
        # Simpler: create already the right pattern by mocking via direct bytes path —
        # call set_image with a crafted image where a few pixels are black (0 in L before invert).
        img = Image.new("L", (16, 4), color=255)  # white
        # Put black pixels at (0,1) and (0,2) so after invert they become white... wait.
        # invert makes 0->255, 255->0. convert("1"): typically 0=black, 255=white in "1" mode
        # but code treats pix==0 as white ("0" bit) and pix!=0 as black ("1" bit).
        # So we need non-zero pixels after invert+convert. That means dark (near 0) in source L
        # -> inverted to near 255 -> "1" image has 255 -> bit 1. Good.
        img.putpixel((0, 1), 0)
        img.putpixel((0, 2), 0)  # identical sparse rows

        transport = FakeTransport()
        client = PrinterClient(transport=transport)
        await client.set_image(img, wait_between_print_lines=0, print_line_batch_size=1, printhead_pixels=96)

        packets = transport.written_packets
        types = [p.type for p in packets]
        # Row 0 empty, rows 1-2 coalesced indexed, row 3 empty
        assert RequestCodeEnum.PRINT_EMPTY_ROW in types
        assert RequestCodeEnum.PRINT_BITMAP_ROW_INDEXED in types
        indexed = [p for p in packets if p.type == RequestCodeEnum.PRINT_BITMAP_ROW_INDEXED]
        assert len(indexed) == 1
        # header: row u16, 3 counters, repeats
        repeats = indexed[0].data[5]
        assert repeats == 2

    run(_test())


def test_set_image_falls_back_to_bitmap_above_six_pixels():
    async def _test():
        img = Image.new("L", (16, 1), color=255)
        for x in range(7):
            img.putpixel((x, 0), 0)

        transport = FakeTransport()
        client = PrinterClient(transport=transport)
        await client.set_image(img, 0, 1, printhead_pixels=96)
        types = [p.type for p in transport.written_packets]
        assert RequestCodeEnum.PRINT_BITMAP_ROW in types
        assert RequestCodeEnum.PRINT_BITMAP_ROW_INDEXED not in types

    run(_test())
