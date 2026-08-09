"""Tests for printer action commands and button entity capability gating."""

import asyncio

from PIL import Image

from custom_components.niimbot.niimprint.model import (
    PrinterModel,
    get_printer_meta_by_id,
    supports_calibration,
    supports_height_calibration,
    supports_label_position_calibration,
    supports_print_test_page,
)
from custom_components.niimbot.niimprint.packet import NiimbotPacket
from custom_components.niimbot.niimprint.parser import NiimbotDevice
from custom_components.niimbot.niimprint.printer import PrinterClient, RequestCodeEnum
from tests.fake_transport import FakeTransport


def run(coro):
    return asyncio.run(coro)


def test_supports_calibration_helper():
    # B1 (4096): vendor calibration yes, but HA hides 0x8E (long feed) and 0x5A (NAK)
    meta_b1 = get_printer_meta_by_id(4096)
    assert meta_b1 is not None
    assert supports_calibration(meta_b1) is True
    assert supports_label_position_calibration(meta_b1) is False
    assert supports_height_calibration(meta_b1) is False
    assert supports_print_test_page(meta_b1) is False

    # D110 (2304) does not support calibration; PrintTestPage not denylisted
    meta_d110 = get_printer_meta_by_id(2304)
    assert meta_d110 is not None
    assert supports_calibration(meta_d110) is False
    assert supports_label_position_calibration(meta_d110) is False
    assert supports_height_calibration(meta_d110) is False
    assert supports_print_test_page(meta_d110) is True

    # B3 (52993): Continuous + calibration → height and paper calibration exposed
    meta_b3 = get_printer_meta_by_id(52993)
    assert meta_b3 is not None
    assert supports_calibration(meta_b3) is True
    assert supports_label_position_calibration(meta_b3) is True
    assert supports_height_calibration(meta_b3) is True
    assert supports_print_test_page(meta_b3) is True

    # None meta returns False
    assert supports_calibration(None) is False
    assert supports_label_position_calibration(None) is False
    assert supports_height_calibration(None) is False
    assert supports_print_test_page(None) is False


def test_calibrate_label_position_command():
    async def _test():
        transport = FakeTransport([NiimbotPacket(143, b"\x01")])  # 0x8E + 1 = 0x8F (143)
        client = PrinterClient(transport=transport)
        res = await client.calibrate_label_position()
        assert res is True
        assert len(transport.written_packets) == 1
        assert transport.written_packets[0].type == RequestCodeEnum.LABEL_POSITIONING_CALIBRATION

    run(_test())


def test_device_paper_calibration_sets_label_type_first():
    async def _test():
        device = NiimbotDevice("aa:bb:cc:dd:ee:ff")
        device.ble_data.labeltype = 2
        transport = FakeTransport(
            [
                NiimbotPacket(51, b"\x01"),  # set_label_type → 0x23+16
                NiimbotPacket(143, b"\x01"),  # calibrate → 0x8F
            ]
        )
        client = PrinterClient(transport=transport)

        async def _ensure(_ble):
            return client

        async def _release():
            return None

        device._ensure_printer = _ensure  # type: ignore[method-assign]
        device._release_printer = _release  # type: ignore[method-assign]

        assert await device.calibrate_label_position("aa:bb:cc:dd:ee:ff") is True
        assert transport.written_packets[0].type == RequestCodeEnum.SET_LABEL_TYPE
        assert transport.written_packets[0].data == b"\x02"
        assert (
            transport.written_packets[1].type
            == RequestCodeEnum.LABEL_POSITIONING_CALIBRATION
        )

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

        orig_write = transport.write

        async def _write_with_cancel(packet_bytes, response=True):
            await orig_write(packet_bytes, response=response)
            # When page size command (0x13 / 19) is written, trigger cancel_requested
            if len(packet_bytes) >= 3 and packet_bytes[2] == RequestCodeEnum.SET_DIMENSION:
                client.cancel_requested = True

        transport.write = _write_with_cancel

        img = Image.new("1", (96, 20), color=0)

        res = await client.print_image(
            model=PrinterModel.B1,
            image=img,
            density=3,
            wait_between_print_lines=0,
            print_line_batch_size=1,
        )

        assert isinstance(res, dict)
        assert res.get("status") == "cancelled"
        written_types = [p.type for p in transport.written_packets]
        assert RequestCodeEnum.CANCEL_PRINT in written_types
        assert client.cancel_requested is False

    run(_test())


def test_niimbot_device_cancel_print_in_flight():
    async def _test():
        device = NiimbotDevice("11:22:33:44:55:66")
        transport = FakeTransport([])
        client = PrinterClient(transport=transport)
        device._printer = client
        device._is_printing = True

        # Calling cancel_print on NiimbotDevice during print job sets cancel_requested on _printer
        res = await device.cancel_print("11:22:33:44:55:66")
        assert res is True
        assert client.cancel_requested is True

    run(_test())
