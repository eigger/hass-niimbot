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

## Increasing print speed

The printer receives data from Home Assistant line by line.  When this data is
sent via a Bluetooth proxy, the latency involved in communicating each packet
and awaiting for a response can cause significant delays that add up.  This
is particularly notorious for complex labels with little to no empty horizontal
space.  This is so because that way of sending data is the maximally conservative
way that ensures maximum reliability.  That reliability comes at a cost of speed.

Despair not, as there are workarounds to accelerate printouts substantially.
In the developer console, you can try the following workarounds documented
below:

```yaml
action: niimbot.print
# We will assume a high-density printer like the B21 Pro.
data:
  payload:
    # Complex figure you can test with.
    - type: rectangle
      x_start: 0
      x_end: 10
      y_start: 0
      y_end: 600
      fill: black
  width: 584
  height: 350
  density: 5
  # The following value reduces the time HA waits between
  # lines sent to the printer, from its default 0.05 (50 ms).
  # Sufficiently small values may cause your printer to fail
  # to print at all, or print corrupted labels.
  wait_between_print_lines: 0.01
  # The following value changes the way that lines are sent
  # to the printer, from a write-with-response to a plain
  # fire-and-forget write, for the number of lines you set
  # minus one (in this example, the value says 16, so HA
  # would send 15 lines without confirmation, and send each
  # 16th line waiting for a response).  The default is 1,
  # which means every line gets sent using write-with-response,
  # which itself costs about 0.1 seconds per line.
  # Sufficiently large values will flood your ESPHome Bluetooth
  # proxies, causing no or partial printout of labels.
  print_line_batch_size: 16
target:
  device: <your device ID>
```

Once you have experimented with these configuration values, you can
set them permanently for every print.  First, delete the existing
configuration entry for your Niimbot printer.  Then, manually add
your printer again.  In the configuration dialog that appears while
adding it, you'll find two configuration settings you have to change:

* Wait time between print lines: set it to the value that worked
  for you, multiplied by 1000 (as the configuration value is in
  milliseconds).
* How often to confirm reception of print lines: set it to the
  value of `print_line_batch_size`.

Thus, the values that worked for you will now be permanent and used
in every print.

You are encouraged to open reports with the values that worked for you,
in order to help us come up with better, less conservative defaults.
Anecdotally, in a congested network, the B21 Pro printer is reliable
down to 10 milliseconds (0.01 seconds) of waiting between print lines,
and up to 16 lines in a batch prior to confirmation, which speeds up
complex labels more than *fourfold*.

## Custom Fonts
* https://github.com/OpenEPaperLink/Home_Assistant_Integration/blob/main/docs/drawcustom/supported_types.md#font-locations
* https://github.com/OpenEPaperLink/Home_Assistant_Integration/commit/4817d7d7b2138c31e3744a5f998751a17106037d

## References
- [MultiMote/nimblue](https://github.com/MultiMote/niimblue.git)
- [OpenEPaperLink](https://github.com/OpenEPaperLink/Home_Assistant_Integration.git)
