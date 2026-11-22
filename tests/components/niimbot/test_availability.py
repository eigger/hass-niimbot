"""Last-known availability and device registry sync against a real HA."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.niimbot.entity import async_sync_device_registry

from .conftest import ADDRESS, device_of, make_ble_device, setup_entry


@contextmanager
def _printer_reachable(device, printer_response):
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
        yield


def _entity_id(hass, entry, domain, *, key):
    for item in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id):
        if item.domain == domain and item.unique_id.endswith(f"_{key}"):
            return item.entity_id
    raise AssertionError((domain, key))


async def test_keep_last_known_while_unreachable(
    hass, enable_bluetooth, printer_response
):
    entry = await setup_entry(hass)
    device = entry.runtime_data.device
    coordinator = entry.runtime_data.coordinator
    ids = {
        "battery": _entity_id(hass, entry, "sensor", key="battery"),
        "density": _entity_id(hass, entry, "sensor", key="density"),
        "select": _entity_id(hass, entry, "select", key="auto_shutdown"),
        "progress": _entity_id(hass, entry, "sensor", key="print_progress"),
        "cover": _entity_id(hass, entry, "binary_sensor", key="closingstate"),
        "connection": _entity_id(hass, entry, "binary_sensor", key="connection"),
        "error_count": _entity_id(hass, entry, "sensor", key="error_count"),
        "duration": _entity_id(hass, entry, "sensor", key="print_duration"),
    }
    # Printer off from the start: nothing known yet.
    assert hass.states.get(ids["battery"]).state == "unavailable"
    assert hass.states.get(ids["select"]).state == "unavailable"
    assert hass.states.get(ids["connection"]).state == "off"
    assert hass.states.get(ids["error_count"]).state != "unavailable"
    assert hass.states.get(ids["duration"]).state != "unavailable"

    with _printer_reachable(device, printer_response):
        await coordinator.async_refresh()
        await hass.async_block_till_done()
    assert coordinator.last_update_success
    known = {k: hass.states.get(v).state for k, v in ids.items()}
    assert known["battery"] not in ("unavailable", "unknown")
    assert known["density"] not in ("unavailable", "unknown")
    assert known["select"] not in ("unavailable", "unknown")
    assert known["progress"] != "unavailable"
    assert known["cover"] in ("on", "off")

    # The next poll fails: the printer is off again.
    with patch(
        "homeassistant.components.bluetooth.async_ble_device_from_address",
        return_value=None,
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()
    assert not coordinator.last_update_success

    for key in ("battery", "density", "select", "error_count", "duration"):
        assert hass.states.get(ids[key]).state == known[key], key
    # State that can change while the printer is off is not trusted.
    assert hass.states.get(ids["progress"]).state == "unavailable"
    assert hass.states.get(ids["cover"]).state == "unavailable"
    # Connectivity is the offline signal: available and off.
    assert hass.states.get(ids["connection"]).state == "off"


async def test_registry_updated_by_later_successful_poll(
    hass, enable_bluetooth, printer_response
):
    entry = await setup_entry(hass)  # printer unreachable at startup
    before = device_of(hass, entry_id=entry.entry_id)
    assert not before.model
    assert not before.sw_version

    device = entry.runtime_data.device
    with _printer_reachable(device, printer_response):
        await entry.runtime_data.coordinator.async_refresh()
        await hass.async_block_till_done()

    after = device_of(hass, entry_id=entry.entry_id)
    assert after.id == before.id
    assert after.model == device.ble_data.model
    assert after.model
    assert after.sw_version == device.ble_data.sw_version == "1"
    assert after.hw_version == "1"
    assert after.serial_number == "TEST00001"


async def test_registry_never_overwritten_with_empty(
    hass, enable_bluetooth, printer_response
):
    entry = await setup_entry(hass)
    device = entry.runtime_data.device
    with _printer_reachable(device, printer_response):
        await entry.runtime_data.coordinator.async_refresh()
        await hass.async_block_till_done()
    known = device_of(hass, entry_id=entry.entry_id)
    assert known.model and known.sw_version

    # Sync with empty values does nothing and does not touch the registry.
    registry = dr.async_get(hass)
    empty = type(device.ble_data)(address=ADDRESS)
    with patch.object(registry, "async_update_device") as update:
        async_sync_device_registry(hass, empty)
        async_sync_device_registry(hass, device.ble_data)  # unchanged
    update.assert_not_called()
    assert device_of(hass, entry_id=entry.entry_id).model == known.model

    # A reload while the printer is off (fresh, empty BLEData) keeps the values.
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    reloaded = device_of(hass, entry_id=entry.entry_id)
    assert reloaded.model == known.model
    assert reloaded.sw_version == known.sw_version
    assert reloaded.hw_version == known.hw_version
    assert reloaded.serial_number == known.serial_number


async def test_registry_updated_by_non_poll_data_update(hass, enable_bluetooth):
    """A print or settings change pushes data via async_set_updated_data."""
    entry = await setup_entry(hass)  # printer unreachable at startup
    assert not device_of(hass, entry_id=entry.entry_id).model

    entry.runtime_data.device.ble_data.model = "B1"
    entry.runtime_data.device.ble_data.sw_version = "5.1"
    entry.runtime_data.coordinator.async_set_updated_data(
        entry.runtime_data.device.ble_data
    )
    await hass.async_block_till_done()

    device = device_of(hass, entry_id=entry.entry_id)
    assert device.model == "B1"
    assert device.sw_version == "5.1"
