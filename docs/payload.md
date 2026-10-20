# Niimbot payloads

**English** | [한국어](payload.ko.md) · [README](../README.md)

## Common payload guide

Use the [imagespec payload guide](https://github.com/eigger/imagespec/blob/main/docs/payload.md) for shared syntax, elements, fonts, colors, rotation and dithering. Niimbot uses the installed `imagespec[datamatrix]` renderer.

## Using payloads in this integration

The `niimbot.print` action takes the element list in `data.payload`. Select the image entity belonging to your configured printer, or use its device target. With one loaded printer, an omitted target selects it; multiple printers require an explicit target. The action supports preview and printing through the same production `render_image` function. See the existing [actions](actions.md) and [examples](../examples/README.md) for the complete API.

Home Assistant prepares action templates before rendering. imagespec receives those resolved values; this integration does not provide a separate Jinja engine inside payload elements. Font lookup uses a basename in the integration's `fonts/` directory, then `/config/www/fonts/`; the default font is bundled `ppb.ttf`. The actual HA recorder history provider is passed to imagespec for history elements. Local/remote image and optional barcode requirements follow the installed imagespec guide; network access, external files and optional features are not exercised by the minimal example.

## Minimal working example

Open the complete [preview action](../examples/payload/minimal.yaml) in Developer tools → Actions. Replace `image.niimbot_label` with your printer's image entity. The example specifies a 240 × 96 px canvas and `preview: true`, so it renders the label without sending it to the printer. After inspecting the preview, set `preview: false` to print on a roll matching the dimensions. Wake the printer and close the NIIMBOT phone app first.

The contract loads the actual HA entry/action, resolves the YAML through HA and renders through the production path. It sends no device command and verifies pixels rather than physical label quality.

## Device output settings

Niimbot renders black and white (`#000000`, `#ffffff`) with a white default background. Whole-image dithering is disabled; supported photo/chart elements may request their own dither setting. Rotation uses `rotate_mode="image"`: 90°/270° swaps output width and height. The minimal example uses 0° and outputs 240 × 96 px, about 30 × 12 mm at 203 DPI. For the rotated D110 recipe see the existing D110 recipe in the [existing examples](../examples/README.md).

Explicit action width/height/rotate take precedence over cloud label dimensions; omitted values use successful online label lookup when enabled, otherwise the legacy 400 × 240 px and 0° defaults. Those defaults do not fit every roll. Choose the actual printer DPI, printhead width and roll dimensions in [label sizing](label-sizing.md). Device density and label type are validated for the detected model during printing.

## Supported features and limitations

Text, shapes, images, supported barcode/Data Matrix and recorder-backed history elements are provided by imagespec, subject to installed extras and available fonts/assets. This integration adds no universal color-printing support or font download service. A completed BLE transfer does not establish that scaling, margins or firmware behavior are correct. Model commands and print width estimates can vary; preserve the [device reference](devices.md) and existing examples when choosing dimensions.

Local contract verification uses a configured HA entry with no nearby printer and the bundled font. Live recorder histories, remote images, proxy firmware, physical printer output and every optional element require their own real data/device checks.

## Troubleshooting

For malformed payloads or incorrect output, inspect the action error and preview before retrying. See [device-specific troubleshooting](troubleshooting.md) and the existing [Issues](https://github.com/eigger/hass-niimbot/issues) path. Remove addresses, private label content and credentials before sharing logs or previews.
