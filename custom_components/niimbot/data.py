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
    cloud_lookup: LabelCloudLookup | None
