"""Tests for printer action commands and button entity capability gating."""

import asyncio

from PIL import Image

from custom_components.niimbot.niimprint.model import (
    PrinterModel,
    get_printer_meta_by_id,
    supports_calibration,
)
from custom_components.niimbot.niimprint.packet import NiimbotPacket
from custom_components.niimbot.niimprint.printer import PrinterClient, RequestCodeEnum
from tests.fake_transport import FakeTransport


def run(coro):
    return asyncio.run(coro)


def test_supports_calibration_helper():
    # B1 (4096) supports calibration
    meta_b1 = get_printer_meta_by_id(4096)
    assert meta_b1 is not None
    assert supports_calibration(meta_b1) is True

    # D110 (2304) does not support calibration
    meta_d110 = get_printer_meta_by_id(2304)
    assert meta_d110 is not None
    assert supports_calibration(meta_d110) is False

    # None meta returns False
    assert supports_calibration(None) is False


def test_calibrate_label_position_command():
    async def _test():
        transport = FakeTransport([NiimbotPacket(143, b"\x01")])  # 0x8E + 1 = 0x8F (143)
        client = PrinterClient(transport=transport)
        res = await client.calibrate_label_position()
        assert res is True
        assert len(transport.written_packets) == 1
        assert transport.written_packets[0].type == RequestCodeEnum.LABEL_POSITIONING_CALIBRATION

    run(_test())


def test_calibrate_height_command():
    async def _test():
        transport = FakeTransport([NiimbotPacket(105, b"\x01")])  # 0x59 + 16 = 0x69 (105)
        client = PrinterClient(transport=transport)
        res = await client.calibrate_height()
        assert res is True
        assert len(transport.written_packets) == 1
        assert transport.written_packets[0].type == RequestCodeEnum.CALIBRATE_HEIGHT

    run(_test())


def test_cancel_print_command():
    async def _test():
        transport = FakeTransport([NiimbotPacket(208, b"\x00")])  # 0xDA - 10 = 0xD0 (208)
        client = PrinterClient(transport=transport)
        res = await client.cancel_print()
        assert res is True
        assert len(transport.written_packets) == 1
        assert transport.written_packets[0].type == RequestCodeEnum.CANCEL_PRINT

    run(_test())


def test_printer_reset_command():
    async def _test():
        transport = FakeTransport([NiimbotPacket(56, b"\x01")])  # 0x28 + 16 = 0x38 (56)
        client = PrinterClient(transport=transport)
        res = await client.printer_reset()
        assert res is True
        assert len(transport.written_packets) == 1
        assert transport.written_packets[0].type == RequestCodeEnum.PRINTER_RESET

    run(_test())


def test_print_test_page_command():
    async def _test():
        transport = FakeTransport([NiimbotPacket(106, b"\x01")])  # 0x5A + 16 = 0x6A (106)
        client = PrinterClient(transport=transport)
        res = await client.print_test_page()
        assert res is True
        assert len(transport.written_packets) == 1
        assert transport.written_packets[0].type == RequestCodeEnum.PRINT_TEST_PAGE

    run(_test())


def test_in_flight_print_cancellation():
    async def _test():
        # Setup fake responses for a print job on B1 (V4)
        responses = [
            NiimbotPacket(49, b"\x01"),   # set_label_density (33 + 16 = 49)
            NiimbotPacket(51, b"\x01"),   # set_label_type (35 + 16 = 51)
            NiimbotPacket(2, b"\x01"),    # start_print_v4 (1 + 1 = 2)
            NiimbotPacket(4, b"\x01"),    # start_page_print (3 + 1 = 4)
            NiimbotPacket(20, b"\x01"),   # set_page_size (19 + 1 = 20)
            NiimbotPacket(208, b"\x00"),  # cancel_print (0xD0)
        ]
        transport = FakeTransport(responses)
        client = PrinterClient(transport=transport)

        img = Image.new("1", (96, 20), color=0)

        # Trigger cancel_requested before line printing begins
        client.cancel_requested = True

        await client.print_image(
            model=PrinterModel.B1,
            image=img,
            density=3,
            wait_between_print_lines=0,
            print_line_batch_size=1,
        )

        written_types = [p.type for p in transport.written_packets]
        assert RequestCodeEnum.CANCEL_PRINT in written_types
        assert client.cancel_requested is False

    run(_test())
