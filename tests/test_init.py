"""Setup, runtime data and unload against a real Home Assistant."""

from __future__ import annotations

from conftest import ADDRESS, ADDRESS_2, setup_entry
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.niimbot.const import DOMAIN
from custom_components.niimbot.services import SERVICE_PRINT, SERVICE_REFRESH_INFO


async def test_setup_attaches_runtime_data_and_registers_services_once(
    hass: HomeAssistant, enable_bluetooth: None
) -> None:
    """Loading two printers keeps one service handler and separate runtime data."""
    first = await setup_entry(hass, address=ADDRESS)
    print_service = hass.services.async_services_for_domain(DOMAIN)[SERVICE_PRINT]
    second = await setup_entry(hass, address=ADDRESS_2)

    assert first.state is ConfigEntryState.LOADED
    assert second.state is ConfigEntryState.LOADED
    assert first.runtime_data.address == ADDRESS
    assert second.runtime_data.address == ADDRESS_2
    assert first.runtime_data.device is not second.runtime_data.device
    assert hass.services.has_service(DOMAIN, SERVICE_PRINT)
    assert hass.services.has_service(DOMAIN, SERVICE_REFRESH_INFO)
    # A second entry must not replace the domain handler.
    assert hass.services.async_services_for_domain(DOMAIN)[SERVICE_PRINT] is print_service


async def test_unload_disconnects_and_leaves_the_other_printer(
    hass: HomeAssistant, enable_bluetooth: None
) -> None:
    """Unloading one entry disconnects that printer and leaves the other loaded."""
    first = await setup_entry(hass, address=ADDRESS)
    second = await setup_entry(hass, address=ADDRESS_2)
    disconnected: list[str] = []

    async def record_disconnect() -> None:
        disconnected.append(ADDRESS)

    first.runtime_data.device.disconnect = record_disconnect

    assert await hass.config_entries.async_unload(first.entry_id)
    await hass.async_block_till_done()

    assert disconnected == [ADDRESS]
    assert first.state is ConfigEntryState.NOT_LOADED
    assert second.state is ConfigEntryState.LOADED
    assert hass.services.has_service(DOMAIN, SERVICE_PRINT)


async def test_a_session_is_recorded_and_a_report_that_cannot_be_built_still_counts(
    hass: HomeAssistant, enable_bluetooth: None, monkeypatch
) -> None:
    """The published session lands in ``reports``; a builder that raises is
    replaced by ``fallback_report`` so the failure is still counted and Last
    Error still gets a report."""
    from blesession import SessionTrace, stages

    entry = await setup_entry(hass, address=ADDRESS)
    device = entry.runtime_data.device
    seen = []
    device.reports.add_listener(lambda: seen.append(device.reports.last_kind))

    trace = SessionTrace()
    with trace.timed(stages.TRANSFER):
        pass
    device.callback_session("print", trace, None)
    assert device.reports.of("print")["success"] is True
    assert device.reports.failures == 0

    def boom(*_args, **_kwargs):
        raise RuntimeError("radio")

    monkeypatch.setattr("custom_components.niimbot.build_session_report", boom)
    failed = SessionTrace()
    device.last_error_trace = failed
    device.callback_session("print", failed, OSError("down"))

    assert device.reports.failures == 1
    assert device.reports.last_failure["error"] == "down"
    assert device.last_error_report is device.reports.last_failure
    assert seen == ["ok", "failure"]


async def test_a_failed_refresh_reaches_the_diagnostic_sensors_and_unload_drops_them(
    hass: HomeAssistant, enable_bluetooth: None
) -> None:
    """Error Count and Last Failure follow ``reports`` through the real
    publisher, and unloading removes their listeners."""
    from blesession import stages
    from homeassistant.helpers import entity_registry as er

    class _Ble:
        name = "B1"
        address = ADDRESS

    entry = await setup_entry(hass, address=ADDRESS)
    device = entry.runtime_data.device

    registry = er.async_get(hass)
    by_key = {
        e.translation_key: e.entity_id
        for e in er.async_entries_for_config_entry(registry, entry.entry_id)
        if e.translation_key in {"error_count", "last_failure"}
    }
    assert set(by_key) == {"error_count", "last_failure"}
    assert hass.states.get(by_key["error_count"]).state == "0"
    listeners_loaded = len(device.reports._listeners)
    assert listeners_loaded >= 2

    async def _fail(_ble):
        trace = device._active_trace
        with trace.timed(stages.CONNECT):
            raise OSError("down")

    async def _release():
        return None

    device._ensure_printer = _fail  # type: ignore[method-assign]
    device._release_printer = _release  # type: ignore[method-assign]
    try:
        await device.refresh_info(_Ble())  # type: ignore[arg-type]
    except OSError:
        pass
    await hass.async_block_till_done()

    assert hass.states.get(by_key["error_count"]).state == "1"
    failure = hass.states.get(by_key["last_failure"])
    assert failure.state not in ("unknown", "unavailable")
    assert failure.attributes["operation"] == "refresh_info"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert len(device.reports._listeners) == listeners_loaded - 2
