import dataclasses
import sys
from typing import Any
from unittest.mock import MagicMock

# Base class mock supporting subclassing and subscripting (e.g. BaseClass[T])
class MockBase:
    def __init__(self, *args, **kwargs):
        self.context = {}

    def _async_current_ids(self):
        return set()

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

    def async_abort(self, **kwargs):
        return {"type": "abort", **kwargs}

    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}

    async def async_set_unique_id(self, *args, **kwargs):
        pass

    def _abort_if_unique_id_configured(self):
        pass

    def __init_subclass__(cls, **kwargs):
        pass

    def __class_getitem__(cls, item):
        return cls


def _make_entity_base(name: str):
    return type(name, (MockBase,), {})


@dataclasses.dataclass(frozen=True)
class _EntityDescriptionStub:
    key: str = ""
    translation_key: str | None = None
    icon: str | None = None
    entity_category: Any = None
    device_class: Any = None
    state_class: Any = None
    native_unit_of_measurement: str | None = None
    entity_registry_enabled_default: bool = True
    name: str | None = None
    has_entity_name: bool = False

# ── Mock Home Assistant Modules ────────────────────────────────────────────────

# Mock homeassistant.exceptions
class MockHomeAssistantError(Exception):
    """Mock HomeAssistantError."""
    pass

class MockServiceValidationError(Exception):
    """Mock ServiceValidationError."""
    pass

ha_exceptions = MagicMock()
ha_exceptions.HomeAssistantError = MockHomeAssistantError
ha_exceptions.ServiceValidationError = MockServiceValidationError
sys.modules["homeassistant.exceptions"] = ha_exceptions

# Mock other homeassistant submodules
sys.modules["homeassistant"] = MagicMock()
sys.modules["homeassistant.components"] = MagicMock()
sys.modules["homeassistant.components.recorder.history"] = MagicMock()
sys.modules["homeassistant.components.bluetooth"] = MagicMock()
sys.modules["homeassistant.components.image"] = MagicMock()
sys.modules["homeassistant.components.sensor"] = MagicMock()
sys.modules["homeassistant.components.binary_sensor"] = MagicMock()
sys.modules["homeassistant.components.button"] = MagicMock()
sys.modules["homeassistant.components.switch"] = MagicMock()
sys.modules["homeassistant.components.select"] = MagicMock()

# Setup bluetooth passive update processor mocks
ha_bt_processor = MagicMock()
ha_bt_processor.PassiveBluetoothProcessorCoordinator = MockBase
ha_bt_processor.PassiveBluetoothDataProcessor = MockBase
sys.modules["homeassistant.components.bluetooth.passive_update_processor"] = ha_bt_processor

ha_config_entries = MagicMock()
ha_config_entries.ConfigFlow = MockBase
ha_config_entries.OptionsFlowWithReload = MockBase
sys.modules["homeassistant.config_entries"] = ha_config_entries

sys.modules["homeassistant.data_entry_flow"] = MagicMock()

ha_const = MagicMock()
ha_const.CONF_ADDRESS = "address"
ha_const.CONF_SCAN_INTERVAL = "scan_interval"
sys.modules["homeassistant.const"] = ha_const

sys.modules["homeassistant.core"] = MagicMock()
sys.modules["homeassistant.helpers"] = MagicMock()
sys.modules["homeassistant.helpers.selector"] = MagicMock()
sys.modules["homeassistant.helpers.device_registry"] = MagicMock()
sys.modules["homeassistant.helpers.entity"] = MagicMock()
sys.modules["homeassistant.helpers.entity_platform"] = MagicMock()
sys.modules["homeassistant.helpers.event"] = MagicMock()
sys.modules["homeassistant.helpers.typing"] = MagicMock()
sys.modules["homeassistant.helpers.update_coordinator"] = MagicMock()
sys.modules["homeassistant.helpers.debounce"] = MagicMock()
sys.modules["homeassistant.helpers.storage"] = MagicMock()
sys.modules["homeassistant.helpers.aiohttp_client"] = MagicMock()
sys.modules["homeassistant.util"] = MagicMock()
sys.modules["homeassistant.util.dt"] = MagicMock()

# Platform entity bases must support subclassing / subscripting, and each
# class used in a multiple-inheritance MRO must be a distinct type.
for _mod_name, _attrs in (
    (
        "homeassistant.components.sensor",
        {
            "SensorEntity": _make_entity_base("SensorEntity"),
            "SensorEntityDescription": _EntityDescriptionStub,
            "SensorDeviceClass": MagicMock(),
            "SensorStateClass": MagicMock(),
        },
    ),
    (
        "homeassistant.components.binary_sensor",
        {
            "BinarySensorEntity": _make_entity_base("BinarySensorEntity"),
            "BinarySensorEntityDescription": _EntityDescriptionStub,
            "BinarySensorDeviceClass": MagicMock(),
        },
    ),
    (
        "homeassistant.components.button",
        {"ButtonEntity": _make_entity_base("ButtonEntity")},
    ),
    (
        "homeassistant.components.switch",
        {"SwitchEntity": _make_entity_base("SwitchEntity")},
    ),
    (
        "homeassistant.components.select",
        {"SelectEntity": _make_entity_base("SelectEntity")},
    ),
    (
        "homeassistant.components.image",
        {"ImageEntity": _make_entity_base("ImageEntity")},
    ),
    (
        "homeassistant.helpers.update_coordinator",
        {
            "CoordinatorEntity": _make_entity_base("CoordinatorEntity"),
            "DataUpdateCoordinator": _make_entity_base("DataUpdateCoordinator"),
        },
    ),
):
    _mod = sys.modules[_mod_name]
    for _attr, _value in _attrs.items():
        setattr(_mod, _attr, _value)

# ── Mock External Modules ─────────────────────────────────────────────────────

# Mock bleak
sys.modules["bleak"] = MagicMock()
sys.modules["bleak.backends.device"] = MagicMock()
sys.modules["bleak_retry_connector"] = MagicMock()

# Mock propcache
sys.modules["propcache"] = MagicMock()
sys.modules["propcache.api"] = MagicMock()

# Mock aiohttp (a Home Assistant core dependency, not one this integration
# declares itself). Real exception/config classes, not MagicMock instances,
# so `except (aiohttp.ClientError, TimeoutError)` and `ClientTimeout(total=…)`
# in cloud.py behave correctly under test.
class MockClientError(Exception):
    """Stub for aiohttp.ClientError."""

class MockClientTimeout:
    """Stub for aiohttp.ClientTimeout."""
    def __init__(self, total=None):
        self.total = total

ha_aiohttp = MagicMock()
ha_aiohttp.ClientError = MockClientError
ha_aiohttp.ClientTimeout = MockClientTimeout
sys.modules["aiohttp"] = ha_aiohttp

# Only mock imagespec when it is not installed. CI installs it via
# requirements.txt; an unconditional MagicMock breaks test_render.py.
try:
    import imagespec  # noqa: F401
except ImportError:
    sys.modules["imagespec"] = MagicMock()

try:
    import voluptuous  # noqa: F401
except ImportError:
    vol_mock = MagicMock()
    vol_mock.Required = lambda key, default=None: key
    vol_mock.Optional = lambda key, default=None: key
    vol_mock.In = lambda values: values
    vol_mock.Schema = lambda schema: schema
    sys.modules["voluptuous"] = vol_mock

