"""Parser for Niimbot BLE devices"""

import asyncio
import dataclasses
import logging
import time

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak_retry_connector import establish_connection

# from logging import Logger
from PIL import Image

from .model import (
    PrinterModel,
    consumable_type_name,
    get_printer_meta_by_id,
    material_name,
    rfid_supported_on_firmware,
    supports_label_rfid,
    supports_ribbon_rfid,
)
from .printer import InfoEnum, PrinterClient, PrinterError, PrinterTimeout, SoundEnum


def _battery_percentage(
    powerlevel: int | None,
    model: str,
    variant: str | None = None,
) -> int | None:
    if powerlevel is None:
        return None
    # Advanced2 always reports a 0–4 charge bucket. The B1 Pro 0–100 special
    # case only applies to Advanced1 heartbeats.
    if model == PrinterModel.B1_PRO.name and variant != "advanced2":
        # The B1 Pro reports a direct 0-100 percentage in powerlevel
        # (observed: 60 -> 60%, 100 -> 100%). Clamp to guard against
        # out-of-range values rather than rescaling.
        return max(0, min(100, round(powerlevel)))
    return round(float(powerlevel) * 25.0)

_LOGGER = logging.getLogger(__name__)

EVENT_ROLL_CHANGED = "niimbot_roll_changed"

RFID_SENSOR_KEYS = (
    "labels_remaining",
    "labels_used",
    "labels_total",
    "consumable_usage",
    "label_sku",
    "tag_uuid",
)

RIBBON_RFID_SENSOR_KEYS = (
    "ribbon_remaining",
    "ribbon_used",
    "ribbon_total",
    "ribbon_usage",
    "ribbon_sku",
    "ribbon_type",
    "ribbon_tag_uuid",
)


@dataclasses.dataclass
class BLEData:
    """Response data with information about the Niimbot device"""

    hw_version: str = ""
    sw_version: str = ""
    name: str = ""
    identifier: str = ""
    address: str = ""
    model: str = ""
    serial_number: str = ""
    density: int | None = None
    printspeed: int | None = None
    labeltype: int | None = None
    languagetype: int | None = None
    autoshutdowntime: int | None = None
    devicetype: str = ""
    sensors: dict[str, str | float | None] = dataclasses.field(
        default_factory=dict
    )


# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
class NiimbotDevice:
    """Data for Niimbot BLE sensors."""

    def __init__(self, address, keep_connection=False, connection_sound_seed: bool | None = True):
        self.address = address
        self.keep_connection = keep_connection
        self.lock = asyncio.Lock()
        self.model = None
        # Seed from legacy use_sound config until the printer reports its state.
        self.connection_sound: bool | None = (
            bool(connection_sound_seed) if connection_sound_seed is not None else True
        )
        self.ble_data = BLEData(
            address=address,
            name="Niimbot",
            identifier=address.replace(":", "")[-6:],
            sensors={
                "battery": None,
                "battery_bucket": None,
                "closingstate": None,
                "paperstate": None,
                "rfidreadstate": None,
                "last_error": None,
                "density": None,
                "printspeed": None,
                "labeltype": None,
                "print_progress": 0.0,
                "connection_sound": self.connection_sound,
            }
        )
        self.client = None
        self._printer: PrinterClient | None = None
        self._heartbeat_payload: bytes | None = None
        self._last_rfid_uuid: str | None = None
        self._last_ribbon_uuid: str | None = None
        self._rfid_attrs: dict = {}
        self._ribbon_rfid_attrs: dict = {}
        self._info_battery_bucket: int | None = None
        self._info_loaded = False
        self.last_error: str | None = None
        self.last_error_time: float | None = None
        self.pending_events: list[dict] = []
        self.callback_connection = None
        self.callback_printing = None
        self.callback_error = None
        self.callback_progress = None
        self._is_printing = False
        self._print_start_time: float | None = None
        self._print_end_time: float | None = None
        self.print_progress: float = 0.0
        self.print_page: int = 0
        self.print_page_print_progress: int = 0
        self.print_page_feed_progress: int = 0
        self._print_progress_started = False
        self.heartbeat_variant: str | None = None
        self._warned_estimated_models: set[str] = set()
        self._warned_rfid_firmware: bool = False
        super().__init__()

    def get_model_meta(self):
        """Return enriched model metadata when device type is known."""
        if self.ble_data.devicetype in ("", None):
            return None
        try:
            return get_printer_meta_by_id(int(self.ble_data.devicetype))
        except (TypeError, ValueError):
            return None

    def supports_label_rfid(self) -> bool:
        meta = self.get_model_meta()
        if meta is None:
            return False
        return supports_label_rfid(meta.get("rfid"))

    def supports_ribbon_rfid(self) -> bool:
        meta = self.get_model_meta()
        if meta is None:
            return False
        return supports_ribbon_rfid(meta.get("rfid"))

    def _apply_heartbeat(self, heartbeat: dict) -> None:
        """Apply heartbeat data to sensors."""
        variant = heartbeat.get("variant")
        if variant:
            self.heartbeat_variant = variant

        self.ble_data.sensors["closingstate"] = heartbeat.get("closingstate")
        self.ble_data.sensors["paperstate"] = heartbeat.get("paperstate")
        self.ble_data.sensors["rfidreadstate"] = heartbeat.get("rfidreadstate")

        # Advanced2 fields are retained once set (consistent with RFID hold-last-known-value policy)
        for sensor_key, hb_key in (
            ("printhead_temperature", "temperature"),
            ("ribbonstate", "ribbonstate"),
            ("ribbon_rfidreadstate", "ribbon_rfidreadstate"),
            ("wifi_rssi", "wifi_rssi"),
            ("voltage_state", "voltage_state"),
            ("lighting_error", "lighting_error"),
        ):
            if hb_key in heartbeat and heartbeat[hb_key] is not None:
                self.ble_data.sensors[sensor_key] = heartbeat[hb_key]

    def _apply_rfid_info(self, info: dict | None) -> None:
        """Update RFID sensors from a tag read. Keeps previous values on None."""
        if info is None:
            return
        total = info.get("total_len")
        used = info.get("used_len")
        remaining = None
        usage = None
        if total is not None and used is not None:
            remaining = max(0, total - used)
            if total > 0:
                usage = round(used / total * 100.0, 1)

        self.ble_data.sensors["labels_remaining"] = remaining
        self.ble_data.sensors["labels_used"] = used
        self.ble_data.sensors["labels_total"] = total
        self.ble_data.sensors["consumable_usage"] = usage
        self.ble_data.sensors["label_sku"] = info.get("barcode")
        self.ble_data.sensors["tag_uuid"] = info.get("uuid")
        type_code = info.get("type")
        if type_code is not None:
            self.ble_data.sensors["consumable_type"] = material_name(type_code)
        self._rfid_attrs = {
            "serial": info.get("serial"),
            "capacity": info.get("capacity"),
            "type_code": type_code,
        }

        new_uuid = info.get("uuid")
        if (
            new_uuid
            and self._last_rfid_uuid is not None
            and new_uuid != self._last_rfid_uuid
        ):
            self.pending_events.append(
                {
                    "event_type": EVENT_ROLL_CHANGED,
                    "data": {
                        "address": self.address,
                        "old_uuid": self._last_rfid_uuid,
                        "new_uuid": new_uuid,
                        "barcode": info.get("barcode"),
                        "total_len": total,
                    },
                }
            )
        if new_uuid:
            self._last_rfid_uuid = new_uuid

    def _apply_ribbon_rfid_info(self, info: dict | None) -> None:
        """Update ribbon RFID sensors from RfidInfo2. Keeps previous on None."""
        if info is None:
            return
        total = info.get("total_len")
        used = info.get("used_len")
        remaining = None
        usage = None
        if total is not None and used is not None:
            remaining = max(0, total - used)
            if total > 0:
                usage = round(used / total * 100.0, 1)

        self.ble_data.sensors["ribbon_remaining"] = remaining
        self.ble_data.sensors["ribbon_used"] = used
        self.ble_data.sensors["ribbon_total"] = total
        self.ble_data.sensors["ribbon_usage"] = usage
        self.ble_data.sensors["ribbon_sku"] = info.get("barcode")
        self.ble_data.sensors["ribbon_type"] = material_name(info.get("type"))
        self.ble_data.sensors["ribbon_tag_uuid"] = info.get("uuid")
        self._ribbon_rfid_attrs = {
            "serial": info.get("serial"),
            "capacity": info.get("capacity"),
            "type_code": info.get("type"),
        }
        new_uuid = info.get("uuid")
        if new_uuid:
            self._last_ribbon_uuid = new_uuid

    def _notify_connection(self):
        """Notify connection state change."""
        if self.callback_connection:
            self.callback_connection()

    def _notify_printing(self):
        """Notify printing state change."""
        if self.callback_printing:
            self.callback_printing()

    def _notify_progress(self):
        if self.callback_progress:
            self.callback_progress()

    def begin_print_progress(self) -> None:
        """Reset progress to 0 for a new job and notify UI immediately."""
        self.print_progress = 0.0
        self.print_page = 0
        self.print_page_print_progress = 0
        self.print_page_feed_progress = 0
        self._print_progress_started = False
        self.ble_data.sensors["print_progress"] = 0.0
        self._notify_progress()

    def _notify_error(self):
        if self.callback_error:
            self.callback_error()

    def _record_error(self, err: Exception) -> None:
        if isinstance(err, PrinterError):
            self.last_error = err.code().name
        else:
            self.last_error = type(err).__name__
        self.last_error_time = time.time()
        self.ble_data.sensors["last_error"] = self.last_error
        self._notify_error()

    def _handle_print_progress(self, status: dict) -> None:
        progress = float(status.get("progress") or 0)
        page = int(status.get("page") or 0)
        # Printers often echo the previous job's 100% right after a new job
        # starts. Ignore that until we have seen real in-progress values.
        if progress < 100:
            self._print_progress_started = True
        elif not self._print_progress_started and page <= 0:
            return
        self.print_page = page
        self.print_page_print_progress = int(status.get("page_print_progress") or 0)
        self.print_page_feed_progress = int(status.get("page_feed_progress") or 0)
        self.print_progress = progress
        self.ble_data.sensors["print_progress"] = self.print_progress
        self._notify_progress()

    async def _ensure_printer(self, ble_device: BLEDevice) -> PrinterClient:
        """Connect and return a PrinterClient, reusing it when keep_connection is on."""
        if not self.is_connected:
            self.client = await establish_connection(
                BleakClient,
                ble_device,
                ble_device.address,
                use_services_cache=False,
            )
            if not self.client.is_connected:
                raise RuntimeError("could not connect to thermal printer")
            self._printer = None
            self._notify_connection()

        if self._printer is None:
            self._printer = PrinterClient(
                self.client, heartbeat_payload=self._heartbeat_payload
            )
            await self._printer.start_notify()
        else:
            self._printer._heartbeat_payload = self._heartbeat_payload
        return self._printer

    async def _release_printer(self) -> None:
        """Stop notify / disconnect unless keep_connection holds the session open."""
        if self._printer is not None and self._printer.heartbeat_payload is not None:
            self._heartbeat_payload = self._printer.heartbeat_payload

        if self.keep_connection and self.is_connected:
            return

        if self._printer is not None:
            try:
                await self._printer.stop_notify()
            except Exception:
                pass
            self._printer = None

        if self.client is not None:
            try:
                await self.client.disconnect()
            except Exception:
                pass
            self._notify_connection()

    @property
    def is_connected(self) -> bool:
        """Return true if connected."""
        return self.client is not None and self.client.is_connected

    @property
    def is_printing(self) -> bool:
        """Return true if printing."""
        return self._is_printing

    @property
    def print_duration(self) -> float:
        """Return print duration in seconds."""
        if self._print_start_time is None:
            return 0.0
        if self._is_printing:
            # 프린트 중: 현재까지 경과 시간
            return time.time() - self._print_start_time
        elif self._print_end_time is not None:
            # 프린트 완료: 총 소요 시간
            return self._print_end_time - self._print_start_time
        return 0.0

    async def disconnect(self):
        """Disconnect from the BLE device if connected."""
        if self._printer is not None:
            try:
                await self._printer.stop_notify()
            except Exception:
                pass
            finally:
                self._printer = None
        if self.client and self.client.is_connected:
            try:
                await self.client.disconnect()
            except Exception:
                pass
            self._notify_connection()

    async def refresh_info(self, ble_device: BLEDevice) -> BLEData:
        """Force-refresh cached PrinterInfo settings."""
        async with self.lock:
            if not self.ble_data.name:
                self.ble_data.name = ble_device.name or "(no such device)"
            printer = await self._ensure_printer(ble_device)
            try:
                await self._load_printer_info(printer, force=True)
            finally:
                await self._release_printer()
            return self.ble_data

    async def _load_printer_info(
        self, printer: PrinterClient, force: bool = False
    ) -> None:
        """Read PrinterInfo settings once (or again when force=True)."""
        if self._info_loaded and not force:
            return

        density = await printer.get_info(InfoEnum.DENSITY)
        printspeed = await printer.get_info(InfoEnum.PRINTSPEED)
        labeltype = await printer.get_info(InfoEnum.LABELTYPE)
        autoshutdown = await printer.get_info(InfoEnum.AUTOSHUTDOWNTIME)
        battery_bucket = await printer.get_info(InfoEnum.BATTERY)
        area = await printer.get_info(InfoEnum.AREA)
        status_data = await printer.get_printer_status_data()

        if density is not None:
            self.ble_data.density = int(density)
            self.ble_data.sensors["density"] = self.ble_data.density
        if printspeed is not None:
            self.ble_data.printspeed = int(printspeed)
            self.ble_data.sensors["printspeed"] = self.ble_data.printspeed
        if labeltype is not None:
            self.ble_data.labeltype = int(labeltype)
            self.ble_data.sensors["labeltype"] = consumable_type_name(
                self.ble_data.labeltype
            )
        if autoshutdown is not None:
            self.ble_data.autoshutdowntime = int(autoshutdown)
        if battery_bucket is not None:
            self._info_battery_bucket = int(battery_bucket)
            self.ble_data.sensors["battery_bucket"] = self._info_battery_bucket
        if area is not None:
            self.ble_data.sensors["print_area"] = area
        if status_data is not None:
            self.ble_data.sensors["protocol_version"] = status_data.get(
                "protocol_version"
            )
            self.ble_data.sensors["colour_support"] = bool(
                status_data.get("support_color")
            )

        self._info_loaded = True

    def _apply_connection_sound(self, on: bool) -> None:
        self.connection_sound = on
        self.ble_data.sensors["connection_sound"] = on

    async def set_auto_shutdown(self, ble_device: BLEDevice, index: int) -> BLEData:
        """Write AutoShutdownTime and update the local cache."""
        async with self.lock:
            printer = await self._ensure_printer(ble_device)
            try:
                ok = await printer.set_auto_shutdown_time(index)
                if not ok:
                    raise RuntimeError(
                        f"Printer rejected auto shutdown index {index}"
                    )
                self.ble_data.autoshutdowntime = int(index)
            finally:
                await self._release_printer()
            return self.ble_data

    async def set_connection_sound(
        self, ble_device: BLEDevice, on: bool
    ) -> BLEData:
        """Write Bluetooth connection beep and update the local cache."""
        async with self.lock:
            printer = await self._ensure_printer(ble_device)
            try:
                ok = await printer.set_sound(
                    SoundEnum.BluetoothConnectionSound, on
                )
                if not ok:
                    raise RuntimeError("Printer rejected connection sound setting")
                self._apply_connection_sound(on)
            finally:
                await self._release_printer()
            return self.ble_data

    async def update_device(self, ble_device: BLEDevice) -> BLEData:
        """Connects to the device through BLE and retrieves relevant data"""
        async with self.lock:
            if not self.ble_data.name:
                self.ble_data.name = ble_device.name or "(no such device)"
            if not self.ble_data.address:
                self.ble_data.address = ble_device.address

            try:
                printer = await self._ensure_printer(ble_device)
                if not self.ble_data.serial_number:
                    self.ble_data.serial_number = str(
                        await printer.get_info(InfoEnum.DEVICESERIAL)
                    )
                if not self.ble_data.hw_version:
                    self.ble_data.hw_version = str(
                        await printer.get_info(InfoEnum.HARDVERSION)
                    )
                if not self.ble_data.sw_version:
                    self.ble_data.sw_version = str(
                        await printer.get_info(InfoEnum.SOFTVERSION)
                    )
                if not self.ble_data.devicetype:
                    device_type = await printer.get_info(InfoEnum.DEVICETYPE)
                    if device_type is not None:
                        self.ble_data.devicetype = device_type
                        meta = get_printer_meta_by_id(int(device_type))
                        self.ble_data.model = (
                            meta["model"].name if meta else str(device_type)
                        )
                        self.model = self.ble_data.model

                await self._load_printer_info(printer)

                sound = await printer.get_sound(SoundEnum.BluetoothConnectionSound)
                if sound is not None:
                    self._apply_connection_sound(sound)
                else:
                    self.ble_data.sensors["connection_sound"] = self.connection_sound

                heartbeat = await printer.heartbeat(model_id=self.ble_data.devicetype)
                if printer.heartbeat_payload is not None:
                    self._heartbeat_payload = printer.heartbeat_payload
                self._apply_heartbeat(heartbeat)
                _LOGGER.debug(
                    "Heartbeat raw: closingstate=%s paperstate=%s "
                    "rfidreadstate=%s powerlevel=%s variant=%s",
                    heartbeat.get("closingstate"),
                    heartbeat.get("paperstate"),
                    heartbeat.get("rfidreadstate"),
                    heartbeat.get("powerlevel"),
                    heartbeat.get("variant"),
                )
                battery = _battery_percentage(
                    heartbeat["powerlevel"],
                    self.ble_data.model,
                    variant=heartbeat.get("variant"),
                )
                # Prefer live heartbeat; fall back to cached PrinterInfo key 10.
                if battery is None and self._info_battery_bucket is not None:
                    battery = round(float(self._info_battery_bucket) * 25.0)
                self.ble_data.sensors["battery"] = battery
                if self._info_battery_bucket is not None:
                    self.ble_data.sensors["battery_bucket"] = self._info_battery_bucket

                await self._maybe_read_rfid(printer, heartbeat)
                await self._maybe_read_ribbon_rfid(printer)
            except PrinterTimeout as err:
                _LOGGER.warning("Printer timed out during update: %s", err)
                raise
            finally:
                await self._release_printer()

            _LOGGER.debug("Obtained BLEData: %s", self.ble_data)
            return self.ble_data

    def _check_rfid_firmware_support(self) -> bool:
        """Check if RFID reading is supported on this firmware version, logging once per connection."""
        if not rfid_supported_on_firmware(
            self.ble_data.devicetype, self.ble_data.sw_version
        ):
            if not self._warned_rfid_firmware:
                self._warned_rfid_firmware = True
                _LOGGER.info(
                    "Skipping RFID read for %s (model_id=%s, sw_version=%s): RFID unsupported on this firmware version",
                    self.ble_data.model,
                    self.ble_data.devicetype,
                    self.ble_data.sw_version,
                )
            return False
        return True

    async def _maybe_read_rfid(
        self, printer: PrinterClient, heartbeat: dict, *, force: bool = False
    ) -> None:
        """Read label RFID when the model supports it."""
        if not self.supports_label_rfid():
            return

        if not self._check_rfid_firmware_support():
            return

        # Seed keys so entity platforms can discover them even before a tag read.
        for key in RFID_SENSOR_KEYS:
            self.ble_data.sensors.setdefault(key, None)

        rfid_ready = heartbeat.get("rfidreadstate")
        # Still attempt a read when rfidreadstate is missing/unknown. Only skip
        # the round-trip when the printer explicitly reports unreadiness as 0 —
        # and even then fall through if we have never successfully read a tag,
        # because some models (observed on B1) leave the flag at 0 with stock
        # loaded. After a print, force=True so used_len is re-read even when the
        # readiness flag stays 0.
        if (
            not force
            and rfid_ready is not None
            and not rfid_ready
            and self._last_rfid_uuid is not None
        ):
            _LOGGER.debug("Skipping RFID read: rfidreadstate falsy")
            return

        try:
            info = await printer.get_rfid()
        except Exception as err:
            _LOGGER.debug("RFID read failed; retaining previous values: %s", err)
            return

        self._apply_rfid_info(info)

    async def _maybe_read_ribbon_rfid(self, printer: PrinterClient) -> None:
        """Read ribbon RFID when the model supports it."""
        if not self.supports_ribbon_rfid():
            return

        # Note: All currently gated model IDs (512, 771, 775, 777) are LABEL-class models,
        # so supports_ribbon_rfid() returns False above for them. This gate check is kept
        # for consistency if ribbon-class models with firmware gates are added in the future.
        if not self._check_rfid_firmware_support():
            return

        for key in RIBBON_RFID_SENSOR_KEYS:
            self.ble_data.sensors.setdefault(key, None)

        try:
            info = await printer.get_rfid2()
        except Exception as err:
            _LOGGER.debug("Ribbon RFID read failed; retaining previous: %s", err)
            return

        self._apply_ribbon_rfid_info(info)

    async def _refresh_after_print(self, printer: PrinterClient) -> None:
        """Re-read heartbeat + RFID after a job — used_len is written during print."""
        try:
            # Give the printer a moment to finish writing the tag.
            await asyncio.sleep(0.5)
            heartbeat = await printer.heartbeat(model_id=self.ble_data.devicetype)
            self._apply_heartbeat(heartbeat)
            battery = _battery_percentage(
                heartbeat["powerlevel"],
                self.ble_data.model,
                variant=heartbeat.get("variant"),
            )
            if battery is None and self._info_battery_bucket is not None:
                battery = round(float(self._info_battery_bucket) * 25.0)
            if battery is not None:
                self.ble_data.sensors["battery"] = battery
            await self._maybe_read_rfid(printer, heartbeat, force=True)
            await self._maybe_read_ribbon_rfid(printer)
        except Exception as err:
            _LOGGER.debug("Post-print status refresh failed: %s", err)

    async def print_image(
        self,
        ble_device: BLEDevice,
        image: Image.Image,
        density: int,
        wait_between_print_lines: float,
        print_line_batch_size: int,
        label_type: int = 1,
        copies: int = 1,
    ) -> dict:
        async with self.lock:
            self._is_printing = True
            self._print_start_time = time.time()
            self._print_end_time = None
            self.begin_print_progress()
            self._notify_printing()

            try:
                printer = await self._ensure_printer(ble_device)
                printer.on_progress = self._handle_print_progress

                if not self.model:
                    device_type = await printer.get_info(InfoEnum.DEVICETYPE)
                    if device_type is not None:
                        meta = get_printer_meta_by_id(int(device_type))
                        self.model = meta["model"].name if meta else str(device_type)
                        self.ble_data.model = self.model
                        self.ble_data.devicetype = device_type
                        _LOGGER.debug("Resolved model during print: %s", self.model)

                meta = self.get_model_meta()
                if (
                    meta
                    and meta.get("printheadPixelsEstimated")
                    and self.model not in self._warned_estimated_models
                ):
                    self._warned_estimated_models.add(self.model)
                    _LOGGER.warning(
                        "Printer model %s (%s) uses an estimated printheadPixels value (%d px). "
                        "Please report whether output alignment and scaling are correct.",
                        self.model,
                        self.ble_data.devicetype,
                        meta["printheadPixels"],
                    )

                try:
                    printer_model = PrinterModel(self.model)
                except (ValueError, TypeError):
                    printer_model = PrinterModel.UNKNOWN
                    _LOGGER.warning(
                        "Unknown printer model %r, falling back to UNKNOWN", self.model
                    )

                await printer.print_image(
                    printer_model,
                    image,
                    density,
                    wait_between_print_lines,
                    print_line_batch_size,
                    label_type=label_type,
                    copies=copies,
                )
            except Exception as err:
                self._record_error(err)
                raise
            else:
                # Only mark 100% on a clean finish; leave the last reported
                # value (and last_error) alone when the job failed.
                if self.print_progress < 100:
                    self.print_progress = 100.0
                    self.ble_data.sensors["print_progress"] = 100.0
                # Printer writes used_len back to the RFID tag during the job;
                # re-read before disconnecting so remaining/usage sensors update.
                await self._refresh_after_print(printer)
            finally:
                if self._printer is not None:
                    self._printer.on_progress = None
                self._print_end_time = time.time()
                self._is_printing = False
                self._notify_printing()
                self._notify_progress()
                await self._release_printer()

        return {
            "status": "ok",
            "duration": self.print_duration,
            "copies": copies,
        }

