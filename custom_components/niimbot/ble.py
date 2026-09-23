"""Resolve the printer Home Assistant can see right now.

The lookup is `blesession`'s, so a printer no radio can see fails the same
way it does in the other integrations: `Unreachable`, with a stage and a
sentence, instead of a message worded only here.
"""

from __future__ import annotations

from bleak.backends.device import BLEDevice
from blesession import Unreachable
from blesession.hass import ble_device_or_raise
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError


def require_ble_device(hass: HomeAssistant, address: str) -> BLEDevice:
    """The handle to connect with, or HomeAssistantError when none is visible."""
    try:
        return ble_device_or_raise(hass, address)
    except Unreachable as err:
        raise HomeAssistantError(str(err)) from err
