"""BLE session traces and the diagnostic report built from them."""

import asyncio

from PIL import Image
import pytest
from blesession import LinkInfo, SessionTrace, stages

from custom_components.niimbot.niimprint.parser import NiimbotDevice
from custom_components.niimbot.niimprint.printer import PrinterError, PrinterErrorCodeEnum
from custom_components.niimbot.session_report import (
    build_session_report,
    file_session_report,
    likely_cause,
)


def run(coro):
    return asyncio.run(coro)


class _Ble:
    name = "B1"
    address = "aa:bb:cc:dd:ee:ff"


def _patch_link(device: NiimbotDevice, printer, *, fail: BaseException | None = None) -> None:
    async def _ensure(_ble):
        if fail is not None:
            raise fail
        return printer

    async def _release():
        return None

    device._ensure_printer = _ensure  # type: ignore[method-assign]
    device._release_printer = _release  # type: ignore[method-assign]


def test_a_later_failure_does_not_replace_the_print_report():
    """Print Duration reads reports.last; a refresh failure stays on last_failure."""
    device = NiimbotDevice("aa:bb:cc:dd:ee:ff")
    printed = {"operation": "print", "success": True}
    file_session_report(device.reports, "print", printed, is_recorded_failure=False)
    assert device.reports.last == printed
    assert device.reports.last_failure is None

    failed = {"operation": "refresh_info", "success": False, "error": "down"}
    file_session_report(device.reports, "refresh_info", failed, is_recorded_failure=True)
    assert device.reports.last == printed
    assert device.reports.last_failure == failed


def test_a_successful_print_keeps_the_previous_failure():
    device = NiimbotDevice("aa:bb:cc:dd:ee:ff")
    failed = {"operation": "print", "success": False, "error": "cover"}
    file_session_report(device.reports, "print", failed, is_recorded_failure=True)
    assert device.reports.last == failed
    assert device.reports.last_failure == failed

    printed = {"operation": "print", "success": True}
    file_session_report(device.reports, "print", printed, is_recorded_failure=False)
    assert device.reports.last == printed
    assert device.reports.last_failure == failed


def test_a_report_that_cannot_be_built_clears_the_slot_it_owned():
    device = NiimbotDevice("aa:bb:cc:dd:ee:ff")
    device.reports.last = {"operation": "print", "success": True}
    device.reports.last_failure = {"operation": "print", "error": "cover"}
    file_session_report(device.reports, "print", None, is_recorded_failure=True)
    assert device.reports.last is None
    assert device.reports.last_failure is None


def test_cover_open_has_its_own_sentence():
    text = likely_cause(
        stages.TRANSFER, None, "Printer error: CoverOpen", {}, "print"
    )
    assert "cover" in text.lower()


def test_status_poll_connect_failure_is_described_as_normal():
    text = likely_cause(stages.CONNECT, None, "could not connect", {}, "update")
    assert "poll" in text.lower()


def test_report_carries_stages_radio_and_cause(monkeypatch):
    monkeypatch.setattr(
        "custom_components.niimbot.session_report.radio_facts",
        lambda *_args, **_kwargs: {
            "via": "kitchen",
            "via_type": "proxy",
            "rssi": -70,
            "paths": 1,
        },
    )
    trace = SessionTrace()
    with trace.timed(stages.CONNECT):
        pass
    with pytest.raises(PrinterError):
        with trace.timed(stages.TRANSFER):
            raise PrinterError(PrinterErrorCodeEnum.CoverOpen)
    report = build_session_report(
        None,  # type: ignore[arg-type]
        "aa:bb:cc:dd:ee:ff",
        operation="print",
        trace=trace,
        exc=PrinterError(PrinterErrorCodeEnum.CoverOpen),
    )
    assert report["success"] is False
    assert report["operation"] == "print"
    assert report["failed_stage"] == stages.TRANSFER
    assert "connect_s" in report
    assert "transfer_s" in report
    assert report["via"] == "kitchen"
    assert "cover" in report["likely_cause"].lower()


