"""Multi-copy packet counts and incomplete jobs through the HA action."""

import struct
import time
from asyncio import CancelledError
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from PIL import Image
import pytest

from custom_components.niimbot.const import DOMAIN
from custom_components.niimbot.niimprint import printer as printer_module
from custom_components.niimbot.niimprint.model import (
    PrinterModel,
    PrintGeneration,
    modelsLibrary,
    density_range,
    get_printer_meta_by_model,
)
from custom_components.niimbot.niimprint.packet import NiimbotPacket
from custom_components.niimbot.niimprint.printer import (
    PAGE_INDEX_CMD,
    PrinterClient,
    PrinterCompletionTimeout,
    PrinterError,
    PrinterErrorCodeEnum,
    RequestCodeEnum,
)
from custom_components.niimbot.services import SERVICE_PRINT
from tests.components.niimbot.conftest import make_ble_device, setup_entry
from tests.components.niimbot.fake_transport import FakeTransport


class StatusTransport(FakeTransport):
    """Answer commands when sent; simulate physical page completion over time."""

    def __init__(
        self,
        statuses,
        *,
        cleanup_error=False,
        page_index=None,
        reject_command=None,
        fail_command=None,
        failure=None,
        status_error=0,
        on_command=None,
        protocol_version=5,
    ):
        super().__init__()
        self.statuses = iter(statuses)
        self.now = 0.0
        self.cleanup_error = cleanup_error
        self.page_index = page_index
        self.reject_command = reject_command
        self.fail_command = fail_command
        self.failure = failure
        self.status_error = status_error
        self.on_command = on_command
        self.protocol_version = protocol_version

    async def write(self, data, response=True):
        await super().write(data, response=response)
        packet = NiimbotPacket.from_bytes(data)
        command = packet.type
        if self.on_command:
            self.on_command(command)
        if command == self.fail_command:
            raise self.failure
        if command == self.reject_command:
            offset = (
                16
                if command
                in (
                    RequestCodeEnum.SET_LABEL_DENSITY,
                    RequestCodeEnum.SET_LABEL_TYPE,
                    RequestCodeEnum.ALLOW_PRINT_CLEAR,
                )
                else 1
            )
            self.queue(NiimbotPacket(command + offset, b"\x00"))
            return
        if command == RequestCodeEnum.GET_PRINT_STATUS:
            self.now, page, progress = next(self.statuses)
            payload = struct.pack(">HBB", page, progress, progress)
            if self.status_error:
                payload += bytes((0, 0, self.status_error, 0, 0, 0))
            self.queue(NiimbotPacket(command + 16, payload))
        elif command == RequestCodeEnum.GET_PRINTER_STATUS_DATA:
            self.queue(
                NiimbotPacket(
                    command + 16,
                    bytes(11) + bytes((3, 2 if self.protocol_version == 5 else 0)),
                )
            )
        elif command == RequestCodeEnum.CANCEL_PRINT:
            self.queue(NiimbotPacket(0xD0, b"\x00"))
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


@pytest.mark.parametrize("meta", modelsLibrary, ids=lambda meta: meta["model"].name)
@pytest.mark.parametrize("copies", [1, 5, 99])
async def test_all_models_declare_copies(monkeypatch, meta, copies):
    transport = StatusTransport([], page_index=copies)
    use_clock(monkeypatch, transport)
    client = PrinterClient(transport=transport)
    await client.print_image(
        meta["model"],
        Image.new("1", (meta["printheadPixels"], 1)),
        density=density_range(get_printer_meta_by_model(meta["model"]))[0],
        copies=copies,
    )
    packets = transport.written_packets
    if meta["generation"] in (PrintGeneration.OLD_D11, PrintGeneration.D110):
        quantity = next(p for p in packets if p.type == RequestCodeEnum.SET_QUANTITY)
        assert struct.unpack(">H", quantity.data)[0] == copies
    else:
        start = next(p for p in packets if p.type == RequestCodeEnum.START_PRINT)
        dimension = next(p for p in packets if p.type == RequestCodeEnum.SET_DIMENSION)
        assert struct.unpack(">H", start.data[:2])[0] == copies
        assert struct.unpack(">H", dimension.data[4:6])[0] == copies


@pytest.mark.parametrize("protocol_version", [4, 5])
async def test_unknown_model_multicopy_fallback(monkeypatch, protocol_version):
    transport = StatusTransport([], page_index=5, protocol_version=protocol_version)
    use_clock(monkeypatch, transport)
    await PrinterClient(transport=transport).print_image(
        PrinterModel.UNKNOWN, Image.new("1", (96, 1)), density=3, copies=5
    )
    start = next(
        p for p in transport.written_packets if p.type == RequestCodeEnum.START_PRINT
    )
    assert len(start.data) == (9 if protocol_version == 5 else 7)
    assert struct.unpack(">H", start.data[:2])[0] == 5


GENERATIONS = [
    PrinterModel.D11,
    PrinterModel.D110,
    PrinterModel.B1,
    PrinterModel.D110_M,
]
COMMON_COMMANDS = [
    RequestCodeEnum.SET_LABEL_DENSITY,
    RequestCodeEnum.SET_LABEL_TYPE,
    RequestCodeEnum.START_PRINT,
    RequestCodeEnum.SET_DIMENSION,
    RequestCodeEnum.END_PAGE_PRINT,
    RequestCodeEnum.END_PRINT,
]
ACK_CASES = [(model, command) for model in GENERATIONS for command in COMMON_COMMANDS]
ACK_CASES += [
    (model, command)
    for model in GENERATIONS[:3]
    for command in [RequestCodeEnum.START_PAGE_PRINT]
]
ACK_CASES += [(model, RequestCodeEnum.SET_QUANTITY) for model in GENERATIONS[:2]]
ACK_CASES += [(PrinterModel.D11, RequestCodeEnum.ALLOW_PRINT_CLEAR)]


