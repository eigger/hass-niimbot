"""The Niimbot BLE integration."""

import base64
import io
import logging

from datetime import timedelta
from .niimprint import NiimbotDevice, BLEData, PrinterError
from .render import render_image
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import (
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from bleak_retry_connector import close_stale_connections_by_address
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.components.image import Image

from .const import (
    CONF_USE_SOUND,
    CONF_WAIT_BETWEEN_EACH_PRINT_LINE,
    CONF_CONFIRM_EVERY_NTH_PRINT_LINE,
    CONF_KEEP_CONNECTION,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WAIT_BETWEEN_EACH_PRINT_LINE,
    DEFAULT_CONFIRM_EVERY_NTH_PRINT_LINE,
    DEFAULT_KEEP_CONNECTION,
    LEGACY_WAIT_BETWEEN_EACH_PRINT_LINE,
    LEGACY_CONFIRM_EVERY_NTH_PRINT_LINE,
    DOMAIN,
    EMPTY_PNG,
    ImageAndBLEData,
)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.IMAGE,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.SWITCH,
]

_LOGGER = logging.getLogger(__name__)


def _migrate_print_flow_defaults(data: dict) -> dict:
    """Bump legacy slow print pacing defaults once."""
    out = dict(data)
    if out.get(CONF_WAIT_BETWEEN_EACH_PRINT_LINE) == LEGACY_WAIT_BETWEEN_EACH_PRINT_LINE:
        out[CONF_WAIT_BETWEEN_EACH_PRINT_LINE] = DEFAULT_WAIT_BETWEEN_EACH_PRINT_LINE
    if (
        out.get(CONF_CONFIRM_EVERY_NTH_PRINT_LINE)
        == LEGACY_CONFIRM_EVERY_NTH_PRINT_LINE
    ):
        out[CONF_CONFIRM_EVERY_NTH_PRINT_LINE] = DEFAULT_CONFIRM_EVERY_NTH_PRINT_LINE
    return out


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entry to a new version."""
    if entry.version < 2:
        hass.config_entries.async_update_entry(
            entry,
            data=_migrate_print_flow_defaults(dict(entry.data)),
            options=_migrate_print_flow_defaults(dict(entry.options)),
            version=2,
        )
        _LOGGER.info(
            "Migrated %s to config v2 (faster print pacing defaults)",
            entry.title,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Niimbot BLE device from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    address = entry.unique_id
    # Legacy option — only seeds the Connection Sound switch until get_sound works.
    connection_sound_seed = entry.options.get(
        CONF_USE_SOUND, entry.data.get(CONF_USE_SOUND, True)
    )
    scan_interval = float(
        entry.options.get(
            CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
    )
    # Number of seconds (usually sub-second amount) to wait between
    # data packet sends.  Too little and you risk your BLE proxy
    # getting congested or failing to write data to your printer.
    wait_between_each_print_line = int(
        entry.options.get(
            CONF_WAIT_BETWEEN_EACH_PRINT_LINE,
            entry.data.get(
                CONF_WAIT_BETWEEN_EACH_PRINT_LINE,
                DEFAULT_WAIT_BETWEEN_EACH_PRINT_LINE,
            ),
        )
    )
    # The default for most printers is 1 which means every line
    # written causes a read from the printer, which is very slow
    # (0.1 ms per line sent).  With this you can tell the code
    # to fire-and-forget up to N-1 lines sent to the printer
    # confirmation, and confirm on the Nth line.
    confirm_every_nth_print_line = int(
        entry.options.get(
            CONF_CONFIRM_EVERY_NTH_PRINT_LINE,
            entry.data.get(
                CONF_CONFIRM_EVERY_NTH_PRINT_LINE,
                DEFAULT_CONFIRM_EVERY_NTH_PRINT_LINE,
            ),
        )
    )
    keep_connection = bool(
        entry.options.get(
            CONF_KEEP_CONNECTION,
            entry.data.get(CONF_KEEP_CONNECTION, DEFAULT_KEEP_CONNECTION),
        )
    )
    assert address is not None
    await close_stale_connections_by_address(address)

    ble_device = bluetooth.async_ble_device_from_address(hass, address)
    if not ble_device:
        _LOGGER.warning(
            "Could not find Niimbot device with address %s during setup; continuing without initial data",
            address,
        )

    niimbot = NiimbotDevice(
        address,
        keep_connection=keep_connection,
        connection_sound_seed=connection_sound_seed,
    )

    async def _async_update_method() -> BLEData:
        """Get data from Niimbot BLE."""
        ble_device = bluetooth.async_ble_device_from_address(hass, address)
        if ble_device is None:
            _LOGGER.warning("BLE device not available for address %s; returning last known data", address)
            return niimbot.ble_data

        try:
            data = await niimbot.update_device(ble_device)
        except Exception as err:
            _LOGGER.warning("Unable to fetch data from %s: %s; returning last known data", address, err)
            data = niimbot.ble_data
        finally:
            # Fire roll-change events even when the rest of the poll failed
            # after RFID data was already applied.
            for event in niimbot.pending_events:
                hass.bus.async_fire(event["event_type"], event["data"])
            niimbot.pending_events.clear()

        return data

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=_async_update_method,
        update_interval=timedelta(seconds=scan_interval),
    )
    coordinator.data = niimbot.ble_data
    await coordinator.async_refresh()
    if not coordinator.last_update_success:
        _LOGGER.warning(
            "Initial update failed for %s; entities will start as unavailable: %s",
            address,
            coordinator.last_exception,
        )

    image_coordinator: DataUpdateCoordinator[ImageAndBLEData] = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
    )
    image_coordinator.async_set_updated_data(
        (Image(content_type="image/png", content=EMPTY_PNG), coordinator.data)
    )

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "image_coordinator": image_coordinator,
        "device": niimbot,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    # callback for the draw custom service
    async def printservice(service: ServiceCall) -> ServiceResponse:
        try:
            image = await hass.async_add_executor_job(
                render_image, entry.entry_id, service, hass
            )
        except Exception as e:
            raise ServiceValidationError("Failed to create image: %s" % e) from e

        d = io.BytesIO()
        image.save(d, format="PNG")
        d.seek(0)
        read = d.read()
        image_coordinator.async_set_updated_data(
            (Image(content_type="image/png", content=read), coordinator.data)
        )
        encoded = base64.b64encode(read).decode("ascii")
        image_data = f"data:image/png;base64,{encoded}"

        if service.data.get("preview"):
            return {"image": image_data}

        ble_device = bluetooth.async_ble_device_from_address(hass, address)
        if ble_device is None:
            raise HomeAssistantError(
                f"could not find printer with address {address} through your Bluetooth network"
            )

        try:
            # Clear leftover 100% in the UI before the BLE job starts.
            niimbot.begin_print_progress()
            coordinator.async_set_updated_data(niimbot.ble_data)
            result = await niimbot.print_image(
                ble_device,
                image,
                density=int(service.data["density"])
                if "density" in service.data
                else 3,
                wait_between_print_lines=float(service.data["wait_between_print_lines"])
                if "wait_between_print_lines" in service.data
                else wait_between_each_print_line / 1000,
                print_line_batch_size=int(service.data["print_line_batch_size"])
                if "print_line_batch_size" in service.data
                else confirm_every_nth_print_line,
                label_type=int(service.data["label_type"])
                if "label_type" in service.data
                else 1,
                copies=int(service.data["copies"]) if "copies" in service.data else 1,
            )
            # Push post-print RFID / heartbeat updates into entities immediately.
            coordinator.async_set_updated_data(niimbot.ble_data)
            result["image"] = image_data
            return result
        except (PrinterError, RuntimeError, ValueError) as e:
            raise HomeAssistantError("Failed to print: %s" % e) from e

    @callback
    async def refresh_info_service(service: ServiceCall) -> ServiceResponse:
        ble_device = bluetooth.async_ble_device_from_address(hass, address)
        if ble_device is None:
            raise HomeAssistantError(
                f"could not find printer with address {address} through your Bluetooth network"
            )
        try:
            data = await niimbot.refresh_info(ble_device)
            coordinator.async_set_updated_data(data)
            return {
                "density": data.density,
                "printspeed": data.printspeed,
                "labeltype": data.labeltype,
                "autoshutdowntime": data.autoshutdowntime,
                "battery_bucket": niimbot._info_battery_bucket,
            }
        except Exception as e:
            raise HomeAssistantError("Failed to refresh printer info: %s" % e) from e

    # register the services
    hass.services.async_register(
        DOMAIN, "print", printservice, supports_response=SupportsResponse.OPTIONAL
    )
    hass.services.async_register(
        DOMAIN,
        "refresh_info",
        refresh_info_service,
        supports_response=SupportsResponse.OPTIONAL,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    niimbot: NiimbotDevice = hass.data[DOMAIN][entry.entry_id]["device"]
    await niimbot.disconnect()
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
