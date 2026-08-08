"""Parser for Niimbot BLE devices"""

import dataclasses
import logging
import asyncio
import time

# from logging import Logger
from PIL import Image, ImageOps
from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak_retry_connector import establish_connection

from .printer import PrinterClient, InfoEnum, SoundEnum, PrinterTimeout, PrinterError
from .model import (
    PrinterModel,
    consumable_type_name,
    get_printer_meta_by_id,
    supports_label_rfid,
)


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
    "consumable_type",
    "tag_uuid",
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
        default_factory=lambda: {}
    )


# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
class NiimbotDevice:
    """Data for Niimbot BLE sensors."""

    def __init__(self, address, use_sound, keep_connection=False):
        self.address = address
        self.use_sound = use_sound
        self.keep_connection = keep_connection
        self.lock = asyncio.Lock()
        self.set_sound = None
        self.model = None
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
                "autoshutdowntime": None,
                "print_progress": 0.0,
            }
        )
        self.client = None
        self._printer: PrinterClient | None = None
        self._heartbeat_payload: bytes | None = None
        self._last_rfid_uuid: str | None = None
        self._rfid_attrs: dict = {}
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
        self.ble_data.sensors["consumable_type"] = consumable_type_name(
            info.get("type")
        )
        self.ble_data.sensors["tag_uuid"] = info.get("uuid")
        self._rfid_attrs = {
            "serial": info.get("serial"),
            "capacity": info.get("capacity"),
            "type_code": info.get("type"),
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
        self.print_page = int(status.get("page") or 0)
        self.print_page_print_progress = int(status.get("page_print_progress") or 0)
        self.print_page_feed_progress = int(status.get("page_feed_progress") or 0)
        self.print_progress = float(status.get("progress") or 0)
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
            self.ble_data.sensors["autoshutdowntime"] = self.ble_data.autoshutdowntime
        if battery_bucket is not None:
            self._info_battery_bucket = int(battery_bucket)
            self.ble_data.sensors["battery_bucket"] = self._info_battery_bucket

        self._info_loaded = True

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
                if not self.set_sound:
                    self.set_sound = await printer.set_sound(
                        SoundEnum.BluetoothConnectionSound, self.use_sound
                    )

                await self._load_printer_info(printer)

                heartbeat = await printer.heartbeat(model_id=self.ble_data.devicetype)
                if printer.heartbeat_payload is not None:
                    self._heartbeat_payload = printer.heartbeat_payload
                self.ble_data.sensors["closingstate"] = heartbeat["closingstate"]
                self.ble_data.sensors["paperstate"] = heartbeat["paperstate"]
                self.ble_data.sensors["rfidreadstate"] = heartbeat["rfidreadstate"]
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
            except PrinterTimeout as err:
                _LOGGER.warning("Printer timed out during update: %s", err)
                raise
            finally:
                await self._release_printer()

            _LOGGER.debug("Obtained BLEData: %s", self.ble_data)
            return self.ble_data

    async def _maybe_read_rfid(self, printer: PrinterClient, heartbeat: dict) -> None:
        """Read label RFID when the model supports it."""
        if not self.supports_label_rfid():
            return

        # Seed keys so entity platforms can discover them even before a tag read.
        for key in RFID_SENSOR_KEYS:
            self.ble_data.sensors.setdefault(key, None)

        rfid_ready = heartbeat.get("rfidreadstate")
        # Still attempt a read when rfidreadstate is missing/unknown. Only skip
        # the round-trip when the printer explicitly reports unreadiness as 0 —
        # and even then fall through if we have never successfully read a tag,
        # because some models (observed on B1) leave the flag at 0 with stock
        # loaded.
        if (
            rfid_ready is not None
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
            self.print_progress = 0.0
            self.print_page = 0
            self.print_page_print_progress = 0
            self.print_page_feed_progress = 0
            self.ble_data.sensors["print_progress"] = 0.0
            self._notify_printing()
            self._notify_progress()

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

