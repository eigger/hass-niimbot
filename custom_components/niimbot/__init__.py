"""The Niimbot BLE integration."""

from datetime import timedelta
import logging
from .niimprint import NiimbotDevice, BLEData
from .imagegen import customimage
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from bleak_retry_connector import close_stale_connections_by_address
from homeassistant.const import CONF_SCAN_INTERVAL

from .const import (
    CONF_USE_SOUND,
    CONF_WAIT_BETWEEN_EACH_PRINT_LINE,
    CONF_CONFIRM_EVERY_NTH_PRINT_LINE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WAIT_BETWEEN_EACH_PRINT_LINE,
    DEFAULT_CONFIRM_EVERY_NTH_PRINT_LINE,
    DOMAIN,
)

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Niimbot BLE device from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    address = entry.unique_id
    use_sound = entry.data.get(CONF_USE_SOUND)
    scan_interval = float(entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
    # Number of seconds (usually sub-second amount) to wait between
    # data packet sends.  Too little and you risk your BLE proxy
    # getting congested or failing to write data to your printer.
    wait_between_each_print_line = int(
        entry.data.get(
            CONF_WAIT_BETWEEN_EACH_PRINT_LINE,
            DEFAULT_WAIT_BETWEEN_EACH_PRINT_LINE,
        )
    )
    # The default for most printers is 1 which means every line
    # written causes a read from the printer, which is very slow
    # (0.1 ms per line sent).  With this you can tell the code
    # to fire-and-forget up to N-1 lines sent to the printer
    # confirmation, and confirm on the Nth line.
    confirm_every_nth_print_line = int(
        entry.data.get(
            CONF_CONFIRM_EVERY_NTH_PRINT_LINE,
            DEFAULT_CONFIRM_EVERY_NTH_PRINT_LINE,
        )
    )
    assert address is not None
    await close_stale_connections_by_address(address)

    ble_device = bluetooth.async_ble_device_from_address(hass, address)
    if not ble_device:
        raise ConfigEntryNotReady(
            f"Could not find Niimbot device with address {address}"
        )

    niimbot = NiimbotDevice(address, use_sound)

    async def _async_update_method() -> BLEData:
        """Get data from Niimbot BLE."""
        ble_device = bluetooth.async_ble_device_from_address(hass, address)
        if ble_device is None:
            raise UpdateFailed(
                f"BLE device could not be obtained from address {address}"
            )

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
        update_interval=timedelta(seconds=scan_interval),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    # callback for the draw custom service
    async def printservice(service: ServiceCall) -> None:
        image = await hass.async_add_executor_job(
            customimage, entry.entry_id, service, hass
        )
        ble_device = bluetooth.async_ble_device_from_address(hass, address)
        if ble_device is None:
            raise RuntimeError(
                "could not find printer with address {address} through your Bluetooth network"
            )

        await niimbot.print_image(
            ble_device,
            image,
            density=int(service.data["density"]) if "density" in service.data else 3,
            wait_between_print_lines=float(service.data["wait_between_print_lines"])
            if "wait_between_print_lines" in service.data
            else wait_between_each_print_line / 1000,
            print_line_batch_size=int(service.data["print_line_batch_size"])
            if "print_line_batch_size" in service.data
            else confirm_every_nth_print_line,
        )

    # register the services
    hass.services.async_register(DOMAIN, "print", printservice)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
