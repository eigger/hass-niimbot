"""Load the disabled-by-default maintenance button through the actual HA entry."""

from homeassistant.helpers import entity_registry as er

from .conftest import setup_entry


async def test_button_platform_registers_disabled_maintenance_button(
    hass, enable_bluetooth
):
    entry = await setup_entry(hass)
    registry = er.async_get(hass)
    buttons = [
        entity
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
        if entity.domain == "button"
    ]
    assert len(buttons) == 1
    assert buttons[0].disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(buttons[0].entity_id) is None
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get(buttons[0].entity_id) is not None
    assert hass.states.get(buttons[0].entity_id) is None
