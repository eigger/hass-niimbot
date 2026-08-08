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
from .model import PrinterModel, get_printer_meta_by_model


WrapFuncType = TypeVar("WrapFuncType", bound=Callable[..., Any])

_LOGGER = logging.getLogger(__name__)

# PrintBitmapRowIndexed is only safe at or below this black-pixel count.
INDEXED_BLACK_PIXEL_LIMIT = 6


class BleakCharacteristicMissing(BleakError):
    """Raised when a characteristic is missing from a service."""


class BleakServiceMissing(BleakError):
    """Raised when a service is missing."""


SERVICE_UUID = "e7810a71-73ae-499d-8c15-faa9aef0c3f2"
CHARACTERISTIC_UUID = "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f"

# niimblue: models where lidClosed state is inverted
INVERTED_LID_MODELS = [512, 514, 513, 2304, 1792, 3584, 5120, 2560, 3840, 4352, 272, 273, 274]


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


class PrinterTimeout(RuntimeError):
    """Raised when the printer does not answer a request in time."""


# Heartbeat response command IDs (not derived as reqcode + 1 for Advanced2).
HEARTBEAT_RESP_ADVANCED1 = 0xDD
HEARTBEAT_RESP_BASIC = 0xDE
HEARTBEAT_RESP_UNKNOWN = 0xDF
HEARTBEAT_RESP_ADVANCED2 = 0xD9
HEARTBEAT_RESP_CODES = {
    HEARTBEAT_RESP_ADVANCED1,
    HEARTBEAT_RESP_BASIC,
    HEARTBEAT_RESP_UNKNOWN,
    HEARTBEAT_RESP_ADVANCED2,
}

# Default read budget for status/info commands. Print acknowledgements may
# override with a longer timeout.
DEFAULT_TRANSCEIVE_TIMEOUT = 5.0


def _packet_to_int(x):
    return int.from_bytes(x.data, "big")


def _packet_to_float(x):
    return float.from_bytes(x.data, "big")


