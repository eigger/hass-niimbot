"""Config flow for Niimbot BlE integration."""

import dataclasses
import logging
from typing import Any
import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfo,
    async_discovered_service_info,
)
from homeassistant.core import callback
from homeassistant.config_entries import (
    ConfigFlow,
    OptionsFlowWithReload,
    ConfigEntry,
    ConfigFlowResult,
)
from homeassistant.const import CONF_ADDRESS, CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResult, FlowContext
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_WAIT_BETWEEN_EACH_PRINT_LINE,
    CONF_CONFIRM_EVERY_NTH_PRINT_LINE,
    CONF_KEEP_CONNECTION,
    CONF_USE_CLOUD_LABEL_INFO,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WAIT_BETWEEN_EACH_PRINT_LINE,
    DEFAULT_CONFIRM_EVERY_NTH_PRINT_LINE,
    DEFAULT_KEEP_CONNECTION,
    DEFAULT_USE_CLOUD_LABEL_INFO,
    DOMAIN,
    NIIMBOT_SERVICE_UUID,
)


_LOGGER = logging.getLogger(__name__)


OPTIONS_SCHEMA = {
    vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): NumberSelector(
        NumberSelectorConfig(
            min=10,
            max=9999,
            step=1,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement="seconds",
        )
    ),
    vol.Required(
        CONF_WAIT_BETWEEN_EACH_PRINT_LINE,
        default=DEFAULT_WAIT_BETWEEN_EACH_PRINT_LINE,
    ): NumberSelector(
        NumberSelectorConfig(
            min=0,
            max=1000,
            step=1,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement="milliseconds",
        )
    ),
    vol.Required(
        CONF_CONFIRM_EVERY_NTH_PRINT_LINE,
        default=DEFAULT_CONFIRM_EVERY_NTH_PRINT_LINE,
    ): NumberSelector(
        NumberSelectorConfig(
            min=1,
            max=512,
            step=1,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement="lines",
        )
    ),
    vol.Required(CONF_KEEP_CONNECTION, default=DEFAULT_KEEP_CONNECTION): bool,
    vol.Required(
        CONF_USE_CLOUD_LABEL_INFO, default=DEFAULT_USE_CLOUD_LABEL_INFO
    ): bool,
}


@dataclasses.dataclass
class Discovery:
    """A discovered bluetooth device."""

    name: str
    discovery_info: BluetoothServiceInfo


NIIMBOT_NAME_PREFIXES = (
    "A63",
    "B1",
    "B2",
    "B3",
    "B4",
    "B11",
    "B16",
    "B18",
    "B203",
    "B21",
    "B31",
    "B32",
    "B50",
    "D11",
    "D101",
    "D41",
    "D61",
    "DXX",
    "T2S",
    "T6",
    "T7",
    "T8",
    "H1",
    "JC",
    "K2",
    "K3",
    "K4",
    "M2",
    "M3",
    "P1",
    "P18",
    "S1",
    "S3",
    "S6",
    "A8",
    "A20",
    "A203",
    "C1",
    "ET10",
    "NIIMBOT",
)


def _name_looks_like_niimbot(name: str | None) -> bool:
    """Check if the device name begins with a known Niimbot model prefix."""
    if not name:
        return False
    upper = name.upper()
    return any(upper.startswith(prefix) for prefix in NIIMBOT_NAME_PREFIXES)


def _discovery_display_name(discovery_info: BluetoothServiceInfo) -> str:
    """Return a user-friendly display name for a discovered Bluetooth device."""
    name = discovery_info.name
    if not name or name == discovery_info.address:
        return f"Niimbot ({discovery_info.address})"
    return name


class NiimbotDeviceUpdateError(Exception):
    """Custom error class for device updates."""


class NiimbotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Niimbot BLE."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        self._discovered_device: Discovery | None = None
        self._discovered_devices: dict[str, Discovery] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfo
    ) -> ConfigFlowResult:
        """Handle the bluetooth discovery step."""
        _LOGGER.debug("Discovered BT device: %s", discovery_info)
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        name = _discovery_display_name(discovery_info)
        self.context["title_placeholders"] = {"name": name}
        self._discovered_device = Discovery(name, discovery_info)

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery and configure options."""
        if user_input is not None:
            return self.async_create_entry(
                title=self.context["title_placeholders"]["name"], data=user_input
            )

        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders=self.context["title_placeholders"],
            data_schema=vol.Schema(OPTIONS_SCHEMA),
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step to pick discovered device."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            discovery = self._discovered_devices[address]

            self.context["title_placeholders"] = {
                "name": discovery.name,
            }

            self._discovered_device = discovery

            return self.async_create_entry(title=discovery.name, data=user_input)

        current_addresses = self._async_current_ids()
        all_discovered = list(async_discovered_service_info(self.hass))

        # First pass: look for devices matching Niimbot service UUID or known name prefixes
        for discovery_info in all_discovered:
            address = discovery_info.address
            if address in current_addresses or address in self._discovered_devices:
                continue

            matched = (
                NIIMBOT_SERVICE_UUID in discovery_info.service_uuids
                or _name_looks_like_niimbot(discovery_info.name)
            )
            if matched:
                _LOGGER.debug("Found Niimbot candidate: %s (%s)", discovery_info.name, address)
                name = _discovery_display_name(discovery_info)
                self._discovered_devices[address] = Discovery(name, discovery_info)

        # Fallback: if no devices matched the Niimbot filters, list all available
        # unconfigured BLE devices so the user can select their printer by MAC address.
        if not self._discovered_devices:
            for discovery_info in all_discovered:
                address = discovery_info.address
                if address in current_addresses or address in self._discovered_devices:
                    continue
                name = _discovery_display_name(discovery_info)
                self._discovered_devices[address] = Discovery(name, discovery_info)

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        titles = {
            title: f"{discovery.name} ({discovery.discovery_info.address})"
            for (title, discovery) in self._discovered_devices.items()
        }
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(titles),
                }
                | OPTIONS_SCHEMA
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler()


class OptionsFlowHandler(OptionsFlowWithReload):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # options가 비어있으면 data에서 가져옴
        suggested_values = {**self.config_entry.data, **self.config_entry.options}

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(OPTIONS_SCHEMA), suggested_values
            ),
        )
