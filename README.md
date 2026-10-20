<!-- hass-standards:header:start -->
# hass-niimbot

Print labels with Niimbot printers from Home Assistant using imagespec payloads over Bluetooth.

**English** | [한국어](README.ko.md)

<!-- hass-standards:badges:start -->
[![Release](https://img.shields.io/github/v/release/eigger/hass-niimbot?style=flat)](https://github.com/eigger/hass-niimbot/releases)
[![HACS Default](https://img.shields.io/badge/HACS-Default-41BDF5?style=flat)](#installation)
[![Home Assistant minimum](https://img.shields.io/badge/HA-%E2%89%A5%202025.1.0-41BDF5?style=flat)](hacs.json)
[![Tests](https://img.shields.io/github/actions/workflow/status/eigger/hass-niimbot/tests.yml?branch=master&style=flat&label=Tests)](https://github.com/eigger/hass-niimbot/actions/workflows/tests.yml)
[![Validate](https://img.shields.io/github/actions/workflow/status/eigger/hass-niimbot/validate.yml?branch=master&style=flat&label=Validate)](https://github.com/eigger/hass-niimbot/actions/workflows/validate.yml)
[![License](https://img.shields.io/github/license/eigger/hass-niimbot?style=flat)](LICENSE)
[![HACS Downloads](https://img.shields.io/badge/dynamic/json?style=flat&color=41BDF5&label=HACS+Downloads&query=%24%5B%3F%28%40.full_name%3D%3D%22eigger%2Fhass-niimbot%22%29%5D.downloads&url=https%3A%2F%2Fdata-v2.hacs.xyz%2Fintegration%2Fdata.json)](https://www.hacs.xyz/)
<!-- hass-standards:badges:end -->
<!-- hass-standards:header:end -->

| B1 / B1 Pro | B21 Pro | D110 |
|---|---|---|
| <img src="docs/images/b1.jpg" width="280" alt="B1 / B1 Pro"> | <img src="docs/images/b21pro.jpg" width="280" alt="B21 Pro"> | <img src="docs/images/d110.jpg" width="280" alt="D110"> |

## Requirements

This is a custom integration distributed through the HACS default catalog. Home Assistant **2025.1.0 or later**, **Python 3.13 or later** (required by the existing runtime dependencies), a supported Niimbot BLE printer and a connectable Home Assistant Bluetooth adapter or active ESPHome Bluetooth proxy are required. HA 2025.1 installations running Python 3.12 cannot install these dependency versions; use a compatible Python runtime. The HA minimum remains unchanged.

## Installation

<!-- hass-standards:installation:start -->
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=eigger&repository=hass-niimbot)
<!-- hass-standards:installation:end -->

Install and configure HACS first; the button opens this repository in HACS. In HACS, search for **Niimbot** and install it from the default catalog, or copy `custom_components/niimbot` into your Home Assistant configuration. Restart Home Assistant, add **Niimbot** from **Settings → Devices & services**, then select a discovered printer.

Turn the printer on, wake it from sleep and disconnect the NIIMBOT phone app before setup or printing. See [Bluetooth proxy setup](https://github.com/eigger/blesession/blob/main/docs/bluetooth.md), [Niimbot setup](docs/setup.md#bluetooth-connection) and [troubleshooting](docs/troubleshooting.md).

## Quick start

Enable **Fetch Label Info Online** in the integration options to automatically use the loaded label's size after a successful lookup. Run this from **Developer tools → Actions** and replace the target with your printer:

```yaml
action: niimbot.print
target:
  device_id: <your device>
data:
  payload:
    - type: text
      value: Hello World!
      x: 10
      y: 10
      size: 28
```

See [payload guide](docs/payload.md) and [examples](examples/README.md) for more print and automation recipes. See [Actions](docs/actions.md) for parameters and [imagespec's element reference](https://github.com/eigger/imagespec/blob/main/docs/elements.md) for payload syntax.

## Important limits

B1, B1 Pro, B2 Pro, B21 Pro and D110 are the representative verified models; other models and firmware may behave differently. See [model settings and label sizing](docs/label-sizing.md) and the [full device reference](docs/devices.md).

Online label lookup is optional and off by default. When enabled, only the label product barcode is sent to NIIMBOT's catalogue. If lookup fails, specify dimensions explicitly: the legacy `400×240` px fallback does not fit every roll. A reported BLE success does not verify physical print quality.

## Documentation and support

- [Documentation index](docs/README.md)
- [Setup and options](docs/setup.md)
- [Troubleshooting](docs/troubleshooting.md) ([한국어](docs/ko/troubleshooting.md))
- [Development and tests](CONTRIBUTING.md)
- [License](LICENSE)
- [Report a bug](https://github.com/eigger/hass-niimbot/issues) · [Questions and feature requests](https://github.com/eigger/hass-niimbot/discussions)

The HACS Downloads badge uses the target asset download count for the release selected by HACS, from official HACS data. It is not a total across all releases or assets, or a count of active installations. Missing data or a failed request means the count is unavailable, not zero installations.

<!-- hass-standards:support:start -->
## Support

- [Issues](https://github.com/eigger/hass-niimbot/issues): Report bugs or request features.
- [Discussions](https://github.com/eigger/hass-niimbot/discussions): Ask questions and share your experience.
<!-- hass-standards:support:end -->

<!-- hass-standards:related-projects:start -->
## Related Projects

- [imagespec](https://github.com/eigger/imagespec): payload renderer and element reference
- [niimblue](https://github.com/MultiMote/niimblue): Niimbot protocol implementation
- [Stash](https://github.com/eigger/stash): inventory manager with Niimbot printing support
<!-- hass-standards:related-projects:end -->

<!-- hass-standards:license:start -->
## License

Released under the [MIT License](LICENSE).
<!-- hass-standards:license:end -->
