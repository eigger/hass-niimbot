# Label sizing

## Verified printer examples

These representative models have been verified. Sizes below are **manual action settings for the example label**, not fixed sizes for every roll.

| Model | Resolution | Label example | `width` | `height` | `rotate` | Density (default) |
|---|---|---|---|---|---|---|
| B1 | 203 DPI | 40×30 mm | `320` | `240` | `0` | 1–5 (3) |
| B1 Pro | 300 DPI | 40×30 mm | `472` | `354` | `0` | 1–5 (3) |
| B2 Pro | 300 DPI | 40×30 mm | `472` | `354` | `0` | 1–5 (3) |
| B21 Pro | 300 DPI | 40×30 mm | `472` | `354` | `0` | 1–5 (3) |
| D110 | 203 DPI | 30×12 mm | `240` | `96` | `90` | 1–3 (2) |

For other label sizes, calculate pixels with `round(mm × DPI / 25.4)` and allow for the label's printable margins. `width` and `height` describe the canvas before rotation; `90` or `270` swaps the output dimensions. The [D110 example](../examples/d110.yaml) renders 240×96 px and sends a 96×240 px image.

**Automatic label sizing:** Enable **Fetch Label Info Online** in the integration options. Once **Cloud Label Info** has successfully resolved the loaded label, omit `width`, `height` and `label_type` from the print action to use that label's dimensions and paper type automatically. The lookup already accounts for the catalogue orientation; leave `rotate` at `0` unless you want to rotate the content further. Explicit action values override the lookup. If lookup is unavailable, the size falls back to `400×240` px; this legacy fallback is not a universal label size.

See the [device reference](devices.md) for the full model list and supported label types, and [Actions](actions.md) for sizing and rotation.

