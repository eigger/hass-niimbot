"""Fake BLE transport for protocol unit tests."""

from __future__ import annotations

from collections import deque

from custom_components.niimbot.niimprint.packet import NiimbotPacket
from custom_components.niimbot.niimprint.printer import BaseTransport


class FakeTransport(BaseTransport):
    """Records writes and returns canned response packets."""

    def __init__(self, responses: list[NiimbotPacket] | None = None):
        self.written: list[bytes] = []
        self._responses: deque[bytes] = deque(p.to_bytes() for p in (responses or []))

    def queue(self, *packets: NiimbotPacket) -> None:
        for packet in packets:
            self._responses.append(packet.to_bytes())

    async def read(self, length: int, timeout: float = 30.0) -> bytes:
        if not self._responses:
            raise TimeoutError("no canned response")
        return self._responses.popleft()

    # Auto-answer for the prefixed Connect request; None leaves it unanswered.
    connect_reply: int | None = None

    async def write(self, data: bytes, response=True):
        self.written.append(data)
        if data[:1] == b"\x03" and self.connect_reply is not None:
            self.queue(NiimbotPacket(0xC2, bytes((self.connect_reply,))))

    async def start_notify(self, uuid: str):
        return None

    async def stop_notify(self, uuid: str):
        return None

    @property
    def written_packets(self) -> list[NiimbotPacket]:
        # Connect is framed with one extra leading 0x03 byte; strip it to parse.
        return [
            NiimbotPacket.from_bytes(b[1:] if b[:1] == b"\x03" else b)
            for b in self.written
        ]
