"""Tests for label_type capability validation and dynamic default resolution."""

import asyncio
import struct

import pytest
from PIL import Image

from custom_components.niimbot.niimprint.model import (
    PrinterModel,
    get_printer_meta_by_id,
    get_supported_label_type_codes,
)
from custom_components.niimbot.niimprint.packet import NiimbotPacket
from custom_components.niimbot.niimprint.printer import (
    PAGE_INDEX_CMD,
    PrinterClient,
    RequestCodeEnum,
)
from tests.fake_transport import FakeTransport


def run(coro):
    return asyncio.run(coro)


def test_get_supported_label_type_codes():
    meta_b1 = get_printer_meta_by_id(4096)
    assert get_supported_label_type_codes(meta_b1) == [1, 2, 5]

    meta_p1 = get_printer_meta_by_id(1024)
    assert get_supported_label_type_codes(meta_p1) == [6]

    meta_c1 = get_printer_meta_by_id(5120)
    assert get_supported_label_type_codes(meta_c1) == [3]

    meta_a1_pro = get_printer_meta_by_id(7424)
    assert get_supported_label_type_codes(meta_a1_pro) == [4, 3]

    assert get_supported_label_type_codes(None) == [1, 2, 3, 4, 5, 6, 10, 11]


def test_print_image_rejects_unsupported_label_type():
    async def _test():
        transport = FakeTransport([])
        client = PrinterClient(transport=transport)
        img = Image.new("1", (96, 10))

        # B1 supports [1, 2, 5]; passing label_type=3 (Continuous) must raise ValueError locally
        with pytest.raises(ValueError, match="Label type 3 is not supported for printer model B1"):
            await client.print_image(
                model=PrinterModel.B1,
                image=img,
                density=3,
                wait_between_print_lines=0,
                print_line_batch_size=1,
                label_type=3,
            )

    run(_test())


def test_print_image_defaults_to_model_primary_paper_type():
    async def _test():
        # Setup responses for P1 (V4, primary paperType = 6 PvcTag)
        responses = [
            NiimbotPacket(49, b"\x01"),   # set_label_density (33 + 16 = 49)
            NiimbotPacket(51, b"\x01"),   # set_label_type (35 + 16 = 51)
            NiimbotPacket(2, b"\x01"),    # start_print_v4 (1 + 1 = 2)
            NiimbotPacket(4, b"\x01"),    # start_page_print (3 + 1 = 4)
            NiimbotPacket(20, b"\x01"),   # set_page_size (19 + 1 = 20)
            NiimbotPacket(228, b"\x01"),  # end_page_print (227 + 1 = 228)
            NiimbotPacket(PAGE_INDEX_CMD, struct.pack(">H", 1)),
            NiimbotPacket(244, b"\x01"),  # end_print (243 + 1 = 244)
        ]
        transport = FakeTransport(responses)
        client = PrinterClient(transport=transport)
        img = Image.new("1", (96, 10))

        # Pass label_type=None so it defaults to P1's primary paper type (6)
        await client.print_image(
            model=PrinterModel.P1,
            image=img,
            density=3,
            wait_between_print_lines=0,
            print_line_batch_size=1,
            label_type=None,
        )

        set_label_pkt = next(
            p for p in transport.written_packets if p.type == RequestCodeEnum.SET_LABEL_TYPE
        )
        assert set_label_pkt.data == b"\x06"

    run(_test())
