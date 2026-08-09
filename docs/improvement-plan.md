# Implementation Plan: Sensors and Print Pipeline

Derived from the protocol reference in [protocol.md](protocol.md), [device-info.md](device-info.md),
[printing.md](printing.md), [rfid.md](rfid.md) and [devices.md](devices.md), compared against the
current implementation.

Baseline: `master` at version 3.0.0. The original plan was written against 2.3.1; phases 1 and 2 and
most of 3 and 4 have since landed, so what follows records what shipped and keeps only the work that
is still open. New findings from the app decompile live in
[app-gap-analysis.md](app-gap-analysis.md) and are referenced rather than repeated.

## Status

| Phase | Status |
| --- | --- |
| 1 Correctness | **Done** |
| 2 RFID sensors | **Done**, label and ribbon |
| 3 Device info | Mostly done — 3.3 open |
| 4 Print pipeline | Mostly done — the adaptive half of 4.6 open |
| 5 Model coverage | 5.3 / 5.4 done; **5.1 and 5.2 open** |

Items marked **[HW]** cannot be validated without a physical printer. Implement them behind the
existing model/capability checks, keep the previous behaviour as fallback, and list them for the
maintainer to confirm.

---

## Shipped in 3.0.0

Recorded briefly, since the reasoning behind each is in the docs linked above and the code is the
authority now.

**Phase 1 — correctness.** `_battery_percentage` tolerates a missing `powerlevel`; `_transceive`
raises `PrinterTimeout` instead of returning `None` and shares one time budget across its retries
with a 5 s default; the heartbeat accepts `0xDD`, `0xDE`, `0xDF` and `0xD9` and dispatches parsing on
the response code; `_parse_rfid_payload` tests the payload length and treats `capacity` as optional;
`paperstate` uses the `inverted` flag; the dead commented blocks are gone.

**Phase 2 — consumables.** `PrinterModelMeta` carries `rfid`, `densityMin/Max/Default`. Both tags are
read (`0x1A` and `0x1C`) behind the capability gate, with the previous values retained on a failed
read. Remaining / Used / Total / Usage / SKU / Type / UUID exist for label and ribbon, `serial` and
`capacity` ride as attributes, and a changed UUID fires `niimbot_roll_changed`.

**Phase 3 — device info.** `PrinterInfo` keys 1, 2, 3, 7, 10 and 15 are read once and cached, with a
`niimbot.refresh_info` service to re-read. Battery prefers key 10 and exposes the raw bucket.
`PrinterStatusData` (`0xA5`) feeds Protocol Version and Colour Support. Last Error and live Print
Progress exist.

**Phase 4 — print pipeline.** Identical rows coalesce through `repeats`; rows with ≤ 6 black pixels go
out as `PrintBitmapRowIndexed` (`0x83`); counter bytes follow the split/total rule keyed on
`printheadPixels`; completion drains `0xE0` first and keeps the `0xA3` poll as fallback; `copies` is a
print-service parameter; `PrinterCheckLine` (`0x86`) runs every 200 rows; the client and its
notification subscription are held for the lifetime of the connection under `keep_connection`.
Defaults moved to 10 ms between rows and a confirmation every 16 rows.

**Phase 5 — partial.** Density validates against the model's range, `label_type` is a service
parameter, and entity creation is driven by capability rather than by whatever the first refresh
happened to contain.

---

## Open work

Ordered by value per unit of risk. The first two need no hardware. Each item has a corresponding task
order — files, exact change, tests, acceptance criteria — in [work-plan.md](work-plan.md).

### 1. Material codes for `type` — **Done (T1)** — [rfid.md §4](rfid.md#4-consumable-type-code-type)

`material_name()` maps the RFID `type` byte through the 37-value material enumeration for `consumable_type` and `ribbon_type` sensors. `PrinterInfo` key 3 remains the authoritative `labeltype`.

**[HW]** The material reading is inference until a tag returns a value above 11. Black-mark stock made
of plain thermal paper settles it — see the test described in rfid.md.

### 2. Advanced2 heartbeat sensors — **Done (T2)** (was 3.3)

`_parse_heartbeat_advanced2` returns six extra fields when parsed. Surfaced as diagnostic sensors and binary sensors when present in the heartbeat payload:

| Entity | Platform | Notes |
| --- | --- | --- |
| Print Head Temperature | sensor | Diagnostic, raw value (unit unconfirmed) |
| Ribbon Loaded | binary_sensor | `0` means inserted |
| Ribbon RFID Readable | binary_sensor | non-zero means success |
| WiFi Signal | sensor | `SIGNAL_STRENGTH`, dBm, diagnostic |
| Voltage State | sensor | diagnostic, raw, disabled by default |
| Lighting Error Code | sensor | diagnostic, raw, disabled by default |

Entities are created dynamically only when the Advanced2 payload provides the value, leaving protocol-v1/v2 hardware unaffected. **[HW]** all six — no Advanced2 device has been observed by this project.

### 3. The 14 missing model IDs — **Done (T3)** (was 5.1)

