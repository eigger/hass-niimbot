"""Tests for print sequence dispatch and generation mappings."""

import asyncio
import struct

from PIL import Image

from custom_components.niimbot.niimprint.model import (
    PrinterModel,
    PrintGeneration,
    modelsLibrary,
)
from custom_components.niimbot.niimprint.packet import NiimbotPacket
from custom_components.niimbot.niimprint.printer import (
    PAGE_INDEX_CMD,
    PRINTER_STATUS_DATA_RESP,
    PrinterClient,
    RequestCodeEnum,
)
from tests.fake_transport import FakeTransport


def run(coro):
    return asyncio.run(coro)


def test_models_library_generation_assignments():
    old_d11_models = {PrinterModel.D11, PrinterModel.D11S}
    d110_models = {PrinterModel.D110, PrinterModel.B21S, PrinterModel.B21S_C2B}
    v5_models = {
        PrinterModel.D11_H,
        PrinterModel.D11_PRO,
        PrinterModel.B21_PRO,
        PrinterModel.D110_M,
        PrinterModel.B2_PRO,
    }

    for meta in modelsLibrary:
        model = meta["model"]
        gen = meta["generation"]
        if model in old_d11_models:
            assert gen == PrintGeneration.OLD_D11, f"{model} expected OLD_D11, got {gen}"
        elif model in d110_models:
            assert gen == PrintGeneration.D110, f"{model} expected D110, got {gen}"
        elif model in v5_models:
            assert gen == PrintGeneration.V5, f"{model} expected V5, got {gen}"
        else:
            assert gen == PrintGeneration.V4, f"{model} expected V4, got {gen}"


def _build_standard_responses():
    return [
        NiimbotPacket(49, b"\x01"),   # SET_LABEL_DENSITY (0x21 + 16 = 49)
        NiimbotPacket(51, b"\x01"),   # SET_LABEL_TYPE (0x23 + 16 = 51)
        NiimbotPacket(2, b"\x01"),    # START_PRINT (0x01 + 1 = 2)
        NiimbotPacket(48, b"\x01"),   # ALLOW_PRINT_CLEAR (0x20 + 16 = 48)
        NiimbotPacket(4, b"\x01"),    # START_PAGE_PRINT (0x03 + 1 = 4)
        NiimbotPacket(20, b"\x01"),   # SET_DIMENSION (0x13 + 1 = 20)
        NiimbotPacket(22, b"\x01"),   # SET_QUANTITY (0x15 + 1 = 22)
        NiimbotPacket(132, b"\x01"),  # PRINT_BITMAP_ROW_INDEXED (0x83 + 1 = 132)
        NiimbotPacket(228, b"\x01"),  # END_PAGE_PRINT (0xE3 + 1 = 228)
        NiimbotPacket(PAGE_INDEX_CMD, struct.pack(">H", 1)), # Page index 1 complete
        NiimbotPacket(244, b"\x01"),  # END_PRINT (0xF3 + 1 = 244)
    ]


def test_print_sequence_old_d11():
    async def _test():
        responses = _build_standard_responses()
        transport = FakeTransport(responses)
        client = PrinterClient(transport=transport)
        img = Image.new("1", (96, 10))

        await client.print_image(
            PrinterModel.D11,
            img,
            density=3,
            wait_between_print_lines=0,
            print_line_batch_size=1,
        )

        sent_types = [p.type for p in transport.written_packets]
        # OLD_D11 sequence includes ALLOW_PRINT_CLEAR (0x20)
        assert RequestCodeEnum.ALLOW_PRINT_CLEAR in sent_types
        # OLD_D11 sequence includes SET_QUANTITY (0x15)
        assert RequestCodeEnum.SET_QUANTITY in sent_types

    run(_test())


