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

**Verified printers:** B1, B1 Pro, B2 Pro, B21 Pro and D110.

The integration also has model profiles for the Bluetooth printers below. These profiles provide model-specific label types, density ranges and hardware limits; not every model has been individually tested. Models using a different, non-Niimbot Bluetooth protocol are not supported.

<details>
<summary>View model profiles</summary>

- **D11:** D41, D61, Dxx, D11, Hi-NB-D11, Fust, D11S, D11_H, D11_Pro
- **B3S:** A8, B3S, JCB3S, S6, B3S_P, A8_P, S6_P
- **B21:** B21, B21-L2B, B21-C2B, B21S-C2B, B21S, B21_Pro
- **P1S:** P1, P1S, P18
- **B16:** B16
- **B32:** B32, B32R, Z401, T8S, A63
- **D110:** D110, Hi-D110, D110_M
- **D101:** D101, Betty
- **B203:** B203, A20, A203
- **B18/N1:** B18, B18S, N1, A1 Pro
- **H1:** H1
- **B1:** B1, B1 Pro, B1 SE
- **H1S:** H1S
- **M2:** M2_H, TP2M_H, EP2M_H
- **K3:** K3, K3_W, MP3K, MP3K_W, K3_ITD, K4
- **C1:** C1, EP1C
- **ET10:** ET10
- **B31:** B31
- **K2:** K2
- **M3:** M3, EP3M
- **B4:** B4, B4 Pro
- **B2:** B2 Pro, B2
- **B11:** B11, S1, S3, JC-M90
- **B50:** B50, B50W, T6, T7
- **T8:** T8
- **B3:** B3
- **T2:** T2S

</details>

See the [device reference](docs/devices.md) for model IDs, label types, density ranges and hardware limits.

## Documentation and support

- [Documentation index](docs/README.md)
- [Setup and options](docs/setup.md)
- [Troubleshooting](docs/troubleshooting.md) ([한국어](docs/ko/troubleshooting.md))
- [Open an issue](https://github.com/eigger/hass-niimbot/issues) · [Discussions](https://github.com/eigger/hass-niimbot/discussions)

## Related

- [imagespec](https://github.com/eigger/imagespec) — payload renderer and element reference
- [niimblue](https://github.com/MultiMote/niimblue) — Niimbot protocol implementation
- [Stash](https://github.com/eigger/stash) — inventory manager with Niimbot printing support
