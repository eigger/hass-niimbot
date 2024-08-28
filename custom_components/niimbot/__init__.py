"""The Niimbot BLE integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from .niimprint import NiimbotDevice, BLEData

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.unit_system import METRIC_SYSTEM
from bleak_retry_connector import close_stale_connections_by_address

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

def setup(hass, config):
    # callback for the draw custom service
    async def printservice(service: ServiceCall) -> None:
        ip = hass.states.get(DOMAIN + ".ip").state 
        entity_ids = service.data.get("entity_id")
        #sometimes you get a string, that's not nice to iterate over for ids....
        if isinstance(entity_ids, str):
            entity_ids=[entity_ids]

        dither = service.data.get("dither", False)
        ttl = service.data.get("ttl", 60)
        preloadtype = service.data.get("preloadtype", 0)
        preloadlut = service.data.get("preloadlut", 0)
        dry_run = service.data.get("dry-run", False)
        for entity_id in entity_ids:
            _LOGGER.info("Called entity_id: %s" % (entity_id))
            imgbuff = await hass.async_add_executor_job(customimage,entity_id, service, hass)
            id = entity_id.split(".")
            if (dry_run is False):
                result = await hass.async_add_executor_job(uploadimg, imgbuff, id[1], ip, dither,ttl,preloadtype,preloadlut,hass)
            else:
                _LOGGER.info("Running dry-run - no upload to AP!")
                result = True
                

    # register the services
    hass.services.register(DOMAIN, "print", printservice)
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Niimbot BLE device from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    address = entry.unique_id

    elevation = hass.config.elevation
    is_metric = hass.config.units is METRIC_SYSTEM
    assert address is not None
    await close_stale_connections_by_address(address)
    
    ble_device = bluetooth.async_ble_device_from_address(hass, address)

    if not ble_device:
        raise ConfigEntryNotReady(f"Could not find Niimbot device with address {address}")

    async def _async_update_method() -> BLEData:
        """Get data from Niimbot BLE."""
        ble_device = bluetooth.async_ble_device_from_address(hass, address)
        niimbot = NiimbotDevice(_LOGGER, elevation, is_metric)

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

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