def test_print_sequence_d110():
    async def _test():
        responses = [
            NiimbotPacket(49, b"\x01"),   # SET_LABEL_DENSITY
            NiimbotPacket(51, b"\x01"),   # SET_LABEL_TYPE
            NiimbotPacket(2, b"\x01"),    # START_PRINT (1 byte b"\x01")
            NiimbotPacket(4, b"\x01"),    # START_PAGE_PRINT
            NiimbotPacket(20, b"\x01"),   # SET_DIMENSION
            NiimbotPacket(22, b"\x01"),   # SET_QUANTITY
            NiimbotPacket(132, b"\x01"),  # PRINT_BITMAP_ROW_INDEXED
            NiimbotPacket(228, b"\x01"),  # END_PAGE_PRINT
            NiimbotPacket(PAGE_INDEX_CMD, struct.pack(">H", 1)),
            NiimbotPacket(244, b"\x01"),  # END_PRINT
        ]
        transport = FakeTransport(responses)
        client = PrinterClient(transport=transport)
        img = Image.new("1", (96, 10))

        await client.print_image(
            PrinterModel.D110,
            img,
            density=3,
            wait_between_print_lines=0,
            print_line_batch_size=1,
        )

        sent_types = [p.type for p in transport.written_packets]
        assert RequestCodeEnum.START_PRINT in sent_types
        # D110 sends 1-byte START_PRINT, SET_QUANTITY, but NOT ALLOW_PRINT_CLEAR
        assert RequestCodeEnum.ALLOW_PRINT_CLEAR not in sent_types
        assert RequestCodeEnum.SET_QUANTITY in sent_types
        start_print_pkt = next(
            p for p in transport.written_packets if p.type == RequestCodeEnum.START_PRINT
        )
        assert len(start_print_pkt.data) == 1

    run(_test())


def test_print_sequence_v4():
    async def _test():
        responses = [
            NiimbotPacket(49, b"\x01"),   # SET_LABEL_DENSITY
            NiimbotPacket(51, b"\x01"),   # SET_LABEL_TYPE
            NiimbotPacket(2, b"\x01"),    # START_PRINT (v4)
            NiimbotPacket(4, b"\x01"),    # START_PAGE_PRINT
            NiimbotPacket(20, b"\x01"),   # SET_DIMENSION
            NiimbotPacket(132, b"\x01"),  # PRINT_BITMAP_ROW_INDEXED
            NiimbotPacket(228, b"\x01"),  # END_PAGE_PRINT
            NiimbotPacket(PAGE_INDEX_CMD, struct.pack(">H", 1)),
            NiimbotPacket(244, b"\x01"),  # END_PRINT
        ]
        transport = FakeTransport(responses)
        client = PrinterClient(transport=transport)
        img = Image.new("1", (384, 10))

        await client.print_image(
            PrinterModel.B1,
            img,
            density=3,
            wait_between_print_lines=0,
            print_line_batch_size=1,
        )

        sent_types = [p.type for p in transport.written_packets]
        # V4 sends START_PRINT (0x01)
        assert RequestCodeEnum.START_PRINT in sent_types
        # V4 does NOT send ALLOW_PRINT_CLEAR (0x20)
        assert RequestCodeEnum.ALLOW_PRINT_CLEAR not in sent_types

    run(_test())


def test_print_sequence_v5():
    async def _test():
        responses = [
            NiimbotPacket(49, b"\x01"),   # SET_LABEL_DENSITY
            NiimbotPacket(51, b"\x01"),   # SET_LABEL_TYPE
            NiimbotPacket(2, b"\x01"),    # START_PRINT_9B
            NiimbotPacket(20, b"\x01"),   # SET_PAGE_SIZE_9B
            NiimbotPacket(134, b"\x01"),  # PRINT_BITMAP_ROW_INDEXED
            NiimbotPacket(228, b"\x01"),  # END_PAGE_PRINT
            NiimbotPacket(PAGE_INDEX_CMD, struct.pack(">H", 1)),
            NiimbotPacket(244, b"\x01"),  # END_PRINT
        ]
        transport = FakeTransport(responses)
        client = PrinterClient(transport=transport)
        img = Image.new("1", (178, 10))

        await client.print_image(
            PrinterModel.D11_H,
            img,
            density=3,
            wait_between_print_lines=0,
            print_line_batch_size=1,
        )

        # V5 start_print sends struct.pack(">HBBBBBBB", ...) -> 9 bytes payload
        start_print_pkt = next(
            p for p in transport.written_packets if p.type == RequestCodeEnum.START_PRINT
        )
        assert len(start_print_pkt.data) == 9

    run(_test())


