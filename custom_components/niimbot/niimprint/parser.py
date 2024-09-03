"""Parser for Niimbot BLE devices"""
import asyncio
import dataclasses
import struct
from collections import namedtuple
from datetime import datetime
import logging
import enum

# from logging import Logger
from math import exp
from typing import Any, Callable, Tuple, TypeVar, cast
from PIL import Image, ImageOps
from bleak import BleakClient, BleakError
from bleak.backends.device import BLEDevice
from bleak_retry_connector import establish_connection

from .printer import PrinterClient, InfoEnum
_LOGGER = logging.getLogger(__name__)

@dataclasses.dataclass
class BLEData:
    """Response data with information about the Niimbot device"""

    hw_version: str = "Unknown"
    sw_version: str = "Unknown"
    name: str = ""
    identifier: str = ""
    address: str = ""
    model: str = "Unknown"
    serial_number: str = "Unknown"
    sensors: dict[str, str | float | None] = dataclasses.field(
        default_factory=lambda: {}
    )


# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
class NiimbotDevice:
    """Data for Niimbot BLE sensors."""
    def __init__(self, address, logger):
        self.address = address
        self.logger = logger
        super().__init__()

    async def update_device(self, ble_device: BLEDevice) -> BLEData:
        """Connects to the device through BLE and retrieves relevant data"""
        client = await establish_connection(BleakClient, ble_device, ble_device.address)
        printer = PrinterClient(client, self.logger)
        await printer.start_notify()
        device = BLEData()
        device.name = ble_device.name
        device.address = ble_device.address
        device.model = device.name.split("-")[0] if "-" in device.name else "Unknown"
        device.serial_number = str(await printer.get_info(InfoEnum.DEVICESERIAL))
        device.hw_version = str(await printer.get_info(InfoEnum.HARDVERSION))
        # device.sw_version = await printer.get_info(InfoEnum.SOFTVERSION)
        device.sensors['battery'] =  float(await printer.get_info(InfoEnum.BATTERY))
        await printer.stop_notify()
        await client.disconnect()

        return device
    
    async def print_image(self, ble_device: BLEDevice, image: Image, path):
        client = await establish_connection(BleakClient, ble_device, ble_device.address)
        printer = PrinterClient(client, self.logger)
        await printer.start_notify()
        img = Image.open(path)
        await printer.print_image(img)
        await printer.stop_notify()
        await client.disconnect()
