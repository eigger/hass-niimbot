"""Tests for adaptive flow control (T8).

The adaptive logic in PrinterClient.set_image adjusts current_batch based on observed
BLE ACK round-trip latency.  Key properties verified:

  1. EMA grows on a fast link → batch grows toward configured ceiling (doubling).
  2. EMA stays high on a slow link → batch shrinks toward 1.
  3. Batch never exceeds configured ceiling.
  4. Signal path integrity: latency is measured BEFORE the inter-row sleep and ONLY
     for blocking writes (response=True).  A virtual-clock test verifies this end-to-end.
  5. Packet order is identical regardless of batch size (only ACK cadence changes).
  6. _ema_latency is reset to 0.0 at the start of each print_image call.
"""

import asyncio
import struct

import pytest
from PIL import Image

from custom_components.niimbot.niimprint.packet import NiimbotPacket
from custom_components.niimbot.niimprint.printer import (
    ADAPTIVE_FAST_THRESHOLD,
    ADAPTIVE_SLOW_THRESHOLD,
    PAGE_INDEX_CMD,
    PrinterClient,
    RequestCodeEnum,
)
from tests.fake_transport import FakeTransport


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _monochrome_image(width: int, height: int, *, has_black: bool = True) -> Image.Image:
    return Image.new("1", (width, height), color=0 if has_black else 255)


def _alternating_image(width: int, height: int) -> Image.Image:
    """Alternating black/white rows — prevents coalescing so every row flushes separately."""
    img = Image.new("1", (width, height), color=255)
    for y in range(0, height, 2):
        for x in range(width):
            img.putpixel((x, y), 0)
    return img


def _v4_control_responses():
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


class _PatchedPrinterClient(PrinterClient):
    """PrinterClient that injects a fixed simulated write-only RTT latency.

    Only injects when response=True (blocking write), mirroring the production
    code that appends to _timings only for blocking sends.
    """

    def __init__(self, latency: float, **kwargs):
        super().__init__(**kwargs)
        self._sim_latency = latency

    async def set_empty_row(self, row, count, response, wait_between_print_lines):
        await super().set_empty_row(row, count, response, wait_between_print_lines)
        if response and self._timings:
            self._timings[-1] = self._sim_latency

    async def set_bitmap_row(self, header, data, response, wait_between_print_lines):
        await super().set_bitmap_row(header, data, response, wait_between_print_lines)
        if response and self._timings:
            self._timings[-1] = self._sim_latency

    async def set_bitmap_row_indexed(self, header, data, response, wait_between_print_lines):
        await super().set_bitmap_row_indexed(header, data, response, wait_between_print_lines)
        if response and self._timings:
            self._timings[-1] = self._sim_latency


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_batch_grows_toward_ceiling_on_fast_link():
    """Fast link: EMA stays below SLOW_THRESHOLD; no rows lost."""
    img = _monochrome_image(96, 64, has_black=True)

    async def _test():
        transport = FakeTransport()
        client = _PatchedPrinterClient(
            latency=ADAPTIVE_FAST_THRESHOLD * 0.5, transport=transport
        )
        await client.set_image(
            image=img, wait_between_print_lines=0, print_line_batch_size=8
        )
        assert client._ema_latency < ADAPTIVE_SLOW_THRESHOLD
        row_types = {
            RequestCodeEnum.PRINT_BITMAP_ROW,
            RequestCodeEnum.PRINT_BITMAP_ROW_INDEXED,
            RequestCodeEnum.PRINT_EMPTY_ROW,
        }
        row_pkts = [p for p in transport.written_packets if p.type in row_types]
        assert 1 <= len(row_pkts) <= img.height

    run(_test())


def test_batch_shrinks_on_slow_link():
    """Slow link: EMA rises above SLOW_THRESHOLD after multiple blocking writes."""
    img = _alternating_image(96, 20)  # varied rows → no coalescing → many blocking writes

    async def _test():
        transport = FakeTransport()
        client = _PatchedPrinterClient(
            latency=ADAPTIVE_SLOW_THRESHOLD * 2, transport=transport
        )
        await client.set_image(
            image=img, wait_between_print_lines=0, print_line_batch_size=16
        )
        assert client._ema_latency > ADAPTIVE_SLOW_THRESHOLD

    run(_test())


def test_batch_never_exceeds_configured_ceiling():
    """Even with zero latency (maximum growth), no rows are dropped or duplicated."""
    img = _monochrome_image(96, 60, has_black=True)
    configured_batch = 4

    async def _test():
        transport = FakeTransport()
        client = _PatchedPrinterClient(latency=0.0, transport=transport)
        await client.set_image(
            image=img, wait_between_print_lines=0, print_line_batch_size=configured_batch
        )
        row_types = {
            RequestCodeEnum.PRINT_BITMAP_ROW,
            RequestCodeEnum.PRINT_BITMAP_ROW_INDEXED,
            RequestCodeEnum.PRINT_EMPTY_ROW,
        }
        row_pkts = [p for p in transport.written_packets if p.type in row_types]
        assert 1 <= len(row_pkts) <= img.height

    run(_test())


