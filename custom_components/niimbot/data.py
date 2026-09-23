"""Per-entry runtime state for the Niimbot integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .cloud import LabelCloudLookup
from .const import ImageAndBLEData
from .niimprint import BLEData, NiimbotDevice


@dataclass
class NiimbotRuntimeData:
    """Everything a loaded config entry holds, attached as entry.runtime_data."""

    address: str
    device: NiimbotDevice
    coordinator: DataUpdateCoordinator[BLEData]
    image_coordinator: DataUpdateCoordinator[ImageAndBLEData]
    # Snapshotted at setup, matching the values the print service used when
    # each entry registered its own handler.
    wait_between_each_print_line: int
    confirm_every_nth_print_line: int
    cloud_lookup: LabelCloudLookup | None
