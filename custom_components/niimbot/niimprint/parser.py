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

    hw_version: str = None
    sw_version: str = None
    name: str = ""
    identifier: str = ""
    address: str = ""
    model: str = "Unknown"
    serial_number: str = None
    density: str = None
    printspeed: str = None
    labeltype: str = None
    languagetype: str = None
    autoshutdowntime: str = None
    devicetype: str = None
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

        if not device.serial_number:
            device.serial_number = str(await printer.get_info(InfoEnum.DEVICESERIAL))
        if not device.hw_version:
            device.hw_version = str(await printer.get_info(InfoEnum.HARDVERSION))
        if not device.sw_version:
            device.sw_version = str(await printer.get_info(InfoEnum.SOFTVERSION))

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
        # if not device.devicetype:
        #     device.devicetype = str(await printer.get_info(InfoEnum.DEVICETYPE))

        device.sensors['density'] = device.density
        device.sensors['printspeed'] = device.printspeed
        device.sensors['labeltype'] = device.labeltype
        device.sensors['languagetype'] = device.languagetype
        device.sensors['autoshutdowntime'] = device.autoshutdowntime
        device.sensors['devicetype'] = device.devicetype

        heartbeat = await printer.heartbeat()
        device.sensors['closingstate'] =  heartbeat["closingstate"]
        device.sensors['powerlevel'] =  heartbeat["powerlevel"]
        device.sensors['paperstate'] =  heartbeat["paperstate"]
        device.sensors['rfidreadstate'] =  heartbeat["rfidreadstate"]
        device.sensors['battery'] = float(heartbeat["powerlevel"]) * 25.0
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
