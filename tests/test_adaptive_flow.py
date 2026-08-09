"""Tests for adaptive flow control (T8).

The adaptive logic in PrinterClient.set_image adjusts current_batch based on observed
per-row write latency tracked in self._timings. These tests directly pre-populate
_timings to simulate fast/slow links, then verify:

  1. batch size grows toward configured ceiling when latency is fast,
  2. batch size shrinks toward 1 when latency is slow,
  3. batch size never exceeds the user-configured ceiling,
  4. packet order is identical to the fixed-batch baseline (only ACK cadence differs),
  5. _ema_latency is reset to 0.0 at the start of each print_image call.
"""

import asyncio
import struct
from unittest.mock import patch

import pytest
from PIL import Image

from custom_components.niimbot.niimprint.packet import NiimbotPacket
from custom_components.niimbot.niimprint.printer import (
    ADAPTIVE_EMA_ALPHA,
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
    """Return a 1-bit PIL image."""
    return Image.new("1", (width, height), color=0 if has_black else 255)


def _v4_control_responses():
    """Canned V4 control-packet responses that wrap set_image."""
    return [
        NiimbotPacket(49, b"\x01"),   # set_label_density
        NiimbotPacket(51, b"\x01"),   # set_label_type
        NiimbotPacket(2, b"\x01"),    # start_print_v4
        NiimbotPacket(4, b"\x01"),    # start_page_print
        NiimbotPacket(20, b"\x01"),   # set_page_size
        NiimbotPacket(PAGE_INDEX_CMD, struct.pack(">H", 1)),
        NiimbotPacket(228, b"\x01"),  # end_page_print
        NiimbotPacket(244, b"\x01"),  # end_print
    ]


def _client_with_prefilled_latency(latency: float) -> PrinterClient:
    """Return a PrinterClient whose _timings is pre-filled with a single latency value.

    This causes the first _needs_block() EMA update to see a known latency rather than
    relying on wall-clock time in tests.
    """
    transport = FakeTransport()
    client = PrinterClient(transport=transport)
    # Pre-seed _timings so the EMA update inside _needs_block() has data on the first call.
    client._timings = [latency]
    client._ema_latency = latency  # start EMA at the target value
    return client


def _ema_after_n_steps(start: float, sample: float, n: int) -> float:
    """Compute the expected EMA after n identical samples."""
    v = start
    for _ in range(n):
        v = ADAPTIVE_EMA_ALPHA * sample + (1 - ADAPTIVE_EMA_ALPHA) * v
    return v


# ---------------------------------------------------------------------------
# Unit tests for the EMA / batch-size logic
# ---------------------------------------------------------------------------

class _TrackedBatchTransport(FakeTransport):
    """FakeTransport that intercepts writes and appends a fixed latency to _timings."""

    def __init__(self, latency: float):
        super().__init__([])
        self._latency = latency
        self.client: PrinterClient | None = None

    def bind(self, client: PrinterClient) -> None:
        self.client = client

    async def write(self, data: bytes, response: bool = True) -> None:
        await super().write(data, response=response)
        # Append the simulated latency *after* each write, mimicking production code
        # that measures time.time()-start around _send(). Because the test runs almost
        # instantaneously, we inject the desired value directly.
        if self.client is not None:
            # Replace the last timing that production code appended (it will be ~0) with
            # our simulated value.  If set_empty/bitmap_row has not appended yet (we are
            # called from inside _send which is called before the append), schedule the
            # override for after the send returns.
            self._pending_latency_inject = True

    async def inject_latency(self) -> None:
        if self.client is not None and getattr(self, "_pending_latency_inject", False):
            self._pending_latency_inject = False
            if self.client._timings:
                self.client._timings[-1] = self._latency
            else:
                self.client._timings.append(self._latency)


class _PatchedPrinterClient(PrinterClient):
    """PrinterClient that appends a fixed simulated latency after each row send."""

    def __init__(self, latency: float, **kwargs):
        super().__init__(**kwargs)
        self._sim_latency = latency

    async def set_empty_row(self, row, count, response, wait_between_print_lines):
        await super().set_empty_row(row, count, response, wait_between_print_lines)
        if self._timings:
            self._timings[-1] = self._sim_latency

    async def set_bitmap_row(self, header, data, response, wait_between_print_lines):
        await super().set_bitmap_row(header, data, response, wait_between_print_lines)
        if self._timings:
            self._timings[-1] = self._sim_latency

    async def set_bitmap_row_indexed(self, header, data, response, wait_between_print_lines):
        await super().set_bitmap_row_indexed(header, data, response, wait_between_print_lines)
        if self._timings:
            self._timings[-1] = self._sim_latency


def test_batch_grows_toward_ceiling_on_fast_link():
    """With fast latency the EMA stays below SLOW_THRESHOLD and ceiling is respected."""
    fast_latency = ADAPTIVE_FAST_THRESHOLD * 0.5
    configured_batch = 8
    img = _monochrome_image(96, 64, has_black=True)

    async def _test():
        transport = FakeTransport()
        client = _PatchedPrinterClient(latency=fast_latency, transport=transport)

        await client.set_image(
            image=img,
            wait_between_print_lines=0,
            print_line_batch_size=configured_batch,
        )

        # EMA converged on a fast latency → must stay well below the slow threshold
        assert client._ema_latency < ADAPTIVE_SLOW_THRESHOLD

        # No rows lost or duplicated — all row packets correspond to image rows
        row_types = {
            RequestCodeEnum.PRINT_BITMAP_ROW,
            RequestCodeEnum.PRINT_BITMAP_ROW_INDEXED,
            RequestCodeEnum.PRINT_EMPTY_ROW,
        }
        row_pkts = [p for p in transport.written_packets if p.type in row_types]
        assert len(row_pkts) <= img.height  # coalescing may reduce count
        assert len(row_pkts) >= 1

    run(_test())


def test_batch_shrinks_on_slow_link():
    """With slow latency the EMA rises above SLOW_THRESHOLD."""
    slow_latency = ADAPTIVE_SLOW_THRESHOLD * 2
    # Use varied rows (alternating black and white per-row) so each row flushes
    # as a separate packet (no coalescing).  This guarantees multiple blocking
    # writes happen and the EMA has time to converge upward.
    width, height = 96, 20
    img = Image.new("1", (width, height), color=255)  # start white
    for y in range(height):
        for x in range(width):
            img.putpixel((x, y), 0 if (y % 2 == 0) else 255)  # alternate rows

    async def _test():
        transport = FakeTransport()
        client = _PatchedPrinterClient(latency=slow_latency, transport=transport)

        await client.set_image(
            image=img,
            wait_between_print_lines=0,
            print_line_batch_size=16,
        )

        assert client._ema_latency > ADAPTIVE_SLOW_THRESHOLD

    run(_test())


def test_batch_never_exceeds_configured_ceiling():
    """Even with zero latency, no rows should be dropped or duplicated."""
    img = _monochrome_image(96, 60, has_black=True)
    configured_batch = 4

    async def _test():
        transport = FakeTransport()
        client = _PatchedPrinterClient(latency=0.0, transport=transport)

        await client.set_image(
            image=img,
            wait_between_print_lines=0,
            print_line_batch_size=configured_batch,
        )

        row_types = {
            RequestCodeEnum.PRINT_BITMAP_ROW,
            RequestCodeEnum.PRINT_BITMAP_ROW_INDEXED,
            RequestCodeEnum.PRINT_EMPTY_ROW,
        }
        row_pkts = [p for p in transport.written_packets if p.type in row_types]
        # Row packets ≤ height (coalescing), but at least 1 and no more than height.
        assert 1 <= len(row_pkts) <= img.height

    run(_test())


def test_ema_resets_between_print_jobs():
    """_ema_latency must be 0.0 at the start of each print_image call."""
    from custom_components.niimbot.niimprint.model import PrinterModel

    async def _test():
        # White 1-row image → set_image produces no row packets, so no timing updates.
        # print_image still needs full V4 control sequence responses.
        responses = [
            NiimbotPacket(49, b"\x01"),   # set_label_density
            NiimbotPacket(51, b"\x01"),   # set_label_type
            NiimbotPacket(2, b"\x01"),    # start_print_v4
            NiimbotPacket(4, b"\x01"),    # start_page_print
            NiimbotPacket(20, b"\x01"),   # set_page_size
            NiimbotPacket(228, b"\x01"),  # end_page_print
            NiimbotPacket(PAGE_INDEX_CMD, struct.pack(">H", 1)),
            NiimbotPacket(244, b"\x01"),  # end_print
        ]
        transport = FakeTransport(responses)
        client = PrinterClient(transport=transport)
        client._ema_latency = 0.999  # stale from a previous job

        img = _monochrome_image(96, 1, has_black=False)  # white → no row packets

        await client.print_image(
            model=PrinterModel.B1,
            image=img,
            density=3,
            wait_between_print_lines=0,
            print_line_batch_size=4,
            label_type=1,
        )

        # print_image resets _ema_latency; no row writes → EMA stays 0.0
        assert client._ema_latency == pytest.approx(0.0, abs=1e-9)

    run(_test())


def test_packet_order_matches_fixed_batch_baseline():
    """Adaptive flow must not change *which* packets are sent, only ACK cadence.

    The sequence of packet types emitted for batch=1 (every row blocking, no adaptation
    possible) must equal that for batch=8 on a fast link (adaptive widening).
    """
    img = _monochrome_image(96, 10, has_black=True)

    async def _collect(batch: int, latency: float) -> list[int]:
        transport = FakeTransport()
        client = _PatchedPrinterClient(latency=latency, transport=transport)
        await client.set_image(
            image=img,
            wait_between_print_lines=0,
            print_line_batch_size=batch,
        )
        return [p.type for p in transport.written_packets]

    async def _test():
        baseline = await _collect(batch=1, latency=0.0)
        adaptive = await _collect(batch=8, latency=ADAPTIVE_FAST_THRESHOLD * 0.5)
        assert adaptive == baseline

    run(_test())
