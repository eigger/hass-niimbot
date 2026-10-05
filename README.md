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

See [examples](examples/README.md) for more print and automation recipes. See [Actions](docs/actions.md) for parameters and [imagespec's element reference](https://github.com/eigger/imagespec/blob/main/docs/elements.md) for payload syntax.

## Supported printers

These representative models have been verified. Sizes below are **manual action settings for the example label**, not fixed sizes for every roll.

| Model | Resolution | Label example | `width` | `height` | `rotate` | Density (default) |
|---|---|---|---|---|---|---|
| B1 | 203 DPI | 40×30 mm | `320` | `240` | `0` | 1–5 (3) |
| B1 Pro | 300 DPI | 40×30 mm | `472` | `354` | `0` | 1–5 (3) |
| B2 Pro | 300 DPI | 40×30 mm | `472` | `354` | `0` | 1–5 (3) |
| B21 Pro | 300 DPI | 40×30 mm | `472` | `354` | `0` | 1–5 (3) |
| D110 | 203 DPI | 30×12 mm | `240` | `96` | `90` | 1–3 (2) |

For other label sizes, calculate pixels with `round(mm × DPI / 25.4)` and allow for the label's printable margins. `width` and `height` describe the canvas before rotation; `90` or `270` swaps the output dimensions. The [D110 example](examples/d110.yaml) renders 240×96 px and sends a 96×240 px image.

**Automatic label sizing:** Enable **Fetch Label Info Online** in the integration options. Once **Cloud Label Info** has successfully resolved the loaded label, omit `width`, `height` and `label_type` from the print action to use that label's dimensions and paper type automatically. The lookup already accounts for the catalogue orientation; leave `rotate` at `0` unless you want to rotate the content further. Explicit action values override the lookup. If lookup is unavailable, the size falls back to `400×240` px; this legacy fallback is not a universal label size.

See the [device reference](docs/devices.md) for the full model list and supported label types, and [Actions](docs/actions.md) for sizing and rotation.

## Documentation and support

- [Documentation index](docs/README.md)
- [Setup and options](docs/setup.md)
- [Troubleshooting](docs/troubleshooting.md) ([한국어](docs/ko/troubleshooting.md))
- [Open an issue](https://github.com/eigger/hass-niimbot/issues) · [Discussions](https://github.com/eigger/hass-niimbot/discussions)

## Related

- [imagespec](https://github.com/eigger/imagespec) — payload renderer and element reference
- [niimblue](https://github.com/MultiMote/niimblue) — Niimbot protocol implementation
- [Stash](https://github.com/eigger/stash) — inventory manager with Niimbot printing support
