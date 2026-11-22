"""Restoring last known values after a Home Assistant restart."""

from __future__ import annotations

from homeassistant.components.sensor import SensorExtraStoredData
from homeassistant.core import State
from pytest_homeassistant_custom_component.common import (
    mock_restore_cache,
    mock_restore_cache_with_extra_data,
)

from .conftest import setup_entry
from .test_availability import _entity_id, _printer_reachable


def _sensor(entity_id, state, unit=None):
    value = None if state in ("unavailable", "unknown") else state
    return (
        State(entity_id, state),
        SensorExtraStoredData(value, unit).as_dict(),
    )


async def _entry_with_ids(hass):
    """Set up once to learn entity ids, then restore state on a reload."""
    entry = await setup_entry(hass)
    ids = {
        "battery": _entity_id(hass, entry, "sensor", key="battery"),
        "density": _entity_id(hass, entry, "sensor", key="density"),
        "labeltype": _entity_id(hass, entry, "sensor", key="labeltype"),
        "progress": _entity_id(hass, entry, "sensor", key="print_progress"),
        "cloud": None,
        "select": _entity_id(hass, entry, "select", key="auto_shutdown"),
        "switch": _entity_id(hass, entry, "switch", key="connection_sound"),
        "cover": _entity_id(hass, entry, "binary_sensor", key="closingstate"),
    }
    return entry, ids


async def _unload(hass, entry):
    """Unload before the cache is replaced, then load as after a restart."""
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def _load(hass, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_restored_values_shown_while_printer_off(hass, enable_bluetooth):
    entry, ids = await _entry_with_ids(hass)
    await _unload(hass, entry)
    mock_restore_cache_with_extra_data(
        hass,
        (
            _sensor(ids["battery"], "80", "%"),
            _sensor(ids["density"], "3"),
            _sensor(ids["progress"], "55", "%"),
            (State(ids["select"], "30_min"), {}),
            (State(ids["switch"], "off"), {}),
        ),
    )
    await _load(hass, entry)

    battery = hass.states.get(ids["battery"])
    assert battery.state == "80"
    assert battery.attributes["unit_of_measurement"] == "%"
    assert hass.states.get(ids["density"]).state == "3"
    assert hass.states.get(ids["select"]).state == "30_min"
    assert hass.states.get(ids["switch"]).state == "off"
    # Live entities never restore.
    assert hass.states.get(ids["progress"]).state == "unavailable"
    assert hass.states.get(ids["cover"]).state == "unavailable"
    # Nothing restored for labeltype: stays unavailable.
    assert hass.states.get(ids["labeltype"]).state == "unavailable"


async def test_live_value_replaces_restored(hass, enable_bluetooth, printer_response):
    entry, ids = await _entry_with_ids(hass)
    await _unload(hass, entry)
    mock_restore_cache_with_extra_data(
        hass,
        (
            _sensor(ids["battery"], "1", "%"),
            _sensor(ids["density"], "5"),
            (State(ids["select"], "30_min"), {}),
            (State(ids["switch"], "off"), {}),
        ),
    )
    await _load(hass, entry)
    device = entry.runtime_data.device
    with _printer_reachable(device, printer_response):
        await entry.runtime_data.coordinator.async_refresh()
        await hass.async_block_till_done()

    assert hass.states.get(ids["battery"]).state not in ("1", "unavailable")
    assert hass.states.get(ids["density"]).state == "3"
    assert hass.states.get(ids["select"]).state != "30_min"
    assert hass.states.get(ids["select"]).state != "unavailable"
    assert hass.states.get(ids["switch"]).state == "on"


async def test_unavailable_restored_state_ignored(hass, enable_bluetooth):
    entry, ids = await _entry_with_ids(hass)
    await _unload(hass, entry)
    mock_restore_cache_with_extra_data(
        hass,
        (
            _sensor(ids["battery"], "unavailable"),
            _sensor(ids["density"], "unknown"),
            (State(ids["select"], "unavailable"), {}),
            (State(ids["switch"], "unknown"), {}),
        ),
    )
    await _load(hass, entry)
    for key in ("battery", "density", "select"):
        assert hass.states.get(ids[key]).state == "unavailable", key
    # The switch has no restored value and shows the configured seed.
    assert hass.states.get(ids["switch"]).state == "on"


async def test_invalid_restored_option_ignored(hass, enable_bluetooth):
    entry, ids = await _entry_with_ids(hass)
    await _unload(hass, entry)
    mock_restore_cache(
        hass, (State(ids["select"], "bogus"), State(ids["switch"], "maybe"))
    )
    await _load(hass, entry)
    assert hass.states.get(ids["select"]).state == "unavailable"
    assert hass.states.get(ids["switch"]).state == "on"


async def test_restored_values_not_used_by_device(hass, enable_bluetooth):
    entry, ids = await _entry_with_ids(hass)
    await _unload(hass, entry)
    mock_restore_cache_with_extra_data(
        hass,
        (
            _sensor(ids["density"], "5"),
            _sensor(ids["labeltype"], "2"),
            (State(ids["select"], "30_min"), {}),
        ),
    )
    await _load(hass, entry)
    assert hass.states.get(ids["density"]).state == "5"
    assert hass.states.get(ids["labeltype"]).state == "2"

    device = entry.runtime_data.device
    assert device.ble_data.density is None
    assert device.ble_data.labeltype is None
    assert device.ble_data.autoshutdowntime is None
    sensors = entry.runtime_data.coordinator.data.sensors
    assert sensors["density"] is None
    assert sensors["labeltype"] is None


async def test_restored_value_dropped_once_printer_reached(
    hass, enable_bluetooth, printer_response
):
    entry, ids = await _entry_with_ids(hass)
    ids["last_error"] = _entity_id(hass, entry, "sensor", key="last_error")
    await _unload(hass, entry)
    mock_restore_cache_with_extra_data(
        hass,
        (
            _sensor(ids["last_error"], "CoverOpen"),
            _sensor(ids["labeltype"], "2"),
        ),
    )
    await _load(hass, entry)
    assert hass.states.get(ids["last_error"]).state == "CoverOpen"
    assert hass.states.get(ids["labeltype"]).state == "2"

    device = entry.runtime_data.device
    with _printer_reachable(device, printer_response):
        await entry.runtime_data.coordinator.async_refresh()
        await hass.async_block_till_done()
    # Clean session: no error, and the old code is not shown again.
    assert hass.states.get(ids["last_error"]).state != "CoverOpen"
    # The key's live value is None after a successful poll.
    entry.runtime_data.coordinator.data.sensors["labeltype"] = None
    entry.runtime_data.coordinator.async_update_listeners()
    await hass.async_block_till_done()
    assert hass.states.get(ids["labeltype"]).state != "2"
