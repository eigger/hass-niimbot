# hass-niimbot
Niimbot Label Printer Home Assistant Integration

## 💬 Feedback & Support

🐞 Found a bug? Let us know via an [Issue](https://github.com/eigger/hass-niimbot/issues).  
💡 Have a question or suggestion? Join the [Discussion](https://github.com/eigger/hass-niimbot/discussions)!


## Supported Models
- B1 (confirmed)
- B1 Pro (confirmed)
- D110 (confirmed)
- other models with Bluetooth may work

## Installation
1. Install this integration with HACS (adding repository required), or copy the contents of this
repository into the `custom_components/niimbot` directory.
2. Restart Home Assistant.
3. Go to Settings / Integrations and add integration "Niimbot"
4. Please select a discovered Niimbot device from the list.
   
## Examples for B1

```yaml
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

```yaml
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

## Example for B21 Pro

```yaml
action: niimbot.print
data:
  payload:
    - type: rectangle
      x_start: 0
      x_end: 600
      y_start: 0
      y_end: 600
      fill: black
  width: 584 # maximum label width
  height: 354 # maximum label height
  density: 5 # use this density to get full use of the printer's resolution
target:
  area_id: kitchen
```

## Script example for multiline text with width auto-fit

```yaml
sequence:
  - action: niimbot.print
    data:
      payload:
        - type: new_multiline
          x: 0
          "y": 20
          size: 100
          width: 560
          height: None
          fit_width: true
          spacing: 35
          font: rbm.ttf
          value: "{{ contents }}"
      width: 584
      height: 350
      density: 5
    target:
      area_id: kitchen
fields:
  contents:
    selector:
      text:
        multiline: true
    name: Contents
    required: true
    description: >-
      Contents of the label (e.g. the full address of a letter's recipient) each
      part in a separate line.
alias: Print label with multiple lines of text
description: >-
  Use this tool to quick-print any label, for example a recipient label for
  mailing a letter.  Give the contents of the label, in multiple lines, in the
  `content` field, for the print to be successful.  The text will resize to fit
  the width, and the height will fit a maximum of five lines.
```


## Custom Fonts
* https://github.com/OpenEPaperLink/Home_Assistant_Integration/blob/main/docs/drawcustom/supported_types.md#font-locations
* https://github.com/OpenEPaperLink/Home_Assistant_Integration/commit/4817d7d7b2138c31e3744a5f998751a17106037d

## References
- [MultiMote/nimblue](https://github.com/MultiMote/niimblue.git)
- [OpenEPaperLink](https://github.com/OpenEPaperLink/Home_Assistant_Integration.git)
