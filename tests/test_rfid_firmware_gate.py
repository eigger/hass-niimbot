"""Tests for firmware version gating of RFID reads."""

import asyncio

from custom_components.niimbot.niimprint.model import rfid_supported_on_firmware
from custom_components.niimbot.niimprint.packet import NiimbotPacket
from custom_components.niimbot.niimprint.parser import NiimbotDevice
from custom_components.niimbot.niimprint.printer import PrinterClient, RequestCodeEnum
from tests.fake_transport import FakeTransport


def run(coro):
    return asyncio.run(coro)


def test_rfid_supported_on_firmware_helper():
    # Model 512 (D11 / Hi-NB-D11)
    assert not rfid_supported_on_firmware(512, "2.08")
    assert not rfid_supported_on_firmware("512", 2.08)
    assert not rfid_supported_on_firmware(512, "1.04")
    assert rfid_supported_on_firmware(512, "2.10")
    assert rfid_supported_on_firmware(512, "3.00")

    # Model 777 (B21S)
    assert not rfid_supported_on_firmware(777, "2.08")
    assert not rfid_supported_on_firmware(777, "35.01")
    assert rfid_supported_on_firmware(777, "36.00")

    # Models 771 & 775 (B21-C2B)
    assert not rfid_supported_on_firmware(771, "1.01")
    assert not rfid_supported_on_firmware(775, "1.01")

    # Model 4096 (B1 - no firmware gate)
    assert rfid_supported_on_firmware(4096, "2.08")

    # Fallback cases (None inputs)
    assert rfid_supported_on_firmware(None, "2.08")
    assert rfid_supported_on_firmware(512, None)
    assert rfid_supported_on_firmware(None, None)


def _rfid_payload():
    uuid = bytes.fromhex("1122334455667788")
    barcode = b"LAB001"
    serial = b"S1"
    data = bytearray(uuid)
    data.append(len(barcode))
    data.extend(barcode)
    data.append(len(serial))
    data.extend(serial)
    data.extend((100).to_bytes(2, "big"))  # total_len
    data.extend((10).to_bytes(2, "big"))   # used_len
    data.append(1)                        # type
    return bytes(data)


def test_device_skips_rfid_on_unsupported_firmware():
    async def _test():
        transport = FakeTransport([])
        printer = PrinterClient(transport=transport)
        device = NiimbotDevice("11:22:33:44:55:66")
        device.ble_data.devicetype = 512
        device.ble_data.sw_version = "2.08"
        device.ble_data.model = "D11"

        heartbeat = {"rfidreadstate": 1}
        await device._maybe_read_rfid(printer, heartbeat)

        written_types = [p.type for p in transport.written_packets]
        assert RequestCodeEnum.GET_RFID not in written_types

    run(_test())


def test_device_reads_rfid_on_supported_firmware():
    async def _test():
        rfid_bytes = _rfid_payload()
        transport = FakeTransport([NiimbotPacket(27, rfid_bytes)])
        printer = PrinterClient(transport=transport)
        device = NiimbotDevice("11:22:33:44:55:66")
        device.ble_data.devicetype = 512
        device.ble_data.sw_version = "2.10"
        device.ble_data.model = "D11"

        heartbeat = {"rfidreadstate": 1}
        await device._maybe_read_rfid(printer, heartbeat)

        written_types = [p.type for p in transport.written_packets]
        assert RequestCodeEnum.GET_RFID in written_types
        assert device.ble_data.sensors["label_sku"] == "LAB001"

    run(_test())