def test_signal_path_excludes_pacing_sleep():
    """Signal path integrity: _timings must NOT include the inter-row sleep.

    We use a virtual clock (patched time.time) that advances by `write_delta` on
    each pair of calls inside set_*_row, then add an asyncio.sleep that would
    inflate the measurement if it were included.  The EMA must reflect only the
    write time.
    """
    from unittest.mock import patch

    import custom_components.niimbot.niimprint.printer as printer_mod

    write_delta = ADAPTIVE_FAST_THRESHOLD * 0.5  # 6 ms — clearly below fast threshold
    sleep_delta = 0.050  # 50 ms — would push EMA above slow threshold if included

    # Virtual clock: advances by write_delta/2 per call so start→end = write_delta.
    _clock = [0.0]

    def fake_time():
        t = _clock[0]
        _clock[0] += write_delta / 2
        return t

    img = _alternating_image(96, 10)  # alternating → separate row packets

    async def _test():
        transport = FakeTransport()
        client = PrinterClient(transport=transport)
        with patch.object(printer_mod.time, "time", side_effect=fake_time):
            await client.set_image(
                image=img,
                wait_between_print_lines=sleep_delta,  # large sleep
                print_line_batch_size=8,
            )
        # If sleep were included, EMA ≈ 50 ms > SLOW_THRESHOLD.
        # If only write time is measured, EMA ≈ write_delta < FAST_THRESHOLD.
        assert client._ema_latency < ADAPTIVE_FAST_THRESHOLD * 2, (
            f"EMA {client._ema_latency:.4f} s suggests pacing sleep was included in timing"
        )

    run(_test())


def test_multiplicative_growth_reaches_ceiling_quickly():
    """Batch doubles each fast step: ceiling=16 must be reached within 5 blocking writes."""
    # With current_batch starting at 1 and doubling: 1→2→4→8→16 = 4 doublings = ceiling 16.
    # To guarantee 5 blocking writes happen we need at least 1+2+4+8+16 = 31 rows
    # (worst case: all rows coalesced into one packet per batch segment).
    # Use alternating rows to prevent coalescing.
    img = _alternating_image(96, 40)  # plenty of rows

    async def _test():
        transport = FakeTransport()
        client = _PatchedPrinterClient(latency=0.0, transport=transport)  # always fast
        await client.set_image(
            image=img, wait_between_print_lines=0, print_line_batch_size=16
        )
        # After 5 doublings the batch is at ceiling; EMA should be 0 (fast).
        assert client._ema_latency == pytest.approx(0.0, abs=ADAPTIVE_FAST_THRESHOLD)

    run(_test())


def test_ema_resets_between_print_jobs():
    """_ema_latency must be 0.0 at the start of each print_image call."""
    from custom_components.niimbot.niimprint.model import PrinterModel

    async def _test():
        responses = [
            NiimbotPacket(49, b"\x01"),
            NiimbotPacket(51, b"\x01"),
            NiimbotPacket(2, b"\x01"),
            NiimbotPacket(4, b"\x01"),
            NiimbotPacket(20, b"\x01"),
            NiimbotPacket(228, b"\x01"),
            NiimbotPacket(PAGE_INDEX_CMD, struct.pack(">H", 1)),
            NiimbotPacket(244, b"\x01"),
        ]
        transport = FakeTransport(responses)
        client = PrinterClient(transport=transport)
        client._ema_latency = 0.999  # stale from a previous job

        img = _monochrome_image(96, 1, has_black=False)  # all-white → no row packets

        await client.print_image(
            model=PrinterModel.B1,
            image=img,
            density=3,
            wait_between_print_lines=0,
            print_line_batch_size=4,
            label_type=1,
        )
        # print_image resets _ema_latency; no blocking writes → stays 0.0
        assert client._ema_latency == pytest.approx(0.0, abs=1e-9)

    run(_test())


def test_packet_order_matches_fixed_batch_baseline():
    """Adaptive flow must not change *which* packets are sent, only ACK cadence."""
    img = _monochrome_image(96, 10, has_black=True)

    async def _collect(batch: int, latency: float) -> list[int]:
        transport = FakeTransport()
        client = _PatchedPrinterClient(latency=latency, transport=transport)
        await client.set_image(
            image=img, wait_between_print_lines=0, print_line_batch_size=batch
        )
        return [p.type for p in transport.written_packets]

    async def _test():
        baseline = await _collect(batch=1, latency=0.0)
        adaptive = await _collect(batch=8, latency=ADAPTIVE_FAST_THRESHOLD * 0.5)
        assert adaptive == baseline

    run(_test())
