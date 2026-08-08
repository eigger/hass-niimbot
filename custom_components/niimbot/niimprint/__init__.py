"""Parser for Niimbot BLE advertisements."""

from .parser import NiimbotDevice, BLEData, EVENT_ROLL_CHANGED
from .printer import PrinterError, PrinterTimeout, PrinterCommandUnsupported

__version__ = "1.0.0"

__all__ = [
    "NiimbotDevice",
    "BLEData",
    "PrinterError",
    "PrinterTimeout",
    "PrinterCommandUnsupported",
    "EVENT_ROLL_CHANGED",
]