def test_unknown_model_fallback_v5_via_protocol_version():
    async def _test():
        # Respond to PrinterStatusData (0xA5) with protocol version >= 302 -> 5
        status_payload = bytearray(13)
        status_payload[10] = 0  # support_color
        status_payload[11] = 3  # raw_version high byte (3*100)
        status_payload[12] = 2  # raw_version low byte (+2 = 302)

        responses = [
            NiimbotPacket(PRINTER_STATUS_DATA_RESP, bytes(status_payload)),
            NiimbotPacket(49, b"\x01"),   # SET_LABEL_DENSITY
            NiimbotPacket(51, b"\x01"),   # SET_LABEL_TYPE
            NiimbotPacket(2, b"\x01"),    # START_PRINT_9B
            NiimbotPacket(20, b"\x01"),   # SET_PAGE_SIZE_9B
            NiimbotPacket(134, b"\x01"),  # PRINT_BITMAP_ROW_INDEXED
            NiimbotPacket(228, b"\x01"),  # END_PAGE_PRINT
            NiimbotPacket(PAGE_INDEX_CMD, struct.pack(">H", 1)),
            NiimbotPacket(244, b"\x01"),  # END_PRINT
        ]
        transport = FakeTransport(responses)
        client = PrinterClient(transport=transport)
        img = Image.new("1", (200, 10))

        await client.print_image(
            PrinterModel.UNKNOWN,
            img,
            density=3,
            wait_between_print_lines=0,
            print_line_batch_size=1,
        )

        start_print_pkt = next(
            p for p in transport.written_packets if p.type == RequestCodeEnum.START_PRINT
        )
        assert len(start_print_pkt.data) == 9

    run(_test())


def test_unknown_model_fallback_default_v4():
    async def _test():
        # PrinterStatusData fails (NAK packet 0) -> falls back to V4 sequence
        responses = [
            NiimbotPacket(0, b"\x00"),    # PrinterStatusData NAK
            NiimbotPacket(49, b"\x01"),   # SET_LABEL_DENSITY
            NiimbotPacket(51, b"\x01"),   # SET_LABEL_TYPE
            NiimbotPacket(2, b"\x01"),    # START_PRINT (v4)
            NiimbotPacket(4, b"\x01"),    # START_PAGE_PRINT
            NiimbotPacket(20, b"\x01"),   # SET_DIMENSION
            NiimbotPacket(134, b"\x01"),  # PRINT_BITMAP_ROW_INDEXED
            NiimbotPacket(228, b"\x01"),  # END_PAGE_PRINT
            NiimbotPacket(PAGE_INDEX_CMD, struct.pack(">H", 1)),
            NiimbotPacket(244, b"\x01"),  # END_PRINT
        ]
        transport = FakeTransport(responses)
        client = PrinterClient(transport=transport)
        img = Image.new("1", (200, 10))

        await client.print_image(
            PrinterModel.UNKNOWN,
            img,
            density=3,
            wait_between_print_lines=0,
            print_line_batch_size=1,
        )

        sent_types = [p.type for p in transport.written_packets]
        assert RequestCodeEnum.START_PRINT in sent_types
        # V4 start_print sends struct.pack(">HBBBBB", ...) -> 7 bytes data
        start_print_pkt = next(
            p for p in transport.written_packets if p.type == RequestCodeEnum.START_PRINT
        )
        assert len(start_print_pkt.data) == 7

    run(_test())
