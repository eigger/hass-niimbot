# Setup

## Install

1. Install `eigger/hass-niimbot` through HACS as a custom repository, or copy `custom_components/niimbot` into your Home Assistant configuration.
2. Restart Home Assistant.
3. Add **Niimbot** from **Settings → Devices & services** and select a discovered printer.

## Bluetooth connection

A Bluetooth proxy is recommended when the Home Assistant host's Bluetooth adapter has limited range or unreliable connections. Configure the proxy as active and keep the BLE scan interval at its default unless you have a specific reason to change it.

```yaml
esp32_ble_tracker:
  scan_parameters:
    active: true

bluetooth_proxy:
  active: true
```

## Integration options

Open **Settings → Devices & services → Niimbot → Configure**.

| Option | Default | Description |
|---|---:|---|
| Scan interval | 600 seconds | How often printer status is polled (10–9999 seconds) |
| Keep connection | Off | Keep the BLE connection open between polls and print jobs |
| Fetch label info online | Off | Look up the loaded label's name and dimensions from its product code (barcode) |

Online lookup sends the label product code only. It does not send the printer serial number, RFID tag ID or other device identifiers.

To size prints automatically, enable **Fetch Label Info Online**, wait for **Cloud Label Info** to resolve the loaded label, then omit `width`, `height` and `label_type` from the print action. A successful lookup supplies the label dimensions and paper type. Its catalogue orientation is already included in the dimensions, so leave `rotate` at `0` unless you intend an additional rotation. Explicit action values take precedence. If lookup cannot resolve the label, supply dimensions manually; the `400×240` px fallback does not fit every roll.

## Supported printers

See the [device reference](devices.md) for the complete model list, print widths and density ranges. B1, B1 Pro, B2 Pro, B21 Pro and D110 have been verified; other Bluetooth models may work.