class BaseTransport(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def read(self, length: int, timeout: float = 30.0) -> bytes:
        raise NotImplementedError

    @abc.abstractmethod
    async def write(self, data: bytes):
        raise NotImplementedError

    async def start_notify(self, uuid: str):
        raise NotImplementedError

    async def stop_notify(self, uuid: str):
        raise NotImplementedError


class BLETransport(BaseTransport):
    _command_data: bytearray

    def __init__(self, client: BleakClient):
        self._client = client
        self._command_data = bytearray()
        self._event = Event()

    async def read(self, length: int, timeout: float = 30.0) -> bytes:
        return await self.read_notify(timeout)

    async def write(self, data: bytes, response=True):
        return await self.write_ble(CHARACTERISTIC_UUID, data, response)

    async def read_notify(self, timeout: float) -> bytes:
        """Wait for notification data to be received within the timeout."""
        await wait_for(self._event.wait(), timeout=timeout)
        data = bytes(self._command_data)
        self._command_data.clear()
        self._event.clear()  # Reset the event for the next notification
        return data

    async def write_ble(self, uuid: str, data: bytes, response: bool):
        """Write data to the BLE characteristic."""
        await self._client.write_gatt_char(uuid, data, response)

    def _notification_handler(self, _: Any, data: bytearray):
        """Handle incoming notifications and accumulate the received data.

        The printer can emit several notifications in a burst (e.g. unsolicited
        d3 status packets alongside the real reply). Accumulating instead of
        overwriting prevents losing a packet that arrives before the previous
        one is consumed, which would otherwise desync the packet buffer.
        """
        self._command_data.extend(data)
        self._event.set()  # Notify the waiting coroutine that data has arrived

    async def start_notify(self, uuid: str):
        """Start notifications from the BLE characteristic."""
        await self._client.start_notify(uuid, self._notification_handler)
        await sleep(0.5)

    async def stop_notify(self, uuid: str):
        """Stop notifications from the BLE characteristic."""
        await self._client.stop_notify(uuid)


class PrinterClient:
    def __init__(
        self,
        client: BleakClient | None = None,
        *,
        transport: BaseTransport | None = None,
        heartbeat_payload: bytes | None = None,
    ):
        if transport is not None:
            self._transport = transport
        elif client is not None:
            self._transport = BLETransport(client)
        else:
            raise ValueError("client or transport is required")
        self._packetbuf = bytearray()
        self._timings: list[float] = []
        # Cached heartbeat request payload that previously succeeded (b"\x01" or b"\x04").
        self._heartbeat_payload: bytes | None = heartbeat_payload
        self.on_progress: Callable[[dict], None] | None = None

    @property
    def heartbeat_payload(self) -> bytes | None:
        return self._heartbeat_payload

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
        label_type: int = 1,
        copies: int = 1,
    ):
        self._timings = []
        _LOGGER.debug("Printing on printer model %s", model)
        start = time.time()
        try:
            if copies < 1:
                raise ValueError(f"copies must be >= 1, got {copies}")
            meta = get_printer_meta_by_model(model)
            printhead_pixels = meta["printheadPixels"] if meta else None
            density_min = meta.get("densityMin", 1) if meta else 1
            density_max = meta.get("densityMax", 5) if meta else 5
            kwargs = dict(
                image=image,
                density=density,
                wait_between_print_lines=wait_between_print_lines,
                print_line_batch_size=print_line_batch_size,
                printhead_pixels=printhead_pixels,
                label_type=label_type,
                density_min=density_min,
                density_max=density_max,
                copies=copies,
            )
            if model in (PrinterModel.UNKNOWN, PrinterModel.D11, PrinterModel.D11S):
                return await self.print_image_d11_v1(**kwargs)
            elif model in (PrinterModel.B21S, PrinterModel.B21S_C2B, PrinterModel.D110):
                return await self.print_image_d110(**kwargs)
            elif model in (PrinterModel.D11_H, PrinterModel.D11_PRO, PrinterModel.B21_PRO, PrinterModel.D110_M, PrinterModel.B2_PRO):
                return await self.print_image_d110m_v4(**kwargs)
            else:
                return await self.print_image_b1(**kwargs)
        finally:
            avg = (sum(self._timings) / len(self._timings)) if self._timings else 0.0
            _LOGGER.debug(
                "Print of page took %.2f seconds, average per line sent %.4f",
                time.time() - start,
                avg,
            )

    async def print_image_d11_v1(
        self,
        image: Image.Image,
        density,
        wait_between_print_lines: float,
        print_line_batch_size: int,
        printhead_pixels: int | None = None,
        label_type: int = 1,
        density_min: int = 1,
        density_max: int = 5,
        copies: int = 1,
    ):
        """Print task for older D11 printers (OldD11PrintTask from niimblue)."""
        _LOGGER.debug("print_image_d11_v1: %s", locals())
        await self.set_label_density(density, density_min, density_max)
        await self.set_label_type(label_type)
        await self.start_print()
        await self.allow_print_clear()
        await self.start_page_print()
        await self.set_page_size_v2(image.height, 0)  # D11_V1 only sends height
        await self.set_quantity(copies)
        await self.set_image(
            image,
            wait_between_print_lines,
            print_line_batch_size,
            printhead_pixels=printhead_pixels,
        )
        await self.end_page_print()
        start_time = time.time()
        while not await self.get_print_end(copies=copies):
            if time.time() - start_time > 5:
                break
            await sleep(0.5)
        await self.end_print()

    async def print_image_b1(
        self,
        image: Image.Image,
        density,
        wait_between_print_lines: float,
        print_line_batch_size: int,
        printhead_pixels: int | None = None,
        label_type: int = 1,
        density_min: int = 1,
        density_max: int = 5,
        copies: int = 1,
    ):
        _LOGGER.debug("print_image_b1: %s", locals())
        await self.set_label_density(density, density_min, density_max)
        await self.set_label_type(label_type)
        await self.start_print_v4(total_pages=1)
        await self.start_page_print()
        await self.set_page_size_v3(image.height, image.width, copies_count=copies)
        await self.set_image(
            image,
            wait_between_print_lines,
            print_line_batch_size,
            printhead_pixels=printhead_pixels,
        )
        await self.end_page_print()
        # The B1/B1 Pro retains the *previous* job's progress=100 and reports it
        # immediately after end_page_print, before it has reset the counter and
        # started the new page. Trusting that stale 100% makes us call end_print()
        # too early, which aborts the page: the printer feeds the label in and
        # back out without printing (and the paper counter does not increment).
        # So we wait until the printer has actually started the new page (we see
        # progress drop below 100, or the page counter advance) before accepting
        # a 100% as genuine completion. A timeout still guards against a hang.
        start_time = time.time()
        started = False
        while True:
            status = await self.get_print_status()
            if status["progress"] < 100:
                started = True
            if status["page"] >= copies or (started and status["progress"] >= 100):
                break
            if time.time() - start_time > 30:
                _LOGGER.warning(
                    "Print completion not confirmed within timeout (last status: %s)",
                    status,
                )
                break
            await sleep(0.5)
        await self.end_print()

    async def print_image_d110(
        self,
        image: Image.Image,
        density,
        wait_between_print_lines: float,
        print_line_batch_size: int,
        printhead_pixels: int | None = None,
        label_type: int = 1,
        density_min: int = 1,
        density_max: int = 5,
        copies: int = 1,
    ):
        _LOGGER.debug("print_image_d110: %s", locals())
        await self.set_label_density(density, density_min, density_max)
        await self.set_label_type(label_type)
        await self.start_print()
        await self.start_page_print()
        await self.set_page_size_v2(image.height, image.width)
        await self.set_quantity(copies)
        await self.set_image(
            image,
            wait_between_print_lines,
            print_line_batch_size,
            printhead_pixels=printhead_pixels,
        )
        await self.end_page_print()
        start_time = time.time()
        while not await self.get_print_end(copies=copies):
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
        printhead_pixels: int | None = None,
        label_type: int = 1,
        density_min: int = 1,
        density_max: int = 5,
        copies: int = 1,
    ):
        _LOGGER.debug("print_image_d110m_v4: %s", locals())
        if not await self.set_label_density(density, density_min, density_max):
            raise RuntimeError(f"Could not set label density to {density}")
        if not await self.set_label_type(label_type):
            raise RuntimeError(f"Could not set label type to {label_type}")
        if not await self.start_print_9b(total_pages=1):
            raise RuntimeError("Could not start print")
        # https://github.com/MultiMote/niimbluelib/commit/20f3e42b1e457cad5ff3dfe3c9b86e602abc6f44#diff-c9930b13a15bc967ad905fd73c84d631918a2f5b701b9f95ff3fd50c9af37c43
        await self.heartbeat(await_for_response=False)
        await self.set_page_size_9b(image.height, image.width, copies_count=copies)
        await self.set_image(
            image,
            wait_between_print_lines,
            print_line_batch_size,
            printhead_pixels=printhead_pixels,
        )
        if not await self.end_page_print():
            raise RuntimeError("Page did not finish successfully")
        await sleep(1)
        start_time = time.time()
        while not await self.get_print_end(copies=copies):
            if time.time() - start_time > 5:
                break
            await sleep(0.1)
        if not await self.end_print():
            raise RuntimeError("Print did not finish successfully")
        await self.heartbeat(await_for_response=False)

    def _countbitsofbytes(self, data):
        if not data:
            return 0
        # int.bit_count() handles arbitrary-length row buffers correctly.
        return int.from_bytes(data, "big").bit_count()

    def _row_counter_bytes(self, row_bytes: bytes, printhead_pixels: int) -> bytes:
        """Build the three counter bytes for a bitmap / indexed row header."""
        chunk_size = printhead_pixels // 8 // 3
        if chunk_size > 0 and len(row_bytes) <= chunk_size * 3:
            return bytes(
                (
                    self._countbitsofbytes(row_bytes[0:chunk_size]),
                    self._countbitsofbytes(row_bytes[chunk_size : chunk_size * 2]),
                    self._countbitsofbytes(row_bytes[chunk_size * 2 : chunk_size * 3]),
                )
            )
        total = self._countbitsofbytes(row_bytes)
        return bytes((0x00, total & 0xFF, (total >> 8) & 0xFF))

    @staticmethod
    def _black_pixel_indices(row_bytes: bytes, width: int) -> list[int]:
        indices: list[int] = []
        for x in range(width):
            byte = row_bytes[x // 8]
            bit = 7 - (x % 8)
            if byte & (1 << bit):
                indices.append(x)
        return indices

    async def set_image(
        self,
        image: Image.Image,
        wait_between_print_lines: float,
        print_line_batch_size: int,
        printhead_pixels: int | None = None,
    ):
        _LOGGER.debug("Set image")
        if print_line_batch_size < 1:
            print_line_batch_size = 1
        # Block every Nth send to prevent BT congestion.
        blocking_send = itertools.cycle([False] * (print_line_batch_size - 1) + [True])
        img = ImageOps.invert(image.convert("L")).convert("1")
        # Fall back to legacy 96px counters when printhead size is unknown.
        head_pixels = printhead_pixels or 96

        empty_row = 0
        empty_row_count = 0
        pending_y: int | None = None
        pending_bytes: bytes | None = None
        pending_repeats = 0

        async def flush_empty() -> None:
            nonlocal empty_row, empty_row_count
            while empty_row_count > 0:
                empty_rows_to_print = min(255, empty_row_count)
                await self.set_empty_row(
                    empty_row,
                    empty_rows_to_print,
                    response=next(blocking_send),
                    wait_between_print_lines=wait_between_print_lines,
                )
                empty_row += empty_rows_to_print
                empty_row_count -= empty_rows_to_print

        async def flush_pending_bitmap() -> None:
            nonlocal pending_y, pending_bytes, pending_repeats
            if pending_bytes is None or pending_y is None:
                return
            counters = self._row_counter_bytes(pending_bytes, head_pixels)
            indices = self._black_pixel_indices(pending_bytes, img.width)
            if len(indices) <= INDEXED_BLACK_PIXEL_LIMIT:
                header = struct.pack(">H3BB", pending_y, *counters, pending_repeats)
                payload = b"".join(struct.pack(">H", i) for i in indices)
                await self.set_bitmap_row_indexed(
                    header,
                    payload,
                    response=next(blocking_send),
                    wait_between_print_lines=wait_between_print_lines,
                )
            else:
                header = struct.pack(">H3BB", pending_y, *counters, pending_repeats)
                await self.set_bitmap_row(
                    header,
                    pending_bytes,
                    response=next(blocking_send),
                    wait_between_print_lines=wait_between_print_lines,
                )
            pending_y = None
            pending_bytes = None
            pending_repeats = 0

        for y in range(img.height):
            line_data = [img.getpixel((x, y)) for x in range(img.width)]
            line_data_bytes = "".join("0" if pix == 0 else "1" for pix in line_data)
            line_data_ints = int(line_data_bytes, 2).to_bytes(
                math.ceil(img.width / 8), "big"
            )
            if all(byte == 0 for byte in line_data_ints):
                await flush_pending_bitmap()
                if empty_row_count == 0:
                    empty_row = y
                empty_row_count += 1
            else:
                await flush_empty()
                if (
                    pending_bytes is not None
                    and line_data_ints == pending_bytes
                    and pending_repeats < 255
                ):
                    pending_repeats += 1
                else:
                    await flush_pending_bitmap()
                    pending_y = y
                    pending_bytes = line_data_ints
                    pending_repeats = 1

        await flush_pending_bitmap()
        await flush_empty()

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

    async def set_bitmap_row_indexed(
        self,
        header,
        data,
        response: bool,
        wait_between_print_lines: float,
    ):
        packet = NiimbotPacket(RequestCodeEnum.PRINT_BITMAP_ROW_INDEXED, header + data)
        self._log_buffer("send", packet.to_bytes())
        start = time.time()
        await self._send(packet, response)
        await sleep(wait_between_print_lines)
        self._timings.append(time.time() - start)

    async def _recv(self, timeout: float = 30.0):
        packets = []
        try:
            self._packetbuf.extend(await self._transport.read(1024, timeout=timeout))
        except TimeoutError:
            return packets
        while len(self._packetbuf) > 4:
            # Resync to the next 0x55 0x55 header, discarding any stale bytes
            # left over from unsolicited mid-stream packets.
            if self._packetbuf[0] != 0x55 or self._packetbuf[1] != 0x55:
                skip = self._packetbuf.find(b"\x55\x55")
                if skip == -1:
                    self._packetbuf.clear()
                    break
                _LOGGER.debug("Resyncing packet buffer, skipping %d bytes", skip)
                del self._packetbuf[:skip]
                continue
            pkt_len = self._packetbuf[3] + 7
            if len(self._packetbuf) >= pkt_len:
                packet = NiimbotPacket.from_bytes(self._packetbuf[:pkt_len])
                self._log_buffer("recv", packet.to_bytes())
                packets.append(packet)
                del self._packetbuf[:pkt_len]
            else:
                break
        return packets

    async def _send(self, packet, response=True):
        await self._transport.write(packet.to_bytes(), response=response)

    def _log_buffer(self, prefix: str, buff: bytes):
        msg = ":".join(f"{i:#04x}"[-2:] for i in buff)
        _LOGGER.debug(f"{prefix}({len(buff)}): {msg}")

    async def _transceive(
        self,
        reqcode,
        data,
        respoffset=1,
        await_for_response=True,
        resp_codes: set[int] | None = None,
        timeout: float = DEFAULT_TRANSCEIVE_TIMEOUT,
    ):
        if resp_codes is None:
            resp_codes = {respoffset + reqcode}
        packet = NiimbotPacket(reqcode, data)
        self._log_buffer("send", packet.to_bytes())
        await self._send(packet)
        if not await_for_response:
            return None
        deadline = time.monotonic() + timeout
        resp = None
        for _ in range(6):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            for packet in await self._recv(timeout=remaining):
                if packet.type == 219:
                    # We will assume a single byte error.
                    raise PrinterError(PrinterErrorCodeEnum(packet.data[0]))
                elif packet.type == 0:
                    raise NotImplementedError
                elif packet.type in resp_codes:
                    resp = packet
            if resp:
                return resp
        raise PrinterTimeout(
            f"No response for request 0x{int(reqcode):02x} "
            f"(expected {[hex(c) for c in resp_codes]})"
        )

    async def get_info(self, key):
        try:
            packet = await self._transceive(
                RequestCodeEnum.GET_INFO, bytes((key,)), key
            )
        except PrinterTimeout:
            return None
        match key:
            case InfoEnum.DEVICESERIAL:
                # niimblue: varies by length
                if len(packet.data) < 4:
                    return "-1"
                elif len(packet.data) >= 8:
                    return bytes.fromhex(packet.data.hex()).decode("ascii", errors="replace")
                else:
                    return packet.data[:4].hex().upper()
            case InfoEnum.SOFTVERSION:
                return packet.data[0] + (packet.data[1] / 100)
            case InfoEnum.HARDVERSION:
                return packet.data[0] + (packet.data[1] / 100)
            case InfoEnum.DEVICETYPE:
                # niimblue: 1-byte => data[0] << 8, 2-byte => bytesToI16
                if len(packet.data) == 1:
                    return packet.data[0] << 8
                else:
                    return int.from_bytes(packet.data[:2], "big")
            case _:
                return _packet_to_int(packet)

    async def get_rfid(self):
        packet = await self._transceive(RequestCodeEnum.GET_RFID, b"\x01")
        data = packet.data

        # A 1-byte payload means no tag. Do not test data[0] == 0 — that is the
        # first byte of the UUID and can legitimately be zero.
        if len(data) <= 1:
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
        total_len, used_len, type_ = struct.unpack(">HHB", data[idx : idx + 5])
        idx += 5
        capacity = (
            struct.unpack(">H", data[idx : idx + 2])[0]
            if len(data) >= idx + 2
            else None
        )
        return {
            "uuid": uuid,
            "barcode": barcode,
            "serial": serial,
            "used_len": used_len,
            "total_len": total_len,
            "type": type_,
            "capacity": capacity,
        }

    def _parse_heartbeat_advanced1(self, data: bytes, model_id=None) -> dict:
        closingstate = None
        powerlevel = None
        paperstate = None
        rfidreadstate = None
        match len(data):
            case 20:
                paperstate = data[18]
                rfidreadstate = data[19]
            case 13:
                closingstate = data[9]
                powerlevel = data[10]
                paperstate = data[11]
                rfidreadstate = data[12]
            case 19:
                closingstate = data[15]
                powerlevel = data[16]
                paperstate = data[17]
                rfidreadstate = data[18]
            case 10:
                closingstate = data[8]
                powerlevel = data[9]
            case 9:
                closingstate = data[8]
            case _:
                _LOGGER.debug(
                    "Unrecognized Advanced1 heartbeat length %s: %s",
                    len(data),
                    data.hex(),
                )

        if closingstate is not None and model_id is not None:
            if model_id in INVERTED_LID_MODELS:
                closingstate = 0 if closingstate != 0 else 1

        return {
            "closingstate": closingstate,
            "powerlevel": powerlevel,
            "paperstate": paperstate,
            "rfidreadstate": rfidreadstate,
            "variant": "advanced1",
        }

    def _parse_heartbeat_advanced2(self, data: bytes) -> dict:
        """Parse Advanced2 (0xD9) fixed-offset heartbeat. Inverted-lid list does not apply."""
        if len(data) < 9:
            _LOGGER.debug(
                "Advanced2 heartbeat too short (%s): %s", len(data), data.hex()
            )
            return {
                "closingstate": None,
                "powerlevel": None,
                "paperstate": None,
                "rfidreadstate": None,
                "variant": "advanced2",
            }

        result = {
            "closingstate": data[4],
            "powerlevel": data[2],
            "paperstate": data[5],
            "rfidreadstate": data[6],
            "ribbon_rfidreadstate": data[7],
            "ribbonstate": data[8],
            "temperature": data[3],
            "variant": "advanced2",
        }
        if len(data) >= 11:
            result["wifi_rssi"] = int.from_bytes(data[9:11], "big", signed=True)
        if len(data) >= 13:
            result["lighting_error"] = data[12]
        if len(data) >= 14:
            result["voltage_state"] = data[13]
        return result

    def _parse_heartbeat(self, packet: NiimbotPacket, model_id=None) -> dict:
        if packet.type == HEARTBEAT_RESP_ADVANCED2:
            return self._parse_heartbeat_advanced2(packet.data)
        return self._parse_heartbeat_advanced1(packet.data, model_id=model_id)

    async def heartbeat(self, await_for_response=True, model_id=None):
        _LOGGER.debug("Heartbeat")
        if not await_for_response:
            payload = self._heartbeat_payload or b"\x01"
            await self._transceive(
                RequestCodeEnum.HEARTBEAT,
                payload,
                await_for_response=False,
            )
            return None

        # Prefer the payload that worked last time; otherwise try Advanced1 then Advanced2.
        candidates: list[bytes] = []
        if self._heartbeat_payload is not None:
            candidates.append(self._heartbeat_payload)
        for payload in (b"\x01", b"\x04"):
            if payload not in candidates:
                candidates.append(payload)

        last_error: Exception | None = None
        for payload in candidates:
            try:
                packet = await self._transceive(
                    RequestCodeEnum.HEARTBEAT,
                    payload,
                    resp_codes=HEARTBEAT_RESP_CODES,
                    timeout=DEFAULT_TRANSCEIVE_TIMEOUT,
                )
            except PrinterTimeout as err:
                _LOGGER.debug(
                    "Heartbeat payload %s timed out: %s", payload.hex(), err
                )
                last_error = err
                continue
            self._heartbeat_payload = payload
            return self._parse_heartbeat(packet, model_id=model_id)

        assert last_error is not None
        raise last_error

    async def set_label_type(self, n):
        _LOGGER.debug("Set label type %s", n)
        if not 1 <= n <= 11:
            raise ValueError(f"Label type {n} out of range 1-11")
        packet = await self._transceive(RequestCodeEnum.SET_LABEL_TYPE, bytes((n,)), 16)
        return bool(packet.data[0])

    async def set_label_density(self, n, density_min: int = 1, density_max: int = 5):
        if not density_min <= n <= density_max:
            raise ValueError(
                f"Label density {n} out of range {density_min}-{density_max}"
            )
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
        # Some models (e.g. B1 Pro) report progress2=0 even when done;
        # use the maximum of both non-zero values, falling back to whichever is non-zero.
        active = [p for p in (progress1, progress2) if p > 0]
        progress = max(active) if active else 0
        status = {
            "page": page,
            "page_print_progress": progress1,
            "page_feed_progress": progress2,
            "progress": progress,
        }
        if self.on_progress is not None:
            self.on_progress(status)
        return status

    async def get_print_end(self, copies: int = 1):
        status = await self.get_print_status()
        _LOGGER.debug("Status: %s", status)
        if status["page"] >= copies:
            return True
        if status["progress"] < 100:
            return False
        return True
