"""Test configuration.

Protocol and model tests do not start Home Assistant. Integration tests request
the ``hass`` fixture; custom integrations are enabled only for those.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.niimbot.const import DOMAIN

ADDRESS = "AA:BB:CC:DD:EE:01"
ADDRESS_2 = "AA:BB:CC:DD:EE:02"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(request: pytest.FixtureRequest) -> None:
    """Load custom_components/niimbot only for tests that start Home Assistant."""
    if "hass" in request.fixturenames:
        request.getfixturevalue("enable_custom_integrations")


async def setup_entry(
    hass: HomeAssistant,
    *,
    address: str = ADDRESS,
    data: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> MockConfigEntry:
    """Create and load a config entry. No advertisement is required: setup
    continues with the last-known (empty) data when the printer is absent."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=address,
        title=f"Niimbot {address[-5:]}",
        data=data or {},
        options=options or {},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def device_of(
    hass: HomeAssistant, address: str = ADDRESS, *, entry_id: str
) -> dr.DeviceEntry:
    """The HA device created from the printer's entity device info."""
    device = dr.async_get(hass).async_get_device_by_connection(
        (CONNECTION_BLUETOOTH, address), entry_id
    )
    assert device is not None, address
    return device
