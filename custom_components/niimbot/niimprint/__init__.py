"""Parser for Niimbot BLE advertisements."""

from .parser import NiimbotDevice, BLEData
from .printer import PrinterError

__version__ = "1.0.0"

__all__ = ["NiimbotDevice", "BLEData", "PrinterError"]
