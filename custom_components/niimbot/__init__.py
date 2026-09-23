"""The Niimbot BLE integration."""

import logging
from datetime import datetime, timedelta, timezone

from bleak_retry_connector import close_stale_connections_by_address
from homeassistant.components import bluetooth
from homeassistant.components.image import Image
from homeassistant.const import CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .cloud import LabelCloudLookup
from .const import (
    CONF_CONFIRM_EVERY_NTH_PRINT_LINE,
    CONF_KEEP_CONNECTION,
    CONF_USE_CLOUD_LABEL_INFO,
    CONF_USE_SOUND,
    CONF_WAIT_BETWEEN_EACH_PRINT_LINE,
    DEFAULT_CONFIRM_EVERY_NTH_PRINT_LINE,
    DEFAULT_KEEP_CONNECTION,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USE_CLOUD_LABEL_INFO,
    DEFAULT_WAIT_BETWEEN_EACH_PRINT_LINE,
    DOMAIN,
    EMPTY_PNG,
    ImageAndBLEData,
)
from .data import NiimbotRuntimeData
from .niimprint import BLEData, NiimbotDevice
from .services import async_setup_services
from .session_report import build_session_report
from .types import NiimbotConfigEntry

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.IMAGE,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.BUTTON,
]

_LOGGER = logging.getLogger(__name__)

# Config-entry only: a `niimbot:` YAML section is rejected at startup.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up domain services once for this Home Assistant instance."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: NiimbotConfigEntry) -> bool:
    """Set up Niimbot BLE device from a config entry."""
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
    use_cloud_label_info = bool(
        entry.options.get(
            CONF_USE_CLOUD_LABEL_INFO,
            entry.data.get(CONF_USE_CLOUD_LABEL_INFO, DEFAULT_USE_CLOUD_LABEL_INFO),
        )
    )
    # None when the option is off, so no cloud-related object exists at all and
    # no code path below can reach the network.
    cloud_lookup = LabelCloudLookup(hass) if use_cloud_label_info else None
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

    def _publish_session_report(operation: str, trace, outcome) -> None:
        """Freeze this session's report once, then refresh the sensors.

        ``radio_facts`` reads RSSI and path count live, so rebuilding an older
        trace on a later poll would replace that session's radio with whatever
        the adapter sees now. Only the trace that just finished is rendered.
        Diagnostics must not mask the session's own outcome.
        """
        try:
            report = build_session_report(
                hass,
                address,
                operation=operation,
                trace=trace,
                exc=outcome,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Building the session report failed: %s", err)
            # Clear rather than keep: a stale report would describe an older
            # session under this session's timestamp.
            report = None
        else:
            _LOGGER.debug("Session report (%s): %s", operation, report)
        if operation == "print":
            niimbot.last_print_report = report
        if niimbot.last_failure_trace is trace:
            niimbot.last_failure_report = report
        if niimbot.last_error_trace is trace:
            niimbot.last_error_report = report
        niimbot._notify_session_listeners()

    niimbot.callback_session = _publish_session_report

    async def _refresh_cloud_label_info(barcode: str) -> None:
        """Resolve a label barcode via the cloud catalogue and push the result.

        Runs as a background task so a slow or failed lookup never delays or
        fails the coordinator poll. Transient failures (timeout / non-200) leave
        the dedup marker clear so the next poll can retry; definitive misses and
        matches suppress further lookups for that barcode.
        """
        assert cloud_lookup is not None
        requested_at = datetime.now(timezone.utc).isoformat()
        # Claim the barcode while the request is in flight to avoid parallel
        # duplicate fetches from overlapping coordinator polls.
        niimbot._cloud_lookup_barcode = barcode
        niimbot._cloud_lookup_state = {
            "status": "pending",
            "barcode": barcode,
            "requested_at": requested_at,
        }
        coordinator.async_set_updated_data(niimbot.ble_data)

        try:
            info = await cloud_lookup.get(barcode)
        except Exception as err:  # noqa: BLE001 — never leave the sensor on pending
            _LOGGER.warning(
                "Cloud label lookup for %s raised %s",
                barcode,
                f"{type(err).__name__}: {err!r}",
                exc_info=True,
            )
            if niimbot._cloud_lookup_barcode == barcode:
                niimbot._cloud_lookup_barcode = None
            niimbot._cloud_lookup_state = {
                "status": "error",
                "barcode": barcode,
                "requested_at": requested_at,
                "error": f"{type(err).__name__}: {err!r}",
            }
            coordinator.async_set_updated_data(niimbot.ble_data)
            return

        if not cloud_lookup.last_result_definitive:
            if niimbot._cloud_lookup_barcode == barcode:
                niimbot._cloud_lookup_barcode = None
            state = {
                "status": "error",
                "barcode": barcode,
                "requested_at": requested_at,
                "source": cloud_lookup.last_source,
            }
            if cloud_lookup.last_error:
                state["error"] = cloud_lookup.last_error
            niimbot._cloud_lookup_state = state
            coordinator.async_set_updated_data(niimbot.ble_data)
            return

        if info:
            new_attrs = {"barcode": barcode, **info}
            state = {
                "status": "found",
                "barcode": barcode,
                "requested_at": requested_at,
                "source": cloud_lookup.last_source,
                **info,
            }
        else:
            new_attrs = {}
            state = {
                "status": "not_found",
                "barcode": barcode,
                "requested_at": requested_at,
                "source": cloud_lookup.last_source,
            }

        niimbot._cloud_lookup_state = state
        if new_attrs != niimbot._cloud_label_attrs:
            niimbot._cloud_label_attrs = new_attrs
        coordinator.async_set_updated_data(niimbot.ble_data)

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

        # Fires on the roll-change poll and on the first poll after startup;
        # a no-op on every later poll for the same barcode (see dedup above).
        if cloud_lookup is not None:
            barcode = data.sensors.get("label_sku")
            if barcode and barcode != niimbot._cloud_lookup_barcode:
                hass.async_create_task(_refresh_cloud_label_info(barcode))

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

    entry.runtime_data = NiimbotRuntimeData(
        address=address,
        device=niimbot,
        coordinator=coordinator,
        image_coordinator=image_coordinator,
        wait_between_each_print_line=wait_between_each_print_line,
        confirm_every_nth_print_line=confirm_every_nth_print_line,
        cloud_lookup=cloud_lookup,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NiimbotConfigEntry) -> bool:
    """Unload a config entry."""
    await entry.runtime_data.device.disconnect()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
