import abc
import enum
import itertools
import logging
import math
import struct
import time

from PIL import Image, ImageOps
from bleak import BleakClient, BleakError
from typing import Any, Callable, TypeVar
from asyncio import Event, wait_for, sleep
from .packet import NiimbotPacket
from .model import PrinterModel


WrapFuncType = TypeVar("WrapFuncType", bound=Callable[..., Any])

_LOGGER = logging.getLogger(__name__)


class BleakCharacteristicMissing(BleakError):
    """Raised when a characteristic is missing from a service."""


class BleakServiceMissing(BleakError):
    """Raised when a service is missing."""


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
    PRINT_BITMAP_ROW_INDEXED = 131  # 0x83
    PRINT_EMPTY_ROW = 132  # 0x84
    PRINT_BITMAP_ROW = 133  # 0x85
    PRINT_CLEAR = 32  # 0x20
    SET_SOUND = 88  # 0x58


class SoundEnum(enum.IntEnum):
    BluetoothConnectionSound = 1
    PowerSound = 2


class PrinterErrorCodeEnum(enum.IntEnum):
    CoverOpen = 0x01
    LackPaper = 0x02
    LowBattery = 0x03
    BatteryException = 0x04
    UserCancel = 0x05
    DataError = 0x06
    Overheat = 0x07
    PaperOutException = 0x08
    PrinterBusy = 0x09
    NoPrinterHead = 0x0A
    TemperatureLow = 0x0B
    PrinterHeadLoose = 0x0C
    NoRibbon = 0x0D
    WrongRibbon = 0x0E
    UsedRibbon = 0x0F
    WrongPaper = 0x10
    SetPaperFail = 0x11
    SetPrintModeFail = 0x12
    SetPrintDensityFail = 0x13
    WriteRfidFail = 0x14
    SetMarginFail = 0x15
    CommunicationException = 0x16
    Disconnect = 0x17
    CanvasParameterError = 0x18
    RotationParameterException = 0x19
    JsonParameterException = 0x1A
    B3sAbnormalPaperOutput = 0x1B
    ECheckPaper = 0x1C
    RfidTagNotWritten = 0x1D
    SetPrintDensityNoSupport = 0x1E
    SetPrintModeNoSupport = 0x1F
    SetPrintLabelMaterialError = 0x20
    SetPrintLabelMaterialNoSupport = 0x21
    NotSupportWrittenRfid = 0x22
    IllegalPage = 0x32
    IllegalRibbonPage = 0x33
    ReceiveDataTimeout = 0x34
    NonDedicatedRibbon = 0x35
    Unknown = 0xFF


class PrinterError(Exception):
    def __str__(self) -> str:
        return "Printer error: %s" % self.args[0].name

    def code(self) -> PrinterErrorCodeEnum:
        return self.args[0]


def _packet_to_int(x):
    return int.from_bytes(x.data, "big")


def _packet_to_float(x):
    return float.from_bytes(x.data, "big")


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
    _command_data: bytearray | None

    def __init__(self, client: BleakClient):
        self._client = client
        self._command_data = None
        self._event = Event()

    # def disconnect_on_missing_services(func: WrapFuncType) -> WrapFuncType:
    #     """Decorator to handle disconnection on missing services/characteristics."""

    #     async def wrapper(self, *args: Any, **kwargs: Any):
    #         try:
    #             return await func(self, *args, **kwargs)
    #         except (BleakServiceMissing, BleakCharacteristicMissing) as ex:
    #             if self._client.is_connected:
    #                 await self._client.clear_cache()
    #                 await self._client.disconnect()
    #             raise

    #     return cast(WrapFuncType, wrapper)

    async def read(self, length: int) -> bytes:
        return await self.read_notify(30)

    async def write(self, data: bytes, response=True):
        return await self.write_ble(CHARACTERISTIC_UUID, data, response)

    async def read_notify(self, timeout: int) -> bytes:
        """Wait for notification data to be received within the timeout."""
        await wait_for(self._event.wait(), timeout=timeout)
        data = self._command_data
        self._command_data = None
        self._event.clear()  # Reset the event for the next notification
        return data

    # @disconnect_on_missing_services
    async def write_ble(self, uuid: str, data: bytes, response: bool):
        """Write data to the BLE characteristic."""
        await self._client.write_gatt_char(uuid, data, response)

    def _notification_handler(self, _: Any, data: bytearray):
        """Handle incoming notifications and store the received data."""
        self._command_data = data
        self._event.set()  # Notify the waiting coroutine that data has arrived

    # @disconnect_on_missing_services
    async def start_notify(self, uuid: str):
        """Start notifications from the BLE characteristic."""
        await self._client.start_notify(uuid, self._notification_handler)
        await sleep(0.5)

    async def stop_notify(self, uuid: str):
        """Stop notifications from the BLE characteristic."""
        await self._client.stop_notify(uuid)


