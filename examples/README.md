# Examples

Copy an example and replace its target with your Niimbot printer. The photo example also needs a reachable image URL in place of `https://example.com/photo.jpg`. Image sizes should fit the printer's label; see the [device reference](../docs/devices.md). Shared layout and element fields are documented by [imagespec](https://github.com/eigger/imagespec/blob/main/docs/elements.md).

| Example | Use |
|---|---|
| [Basic text and QR](basic-text-qr.yaml) | First print action |
| [Preview](preview.yaml) | Render without printing |
| [Multiline address](multiline-address.yaml) | Fit templated text in a label |
| [D110](d110.yaml) | Small label with 90° rotation |
| [B21 Pro](b21-pro.yaml) | Wide, high-density label |
| [Photo and chart dithering](photo-chart-dither.yaml) | Apply dithering per media element |
| [Dashboard preview](dashboard-preview/README.md) | Show the last rendered label on a dashboard |
| [Grocy](grocy/README.md) | Print a product label from a Grocy webhook |

For Bluetooth proxy setup, see [Setup](../docs/setup.md#bluetooth-connection). For the print action fields and defaults, see [Actions](../docs/actions.md).
