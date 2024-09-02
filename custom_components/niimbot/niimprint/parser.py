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

from .printer import PrinterClient
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
    sensors: dict[str, str | float | None] = dataclasses.field(
        default_factory=lambda: {}
    )


# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
class NiimbotDevice:
    """Data for Niimbot BLE sensors."""
    def __init__(self):
        super().__init__()

    async def update_device(self, ble_device: BLEDevice) -> BLEData:
        """Connects to the device through BLE and retrieves relevant data"""
        client = await establish_connection(BleakClient, ble_device, ble_device.address)
        # printer = PrinterClient(client)
        # device = BLEData()
        # device.name = ble_device.name
        # device.address = ble_device.address
        # heartbeat = await printer.heartbeat()
        # device.sensors['powerlevel'] = heartbeat['powerlevel']
        device.sensors['address'] =  ble_device.address
        await client.disconnect()

        return device
    
    async def print_image(self, ble_device: BLEDevice, image: Image):
        client = await establish_connection(BleakClient, ble_device, ble_device.address)
        printer = PrinterClient(client)
        printer.print_image(image)
        await client.disconnect()