class PrinterClient:
    def __init__(self, client: BleakClient):
        self._transport = BLETransport(client)
        self._packetbuf = bytearray()
        self._timings: list[float] = []
        # Conservative defaults.

    async def start_notify(self):
        await self._transport.start_notify(CHARACTERISTIC_UUID)

    async def stop_notify(self):
        await self._transport.stop_notify(CHARACTERISTIC_UUID)

    async def print_image(
        self,
        model: PrinterModel,
        image: Image.Image,
        density: int,
        wait_between_print_lines: float,
        print_line_batch_size: int,
    ):
        self._timings = []
        _LOGGER.debug("Printing on printer model %s", model)
        start = time.time()
        try:
            if model == PrinterModel.D110:
                return await self.print_image_d110(
                    image,
                    density,
                    wait_between_print_lines,
                    print_line_batch_size,
                )
            elif model == PrinterModel.B21_PRO:
                return await self.print_image_d110m_v4(
                    image,
                    density,
                    wait_between_print_lines,
                    print_line_batch_size,
                )
            else:
                return await self.print_image_b1(
                    image,
                    density,
                    wait_between_print_lines,
                    print_line_batch_size,
                )
        finally:
            avg = (sum(self._timings) / len(self._timings)) if self._timings else 0.0
            _LOGGER.debug(
                "Print of page took %.2f seconds, average per line sent %.4f",
                time.time() - start,
                avg,
            )

    async def print_image_b1(
        self,
        image: Image.Image,
        density,
        wait_between_print_lines: float,
        print_line_batch_size: int,
    ):
        _LOGGER.debug("print_image_b1: %s", locals())
        await self.set_label_density(density)
        await self.set_label_type(1)
        await self.start_print_v4()
        await self.start_page_print()
        await self.set_page_size_v3(image.height, image.width)
        await self.set_image(
            image,
            wait_between_print_lines,
            print_line_batch_size,
        )
        await self.end_page_print()
        start_time = time.time()
        while not await self.get_print_end():
            if time.time() - start_time > 5:
                break
            await sleep(0.5)
        await self.end_print()

    async def print_image_d110(
        self,
        image: Image.Image,
        density,
        wait_between_print_lines: float,
        print_line_batch_size: int,
    ):
        _LOGGER.debug("print_image_b1: %s", locals())
        await self.set_label_density(density)
        await self.set_label_type(1)
        await self.start_print()
        await self.start_page_print()
        await self.set_page_size_v2(image.height, image.width)
        await self.set_quantity(1)
        await self.set_image(
            image,
            wait_between_print_lines,
            print_line_batch_size,
        )
        await self.end_page_print()
        start_time = time.time()
        while not await self.get_print_end():
            if time.time() - start_time > 5:
                break
            await sleep(0.5)
        await self.end_print()

    async def print_image_d110m_v4(
        self,
        image: Image.Image,
        density,
        wait_between_print_lines: float,
        print_line_batch_size: int,
    ):
        _LOGGER.debug("print_image_d110m_v4: %s", locals())
        if not await self.set_label_density(density):
            raise RuntimeError(f"Could not set label density to {density}")
        if not await self.set_label_type(1):
            raise RuntimeError(f"Could not set label type to {1}")
        if not await self.start_print_9b():
            raise RuntimeError("Could not start print")
        # https://github.com/MultiMote/niimbluelib/commit/20f3e42b1e457cad5ff3dfe3c9b86e602abc6f44#diff-c9930b13a15bc967ad905fd73c84d631918a2f5b701b9f95ff3fd50c9af37c43
        await self.heartbeat(await_for_response=False)
        await self.set_page_size_9b(image.height, image.width)
        await self.set_image(
            image,
            wait_between_print_lines,
            print_line_batch_size,
        )
        if not await self.end_page_print():
            raise RuntimeError("Page did not finish successfully")
        await sleep(1)
        start_time = time.time()
        while not await self.get_print_end():
            if time.time() - start_time > 5:
                break
            await sleep(0.1)
        if not await self.end_print():
            raise RuntimeError("Print did not finish successfully")
        await self.heartbeat(await_for_response=False)

    def _countbitsofbytes(self, data):
        n = int.from_bytes(data, "big")
        # https://stackoverflow.com/a/9830282
        n = (n & 0x55555555) + ((n & 0xAAAAAAAA) >> 1)
        n = (n & 0x33333333) + ((n & 0xCCCCCCCC) >> 2)
        n = (n & 0x0F0F0F0F) + ((n & 0xF0F0F0F0) >> 4)
        n = (n & 0x00FF00FF) + ((n & 0xFF00FF00) >> 8)
        n = (n & 0x0000FFFF) + ((n & 0xFFFF0000) >> 16)
        return n

    async def set_image(
        self,
        image: Image.Image,
        wait_between_print_lines: float,
        print_line_batch_size: int,
    ):
        _LOGGER.debug("Set image")
        # Block every 4th send to prevent BT congestion.
        blocking_send = itertools.cycle([False] * (print_line_batch_size - 1) + [True])
        img = ImageOps.invert(image.convert("L")).convert("1")
        empty_row = 0
        empty_row_count = 0
        for y in range(img.height):
            line_data = [img.getpixel((x, y)) for x in range(img.width)]
            line_data_bytes = "".join("0" if pix == 0 else "1" for pix in line_data)
            line_data_ints = int(line_data_bytes, 2).to_bytes(
                math.ceil(img.width / 8), "big"
            )
            counts = (
                self._countbitsofbytes(line_data_ints[i * 4 : (i + 1) * 4])
                for i in range(3)
            )
            header = struct.pack(">H3BB", y, *counts, 1)
            if all(byte == 0 for byte in line_data_ints):
                if empty_row_count == 0:
                    empty_row = y
                empty_row_count += 1
            else:
                # Printer can only "print" maximum 255 empty rows.
                # Do them a max of 255 at a time.
                while empty_row_count > 0:
                    empty_rows_to_print = min([255, empty_row_count])
                    await self.set_empty_row(
                        empty_row,
                        empty_rows_to_print,
                        response=next(blocking_send),
                        wait_between_print_lines=wait_between_print_lines,
                    )
                    empty_row = empty_row + empty_rows_to_print
                    empty_row_count = empty_row_count - empty_rows_to_print
                await self.set_bitmap_row(
                    header,
                    line_data_ints,
                    response=next(blocking_send),
                    wait_between_print_lines=wait_between_print_lines,
                )
        # Finish by printing any empty rows too.
        while empty_row_count > 0:
            empty_rows_to_print = min([255, empty_row_count])
            await self.set_empty_row(
                empty_row,
                empty_rows_to_print,
                response=next(blocking_send),
                wait_between_print_lines=wait_between_print_lines,
            )
            empty_row = empty_row + empty_rows_to_print
            empty_row_count = empty_row_count - empty_rows_to_print

    async def set_empty_row(
        self,
        row,
        count,
        response: bool,
        wait_between_print_lines: float,
    ):
        packet = NiimbotPacket(
            RequestCodeEnum.PRINT_EMPTY_ROW, struct.pack(">HB", row, count)
        )
        self._log_buffer("send", packet.to_bytes())
        start = time.time()
        await self._send(packet, response)
        await sleep(wait_between_print_lines)
        self._timings.append(time.time() - start)

    async def set_bitmap_row(
        self,
        header,
        data,
        response: bool,
        wait_between_print_lines: float,
    ):
        packet = NiimbotPacket(RequestCodeEnum.PRINT_BITMAP_ROW, header + data)
        self._log_buffer("send", packet.to_bytes())
        start = time.time()
        await self._send(packet, response)
        await sleep(wait_between_print_lines)
        self._timings.append(time.time() - start)

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

    async def _send(self, packet, response=True):
        await self._transport.write(packet.to_bytes(), response=response)

    def _log_buffer(self, prefix: str, buff: bytes):
        msg = ":".join(f"{i:#04x}"[-2:] for i in buff)
        _LOGGER.debug(f"{prefix}({len(buff)}): {msg}")

    async def _transceive(self, reqcode, data, respoffset=1, await_for_response=True):
        respcode = respoffset + reqcode
        packet = NiimbotPacket(reqcode, data)
        self._log_buffer("send", packet.to_bytes())
        await self._send(packet)
        if not await_for_response:
            return
        resp = None
        for _ in range(6):
            for packet in await self._recv():
                if packet.type == 219:
                    # We will assume a single byte error.
                    raise PrinterError(PrinterErrorCodeEnum(packet.data[0]))
                elif packet.type == 0:
                    raise NotImplementedError
                elif packet.type == respcode:
                    resp = packet
            if resp:
                return resp
        return resp

    async def get_info(self, key):
        if packet := await self._transceive(
            RequestCodeEnum.GET_INFO, bytes((key,)), key
        ):
            match key:
                case InfoEnum.DEVICESERIAL:
                    return bytes.fromhex(packet.data.hex()).decode("ascii")
                case InfoEnum.SOFTVERSION:
                    return packet.data[0] + (packet.data[1] / 100)
                case InfoEnum.HARDVERSION:
                    return packet.data[0] + (packet.data[1] / 100)
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

    async def heartbeat(self, await_for_response=True):
        _LOGGER.debug("Heartbeat")
        packet = await self._transceive(
            RequestCodeEnum.HEARTBEAT, b"\x01", await_for_response=await_for_response
        )
        if not await_for_response:
            return
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
        _LOGGER.debug("Set label type %s", n)
        assert 1 <= n <= 3
        packet = await self._transceive(RequestCodeEnum.SET_LABEL_TYPE, bytes((n,)), 16)
        return bool(packet.data[0])

    async def set_label_density(self, n):
        assert 1 <= n <= 5  # B21 has 5 levels, not sure for D11
        _LOGGER.debug("Set label density %s", n)
        packet = await self._transceive(
            RequestCodeEnum.SET_LABEL_DENSITY, bytes((n,)), 16
        )
        return bool(packet.data[0])

    async def start_print(self):
        packet = await self._transceive(RequestCodeEnum.START_PRINT, b"\x01")
        return bool(packet.data[0])

    async def start_print_v4(self, total_pages=1, page_color=0):
        packet = await self._transceive(
            RequestCodeEnum.START_PRINT,
            struct.pack(">HBBBBB", total_pages, 0x00, 0x00, 0x00, 0x00, page_color),
        )
        return bool(packet.data[0])

    async def start_print_9b(self, total_pages=1, page_color=0, quality=0, someflag=0):
        _LOGGER.debug("Start print 9 bytes: %s", locals())
        packet = await self._transceive(
            RequestCodeEnum.START_PRINT,
            struct.pack(
                ">HBBBBBBB",
                total_pages,
                0x00,
                0x00,
                0x00,
                0x00,
                page_color,
                quality,
                someflag,
            ),
        )
        return bool(packet.data[0])

    async def end_print(self):
        _LOGGER.debug("End print")
        packet = await self._transceive(RequestCodeEnum.END_PRINT, b"\x01")
        return bool(packet.data[0])

    async def start_page_print(self):
        packet = await self._transceive(RequestCodeEnum.START_PAGE_PRINT, b"\x01")
        return bool(packet.data[0])

    async def end_page_print(self):
        _LOGGER.debug("End page print")
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

    async def set_page_size_v2(self, rows, cols):
        packet = await self._transceive(
            RequestCodeEnum.SET_DIMENSION, struct.pack(">HH", rows, cols)
        )
        return bool(packet.data[0])

    async def set_page_size_v3(self, rows, cols, copies_count=1):
        packet = await self._transceive(
            RequestCodeEnum.SET_DIMENSION, struct.pack(">HHH", rows, cols, copies_count)
        )
        return bool(packet.data[0])

    async def set_page_size_9b(
        self,
        rows,
        cols,
        copies_count=1,
        some_size=0,
        is_divide=0,
    ):
        _LOGGER.debug("Set page size 9 bytes: %s", locals())
        packet = await self._transceive(
            RequestCodeEnum.SET_DIMENSION,
            struct.pack(
                ">HHHHB",
                rows,
                cols,
                copies_count,
                some_size,
                is_divide,
            ),
        )
        return bool(packet.data[0])

    async def set_quantity(self, n):
        packet = await self._transceive(
            RequestCodeEnum.SET_QUANTITY, struct.pack(">H", n)
        )
        return bool(packet.data[0])

    async def set_sound(self, key, on: bool):
        packet = await self._transceive(
            RequestCodeEnum.SET_SOUND,
            struct.pack(">BBB", 0x01, key, 0x01 if on else 0x00),
            16,
        )
        return bool(packet.data[0])

    async def get_print_status(self, await_for_response=True):
        _LOGGER.debug("Get print status")
        packet = await self._transceive(
            RequestCodeEnum.GET_PRINT_STATUS,
            b"\x01",
            16,
            await_for_response=await_for_response,
        )
        if not await_for_response:
            return
        page, progress1, progress2 = struct.unpack(">HBB", packet.data[:4])
        _LOGGER.debug(
            "Print status: page=%s progress1=%s progress2=%s",
            page,
            progress1,
            progress2,
        )
        return {"page": page, "progress": min(progress1, progress2)}

    async def get_print_end(self):
        status = await self.get_print_status()
        _LOGGER.debug("Status: %s", status)
        if status["progress"] < 100:
            return False
        return True
