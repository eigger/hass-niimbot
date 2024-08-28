"""Parser for Niimbot BLE advertisements."""
from __future__ import annotations

from .parser import NiimbotDevice, BLEData
from .printer import PrinterClient

__version__ = "1.0.0"

__all__ = ["NiimbotDevice", "BLEData"]
