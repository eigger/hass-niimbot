"""Fake BLE transport for protocol unit tests."""

from __future__ import annotations

from collections import deque

from custom_components.niimbot.niimprint.packet import NiimbotPacket
from custom_components.niimbot.niimprint.printer import BaseTransport


class FakeTransport(BaseTransport):
    """Records writes and returns canned response packets."""

    def __init__(self, responses: list[NiimbotPacket] | None = None):
        self.written: list[bytes] = []
        self._responses: deque[bytes] = deque(
            p.to_bytes() for p in (responses or [])
        )

    def queue(self, *packets: NiimbotPacket) -> None:
        for packet in packets:
            self._responses.append(packet.to_bytes())

    async def read(self, length: int, timeout: float = 30.0) -> bytes:
        if not self._responses:
            raise TimeoutError("no canned response")
        return self._responses.popleft()

    async def write(self, data: bytes, response=True):
        self.written.append(data)

    async def start_notify(self, uuid: str):
        return None

    async def stop_notify(self, uuid: str):
        return None

    @property
    def written_packets(self) -> list[NiimbotPacket]:
        return [NiimbotPacket.from_bytes(b) for b in self.written]
