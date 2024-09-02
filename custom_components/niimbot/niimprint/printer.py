import abc
import enum
import logging
import math
import struct

from PIL import Image, ImageOps
from serial.tools.list_ports import comports as list_comports
from bleak import BleakScanner, BleakClient, BleakError
from typing import Any, Callable, Tuple, TypeVar, cast
from asyncio import Event, wait_for, sleep

WrapFuncType = TypeVar("WrapFuncType", bound=Callable[..., Any])

class BleakCharacteristicMissing(BleakError):
    """Raised when a characteristic is missing from a service."""

class BleakServiceMissing(BleakError):
    """Raised when a service is missing."""

from bleak_retry_connector import establish_connection
from .packet import NiimbotPacket

SERVICE_UUID = "e7810a71-73ae-499d-8c15-faa9aef0c3f2"
CHARACTERISTIC_UUID = "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f"

class InfoEnum(enum.IntEnum):
    DENSITY = 1
    PRINTSPEED = 2
    LABELTYPE = 3
    LANGUAGETYPE = 6
    AUTOSHUTDOWNTIME = 7
    DEVICETYPE = 8
    SOFTVERSION = 9
    BATTERY = 10
    DEVICESERIAL = 11
    HARDVERSION = 12


class RequestCodeEnum(enum.IntEnum):
    GET_INFO = 64  # 0x40
    GET_RFID = 26  # 0x1A
    HEARTBEAT = 220  # 0xDC
    SET_LABEL_TYPE = 35  # 0x23
    SET_LABEL_DENSITY = 33  # 0x21
    START_PRINT = 1  # 0x01
    END_PRINT = 243  # 0xF3
    START_PAGE_PRINT = 3  # 0x03
    END_PAGE_PRINT = 227  # 0xE3
    ALLOW_PRINT_CLEAR = 32  # 0x20
    SET_DIMENSION = 19  # 0x13
    SET_QUANTITY = 21  # 0x15
    GET_PRINT_STATUS = 163  # 0xA3


def _packet_to_int(x):
    return int.from_bytes(x.data, "big")


