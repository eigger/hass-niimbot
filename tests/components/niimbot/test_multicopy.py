"""Multi-copy packet counts and incomplete jobs through the HA action."""

import struct
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from PIL import Image
import pytest

from custom_components.niimbot.const import DOMAIN
from custom_components.niimbot.niimprint import printer as printer_module
from custom_components.niimbot.niimprint.model import PrinterModel
from custom_components.niimbot.niimprint.packet import NiimbotPacket
from custom_components.niimbot.niimprint.printer import (
    PAGE_INDEX_CMD,
    PrinterClient,
    PrinterCompletionTimeout,
    RequestCodeEnum,
)
from custom_components.niimbot.services import SERVICE_PRINT
from tests.components.niimbot.conftest import make_ble_device, setup_entry
from tests.components.niimbot.fake_transport import FakeTransport


class StatusTransport(FakeTransport):
    """Answer commands when sent; simulate physical page completion over time."""

    def __init__(self, statuses, *, cleanup_error=False, page_index=None):
        super().__init__()
        self.statuses = iter(statuses)
        self.now = 0.0
        self.cleanup_error = cleanup_error
        self.page_index = page_index

    async def write(self, data, response=True):
        await super().write(data, response=response)
        packet = NiimbotPacket.from_bytes(data)
        command = packet.type
        if command == RequestCodeEnum.GET_PRINT_STATUS:
            self.now, page, progress = next(self.statuses)
            self.queue(
                NiimbotPacket(
                    command + 16, struct.pack(">HBB", page, progress, progress)
                )
            )
        elif command == RequestCodeEnum.END_PRINT and self.cleanup_error:
            raise ConnectionError("Disconnected during cleanup")
        elif command in (
            RequestCodeEnum.SET_LABEL_DENSITY,
            RequestCodeEnum.SET_LABEL_TYPE,
        ):
            self.queue(NiimbotPacket(command + 16, b"\x01"))
        elif command in (
            RequestCodeEnum.START_PRINT,
            RequestCodeEnum.START_PAGE_PRINT,
            RequestCodeEnum.SET_DIMENSION,
            RequestCodeEnum.SET_QUANTITY,
            RequestCodeEnum.ALLOW_PRINT_CLEAR,
            RequestCodeEnum.END_PAGE_PRINT,
            RequestCodeEnum.END_PRINT,
        ):
            offset = 16 if command == RequestCodeEnum.ALLOW_PRINT_CLEAR else 1
            self.queue(NiimbotPacket(command + offset, b"\x01"))
            if (
                command == RequestCodeEnum.END_PAGE_PRINT
                and self.page_index is not None
            ):
                self.queue(
                    NiimbotPacket(PAGE_INDEX_CMD, struct.pack(">H", self.page_index))
                )


def use_clock(monkeypatch, transport):
    """Advance only the printer clock, leaving HA's event loop clock intact."""
    monkeypatch.setattr(
        printer_module,
        "time",
        SimpleNamespace(time=time.time, monotonic=lambda: transport.now),
    )
    monkeypatch.setattr(printer_module, "sleep", AsyncMock())


@pytest.mark.parametrize("model", [PrinterModel.B1, PrinterModel.D110_M])
@pytest.mark.parametrize("copies", [1, 5])
async def test_job_and_page_counts_include_every_copy(monkeypatch, model, copies):
    statuses = (
        [(0, 0, 10), (1, 1, 100)]
        if copies == 1
        else [(0, 1, 100), (1, 2, 10), (2, copies, 100)]
    )
    transport = StatusTransport(statuses)
    use_clock(monkeypatch, transport)
    client = PrinterClient(transport=transport)

    await client.print_image(model, Image.new("1", (96, 10)), density=3, copies=copies)

    packets = transport.written_packets
    start = next(p for p in packets if p.type == RequestCodeEnum.START_PRINT)
    dimension = next(p for p in packets if p.type == RequestCodeEnum.SET_DIMENSION)
    assert struct.unpack(">H", start.data[:2])[0] == copies
    assert struct.unpack(">HHH", dimension.data[:6]) == (10, 96, copies)
    assert sum(p.type == RequestCodeEnum.GET_PRINT_STATUS for p in packets) == len(
        statuses
    )
    assert sum(p.type == RequestCodeEnum.END_PRINT for p in packets) == 1


@pytest.mark.parametrize(
    "model", [PrinterModel.D11, PrinterModel.D110, PrinterModel.B1, PrinterModel.D110_M]
)
@pytest.mark.parametrize("cleanup_error", [False, True])
async def test_incomplete_copies_raise_and_end_the_job(
    monkeypatch, model, cleanup_error
):
    transport = StatusTransport([(76, 1, 100)], cleanup_error=cleanup_error)
    use_clock(monkeypatch, transport)
    client = PrinterClient(transport=transport)

    with pytest.raises(PrinterCompletionTimeout, match=r"within 75s .*copies=5"):
        await client.print_image(model, Image.new("1", (96, 10)), density=3, copies=5)

    assert (
        sum(p.type == RequestCodeEnum.END_PRINT for p in transport.written_packets) == 1
    )


async def test_multicopy_completion_notification(monkeypatch):
    transport = StatusTransport([], page_index=5)
    use_clock(monkeypatch, transport)
    client = PrinterClient(transport=transport)

    await client.print_image(
        PrinterModel.D110_M, Image.new("1", (96, 10)), density=3, copies=5
    )

    assert not any(
        p.type == RequestCodeEnum.GET_PRINT_STATUS for p in transport.written_packets
    )
    assert transport.written_packets[-2].type == RequestCodeEnum.END_PRINT


async def test_incomplete_job_fails_ha_action_and_records_error(
    hass: HomeAssistant, enable_bluetooth: None, monkeypatch
):
    entry = await setup_entry(hass)
    device = entry.runtime_data.device
    device.model = "D110_M"
    transport = StatusTransport([(76, 1, 100)])
    use_clock(monkeypatch, transport)
    client = PrinterClient(transport=transport)
    release = AsyncMock()

    with (
        patch.object(device, "_ensure_printer", AsyncMock(return_value=client)),
        patch.object(device, "_release_printer", release),
        patch(
            "homeassistant.components.bluetooth.async_ble_device_from_address",
            lambda *args, **kwargs: make_ble_device(),
        ),
    ):
        with pytest.raises(HomeAssistantError, match="Print completion not confirmed"):
            await hass.services.async_call(
                DOMAIN,
                SERVICE_PRINT,
                {
                    "payload": [
                        {
                            "type": "rectangle",
                            "x_start": 0,
                            "y_start": 0,
                            "x_end": 10,
                            "y_end": 10,
                            "fill": "black",
                        }
                    ],
                    "width": 20,
                    "height": 20,
                    "copies": 5,
                },
                blocking=True,
            )
        await hass.async_block_till_done()

    release.assert_awaited_once()
    assert not device.is_printing
    assert device.last_error == "PrinterCompletionTimeout"
    assert device.reports.of("print")["success"] is False
    assert device.reports.failures == 1
    assert device.print_page == 1
