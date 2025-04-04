# hass-niimbot
Niimbot Label Printer Home Assistant Integration

## Supported Models
- B1 (confirmed)
- D110 (confirmed)
- other models with Bluetooth may work

## Installation
1. Install this integration with HACS (adding repository required), or copy the contents of this
repository into the `custom_components/niimbot` directory.
2. Restart Home Assistant.
3. Go to Settings / Integrations and add integration "Niimbot"
4. Please select a discovered Niimbot device from the list.
   
## Examples for B1

```
action: niimbot.print
data:
  payload:
    - type: text
      value: Hello World!
      font: ppb.ttf
      x: 100
      y: 100
      size: 40
    - type: barcode
      data: "12345"
      code: "code128"
      x: 100
      y: 100
    - type: icon
      value: account-cowboy-hat
      x: 60
      y: 120
      size: 120
    - type: dlimg
      url: "https://image url.png"
      x: 10
      y: 10
      xsize: 120
      ysize: 120
      rotate: 0
    - type: qrcode
      data: "qr data"
      x: 140
      y: 50
      boxsize: 2
      border: 2
      color: "black"
      bgcolor: "white"
  width: 400
  height: 240
  rotate: 0
target:
  device_id: <your device>
```

## Example for D110

```
action: niimbot.print
data:
  payload:
    - type: text
      value: "Hello World!"
      font: ppb.ttf
      x: 10
      "y": 10
      size: 30
  rotate: 90
  width: 240
  height: 96
target:
  device_id: <your device>
```

## Custom Fonts

* https://github.com/OpenEPaperLink/Home_Assistant_Integration/blob/main/docs/drawcustom/supported_types.md#font-locations
* https://github.com/OpenEPaperLink/Home_Assistant_Integration/commit/4817d7d7b2138c31e3744a5f998751a17106037d
