"""The Niimbot BLE integration."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from bleak_retry_connector import close_stale_connections_by_address
from blesession import fallback_report
from homeassistant.components import bluetooth
from homeassistant.components.image import Image
from homeassistant.const import CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .cloud import LabelCloudLookup
from .const import (
    CONF_KEEP_CONNECTION,
    CONF_USE_CLOUD_LABEL_INFO,
    CONF_USE_SOUND,
    DEFAULT_KEEP_CONNECTION,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USE_CLOUD_LABEL_INFO,
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
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    address = entry.unique_id
    # Legacy option — only seeds the Connection Sound switch until get_sound works.
    connection_sound_seed = entry.options.get(
        CONF_USE_SOUND, entry.data.get(CONF_USE_SOUND, True)
    )
    scan_interval = float(
        entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
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
            "Niimbot printer is not visible during setup; wake it and check Bluetooth connectivity",
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
        Diagnostics must not mask the session's own outcome: a report that
        cannot be built is replaced by ``fallback_report`` so the session is
        still counted.
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
            _LOGGER.debug(
                "Building the session report failed (%s); using fallback",
                type(err).__name__,
            )
            report = fallback_report(operation, trace=trace, exc=outcome)
        else:
            _LOGGER.debug(
                "Session completed: operation=%s success=%s failed_stage=%s",
                operation,
                report.get("success"),
                report.get("failed_stage"),
            )
        # Before ``record``: it notifies the sensors, and Last Error's
        # attributes must already be this session's by then.
        if niimbot.last_error_trace is trace:
            niimbot.last_error_report = report
        niimbot.reports.record(report)

    niimbot.callback_session = _publish_session_report
    cloud_tasks: set[asyncio.Task] = set()

    async def _async_cleanup() -> None:
        """Stop entry-owned lookups before releasing the BLE connection."""
        tasks = tuple(cloud_tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await coordinator.async_shutdown()
        await niimbot.disconnect()

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
        coordinator.async_update_listeners()

        try:
            info = await cloud_lookup.get(barcode)
        except Exception as err:  # noqa: BLE001 — never leave the sensor on pending
            _LOGGER.warning(
                "Cloud label lookup failed (%s); check network access and retry",
                type(err).__name__,
            )
            if niimbot._cloud_lookup_barcode == barcode:
                niimbot._cloud_lookup_barcode = None
            niimbot._cloud_lookup_state = {
                "status": "error",
                "barcode": barcode,
                "requested_at": requested_at,
                "error": type(err).__name__,
            }
            coordinator.async_update_listeners()
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
            coordinator.async_update_listeners()
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
        coordinator.async_update_listeners()

    async def _async_update_method() -> BLEData:
        """Get data from Niimbot BLE."""
        ble_device = bluetooth.async_ble_device_from_address(hass, address)
        if ble_device is None:
            raise UpdateFailed(
                "Printer is not visible to a connectable Bluetooth adapter; wake it and check the proxy"
            )

        try:
            data = await niimbot.update_device(ble_device)
        except Exception as err:
            raise UpdateFailed(
                f"Unable to fetch printer data ({type(err).__name__}); wake the printer and check Bluetooth connectivity"
            ) from err
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
                task = entry.async_create_background_task(
                    hass, _refresh_cloud_label_info(barcode), "Niimbot label lookup"
                )
                cloud_tasks.add(task)
                task.add_done_callback(cloud_tasks.discard)

        return data

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=_async_update_method,
        update_interval=timedelta(seconds=scan_interval),
    )
    coordinator.data = niimbot.ble_data
    try:
        await coordinator.async_refresh()
    except BaseException:
        await _async_cleanup()
        raise
    if not coordinator.last_update_success:
        _LOGGER.warning(
            "Initial printer update failed; entities will start as unavailable: %s",
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
        cloud_lookup=cloud_lookup,
        cloud_tasks=cloud_tasks,
    )

    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        try:
            await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        finally:
            await _async_cleanup()
        raise
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NiimbotConfigEntry) -> bool:
    """Unload a config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    data = entry.runtime_data
    tasks = tuple(data.cloud_tasks)
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    await data.coordinator.async_shutdown()
    await data.device.disconnect()
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: NiimbotConfigEntry) -> None:
    """Reload options through the API supported by the minimum HA version."""
    await hass.config_entries.async_reload(entry.entry_id)