def test_failure_is_counted_and_kept_after_a_later_success():
    async def _test():
        device = NiimbotDevice("aa:bb:cc:dd:ee:ff")
        _patch_link(device, None, fail=OSError("down"))
        with pytest.raises(OSError):
            await device.update_device(_Ble())  # type: ignore[arg-type]
        assert device.error_count == 1
        assert device.last_failure_operation == "update"
        assert device.last_failure_at is not None
        failed = device.last_failure_trace
        assert failed is not None

        printer = _Printer()
        _patch_link(device, printer)
        assert await device.calibrate_height(_Ble()) is True  # type: ignore[arg-type]
        assert device.error_count == 1
        assert device.last_failure_trace is failed

    run(_test())


def test_print_failure_records_transfer_and_the_error_sensor_trace():
    async def _test():
        device = NiimbotDevice("aa:bb:cc:dd:ee:ff")
        device.model = "B1"
        device.ble_data.model = "B1"
        device.ble_data.devicetype = "4096"
        printer = _Printer()

        async def _print(*_args, **_kwargs):
            raise PrinterError(PrinterErrorCodeEnum.LackPaper)

        printer.print_image = _print  # type: ignore[method-assign]
        _patch_link(device, printer)

        with pytest.raises(PrinterError):
            await device.print_image(
                _Ble(),  # type: ignore[arg-type]
                Image.new("1", (8, 8)),
                3,
                0,
                1,
                label_type=1,
            )

        assert device.last_error == "LackPaper"
        assert device.error_count == 1
        assert device.last_failure_operation == "print"
        trace = device.last_print_trace
        assert trace is device.last_error_trace
        assert trace is not None
        assert trace.failed_primary == stages.TRANSFER
        assert "transfer_s" in {f"{name}_s" for name in trace.timings}
        assert "prepare_s" in {f"{name}_s" for name in trace.timings}

    run(_test())


def test_asleep_poll_does_not_replace_the_last_real_failure():
    async def _test():
        device = NiimbotDevice("aa:bb:cc:dd:ee:ff")
        device.model = "B1"
        device.ble_data.model = "B1"
        device.ble_data.devicetype = "4096"
        calls: list[str] = []
        device.callback_session = lambda operation, _trace, _exc: calls.append(operation)

        printer = _Printer()

        async def _print(*_args, **_kwargs):
            raise PrinterError(PrinterErrorCodeEnum.CoverOpen)

        printer.print_image = _print  # type: ignore[method-assign]
        _patch_link(device, printer)
        with pytest.raises(PrinterError):
            await device.print_image(
                _Ble(),  # type: ignore[arg-type]
                Image.new("1", (8, 8)),
                3,
                0,
                1,
                label_type=1,
            )
        failed = device.last_failure_trace
        assert device.error_count == 1
        assert calls == ["print"]

        async def _asleep(_ble):
            trace = device._active_trace
            assert trace is not None
            with trace.timed(stages.CONNECT):
                raise OSError("asleep")

        device._ensure_printer = _asleep  # type: ignore[method-assign]
        with pytest.raises(OSError):
            await device.update_device(_Ble())  # type: ignore[arg-type]
        assert device.error_count == 1
        assert device.last_failure_trace is failed
        assert calls == ["print"]

    run(_test())


def test_fresh_connect_uses_ble_session():
    """Opening a link is blesession's job, including the service-cache bypass."""

    async def _test():
        device = NiimbotDevice("aa:bb:cc:dd:ee:ff")
        seen: dict = {}

        class _Client:
            is_connected = True

        class _Session:
            async def __aenter__(self):
                seen["entered"] = True
                return _Client()

            async def __aexit__(self, *_exc):
                seen["exited"] = True

        def _ble_session(*_args, **kwargs):
            seen["kwargs"] = kwargs
            return _Session()

        class _Held:
            heartbeat_payload = None

            async def start_notify(self):
                return None

            async def stop_notify(self):
                return None

        device._active_trace = SessionTrace()
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(
                "custom_components.niimbot.niimprint.parser.ble_session", _ble_session
            )
            patch.setattr(
                "custom_components.niimbot.niimprint.parser.PrinterClient",
                lambda *args, **kwargs: _Held(),
            )
            await device._ensure_printer(_Ble())  # type: ignore[arg-type]
            await device._release_printer()

        assert seen["entered"] is True
        assert seen["exited"] is True
        assert seen["kwargs"]["keep"] is False
        assert seen["kwargs"]["use_services_cache"] is False

    run(_test())


