# hass-niimbot

[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?logo=home-assistant)](https://hacs.xyz/)
[![GitHub Release](https://img.shields.io/github/release/eigger/hass-niimbot.svg)](https://github.com/eigger/hass-niimbot/releases)
[![License](https://img.shields.io/github/license/eigger/hass-niimbot)](https://github.com/eigger/hass-niimbot/blob/main/LICENSE)

Print labels with Niimbot printers from Home Assistant using [imagespec](https://github.com/eigger/imagespec) payloads over Bluetooth.

| B1 / B1 Pro | B21 Pro | D110 |
|---|---|---|
| <img src="https://raw.githubusercontent.com/eigger/hass-niimbot/master/docs/images/b1.jpg" width="280" alt="B1 / B1 Pro"> | <img src="https://raw.githubusercontent.com/eigger/hass-niimbot/master/docs/images/b21pro.jpg" width="280" alt="B21 Pro"> | <img src="https://raw.githubusercontent.com/eigger/hass-niimbot/master/docs/images/d110.jpg" width="280" alt="D110"> |

## Install

Install `eigger/hass-niimbot` through HACS as a custom repository, or copy `custom_components/niimbot` into your Home Assistant configuration. Restart Home Assistant, add **Niimbot** from **Settings → Devices & services**, then select a discovered printer.

An active Bluetooth proxy is recommended when the Home Assistant adapter has limited range. See [setup](docs/setup.md#bluetooth-connection).

## Quick start

Run this from **Developer tools → Actions** and replace the target with your printer:

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
      size: 40
  width: 400
  height: 240
```

See [examples](examples/README.md) for more print and automation recipes. See [Actions](docs/actions.md) for parameters and [imagespec's element reference](https://github.com/eigger/imagespec/blob/main/docs/elements.md) for payload syntax.

## Supported printers

**Verified printers:** B1, B1 Pro, B2 Pro, B21 Pro and D110. The integration also includes profiles for other Niimbot Bluetooth models, including D11, D101, B21 and B3S series printers. See the [device reference](docs/devices.md) for the full model list and hardware limits.

## Documentation and support

- [Documentation index](docs/README.md)
- [Setup and options](docs/setup.md)
- [Troubleshooting](docs/troubleshooting.md) ([한국어](docs/ko/troubleshooting.md))
- [Open an issue](https://github.com/eigger/hass-niimbot/issues) · [Discussions](https://github.com/eigger/hass-niimbot/discussions)

## Related

- [imagespec](https://github.com/eigger/imagespec) — payload renderer and element reference
- [niimblue](https://github.com/MultiMote/niimblue) — Niimbot protocol implementation
- [Stash](https://github.com/eigger/stash) — inventory manager with Niimbot printing support
