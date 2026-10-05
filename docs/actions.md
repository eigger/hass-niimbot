# Actions

The integration provides `niimbot.print` and `niimbot.refresh_info`. Complete action examples are in [examples](../examples/README.md).

## `niimbot.print`

| Field | Required | Default | Description |
|---|---|---|---|
| `payload` | Yes | — | List of [imagespec elements](https://github.com/eigger/imagespec/blob/main/docs/elements.md) to render |
| `rotate` | No | `0` | Rotation in degrees: `0`, `90`, `180` or `270` |
| `width` | No | `400` px fallback | Render width; successful online label lookup can supply a default |
| `height` | No | `240` px fallback | Render height; successful online label lookup can supply a default |
| `density` | No | Model default | Uses the model's `densityDefault`; explicit values are validated against the model's supported range |
| `label_type` | No | Model default | Uses label type `1` when supported, otherwise the model's first supported type; successful online label lookup can supply a paper type |
| `copies` | No | `1` | Number of copies in the print job |
| `preview` | No | `false` | Render the label without sending it to the printer |

Enable **Fetch Label Info Online** and omit `width`, `height` and `label_type` to automatically use the loaded label's dimensions and paper type after a successful lookup. Explicit values override the lookup. The lookup dimensions already account for catalogue rotation; leave `rotate` at `0` unless you want an additional rotation.

Without a matching online lookup, the image size falls back to 400×240 pixels. This is a legacy rendering fallback, not a size selected for the printer or loaded label. For manual sizing, use `round(mm × DPI / 25.4)` and account for printable margins. Width and height must be between 10 and 1600 pixels; the [README model table](../README.md#supported-printers) and [print examples](../examples/README.md) show settings for specific label sizes.

Rotation uses label-printer mode: rotating by 90 or 270 degrees rotates the drawing and swaps the rendered width and height.

### Targeting printers

Target a printer device, one of its entities, or an area or label that contains printers. If there is only one configured printer, the target can be omitted. With multiple printers, specify a target.

The action can return a response to scripts and automations. A preview returns the rendered PNG as a `data:` URL in `image`; a printed job also includes the image and print result. When targeting multiple printers, the response is keyed by printer address and contains each result or error.

Every print and preview updates the printer's **Last Label Made** image entity.

## `niimbot.refresh_info`

Refresh cached printer settings and device information, including density, label type, auto shutdown and protocol information.

## Rendering, colors and fonts

Rendering is provided by [imagespec](https://github.com/eigger/imagespec); use its [element reference](https://github.com/eigger/imagespec/blob/main/docs/elements.md), [authoring guide](https://github.com/eigger/imagespec/blob/main/docs/authoring.md) and [dithering guide](https://github.com/eigger/imagespec/blob/main/docs/dithering.md) for payload syntax.

Niimbot labels render with a black-and-white palette. For photos and charts with colors outside that palette, set `dither` on the individual imagespec element; do not dither the whole label. See the [photo and chart example](../examples/photo-chart-dither.yaml).

The default font is `ppb.ttf`. Font lookup checks `custom_components/niimbot/fonts/` first, then Home Assistant's `www/fonts/`. The `plot` element reads entity history through Home Assistant Recorder.
