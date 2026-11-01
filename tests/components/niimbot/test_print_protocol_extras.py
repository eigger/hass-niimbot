"""Tests for print pacing, 0xE0 completion, CheckLine, status data, ribbon RFID."""

import asyncio
import struct
import time
from types import SimpleNamespace

from bleak import BleakError
from blesession.testing import FakeClient
from PIL import Image
import pytest

from custom_components.niimbot.niimprint import printer as printer_module
from custom_components.niimbot.niimprint.model import (
    PrinterModel,
    RfidClass,
    get_printer_meta_by_id,
    supports_ribbon_rfid,
)
from custom_components.niimbot.niimprint.packet import NiimbotPacket
from custom_components.niimbot.niimprint.printer import (
    CHARACTERISTIC_UUID,
    CHECK_LINE_INTERVAL,
    PAGE_INDEX_CMD,
    PRINTER_CHECK_LINE_RESP,
    PRINTER_STATUS_DATA_RESP,
    BLETransport,
    PrinterClient,
    PrinterTimeout,
    PrinterCommandUnsupported,
    PrinterCompletionTimeout,
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
        await client.set_image(img, printhead_pixels=96, check_line=True)
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


def test_set_image_skips_check_line_by_default():
    async def _test():
        img = Image.new("L", (16, CHECK_LINE_INTERVAL * 2), color=255)
        transport = FakeTransport()
        client = PrinterClient(transport=transport)
        await client.set_image(img, printhead_pixels=96)
        assert RequestCodeEnum.PRINTER_CHECK_LINE not in [
            p.type for p in transport.written_packets
        ]

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


class _PageIndexOnStatusPollTransport(FakeTransport):
    """Never answers 0xA3; announces the page via 0xE0 once it is polled."""

    def __init__(self, page: int | None):
        super().__init__()
        self._page = page

    async def write(self, data: bytes, response=True):
        await super().write(data, response)
        if self._page is not None and data[2] == RequestCodeEnum.GET_PRINT_STATUS:
            self.queue(NiimbotPacket(PAGE_INDEX_CMD, struct.pack(">H", self._page)))


def test_wait_print_complete_accepts_page_index_when_status_poll_unanswered():
    async def _test():
        transport = _PageIndexOnStatusPollTransport(page=1)
        client = PrinterClient(transport=transport)
        status = await client.wait_print_complete(
            copies=1, timeout=2.0, poll_interval=0.01
        )
        assert status["page"] == 1
        assert status["progress"] == 100

    run(_test())


def test_wait_print_complete_times_out_when_status_poll_unanswered():
    async def _test():
        transport = _PageIndexOnStatusPollTransport(page=None)
        client = PrinterClient(transport=transport)
        with pytest.raises(PrinterCompletionTimeout):
            await client.wait_print_complete(copies=1, timeout=0.05, poll_interval=0.01)

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


def _fake_clock(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(
        printer_module,
        "time",
        SimpleNamespace(time=time.time, monotonic=lambda: now[0]),
    )

    async def fake_sleep(seconds):
        now[0] += 1.0

    monkeypatch.setattr(printer_module, "sleep", fake_sleep)
    return now


async def test_wait_print_complete_settle_restarts_when_progress_drops(monkeypatch):
    """A progress dip below 100 must restart the settle window."""
    now = _fake_clock(monkeypatch)
    statuses = [(0, 50, 0), (0, 100, 0), (0, 100, 0), (0, 60, 0)]
    done_at = None
    client = PrinterClient(transport=FakeTransport())

    async def fake_status(await_for_response=True):
        nonlocal done_at
        if statuses:
            return _print_status(*statuses.pop(0))
        # Progress stays at 100 from here on; the settle must run from now.
        if done_at is None:
            done_at = now[0]
        return _print_status(0, 100, 0)

    monkeypatch.setattr(client, "get_print_status", fake_status)
    await client.wait_print_complete(copies=1, timeout=60.0, poll_interval=1)
    assert now[0] - done_at >= printer_module.PRINT_SETTLE_SECONDS


async def test_wait_print_complete_ends_on_page_bump_before_settle(monkeypatch):
    """D110 shape: page=1 arrives with feed still 0, well before the settle."""
    now = _fake_clock(monkeypatch)
    statuses = [(0, 20, 0), (0, 100, 0), (1, 100, 0)]
    client = PrinterClient(transport=FakeTransport())

    async def fake_status(await_for_response=True):
        return _print_status(*statuses.pop(0))

    monkeypatch.setattr(client, "get_print_status", fake_status)
    status = await client.wait_print_complete(copies=1, timeout=60.0, poll_interval=1)
    assert status["page"] == 1
    assert now[0] < printer_module.PRINT_SETTLE_SECONDS


async def test_wait_print_complete_require_page_ignores_feed_and_short_settle(
    monkeypatch,
):
    """B21S: progress 100 arrives long before the label prints; wait for page."""
    now = _fake_clock(monkeypatch)
    statuses = [(0, 20, 0), (0, 100, 0)] + [(0, 100, 100)] * 6 + [(1, 100, 100)]
    client = PrinterClient(transport=FakeTransport())

    async def fake_status(await_for_response=True):
        return _print_status(*statuses.pop(0))

    monkeypatch.setattr(client, "get_print_status", fake_status)
    status = await client.wait_print_complete(
        copies=1, timeout=60.0, poll_interval=1, require_page=True
    )
    assert status["page"] == 1
    assert not statuses
    assert now[0] > printer_module.PRINT_SETTLE_SECONDS


async def test_wait_print_complete_require_page_settles_if_page_never_bumps(
    monkeypatch,
):
    now = _fake_clock(monkeypatch)
    client = PrinterClient(transport=FakeTransport())
    polls = 0

    async def fake_status(await_for_response=True):
        nonlocal polls
        polls += 1
        return _print_status(0, 50 if polls == 1 else 100, 0)

    monkeypatch.setattr(client, "get_print_status", fake_status)
    await client.wait_print_complete(
        copies=1, timeout=120.0, poll_interval=1, require_page=True
    )
    assert now[0] >= printer_module.PRINT_SETTLE_REQUIRE_PAGE_SECONDS


async def test_wait_print_complete_require_page_default_timeout_fits_settle(
    monkeypatch,
):
    """A late progress 100 must still reach the settle before the timeout."""
    now = _fake_clock(monkeypatch)
    client = PrinterClient(transport=FakeTransport())

    async def fake_status(await_for_response=True):
        # Progress dips below 100 until ~20s in, then stays at 100.
        return _print_status(0, 50 if now[0] < 20 else 100, 0)

    monkeypatch.setattr(client, "get_print_status", fake_status)
    await client.wait_print_complete(copies=1, poll_interval=1, require_page=True)
    assert now[0] >= 20 + printer_module.PRINT_SETTLE_REQUIRE_PAGE_SECONDS


async def test_wait_print_complete_require_page_ends_on_page_notification():
    client = PrinterClient(transport=FakeTransport())
    client._last_page_index = 1
    status = await client.wait_print_complete(copies=1, require_page=True)
    assert status["page"] == 1


@pytest.mark.parametrize(
    ("model", "expected", "target"),
    [
        (PrinterModel.B21, True, "print_image_v4"),
        (PrinterModel.B21_L2B, True, "print_image_v4"),
        (PrinterModel.B21S, False, "print_image_d110"),
        (PrinterModel.B1, False, "print_image_v4"),
    ],
)
async def test_print_image_enables_check_line_only_for_b21_models(
    monkeypatch, model, expected, target
):
    client = PrinterClient(transport=FakeTransport())
    seen = {}

    async def fake(**kwargs):
        seen.update(kwargs)

    monkeypatch.setattr(client, target, fake)
    await client.print_image(model, Image.new("1", (16, 8)), density=3)
    assert seen["check_line"] is expected


@pytest.mark.parametrize("error", [PrinterCommandUnsupported, PrinterTimeout])
async def test_print_image_d110_continues_when_print_clear_is_refused(
    monkeypatch, error
):
    client = PrinterClient(transport=FakeTransport())
    calls = []

    def recorder(name):
        async def ok(*args, **kwargs):
            calls.append(name)
            return True

        return ok

    for name in (
        "set_label_density",
        "set_label_type",
        "start_print",
        "start_page_print",
        "set_page_size_v2",
        "set_quantity",
        "set_image",
        "end_page_print",
        "wait_print_complete",
        "end_print",
    ):
        monkeypatch.setattr(client, name, recorder(name))

    async def refused(timeout=None):
        raise error("0x20")

    monkeypatch.setattr(client, "allow_print_clear", refused)
    await client.print_image_d110(Image.new("1", (16, 8)), density=3)
    assert calls[-1] == "end_print"


def _ble_transport(mtu: int | None):
    client = FakeClient()
    if mtu is not None:
        client.mtu_size = mtu
    return client, BLETransport(client)


def _b1_rows(count: int) -> list[bytes]:
    """Bitmap row packets as a 384 px head sends them: 61 bytes each."""
    return [
        NiimbotPacket(
            RequestCodeEnum.PRINT_BITMAP_ROW,
            struct.pack(">H3BB", y, 8, 8, 8, 1) + bytes([y]) * 48,
        ).to_bytes()
        for y in range(count)
    ]


async def test_row_packets_coalesce_into_mtu_sized_writes():
    client, transport = _ble_transport(mtu=240)
    rows = _b1_rows(10)
    for row in rows:
        await transport.write(row, response=False)
    end_page = NiimbotPacket(RequestCodeEnum.END_PAGE_PRINT, b"\x01").to_bytes()
    await transport.write(end_page, response=True)

    *row_writes, last = client.writes
    assert last == (CHARACTERISTIC_UUID, end_page, True)
    assert [len(data) for _, data, _ in row_writes] == [237, 237, 136]
    assert all(response is False for _, _, response in row_writes)
    assert b"".join(data for _, data, _ in row_writes) == b"".join(rows)


@pytest.mark.parametrize(
    ("mtu", "pause"),
    [
        (240, printer_module.BLE_COALESCED_WRITE_DELAY),
        (23, printer_module.BLE_WRITE_CHUNK_DELAY),
    ],
)
async def test_coalesced_and_20_byte_writes_each_use_their_own_pause(
    monkeypatch, mtu, pause
):
    pauses = []

    async def fake_sleep(seconds):
        pauses.append(seconds)

    monkeypatch.setattr(printer_module, "sleep", fake_sleep)
    client, transport = _ble_transport(mtu)
    for row in _b1_rows(10):
        await transport.write(row, response=False)
    await transport.write(
        NiimbotPacket(RequestCodeEnum.END_PAGE_PRINT, b"\x01").to_bytes(), response=True
    )
    assert pauses and set(pauses) == {pause}


@pytest.mark.parametrize("mtu", [23, None])
async def test_row_packets_keep_20_byte_chunks_without_a_larger_mtu(mtu):
    client, transport = _ble_transport(mtu)
    (row,) = _b1_rows(1)
    await transport.write(row, response=False)
    assert [data for _, data, _ in client.writes] == [
        row[offset : offset + 20] for offset in range(0, len(row), 20)
    ]


async def test_a_command_that_expects_a_reply_flushes_buffered_rows_first():
    client, transport = _ble_transport(mtu=240)
    rows = _b1_rows(2)
    for row in rows:
        await transport.write(row, response=False)
    end_page = NiimbotPacket(RequestCodeEnum.END_PAGE_PRINT, b"\x01").to_bytes()
    await transport.write(end_page, response=True)
    assert client.writes == [
        (CHARACTERISTIC_UUID, rows[0] + rows[1], False),
        (CHARACTERISTIC_UUID, end_page, True),
    ]


async def test_a_new_print_discards_rows_left_by_a_failed_one(monkeypatch):
    client, transport = _ble_transport(mtu=240)
    printer = PrinterClient(transport=transport)
    image = Image.new("1", (16, 8))

    async def failed_transfer(**kwargs):
        await transport.write(_b1_rows(1)[0], response=False)
        raise RuntimeError("encoding failed")

    monkeypatch.setattr(printer, "print_image_v4", failed_transfer)
    with pytest.raises(RuntimeError):
        await printer.print_image(PrinterModel.B1, image, density=3)

    start = NiimbotPacket(RequestCodeEnum.START_PRINT, b"\x01").to_bytes()

    async def next_print(**kwargs):
        await transport.write(start, response=True)

    monkeypatch.setattr(printer, "print_image_v4", next_print)
    client.writes.clear()
    await printer.print_image(PrinterModel.B1, image, density=3)
    assert client.writes == [(CHARACTERISTIC_UUID, start, True)]


async def test_a_failed_row_write_drops_the_buffer_before_the_cleanup():
    client, transport = _ble_transport(mtu=240)
    rows = _b1_rows(4)
    client.fail_write = BleakError("write timed out")
    for row in rows[:3]:
        await transport.write(row, response=False)
    with pytest.raises(BleakError):
        await transport.write(rows[3], response=False)

    client.fail_write = None
    end_print = NiimbotPacket(RequestCodeEnum.END_PRINT, b"\x01").to_bytes()
    await transport.write(end_print, response=True)
    assert client.writes == [(CHARACTERISTIC_UUID, end_print, True)]
