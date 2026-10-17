"""Setup, runtime data and unload against a real Home Assistant."""

from __future__ import annotations

from tests.components.niimbot.conftest import (
    ADDRESS,
    ADDRESS_2,
    setup_entry,
    make_ble_device,
)
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
    assert (
        hass.services.async_services_for_domain(DOMAIN)[SERVICE_PRINT] is print_service
    )


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
    hass: HomeAssistant, enable_bluetooth: None, printer_response
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
    assert hass.states.get(by_key["error_count"]).state == "unavailable"
    # A successful external response recovers the coordinator before the
    # independent device session failure updates its diagnostic entities.
    from unittest.mock import AsyncMock, patch

    with (
        patch(
            "homeassistant.components.bluetooth.async_ble_device_from_address",
            return_value=make_ble_device(ADDRESS),
        ),
        patch.object(
            device, "_ensure_printer", AsyncMock(return_value=printer_response)
        ),
        patch.object(device, "_release_printer", AsyncMock()),
    ):
        await entry.runtime_data.coordinator.async_refresh()
        await hass.async_block_till_done()
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


async def test_platform_registry_state_and_reload(hass, enable_bluetooth):
    """All six platforms register entities, expose states, and survive reload."""
    from homeassistant.helpers import entity_registry as er

    entry = await setup_entry(hass)
    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, entry.entry_id)
    assert {item.domain for item in entities} == {
        "sensor",
        "binary_sensor",
        "button",
        "switch",
        "select",
        "image",
    }
    active = [item.entity_id for item in entities if item.disabled_by is None]
    assert active
    assert all(hass.states.get(entity_id) is not None for entity_id in active)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert all(hass.states.get(entity_id) is not None for entity_id in active)


async def test_unload_cancels_inflight_cloud_request(
    hass, enable_bluetooth, printer_response
):
    """An HTTP request that is still waiting is cancelled when its entry unloads."""
    import asyncio
    from unittest.mock import AsyncMock, patch
    from custom_components.niimbot.const import CONF_USE_CLOUD_LABEL_INFO

    entry = await setup_entry(hass, options={CONF_USE_CLOUD_LABEL_INFO: True})
    device = entry.runtime_data.device
    runtime = entry.runtime_data
    device.ble_data.sensors["label_sku"] = "TEST-BARCODE"
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def pending_fetch(_barcode):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    with (
        patch(
            "homeassistant.components.bluetooth.async_ble_device_from_address",
            return_value=make_ble_device(ADDRESS),
        ),
        patch.object(
            device, "_ensure_printer", AsyncMock(return_value=printer_response)
        ),
        patch.object(device, "_release_printer", AsyncMock()),
        patch.object(entry.runtime_data.cloud_lookup, "_fetch", pending_fetch),
    ):
        await entry.runtime_data.coordinator.async_refresh()
        await asyncio.wait_for(started.wait(), timeout=2)
        assert entry.runtime_data.cloud_tasks
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
    assert cancelled.is_set()
    assert not runtime.cloud_tasks


async def test_partial_platform_setup_failure_cleans_entities_and_connection(
    hass, enable_bluetooth
):
    """A failure after forwarding actual platforms releases their resources."""
    from unittest.mock import AsyncMock, patch
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.niimbot.niimprint.parser import NiimbotDevice
    from homeassistant.helpers import entity_registry as er

    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, title="Niimbot")
    entry.add_to_hass(hass)
    original = hass.config_entries.async_forward_entry_setups
    runtimes = []

    async def forward_then_fail(config_entry, platforms):
        await original(config_entry, platforms)
        runtimes.append(config_entry.runtime_data)
        raise RuntimeError("platform setup failed")

    with (
        patch.object(
            hass.config_entries, "async_forward_entry_setups", forward_then_fail
        ),
        patch.object(NiimbotDevice, "disconnect", AsyncMock()) as disconnect,
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    disconnect.assert_awaited_once()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert runtimes[0].coordinator._unsub_refresh is None
    assert not runtimes[0].cloud_tasks
    registered = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert registered
    for item in registered:
        state = hass.states.get(item.entity_id)
        # HA may keep a registry placeholder after the actual entity is removed.
        assert state is None or (
            state.state == "unavailable" and state.attributes.get("restored")
        )


async def test_options_flow_saves_settings_and_reloads(hass, enable_bluetooth):
    """HA options manager persists settings and reloads the configured printer."""
    from custom_components.niimbot.const import (
        CONF_KEEP_CONNECTION,
        CONF_USE_CLOUD_LABEL_INFO,
    )
    from homeassistant.const import CONF_SCAN_INTERVAL

    entry = await setup_entry(hass)
    old_device = entry.runtime_data.device
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"
    options = {
        CONF_SCAN_INTERVAL: 60,
        CONF_KEEP_CONNECTION: True,
        CONF_USE_CLOUD_LABEL_INFO: False,
    }
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=options
    )
    await hass.async_block_till_done()
    assert result["type"] == "create_entry"
    assert dict(entry.options) == options
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.device is not old_device
