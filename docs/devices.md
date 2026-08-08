# Device Codes and Hardware Limits

Per-model reference for the `PrinterModelId` value returned by `PrinterInfo` key 8, together with the
hardware constraints that a client has to respect.

Related: [protocol.md](protocol.md) · [device-info.md](device-info.md) · [printing.md](printing.md) ·
[rfid.md](rfid.md)

## How to read this

- **Model ID** — the value from `PrinterInfo` key 8. Remember the single-byte responses need shifting;
  see [device-info.md](device-info.md#printermodelid-key-8). A model can have several IDs, and some IDs
  are shared by several models, so the ID alone does not uniquely identify hardware.
- **Density** — the range accepted by `SetDensity` (`0x21`). This integration asserts `1 <= n <= 5`, so
  the upper range of the 1–15 and 1–20 models is unreachable.
- **Label types** — the values accepted by `SetLabelType` (`0x23`). This integration always sends
  `1` (Gap) and asserts `1 <= n <= 3`, so 4, 5, 6, 10 and 11 cannot be sent.
- **RFID** — tag class; see [rfid.md](rfid.md#1-checking-support-first).
- **IDs in the 51xxx, 52xxx and 53xxx ranges** are rebadged third-party hardware that speaks a
  different protocol. The commands documented here do not apply to them.

Print width is given in millimetres, but the real per-row pixel limit is `printheadPixels` in
`niimprint/model.py`. The two do not always agree, so size images against `printheadPixels`.

## Models

| Model ID | Model | Series | DPI | Max width (mm) | Max length (mm) | Density | RFID | Label types | Other |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| (none) | D41 | D11 | 203 | 15 | 75 | 1-3 (default 2) | label | 1 Gap, 5 Transparent | - |
| (none) | D61 | D11 | 203 | 15 | 75 | 1-3 (default 2) | label | 1 Gap, 5 Transparent | - |
| (none) | Dxx | D11 | 203 | 15 | 200 | 1-3 (default 2) | label | 1 Gap, 5 Transparent | - |
| 256 | A8 | B3S | 203 | 75 | 200 | 1-5 (default 3) | none | 2 Black, 1 Gap, 3 Continuous | calibration |
| 256, 260, 262 | B3S | B3S | 203 | 75 | 200 | 1-5 (default 3) | none | 1 Gap, 2 Black, 3 Continuous, 5 Transparent | calibration |
| 256 | JCB3S | B3S | 203 | 75 | 200 | 1-5 (default 2) | none | 1 Gap, 2 Black, 3 Continuous, 5 Transparent | calibration |
| 261, 259, 258, 257 | S6 | B3S | 203 | 75 | 200 | 1-5 (default 3) | none | 1 Gap, 2 Black, 5 Transparent | calibration |
| 272 | B3S_P | B3S | 203 | 75 | 350 | 1-5 (default 3) | label | 1 Gap, 2 Black, 3 Continuous, 5 Transparent | calibration |
| 273 | A8_P | B3S | 203 | 75 | 200 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | calibration |
| 274 | S6_P | B3S | 203 | 75 | 200 | 1-5 (default 3) | label | 1 Gap, 5 Transparent | calibration |
| 512 | D11 | D11 | 203 | 15 | 100 | 1-3 (default 2) | label | 1 Gap, 5 Transparent | calibration |
| 512 | Hi-NB-D11 | D11 | 203 | 15 | 100 | 1-3 (default 2) | label | 1 Gap, 5 Transparent | calibration |
| 513 | Fust | D11 | 203 | 15 | 200 | 1-5 (default 3) | label | 1 Gap, 5 Transparent | - |
| 514 | D11S | D11 | 203 | 15 | 75 | 1-3 (default 2) | label | 1 Gap, 5 Transparent | - |
| 528 | D11_H | D11 | 300 | 15 | 200 | 1-5 (default 3) | label | 1 Gap, 5 Transparent | calibration |
| 531 | D11_Pro | D11 | 300 | 15 | 200 | 1-5 (default 3) | label | 5 Transparent, 1 Gap | calibration |
| 768 | B21 | B21 | 203 | 50 | 200 | 1-5 (default 3) | label | 1 Gap, 2 Black, 3 Continuous, 5 Transparent | calibration |
| 769 | B21-L2B | B21 | 203 | 50 | 200 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | calibration |
| 771, 775 | B21-C2B | B21 | 203 | 50 | 200 | 1-5 (default 3) | label | 1 Gap, 3 Continuous, 5 Transparent, 2 Black | calibration |
| 776 | B21S-C2B | B21 | 203 | 50 | 200 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | calibration |
| 777 | B21S | B21 | 203 | 50 | 200 | 1-5 (default 3) | label | 1 Gap, 2 Black, 3 Continuous, 5 Transparent | calibration |
| 785 | B21_Pro | B21 | 300 | 50 | 200 | 1-5 (default 3) | label | 1 Gap, 2 Black, 3 Continuous, 5 Transparent | calibration |
| 1024 | P1 | P1S | 300 | 80 | 150 | 1-5 (default 3) | ribbon | 6 PvcTag | - |
| 1025 | P1S | P1S | 300 | 87 | 150 | 1-5 (default 3) | ribbon | 6 PvcTag | - |
| 1026 | P18 | P1S | 300 | 87 | 150 | 1-5 (default 3) | ribbon | 6 PvcTag | - |
| 1792 | B16 | B16 | 203 | 15 | 100 | 1-3 (default 2) | label | 1 Gap, 5 Transparent | - |
| 2049 | B32 | B32 | 300 | 75 | 240 | 1-15 (default 10) | ribbon | 1 Gap, 5 Transparent | calibration |
| 2050 | B32R | B32 | 300 | 75 | 240 | 1-15 (default 10) | ribbon | 1 Gap | - |
| 2051 | Z401 | B32 | 300 | 75 | 240 | 1-15 (default 10) | ribbon | 1 Gap, 5 Transparent | calibration |
| 2053 | T8S | B32 | 300 | 75 | 120 | 1-15 (default 10) | none | 1 Gap | calibration |
| 2054 | A63 | B32 | 300 | 75 | 240 | 1-15 (default 10) | ribbon | 1 Gap, 5 Transparent, 2 Black | calibration |
| 2304, 2305 | D110 | D110 | 203 | 15 | 100 | 1-3 (default 2) | label | 1 Gap, 5 Transparent | - |
| 2305 | Hi-D110 | D110 | 203 | 15 | 100 | 1-3 (default 3) | label | 1 Gap, 5 Transparent | - |
| 2320 | D110_M | D110 | 203 | 15 | 100 | 1-5 (default 3) | label | 1 Gap, 5 Transparent | calibration |
| 2560 | D101 | D101 | 203 | 25 | 100 | 1-3 (default 2) | label | 1 Gap, 5 Transparent | - |
| 2561 | Betty | D101 | 203 | 25 | 200 | 1-3 (default 2) | label | 1 Gap, 5 Transparent | calibration |
| 2816 | B203 | B203 | 203 | 50 | 200 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | calibration |
| 2817 | A20 | B203 | 203 | 50 | 200 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | calibration |
| 2818 | A203 | B203 | 203 | 50 | 200 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | calibration |
| 3584 | B18 | B18/N1 | 203 | 15 | 120 | 1-3 (default 2) | label+ribbon | 1 Gap, 5 Transparent, 10 BlackMarkGap, 11 HeatShrinkTube, 3 Continuous | - |
| 3585 | B18S | B18/N1 | 203 | 15 | 120 | 1-3 (default 2) | label+ribbon | 1 Gap, 5 Transparent, 10 BlackMarkGap, 11 HeatShrinkTube, 3 Continuous | - |
| 3586 | N1 | B18/N1 | 203 | 15 | 120 | 1-3 (default 2) | label+ribbon | 1 Gap, 11 HeatShrinkTube, 5 Transparent, 10 BlackMarkGap, 3 Continuous | calibration |
| 3840 | H1 | H1 | 203 | 15 | 200 | 1-3 (default 2) | label | 1 Gap, 5 Transparent | calibration |
| 4096 | B1 | B1 | 203 | 50 | 200 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | calibration |
| 4097 | B1 Pro | B1 | 300 | 50 | 200 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | calibration |
| 4098 | B1 SE | B1 | 203 | 54 | 350 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | calibration |
| 4352 | H1S | H1S | 203 | 15 | 200 | 1-3 (default 2) | label | 1 Gap, 3 Continuous, 5 Transparent | calibration |
| 4608 | M2_H | M2 | 300 | 50 | 240 | 1-5 (default 3) | label+ribbon | 1 Gap, 5 Transparent, 2 Black, 10 BlackMarkGap | calibration |
| 4609 | TP2M_H | M2 | 300 | 50 | 240 | 1-5 (default 3) | label+ribbon | 1 Gap, 2 Black, 5 Transparent | calibration |
| 4610 | EP2M_H | M2 | 300 | 200 | 200 | 1-5 (default 3) | label+ribbon | 1 Gap, 5 Transparent, 2 Black, 10 BlackMarkGap | calibration |
| 4864 | K3 | K3 | 203 | 82 | 300 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | calibration |
| 4865 | K3_W | K3 | 203 | 82 | 300 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | WiFi, calibration |
| 4866 | MP3K | K3 | 203 | 82 | 300 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | calibration |
| 4867 | MP3K_W | K3 | 203 | 82 | 300 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | WiFi, calibration |
| 4868 | K3_ITD | K3 | 203 | 82 | 300 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | calibration |
| 5120 | C1 | C1 | 300 | 50 | 50 | 1-5 (default 3) | ribbon | 3 Continuous | calibration |
| 5121 | EP1C | C1 | 300 | 50 | 50 | 1-5 (default 3) | ribbon | 3 Continuous | calibration |
| 5376 | ET10 | ET10 | 203 | 200 | 200 | 3-3 (default 3) | none | 3 Continuous | - |
| 5632 | B31 | B31 | 203 | 77 | 350 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | calibration |
| 6144 | K2 | K2 | 203 | 60 | 300 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | calibration |
| 6400 | M3 | M3 | 300 | 78 | 350 | 1-5 (default 3) | label+ribbon | 1 Gap, 5 Transparent, 2 Black, 10 BlackMarkGap | calibration |
| 6402 | EP3M | M3 | 300 | 78 | 350 | 1-5 (default 3) | label+ribbon | 1 Gap, 5 Transparent, 2 Black, 10 BlackMarkGap | calibration |
| 6656 | B4 | B4 | 203 | 108 | 350 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | calibration |
| 6657 | B4 Pro | B4 | 300 | 108 | 350 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | WiFi, calibration |
| 6912 | B2 Pro | B2 | 300 | 200 | 200 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | calibration |
| 6913 | B2 | B2 | 203 | 50 | 200 | 1-5 (default 3) | label | 1 Gap, 2 Black, 5 Transparent | calibration |
| 7168 | K4 | K3 | 203 | 82 | 300 | 1-15 (default 7) | label | 1 Gap, 2 Black, 5 Transparent | cutter, calibration |
| 7424 | A1 Pro | B18/N1 | 300 | 15 | 120 | 1-5 (default 3) | none | 4 Perforated, 3 Continuous | calibration |
| 51457 | B11 | B11 | 203 | 50 | 200 | 6-15 (default 10) | none | 1 Gap, 2 Black, 3 Continuous, 4 Perforated, 5 Transparent | - |
| 51458 | S1 | B11 | 203 | 50 | 200 | 6-15 (default 10) | none | 1 Gap, 2 Black, 3 Continuous, 4 Perforated | - |
| 51460 | S3 | B11 | 203 | 50 | 200 | 6-15 (default 10) | none | 1 Gap, 2 Black, 3 Continuous, 4 Perforated | - |
| 51461 | JC-M90 | B11 | 203 | 50 | 200 | 6-15 (default 10) | none | 1 Gap, 2 Black, 3 Continuous, 4 Perforated | - |
| 51713 | B50 | B50 | 203 | 50 | 200 | 6-15 (default 10) | none | 1 Gap, 2 Black, 3 Continuous, 4 Perforated | - |
| 51714 | B50W | B50 | 203 | 50 | 200 | 6-15 (default 10) | none | 1 Gap, 2 Black, 3 Continuous, 4 Perforated | - |
| 51715 | T6 | B50 | 203 | 50 | 200 | 6-15 (default 10) | none | 1 Gap, 2 Black, 3 Continuous, 4 Perforated | - |
| 51717 | T7 | B50 | 203 | 50 | 200 | 6-15 (default 10) | none | 1 Gap, 2 Black, 3 Continuous, 4 Perforated | - |
| 51718 | T8 | T8 | 300 | 50 | 200 | 6-15 (default 10) | none | 1 Gap, 2 Black, 3 Continuous, 4 Perforated | - |
| 52993 | B3 | B3 | 203 | 75 | 200 | 1-5 (default 3) | none | 1 Gap, 2 Black, 3 Continuous, 5 Transparent | calibration |
| 53250 | T2S | T2 | 203 | 107 | 280 | 1-20 (default 15) | none | 1 Gap, 2 Black | - |

## Models missing from `model.py`

`modelsLibrary` in `niimprint/model.py` does not cover these IDs, so they resolve to `UNKNOWN`.
`UNKNOWN` is routed to the old D11 print sequence
([printing.md](printing.md#old-d11-generation)), which is wrong for all of them — expect failed or
blank prints.

| Model ID | Model |
| --- | --- |
| 257, 258, 259 | S6 (only 261 is registered) |
| 3840 | H1 |
| 4098 | B1 SE |
| 4352 | H1S |
| 4610 | EP2M_H |
| 4868 | K3_ITD |
| 5120 / 5121 | C1 / EP1C |
| 6144 | K2 |
| 6400 / 6402 | M3 / EP3M |
| 6656 / 6657 | B4 / B4 Pro |
| 7168 | K4 |
| 7424 | A1 Pro |

Going the other way, `model.py` carries one ID that no longer appears in current model listings:
`784` (B21_H). `785` (B21_Pro) occupies that slot instead.

