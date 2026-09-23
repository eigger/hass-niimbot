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
