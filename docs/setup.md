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

Online lookup sends the label product code only. It does not send the printer serial number, RFID tag ID or other device identifiers. If lookup succeeds, the retrieved dimensions and paper type are used as print defaults; explicit values in a print action take precedence.

## Supported printers

See the [device reference](devices.md) for the complete model list, print widths and density ranges. B1, B1 Pro, B2 Pro, B21 Pro and D110 have been verified; other Bluetooth models may work.