All 14 model IDs (3840, 4098, 4352, 4610, 4868, 5120, 5121, 6144, 6400, 6402, 6656, 6657, 7168, 7424) added to `PrinterModel`, `modelsLibrary`, and `_CAPABILITIES_BY_ID`. `printheadPixels` uses estimated values from same-series siblings and DPI pixel ratios, flagged with `printheadPixelsEstimated: True` with warning logging on print jobs. **[HW]** per model; A1 Pro print direction 270 is modelled as LEFT.

### 4. Choose the print sequence from capability, not a model list — **Done (T4)** (was 5.2)

`print_image` dispatches on hardcoded model tuples, so every new model needs a code change in the
right branch and an unlisted model falls through to `print_image_b1` — or, for `UNKNOWN`, to the
oldest sequence. Move the generation into `PrinterModelMeta` and prefer the protocol version from
`PrinterStatusData`, which is already read, so an unknown model picks a sane default instead of the
worst one.

The method names do not line up with [printing.md](printing.md#4-print-sequences) and should be
renamed in the same change:

| Method | Actually implements |
| --- | --- |
| `print_image_d11_v1` | Old D11 |
| `print_image_d110` | D110 |
| `print_image_b1` | V4 (`start_print_v4` + 6-byte `SetPageSize`) |
| `print_image_d110m_v4` | V5 / 9-byte (`start_print_9b` + 9-byte `SetPageSize`) |

### 5. Gate RFID reads on firmware version — **Done (T5)**

The vendor table lists, per model, the firmware versions on which RFID reading does not work
([app-gap-analysis.md §A4](app-gap-analysis.md#a4-firmware-version-gated-capabilities-are-ignored)).
`SOFTVERSION` is already read and formats back to exactly those strings as `f"{major}.{minor:02d}"`.
On an affected unit every poll currently spends a full read timeout on a command that cannot be
answered.

### 6. Printer actions still missing

All are single commands with a documented response; the work is the entity and the confirmation flow,
not the protocol. **[HW]** each — they move paper.

| Command | Entity | Why |
| --- | --- | --- |
| `0x8E` LabelPositioningCalibration | button | The app's paper calibration; most-requested printer action |
| `0x59` CalibrateHeight | button | Roll feed calibration |
| `0xDA` CancelPrint | button | No way to stop a bad job today |
| `0x28` PrinterReset | button | Needs a confirmation step |
| `0x5A` PrintTestPage | button | Trivial |
| `0x07` PrinterConfig2 | service | Carries set-time; clock drift affects date elements |
| `0x40` key 14 PrintMode | sensor | Pairs with the material table in item 1 |

### 7. Enforce `paperTypes` (rest of 5.3)

`label_type` is validated as 1–11 but not against the model's own `paperTypes`, so an unsupported
value reaches the printer and returns `SetPrintLabelMaterialNoSupport`. Validate locally and default
to the model's first entry rather than a hardcoded `1`.

### 8. Adaptive flow control (rest of 4.6)

Defaults are now 10 ms and confirm-every-16. The second half — measuring per-write latency from
`PrinterClient._timings` and adapting the batch size during the page, backing off when latency rises —
is not done. Start conservative and only widen.

---

## Explicitly not planned

With reasoning in [app-gap-analysis.md](app-gap-analysis.md):

- **Firmware update over BLE.** The protocol is documented, but the image is behind an authenticated
  cloud API, a mid-transfer BLE dropout is a realistic HA failure and is not recoverable from HA, and
  the app itself restricts the operation to Bluetooth. Section C of the gap analysis.
- **Firmware "latest version" check.** No public version feed exists; the only source is the same
  authenticated API. Use the version we already read for capability gating (item 5) instead.
- **Cloud label catalogue as a default.** Optional and off by default at most — section B of the gap
  analysis. Do the offline enrichment in item 1 first; it covers most of the value.
- **WiFi / MQTT transport, cutter support, greyscale and two-colour printing, print margins.**
  Separate projects, each larger than everything above.

---

## Testing notes

`tests/` covers rendering, packet encoding, the phase-1 protocol fixes and the print-protocol extras.
A fake transport that records written packets and replays canned responses already exists in
`tests/fake_transport.py`; new protocol work should extend it rather than mocking `PrinterClient`.

Worth adding as the items above land:

- Material-code rendering for `type`, including a value above 11 and an unknown code.
- Advanced2 heartbeat payloads at each length boundary (9, 11, 13, 14 bytes).
- Sequence assertions per generation — that the 9-byte path omits `PageStart` and injects the
  fire-and-forget heartbeat, that the Old D11 path sends `PrintClear` and a height-only `SetPageSize`.
- Firmware-version gating: an affected version skips `RfidInfo` entirely.

## Items needing hardware confirmation

| Item | What to check |
| --- | --- |
| 1 | Whether `type` is a label type or a material code — black-mark stock on plain thermal paper, compared against `PrinterInfo` key 3 |
| 1 | Whether `capacity / total_len` is the label pitch, against a roll of known size |
| 2 | Whether any available printer answers `0xD9`; temperature unit and scale |
| 3 | `printheadPixels` and print direction for the 14 added models; whether direction 270 differs from 90 |
| 6 | Every action command, on hardware that can be reset and recalibrated |
| — | Units of `total_len` on a known roll (label count vs length) |
| — | `Print Area` (key 15) payload layout |