def test_reused_connection_keeps_the_probed_link():
    async def _test():
        device = NiimbotDevice("aa:bb:cc:dd:ee:ff", keep_connection=True)

        class _Client:
            is_connected = True

        class _Held:
            heartbeat_payload = None

        device.client = _Client()
        device._printer = _Held()  # type: ignore[assignment]
        device._link = LinkInfo(via="proxy-1")
        device._active_trace = SessionTrace()
        await device._ensure_printer(_Ble())  # type: ignore[arg-type]
        await device._release_printer()
        assert device._active_trace.facts["reused"] is True
        assert stages.CONNECT not in device._active_trace.timings
        assert device.client is not None

    run(_test())


def test_refresh_info_failure_is_attributed_to_info():
    async def _test():
        device = NiimbotDevice("aa:bb:cc:dd:ee:ff")

        async def _load(_printer, force=False):
            raise RuntimeError("status")

        device._load_printer_info = _load  # type: ignore[method-assign]
        _patch_link(device, _Printer())
        with pytest.raises(RuntimeError):
            await device.refresh_info(_Ble())  # type: ignore[arg-type]
        trace = device.last_failure_trace
        assert trace is not None
        assert trace.failed_detail == "info"
        assert device.last_failure_operation == "refresh_info"
        assert device.error_count == 1

    run(_test())


def test_refresh_info_connect_failure_is_a_real_failure():
    """Unlike the background poll, a user-triggered refresh that cannot
    connect must land on Last Failure."""

    async def _test():
        device = NiimbotDevice("aa:bb:cc:dd:ee:ff")
        calls: list[str] = []
        device.callback_session = lambda operation, _trace, _exc: calls.append(operation)

        async def _asleep(_ble):
            trace = device._active_trace
            assert trace is not None
            with trace.timed(stages.CONNECT):
                raise OSError("asleep")

        device._ensure_printer = _asleep  # type: ignore[method-assign]

        async def _release():
            return None

        device._release_printer = _release  # type: ignore[method-assign]
        with pytest.raises(OSError):
            await device.refresh_info(_Ble())  # type: ignore[arg-type]
        assert device.error_count == 1
        assert device.last_failure_operation == "refresh_info"
        assert calls == ["refresh_info"]

    run(_test())


class _Printer:
    async def calibrate_height(self) -> bool:
        return True


def test_a_dropped_link_ends_the_command_without_the_step_timeout():
    """A printer that powers off mid-command must not sit out the read timeout."""

    async def _test():
        from blesession import SessionDropped, ble_session
        from blesession import session as session_mod
        from blesession.testing import FakeClient, FakeDevice, fake_connect

        from custom_components.niimbot.niimprint.printer import (
            BLETransport,
            PrinterClient,
            RequestCodeEnum,
        )

        client = FakeClient()
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(session_mod, "establish_connection", fake_connect(client))
            async with ble_session(FakeDevice()):
                transport = BLETransport(client)
                printer = PrinterClient(transport=transport)
                client.drop()
                started = asyncio.get_running_loop().time()
                with pytest.raises(SessionDropped, match="link dropped"):
                    await printer._transceive(
                        RequestCodeEnum.HEARTBEAT, b"\x01", timeout=30
                    )
                assert asyncio.get_running_loop().time() - started < 1

                # A reply that already arrived is the answer, even if the
                # link went away before it was read.
                transport._notification_handler(None, bytearray(b"\x55\x55"))
                assert await transport.read(8, timeout=30) == b"\x55\x55"

    run(_test())