@pytest.mark.parametrize("model,command", ACK_CASES)
async def test_rejected_print_command_fails_and_stops_sequence(
    monkeypatch, model, command
):
    transport = StatusTransport([], page_index=5, reject_command=command)
    use_clock(monkeypatch, transport)
    with pytest.raises(RuntimeError):
        await PrinterClient(transport=transport).print_image(
            model, Image.new("1", (96, 1)), density=3, copies=5
        )
    packets = transport.written_packets
    index = next(i for i, p in enumerate(packets) if p.type == command)
    assert all(p.type == RequestCodeEnum.END_PRINT for p in packets[index + 1 :])
    cleanup_expected = command not in (
        RequestCodeEnum.SET_LABEL_DENSITY,
        RequestCodeEnum.SET_LABEL_TYPE,
        RequestCodeEnum.START_PRINT,
    )
    assert sum(p.type == RequestCodeEnum.END_PRINT for p in packets) == int(
        cleanup_expected
    )


@pytest.mark.parametrize("model", GENERATIONS)
@pytest.mark.parametrize("during_poll", [False, True])
async def test_cancellation_after_upload_reaches_printer(
    monkeypatch, model, during_poll
):
    transport = StatusTransport([(0, 0, 10)])
    use_clock(monkeypatch, transport)
    client = PrinterClient(transport=transport)
    trigger = (
        RequestCodeEnum.GET_PRINT_STATUS
        if during_poll
        else RequestCodeEnum.END_PAGE_PRINT
    )

    def request_cancel(command):
        if command == trigger:
            client.cancel_requested = True

    transport.on_command = request_cancel
    result = await client.print_image(
        model, Image.new("1", (96, 1)), density=3, copies=5
    )
    assert result == {"status": "cancelled"}
    assert not client.cancel_requested
    assert not client._print_task_active
    assert transport.written_packets[-1].type == RequestCodeEnum.CANCEL_PRINT


@pytest.mark.parametrize("model", GENERATIONS)
@pytest.mark.parametrize(
    "failure", [ConnectionError("Transfer disconnected"), CancelledError()]
)
async def test_transfer_failure_cleans_task_without_masking_error(
    monkeypatch, model, failure
):
    transport = StatusTransport(
        [],
        fail_command=RequestCodeEnum.PRINT_BITMAP_ROW,
        failure=failure,
        cleanup_error=True,
    )
    use_clock(monkeypatch, transport)
    with pytest.raises(type(failure)) as caught:
        await PrinterClient(transport=transport).print_image(
            model, Image.new("1", (96, 1)), density=3
        )
    assert caught.value is failure
    assert transport.written_packets[-1].type == RequestCodeEnum.END_PRINT


@pytest.mark.parametrize("model", GENERATIONS)
@pytest.mark.parametrize("error", [PrinterErrorCodeEnum.LackPaper, 0xFE])
async def test_status_error_fails_even_with_completed_page(monkeypatch, model, error):
    transport = StatusTransport([(0, 5, 100)], status_error=error)
    use_clock(monkeypatch, transport)
    with pytest.raises(PrinterError) as caught:
        await PrinterClient(transport=transport).print_image(
            model, Image.new("1", (96, 1)), density=3, copies=5
        )
    assert caught.value.raw_code == error
    assert transport.written_packets[-1].type == RequestCodeEnum.END_PRINT


@pytest.mark.parametrize("copies", [0, -1, 65536, 1.5])
async def test_invalid_copy_count_fails_before_print_commands(copies):
    transport = StatusTransport([])
    with pytest.raises(ValueError, match="copies must be an integer"):
        await PrinterClient(transport=transport).print_image(
            PrinterModel.B1, Image.new("1", (96, 1)), density=3, copies=copies
        )
    assert not transport.written_packets


@pytest.mark.parametrize("model", GENERATIONS)
@pytest.mark.parametrize("copies", [1, 5])
async def test_short_job_completes_on_observed_page_advance(monkeypatch, model, copies):
    transport = StatusTransport([(0, 0, 100), (1, copies, 100)])
    use_clock(monkeypatch, transport)
    await PrinterClient(transport=transport).print_image(
        model, Image.new("1", (96, 1)), density=3, copies=copies
    )
    assert (
        transport.written_packets[-1 if model != PrinterModel.D110_M else -2].type
        == RequestCodeEnum.END_PRINT
    )


@pytest.mark.parametrize("copies", [1, 5])
async def test_stale_completed_snapshot_is_not_current_job_success(monkeypatch, copies):
    transport = StatusTransport([(0, copies, 100), (76, copies, 100)])
    use_clock(monkeypatch, transport)
    with pytest.raises(PrinterCompletionTimeout):
        await PrinterClient(transport=transport).print_image(
            PrinterModel.B1, Image.new("1", (96, 1)), density=3, copies=copies
        )


async def test_print_image_rejects_width_over_printhead():
    transport = StatusTransport([(0, 0, 10), (1, 1, 100)])
    client = PrinterClient(transport=transport)
    with pytest.raises(ValueError, match="exceeds the 96px printhead"):
        await client.print_image(
            PrinterModel.D11, Image.new("1", (240, 96)), density=2
        )
    assert not transport.written_packets
