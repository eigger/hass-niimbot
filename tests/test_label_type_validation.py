"""Tests for label_type capability validation and dynamic default resolution."""

import asyncio
import struct

import pytest
from PIL import Image

from custom_components.niimbot.niimprint.model import (
    PrinterModel,
    default_label_type_code,
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


def _make_v4_responses():
    """Minimal V4 print sequence responses."""
    return [
        NiimbotPacket(49, b"\x01"),   # set_label_density
        NiimbotPacket(51, b"\x01"),   # set_label_type
        NiimbotPacket(2, b"\x01"),    # start_print_v4
        NiimbotPacket(4, b"\x01"),    # start_page_print
        NiimbotPacket(20, b"\x01"),   # set_page_size
        NiimbotPacket(228, b"\x01"),  # end_page_print
        NiimbotPacket(PAGE_INDEX_CMD, struct.pack(">H", 1)),
        NiimbotPacket(244, b"\x01"),  # end_print
    ]


def test_get_supported_label_type_codes():
    meta_b1 = get_printer_meta_by_id(4096)
    assert get_supported_label_type_codes(meta_b1) == [1, 2, 5]

    meta_p1 = get_printer_meta_by_id(1024)
    assert get_supported_label_type_codes(meta_p1) == [6]

    meta_c1 = get_printer_meta_by_id(5120)
    assert get_supported_label_type_codes(meta_c1) == [3]

    meta_a1_pro = get_printer_meta_by_id(7424)
    assert get_supported_label_type_codes(meta_a1_pro) == [4, 3]

    # N1 / B18 / B18S must include Continuous (3) — vendor DB includes it; T7
    # rejects unsupported codes locally, so a missing entry is a user-visible
    # regression.
    for model_id in (3584, 3585, 3586):
        codes = get_supported_label_type_codes(get_printer_meta_by_id(model_id))
        assert 3 in codes, f"model {model_id} missing Continuous"

    # B2 / B2 Pro must not advertise Continuous (vendor DB has Gap/Black/Transparent only).
    for model_id in (6912, 6913):
        codes = get_supported_label_type_codes(get_printer_meta_by_id(model_id))
        assert 3 not in codes, f"model {model_id} should not list Continuous"
        assert codes == [1, 2, 5]

    # Unknown model: every known code is returned (never reject what the printer may accept)
    fallback = get_supported_label_type_codes(None)
    assert 1 in fallback
    assert 6 in fallback


def test_default_label_type_code_prefers_with_gaps():
    # B1 supports [1, 2, 5] — default must be 1 (WithGaps)
    meta_b1 = get_printer_meta_by_id(4096)
    assert default_label_type_code(meta_b1) == 1

    # A8 supports [2, 1, 3] (Black, WithGaps, Continuous) — default must still be 1
    meta_a8 = get_printer_meta_by_id(256)
    assert default_label_type_code(meta_a8) == 1

    # P1 supports [6] only — no WithGaps, so first entry (6) is used
    meta_p1 = get_printer_meta_by_id(1024)
    assert default_label_type_code(meta_p1) == 6

    # C1 supports [3] only — no WithGaps, so first entry (3) is used
    meta_c1 = get_printer_meta_by_id(5120)
    assert default_label_type_code(meta_c1) == 3

    # A1_PRO supports [4, 3] — no WithGaps, so first entry (4) is used
    meta_a1_pro = get_printer_meta_by_id(7424)
    assert default_label_type_code(meta_a1_pro) == 4

    # Unknown model fallback: WithGaps (1) is in the full list, so 1 is returned
    assert default_label_type_code(None) == 1


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


def test_print_image_defaults_p1_to_pvc_tag():
    """P1 supports only PvcTag (6); omitting label_type must send 0x06."""
    async def _test():
        transport = FakeTransport(_make_v4_responses())
        client = PrinterClient(transport=transport)
        img = Image.new("1", (96, 10))

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


def test_print_image_defaults_b1_to_with_gaps():
    """B1 supports [1, 2, 5]; omitting label_type must keep sending 0x01 (WithGaps) — no regression."""
    async def _test():
        transport = FakeTransport(_make_v4_responses())
        client = PrinterClient(transport=transport)
        img = Image.new("1", (96, 10))

        await client.print_image(
            model=PrinterModel.B1,
            image=img,
            density=3,
            wait_between_print_lines=0,
            print_line_batch_size=1,
            label_type=None,
        )

        set_label_pkt = next(
            p for p in transport.written_packets if p.type == RequestCodeEnum.SET_LABEL_TYPE
        )
        # Must still be 1 (WithGaps), same as the hardcoded default that existed before T7
        assert set_label_pkt.data == b"\x01"

    run(_test())
