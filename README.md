# hass-niimbot
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?logo=home-assistant)](https://hacs.xyz/)
[![GitHub Release](https://img.shields.io/github/release/eigger/hass-niimbot.svg)](https://github.com/eigger/hass-niimbot/releases)
[![License](https://img.shields.io/github/license/eigger/hass-niimbot)](https://github.com/eigger/hass-niimbot/blob/main/LICENSE)
![integration usage](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=%24.niimbot.total)

Niimbot Label Printer Home Assistant Integration

You can also use Niimbot as a label printer in [Stash](https://github.com/eigger/stash).

## Gallery

| B1 / B1 Pro | B21 Pro | D110 |
| :---: | :---: | :---: |
| <img src="https://raw.githubusercontent.com/eigger/hass-niimbot/master/docs/images/b1.jpg" width="300" alt="B1 / B1 Pro"> | <img src="https://raw.githubusercontent.com/eigger/hass-niimbot/master/docs/images/b21pro.jpg" width="370" alt="B21 Pro"> | <img src="https://raw.githubusercontent.com/eigger/hass-niimbot/master/docs/images/d110.jpg" width="300" alt="D110"> |

> [!IMPORTANT]
>
> For all NIIMBOT users using Bluetooth proxies:
> Please update your proxy devices to **ESPHome 2025.11.2 or later**.
>
> **Benefits of updating:**
> - Much faster printing (almost instant)
> - Greatly improved reliability
> - Reduced delays thanks to improved internal GATT handling

## Feedback & Support

- Found a bug? [Open an issue](https://github.com/eigger/hass-niimbot/issues)
- Questions or ideas? [Join the discussion](https://github.com/eigger/hass-niimbot/discussions)

---

## Supported Models

| Model | Status |
|-------|--------|
| B1 | confirmed |
| B1 Pro | confirmed |
| B2 Pro | confirmed |
| B21 Pro | confirmed |
| D110 | confirmed |
| Other models with Bluetooth | may work |

## Installation

1. Install with HACS (custom repository required), or copy this repo into `custom_components/niimbot`.
2. Restart Home Assistant.
3. Go to **Settings** → **Integrations** and add **Niimbot**.
4. Select a discovered printer from the list.

## Important Notice

It is **strongly recommended to use a Bluetooth proxy** instead of a built-in Bluetooth adapter for more stable connections and better range.

> [!TIP]
> Hardware recommendations: [Great ESP32 Board for an ESPHome Bluetooth Proxy](https://community.home-assistant.io/t/great-esp32-board-for-an-esphome-bluetooth-proxy/916767/31)

When using a proxy, keep the scan interval reasonable. Example ESPHome config:

```yaml
esp32_ble_tracker:
  scan_parameters:
    active: true

bluetooth_proxy:
  active: true
```

## Options

Configure via **Settings** → **Devices & Services** → **Niimbot** → **Configure**:

| Option | Default | Range | Description |
|--------|---------|-------|-------------|
| **Use Sound** | On | On/Off | Play sound when the printer connects |
| **Scan Interval** | 600 | 10–9999 s | How often to scan for the device |
| **Wait Between Each Print Line** | 50 | 0–1000 ms | Delay between each line sent to the printer |
| **Confirm Every Nth Print Line** | 1 | 1–512 | Confirm every N lines (higher = faster, less reliable) |

> [!TIP]
> If printing is slow, try **Confirm Every Nth Print Line** = 16 and **Wait Between Each Print Line** = 10 ms. If prints fail or look corrupted, use more conservative values. See [Increasing print speed](#increasing-print-speed).

---

## Payload & rendering (`imagespec`)

From version 2.0.0, labels are rendered with **[imagespec](https://github.com/eigger/imagespec)** — a declarative YAML/JSON list of drawing elements that becomes a bitmap sent to the printer.

**Documentation (maintained in imagespec, not duplicated here):**

| Topic | Link |
|-------|------|
| Element examples with preview images | [imagespec/docs/elements.md](https://github.com/eigger/imagespec/blob/main/docs/elements.md) |
| All element fields & defaults | [imagespec README — Element Reference](https://github.com/eigger/imagespec#elements-reference) |
| Layout, palette, LLM authoring guide | [imagespec/docs/authoring.md](https://github.com/eigger/imagespec/blob/main/docs/authoring.md) |

**Niimbot-specific behaviour:**

- **Palette:** black & white only. Off-palette colors (e.g. `red`, `orange`) are quantized to the nearest supported color.
- **Rotation:** `rotate: 90/180/270` rotates the drawing and **swaps output width/height** (label-printer mode).
- **Default font:** `ppb.ttf` in `custom_components/niimbot/fonts/`. Custom fonts also work from `www/fonts/`.
- **`plot` element:** reads history from Home Assistant **Recorder**.
- **`dither`:** set on the service call (or per element in the payload) to halftone photos/charts on a 2-color printer. Keep text and barcodes undithered for sharp edges — see [imagespec dithering docs](https://github.com/eigger/imagespec#dithering).
- **Layout:** prefer `row` / `column` / `stack` for stacked content instead of hand-calculated coordinates.

---

## Service: `niimbot.print`

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `payload` | yes | — | List of [imagespec elements](https://github.com/eigger/imagespec/blob/main/docs/elements.md) |
| `rotate` | no | `0` | `0`, `90`, `180`, or `270` |
| `width` | no | `400` | Label width in pixels (10–1600) |
| `height` | no | `240` | Label height in pixels (10–1600) |
| `density` | no | `3` | Print density 1–5 (some models max out at 3) |
| `dither` | no | `false` | Floyd–Steinberg halftone for the whole label |
| `wait_between_print_lines` | no | `0.05` | Seconds between lines (overrides device option) |
| `print_line_batch_size` | no | `1` | Lines per batch before confirmation (overrides device option) |
| `preview` | no | `false` | Render only; do not send to the printer |

Use `response_variable` in scripts to receive the generated image as a `data:` URL when `preview: true`.

### Basic example

```yaml
action: niimbot.print
target:
  device_id: <your device>
data:
  payload:
    - type: text
      value: Hello World!
      font: ppb.ttf
      x: 10
      y: 10
      size: 40
    - type: qrcode
      data: "https://www.home-assistant.io"
      x: 280
      y: 10
      width: 80
      height: 80
  width: 400
  height: 240
```

### Model-specific sizes

**D110** (small label, often rotated):

```yaml
action: niimbot.print
target:
  device_id: <your device>
data:
  payload:
    - type: text
      value: "Hello World!"
      font: ppb.ttf
      x: 10
      y: 10
      size: 30
  rotate: 90
  width: 240
  height: 96
```

**B21 Pro** (large label, high density):

```yaml
action: niimbot.print
target:
  area_id: kitchen
data:
  payload:
    - type: rectangle
      x_start: 0
      x_end: 584
      y_start: 0
      y_end: 354
      fill: black
  width: 584
  height: 354
  density: 5
```

### Preview without printing

Use **`preview: true`** while designing labels so nothing is sent to the printer. The **[Niimbot Payload Layout Editor](https://eigger.github.io/Niimbot_Payload_Editor.html)** can generate YAML via drag-and-drop — paste the result here and preview first.

```yaml
action: niimbot.print
target:
  device_id: <your device>
data:
  preview: true
  payload:
    - type: text
      value: Preview Test
      x: 10
      y: 10
      size: 30
  width: 400
  height: 240
```

Every print or preview updates `image.<device>_last_label_made` (disable in entity settings if unwanted).

---

## Script: multiline address label

`new_multiline` with `fit: true` shrinks text to fit the label box — useful for shipping addresses:

```yaml
alias: Print label with multiple lines of text
fields:
  contents:
    selector:
      text:
        multiline: true
    name: Contents
    required: true
sequence:
  - action: niimbot.print
    target:
      area_id: kitchen
    data:
      payload:
        - type: new_multiline
          x: 0
          y: 20
          size: 100
          width: 520
          height: 300
          fit: true
          font: rbm.ttf
          value: "{{ contents }}"
      width: 584
      height: 350
      density: 5
```

See [`new_multiline` in imagespec](https://github.com/eigger/imagespec/blob/main/docs/elements.md#new_multiline) for `fit_width`, `fit_height`, and spacing options.

---

## Increasing print speed

The printer receives data line by line. Over Bluetooth proxies, waiting for a response on every line adds up — especially on dense labels.

Tune per call first:

```yaml
action: niimbot.print
target:
  device_id: <your device>
data:
  payload:
    - type: rectangle
      x_start: 0
      x_end: 10
      y_start: 0
      y_end: 600
      fill: black
  width: 584
  height: 350
  density: 5
  wait_between_print_lines: 0.01
  print_line_batch_size: 16
```

Then persist working values in the integration **Configure** dialog (`wait_between_print_lines × 1000` → ms for **Wait Between Each Print Line**).

Anecdotally, B21 Pro on a busy network is reliable at 10 ms wait and batch size 16 (~4× faster on complex labels). Report what works for your setup in [issues](https://github.com/eigger/hass-niimbot/issues).

---

## Preview on a dashboard

With `preview: true` and `response_variable`, a script can save the rendered image to disk and show it on a dashboard camera card.

1. Add to `configuration.yaml`:

```yaml
shell_command:
  update_label: >-
    bash -c 'set -o pipefail; echo "$0" | cut -d, -f2 | base64 -d >/config/www/label.png' {{ image_data }}
```

2. Add a **Local file** camera pointing at `/config/www/label.png`.

3. Script to preview and update the file:

```yaml
alias: Iterate on a label
fields:
  payload:
    selector:
      object: {}
    name: Payload
sequence:
  - action: niimbot.print
    target:
      device_id: <your device id>
    data:
      payload: "{{ payload }}"
      width: 584
      height: 350
      density: 5
      preview: true
    response_variable: previewed
  - action: shell_command.update_label
    data:
      image_data: "{{ previewed.image }}"
```

---

## Tools

**[Niimbot Payload Layout Editor](https://eigger.github.io/Niimbot_Payload_Editor.html)** — drag-and-drop layout designer; exports YAML for `niimbot.print`.

---

## Examples

| Example | Description |
|---------|-------------|
| [examples/grocy/README.md](examples/grocy/README.md) | Print a Grocy product label via webhook |

---

## Custom fonts

Place `.ttf` files in `custom_components/niimbot/fonts/` or `config/www/fonts/` and reference by filename (e.g. `ppb.ttf`, `rbm.ttf`).

---

## References

- [imagespec](https://github.com/eigger/imagespec) — rendering engine
- [MultiMote/niimblue](https://github.com/MultiMote/niimblue)
- [OpenEPaperLink](https://github.com/OpenEPaperLink/Home_Assistant_Integration)
