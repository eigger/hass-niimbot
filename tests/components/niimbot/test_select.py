"""Load the select platform through the actual Home Assistant entry."""

from homeassistant.helpers import entity_registry as er

from .conftest import setup_entry


async def test_select_platform_loads_and_unloads(hass, enable_bluetooth):
    entry = await setup_entry(hass)
    registry = er.async_get(hass)
    entities = [
        entity
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
        if entity.domain == "select" and entity.disabled_by is None
    ]
    assert entities
    assert all(hass.states.get(entity.entity_id) is not None for entity in entities)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert all(
        hass.states.get(entity.entity_id).state == "unavailable" for entity in entities
    )
