"""Parser for Niimbot BLE devices"""

import dataclasses
import logging
import asyncio
import time

# from logging import Logger
from PIL import Image, ImageOps
from bleak import BleakClient, BleakError
from bleak.backends.device import BLEDevice
from bleak_retry_connector import establish_connection

from .printer import PrinterClient, InfoEnum, SoundEnum
from .model import PrinterModel, get_printer_meta_by_id
import typing

_LOGGER = logging.getLogger(__name__)


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

    def __init__(self, address, use_sound):
        self.address = address
        self.use_sound = use_sound
        self.lock = asyncio.Lock()
        self.set_sound = None
        self.model = None
        self.ble_data = BLEData()
        self.client = None
        self.callback_connection = None
        self.callback_printing = None
        self._is_printing = False
        self._print_start_time: float | None = None
        self._print_end_time: float | None = None
        super().__init__()

    def _notify_connection(self):
        """Notify connection state change."""
        if self.callback_connection:
            self.callback_connection()

    def _notify_printing(self):
        """Notify printing state change."""
        if self.callback_printing:
            self.callback_printing()

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

    async def update_device(self, ble_device: BLEDevice) -> BLEData:
        """Connects to the device through BLE and retrieves relevant data"""
        async with self.lock:
            if not self.ble_data.name:
                self.ble_data.name = ble_device.name or "(no such device)"
            if not self.ble_data.address:
                self.ble_data.address = ble_device.address

            self.client = await establish_connection(
                BleakClient, ble_device, ble_device.address
            )
            if not self.client.is_connected:
                raise RuntimeError("could not connect to thermal printer")

            self._notify_connection()

            try:
                printer = PrinterClient(self.client)
                await printer.start_notify()
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
                    self.ble_data.devicetype = await printer.get_info(InfoEnum.DEVICETYPE)
                    meta = get_printer_meta_by_id(int(self.ble_data.devicetype))
                    self.ble_data.model = (
                        meta["model"].name if meta else str(self.ble_data.devicetype)
                    )
                    self.model = self.ble_data.model
                if not self.set_sound:
                    self.set_sound = await printer.set_sound(
                        SoundEnum.BluetoothConnectionSound, self.use_sound
                    )

                # if not device.density:
                #     device.density = str(await printer.get_info(InfoEnum.DENSITY))
                # if not device.printspeed:
                #     device.printspeed = str(await printer.get_info(InfoEnum.PRINTSPEED))
                # if not device.labeltype:
                #     device.labeltype = str(await printer.get_info(InfoEnum.LABELTYPE))
                # if not device.languagetype:
                #     device.languagetype = str(await printer.get_info(InfoEnum.LANGUAGETYPE))
                # if not device.autoshutdowntime:
                #     device.autoshutdowntime = str(await printer.get_info(InfoEnum.AUTOSHUTDOWNTIME))

                if self.ble_data.density is not None:
                    self.ble_data.sensors["density"] = self.ble_data.density
                if self.ble_data.printspeed is not None:
                    self.ble_data.sensors["printspeed"] = self.ble_data.printspeed
                if self.ble_data.labeltype is not None:
                    self.ble_data.sensors["labeltype"] = self.ble_data.labeltype
                if self.ble_data.languagetype is not None:
                    self.ble_data.sensors["languagetype"] = self.ble_data.languagetype
                if self.ble_data.autoshutdowntime is not None:
                    self.ble_data.sensors["autoshutdowntime"] = self.ble_data.autoshutdowntime

                heartbeat = await printer.heartbeat()
                self.ble_data.sensors["closingstate"] = heartbeat["closingstate"]
                self.ble_data.sensors["paperstate"] = heartbeat["paperstate"]
                self.ble_data.sensors["rfidreadstate"] = heartbeat["rfidreadstate"]
                self.ble_data.sensors["battery"] = float(heartbeat["powerlevel"]) * 25.0
                await printer.stop_notify()
            finally:
                await self.client.disconnect()
                self._notify_connection()

            _LOGGER.debug("Obtained BLEData: %s", self.ble_data)
            return self.ble_data

    async def print_image(
        self,
        ble_device: BLEDevice,
        image: Image.Image,
        density: int,
        wait_between_print_lines: float,
        print_line_batch_size: int,
    ) -> dict:
        try:
            printer_model = PrinterModel(self.model)
        except ValueError:
            printer_model = PrinterModel.UNKNOWN
        async with self.lock:
            self.client = await establish_connection(
                BleakClient, ble_device, ble_device.address
            )
            if not self.client.is_connected:
                raise RuntimeError("could not connect to thermal printer")

            self._notify_connection()

            # 프린트 시작
            self._is_printing = True
            self._print_start_time = time.time()
            self._print_end_time = None
            self._notify_printing()

            try:
                printer = PrinterClient(self.client)
                await printer.start_notify()
                await printer.print_image(
                    printer_model,
                    image,
                    density,
                    wait_between_print_lines,
                    print_line_batch_size,
                )
                await printer.stop_notify()
            finally:
                # 프린트 종료
                self._print_end_time = time.time()
                self._is_printing = False
                self._notify_printing()

                await self.client.disconnect()
                self._notify_connection()

        return {
            "status": "ok",
            "duration": self.print_duration,
        }