class BaseTransport(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def read(self, length: int) -> bytes:
        raise NotImplementedError

    @abc.abstractmethod
    async def write(self, data: bytes):
        raise NotImplementedError
    
    async def start_notify(self, uuid: str):
        raise NotImplementedError
    
    async def stop_notify(self, uuid: str):
        raise NotImplementedError
    
class BLETransport(BaseTransport):
    _event: Event | None
    _command_data: bytearray | None
    def __init__(self, client: BleakClient):
        self._client = client
        self._command_data = None
        self._event = Event()

    async def read(self, length: int) -> bytes:
        return await self.read_notify(10)

    async def write(self, data: bytes):
        return await self.write(CHARACTERISTIC_UUID, data)
    
    async def read_notify(self, timeout: int) -> bytes:
        """Wait for notification data to be received within the timeout."""
        await wait_for(self._event.wait(), timeout=timeout)
        data = self._command_data
        self._command_data = None
        self._event.clear()  # Reset the event for the next notification
        return data

    async def write(self, uuid: str, data: bytes):
        """Write data to the BLE characteristic."""
        await self._client.write_gatt_char(uuid, data)

    def _notification_handler(self, _: Any, data: bytearray):
        """Handle incoming notifications and store the received data."""
        self._command_data = data
        self._event.set()  # Notify the waiting coroutine that data has arrived

    def disconnect_on_missing_services(func: WrapFuncType) -> WrapFuncType:
        """Decorator to handle disconnection on missing services/characteristics."""
        async def wrapper(self, *args: Any, **kwargs: Any):
            try:
                return await func(self, *args, **kwargs)
            except (BleakServiceMissing, BleakCharacteristicMissing) as ex:
                if self._client.is_connected:
                    await self._client.clear_cache()
                    await self._client.disconnect()
                raise
        return cast(WrapFuncType, wrapper)
    
    async def start_notify(self, uuid: str = CHARACTERISTIC_UUID):
        """Start notifications from the BLE characteristic."""
        await self._client.start_notify(uuid, self._notification_handler)
        await sleep(0.5)

    async def stop_notify(self, uuid: str = CHARACTERISTIC_UUID):
        """Stop notifications from the BLE characteristic."""
        await self._client.stop_notify(uuid)

class PrinterClient:
    def __init__(self, client: BleakClient):
        self._transport = BLETransport(client)
        self._packetbuf = bytearray()

    async def print_image(self, image: Image, density: int = 3):
        await self._transport.start_notify()
        await self.set_label_density(density)
        await self.set_label_type(1)
        await self.start_print()
        # self.allow_print_clear()  # Something unsupported in protocol decoding (B21)
        await self.start_page_print()
        await self.set_dimension(image.height, image.width)
        # self.set_quantity(1)  # Same thing (B21)
        for pkt in await self._encode_image(image):
            await self._send(pkt)
        await self.end_page_print()
        #time.sleep(0.3)  # FIXME: Check get_print_status()
        await sleep(0.3)
        while not await self.end_print():
            #time.sleep(0.1)
            await sleep(0.1)
        await self._transport.stop_notify()

    async def _encode_image(self, image: Image):
        img = ImageOps.invert(image.convert("L")).convert("1")
        for y in range(img.height):
            line_data = [img.getpixel((x, y)) for x in range(img.width)]
            line_data = "".join("0" if pix == 0 else "1" for pix in line_data)
            line_data = int(line_data, 2).to_bytes(math.ceil(img.width / 8), "big")
            counts = (0, 0, 0)  # It seems like you can always send zeros
            header = struct.pack(">H3BB", y, *counts, 1)
            pkt = NiimbotPacket(0x85, header + line_data)
            yield pkt

    async def _recv(self):
        packets = []
        self._packetbuf.extend(await self._transport.read(1024))
        while len(self._packetbuf) > 4:
            pkt_len = self._packetbuf[3] + 7
            if len(self._packetbuf) >= pkt_len:
                packet = NiimbotPacket.from_bytes(self._packetbuf[:pkt_len])
                self._log_buffer("recv", packet.to_bytes())
                packets.append(packet)
                del self._packetbuf[:pkt_len]
        return packets

    async def _send(self, packet):
        await self._transport.write(packet.to_bytes())

    def _log_buffer(self, prefix: str, buff: bytes):
        msg = ":".join(f"{i:#04x}"[-2:] for i in buff)
        logging.debug(f"{prefix}: {msg}")

    async def _transceive(self, reqcode, data, respoffset=1):
        respcode = respoffset + reqcode
        packet = NiimbotPacket(reqcode, data)
        self._log_buffer("send", packet.to_bytes())
        await self._send(packet)
        resp = None
        for _ in range(6):
            for packet in await self._recv():
                if packet.type == 219:
                    raise ValueError
                elif packet.type == 0:
                    raise NotImplementedError
                elif packet.type == respcode:
                    resp = packet
            if resp:
                return resp
        return resp

    async def get_info(self, key):
        if packet := await self._transceive(RequestCodeEnum.GET_INFO, bytes((key,)), key):
            match key:
                case InfoEnum.DEVICESERIAL:
                    return packet.data.hex()
                case InfoEnum.SOFTVERSION:
                    return _packet_to_int(packet) / 100
                case InfoEnum.HARDVERSION:
                    return _packet_to_int(packet) / 100
                case _:
                    return _packet_to_int(packet)
        else:
            return None

    async def get_rfid(self):
        packet = await self._transceive(RequestCodeEnum.GET_RFID, b"\x01")
        data = packet.data

        if data[0] == 0:
            return None
        uuid = data[0:8].hex()
        idx = 8

        barcode_len = data[idx]
        idx += 1
        barcode = data[idx : idx + barcode_len].decode()

        idx += barcode_len
        serial_len = data[idx]
        idx += 1
        serial = data[idx : idx + serial_len].decode()

        idx += serial_len
        total_len, used_len, type_ = struct.unpack(">HHB", data[idx:])
        return {
            "uuid": uuid,
            "barcode": barcode,
            "serial": serial,
            "used_len": used_len,
            "total_len": total_len,
            "type": type_,
        }

    async def heartbeat(self):
        packet = await self._transceive(RequestCodeEnum.HEARTBEAT, b"\x01")
        closingstate = None
        powerlevel = None
        paperstate = None
        rfidreadstate = None

        match len(packet.data):
            case 20:
                paperstate = packet.data[18]
                rfidreadstate = packet.data[19]
            case 13:
                closingstate = packet.data[9]
                powerlevel = packet.data[10]
                paperstate = packet.data[11]
                rfidreadstate = packet.data[12]
            case 19:
                closingstate = packet.data[15]
                powerlevel = packet.data[16]
                paperstate = packet.data[17]
                rfidreadstate = packet.data[18]
            case 10:
                closingstate = packet.data[8]
                powerlevel = packet.data[9]
                rfidreadstate = packet.data[8]
            case 9:
                closingstate = packet.data[8]

        return {
            "closingstate": closingstate,
            "powerlevel": powerlevel,
            "paperstate": paperstate,
            "rfidreadstate": rfidreadstate,
        }

    async def set_label_type(self, n):
        assert 1 <= n <= 3
        packet = await self._transceive(RequestCodeEnum.SET_LABEL_TYPE, bytes((n,)), 16)
        return bool(packet.data[0])

    async def set_label_density(self, n):
        assert 1 <= n <= 5  # B21 has 5 levels, not sure for D11
        packet = await self._transceive(RequestCodeEnum.SET_LABEL_DENSITY, bytes((n,)), 16)
        return bool(packet.data[0])

    async def start_print(self):
        packet = await self._transceive(RequestCodeEnum.START_PRINT, b"\x01")
        return bool(packet.data[0])

    async def end_print(self):
        packet = await self._transceive(RequestCodeEnum.END_PRINT, b"\x01")
        return bool(packet.data[0])

    async def start_page_print(self):
        packet = await self._transceive(RequestCodeEnum.START_PAGE_PRINT, b"\x01")
        return bool(packet.data[0])

    async def end_page_print(self):
        packet = await self._transceive(RequestCodeEnum.END_PAGE_PRINT, b"\x01")
        return bool(packet.data[0])

    async def allow_print_clear(self):
        packet = await self._transceive(RequestCodeEnum.ALLOW_PRINT_CLEAR, b"\x01", 16)
        return bool(packet.data[0])

    async def set_dimension(self, w, h):
        packet = await self._transceive(
            RequestCodeEnum.SET_DIMENSION, struct.pack(">HH", w, h)
        )
        return bool(packet.data[0])

    async def set_quantity(self, n):
        packet = await self._transceive(RequestCodeEnum.SET_QUANTITY, struct.pack(">H", n))
        return bool(packet.data[0])

    async def get_print_status(self):
        packet = await self._transceive(RequestCodeEnum.GET_PRINT_STATUS, b"\x01", 16)
        page, progress1, progress2 = struct.unpack(">HBB", packet.data)
        return {"page": page, "progress1": progress1, "progress2": progress2}