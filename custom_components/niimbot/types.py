"""Type aliases for the Niimbot integration."""

from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .data import NiimbotRuntimeData

type NiimbotConfigEntry = ConfigEntry[NiimbotRuntimeData]
