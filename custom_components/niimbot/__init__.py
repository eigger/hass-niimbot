"""The Niimbot BLE integration."""
from datetime import timedelta
import logging
from .niimprint import NiimbotDevice, BLEData
from .imagegen import *
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from bleak_retry_connector import close_stale_connections_by_address

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, CONF_USE_SOUND

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Niimbot BLE device from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    address = entry.unique_id
    use_sound = entry.data.get(CONF_USE_SOUND)
    assert address is not None
    await close_stale_connections_by_address(address)
    
    ble_device = bluetooth.async_ble_device_from_address(hass, address)
    if not ble_device:
        raise ConfigEntryNotReady(f"Could not find Niimbot device with address {address}")

    niimbot = NiimbotDevice(address, use_sound)
    async def _async_update_method() -> BLEData:
        """Get data from Niimbot BLE."""
        ble_device = bluetooth.async_ble_device_from_address(hass, address)
        try:
            data = await niimbot.update_device(ble_device)
        except Exception as err:
            raise UpdateFailed(f"Unable to fetch data: {err}") from err

        return data

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=_async_update_method,
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    # callback for the draw custom service
    async def printservice(service: ServiceCall) -> None:
        image = await hass.async_add_executor_job(customimage, entry.entry_id, service, hass)
        ble_device = bluetooth.async_ble_device_from_address(hass, address)
        await niimbot.print_image(ble_device, image)             

    # register the services
    hass.services.async_register(DOMAIN, "print", printservice)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
