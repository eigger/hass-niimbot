# Setup

## Install

Requires HA 2025.1.0 or later and Python 3.13 or later for the existing blesession/imagespec requirements. HA 2025.1 running Python 3.12 cannot install those packages.

1. Install `eigger/hass-niimbot` through HACS as a custom repository, or copy `custom_components/niimbot` into your Home Assistant configuration.
2. Restart Home Assistant.
3. Add **Niimbot** from **Settings → Devices & services** and select a discovered printer.

## Bluetooth connection

Use a connectable local adapter or an ESPHome Bluetooth proxy registered through HA's ESPHome integration. Start with the [shared Bluetooth proxy setup and recommended devices (한국어)](https://github.com/eigger/hass-repo-standards/blob/main/docs/bluetooth.md) for board revision, firmware, network and connection-slot guidance.

`bluetooth_proxy.active` enables GATT connections; `esp32_ble_tracker.scan_parameters.active` requests scan responses. Finding advertisements, including with passive scanning, does not prove a connection or write will succeed. Keep scan interval/window defaults initially. For an ESP32 proxy, the following is only a Bluetooth configuration fragment; merge it with the correct board and network configuration:

```yaml
esp32_ble_tracker:
  scan_parameters:
    active: true

bluetooth_proxy:
  active: true
```

Source: [shared Bluetooth guide](https://github.com/eigger/hass-repo-standards/blob/main/docs/bluetooth.md), reviewed 2026-10-18. This guidance does not certify a physical Niimbot/proxy combination.

Power on and wake the printer before discovery or printing, charge it, load the matching roll and close the cover. Disconnect the NIIMBOT phone app or other BLE clients first. This integration connects through HA Bluetooth; its config flow does not ask for a PIN, bonding procedure or account login. Model/firmware-specific authentication beyond this flow has not been verified. See [Niimbot troubleshooting](troubleshooting.md) for model and transport failures.

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
