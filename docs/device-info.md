# Device Information Protocol

How to identify a printer and read its live state. Framing and the command ID table are in
[protocol.md](protocol.md).

## 1. Connect handshake (`0xC1`)

**(not implemented here)** — this integration relies on the BLE GATT connection alone and never sends
`Connect`.

`Connect` is the only command whose framed packet is prefixed with an extra `0x03` byte:

```
03 55 55 C1 01 01 C1 AA AA
```

The response is `0xC2` with a single status byte:

| Value | Meaning |
| --- | --- |
| 0 | Disconnected |
| 1 | Connected |
| 2 | Connected, newer protocol |
| 3 | Connected, protocol v3 |
| 90 | Firmware errors |

## 2. Protocol version (`PrinterStatusData`, `0xA5`)

Implemented in `PrinterClient.get_printer_status_data`; feeds the Protocol Version and Colour Support
diagnostic sensors.

Send `01`, response is `0xB5`. When the payload is longer than 12 bytes:

| Offset | Size | Field |
| --- | --- | --- |
| 10 | 1 | Colour support flag |
| 11 | 1 | Version high part |
| 12 | 1 | Version low part |

The version number is `data[11] * 100 + data[12]`, then bucketed:

| Computed value | Protocol version |
| --- | --- |
| 204 – 299 | 3 |
| 300 – 301 | 4 |
| ≥ 302 | 5 |
| otherwise | 0 |

This matters because the protocol version selects which heartbeat variant the printer answers
(section 4) and which print sequence it expects ([printing.md](printing.md)).

## 3. Printer info (`0x40`)

One byte of payload selects the field. The response command ID is `0x40 + key`, so each field has its
own response ID — a client can therefore tell responses apart even if they arrive out of order.

| Key | Response | Field | Payload parsing |
| --- | --- | --- | --- |
| 1 | `0x41` | Density | `u8` |
| 2 | `0x42` | Speed | `u8` |
| 3 | `0x43` | LabelType | `u8`, values in [protocol.md](protocol.md#6-label-types-setlabeltype-0x23) |
| 6 | `0x46` | Language | `u8` |
| 7 | `0x47` | AutoShutdownTime | `u8` 1–4 |
| 8 | `0x48` | PrinterModelId | 1 byte → `data[0] << 8`; 2 bytes → `u16` |
| 9 | `0x49` | SoftwareVersion | 2 bytes, format varies (below) |
| 10 | `0x4A` | BatteryChargeLevel | `u8` 0–4 |
| 11 | `0x4B` | SerialNumber | length-dependent (below) |
| 12 | `0x4C` | HardwareVersion | 2 bytes, format varies (below) |
| 13 | `0x4D` | BluetoothAddress | MAC in reverse byte order. **(not implemented here)** |
| 14 | — | PrintMode | **(not implemented here)** |
| 15 | `0x4F` | Area | Printable area. Parsed best-effort into the Print Area sensor; layout unconfirmed |

Keys 4 and 5 are unused.

### PrinterModelId (key 8)

This is the value used throughout [devices.md](devices.md) to look up DPI, print width, density range
and RFID support.

The single-byte case must be shifted, not used directly:

```python
if len(data) == 1:
    model_id = data[0] << 8      # 0x02 -> 512 (D11), not 2
else:
    model_id = int.from_bytes(data[:2], "big")
```

Getting this wrong silently selects the wrong print sequence, which usually shows up as a blank label
rather than an error.

### SoftwareVersion / HardwareVersion (keys 9, 12)

Two bytes, but **the format is not consistent across models.** Two readings are plausible:

```python
v1 = data[0] + data[1] / 100          # 03 1D -> 3.29
v2 = (data[0] * 256 + data[1]) / 100  # 03 1D -> 7.81
```

This integration uses `v1`. There is no known way to tell from the response alone which one a given
model means, so treat the version as a display string and avoid arithmetic comparisons against it.

### SerialNumber (key 11)

Parsing depends on the payload length:

| Length | Interpretation |
| --- | --- |
| < 4 | No serial available, report `-1` |
| ≥ 8 | ASCII string |
| 4 – 7 | Hex of the first 4 bytes, uppercase |

### BatteryChargeLevel (key 10)

A coarse bucket, not a percentage:

| Value | Charge |
| --- | --- |
| 0 | 0 % |
| 1 | 25 % |
| 2 | 50 % |
| 3 | 75 % |
| 4 | 100 % |

### AutoShutdownTime (key 7)

An index, not minutes. The mapping is model-dependent:

| Value | Typical |
| --- | --- |
| 1 | 15 min |
| 2 | 30 min |
| 3 | 45 or 60 min |
| 4 | 60 min or never |

Write it back with `SetAutoShutdownTime` (`0x27`). Exposed as the Auto Shutdown select entity.

## 4. Heartbeat (`0xDC`)

The heartbeat carries everything worth polling: lid, battery, paper, ribbon, RFID readiness.

### Request types

The single payload byte selects a variant, and each variant has its own response ID:

| Payload | Type | Response ID |
| --- | --- | --- |
| `01` | Advanced1 | `0xDD` |
| `02` | Basic | `0xDE` |
| `03` | Unknown | `0xDF` |
| `04` | Advanced2 | `0xD9` |

Use Advanced2 (`04`) on printers reporting protocol version ≥ 3, Advanced1 (`01`) otherwise.

**This integration always sends `01` and only matches `0xDD`.** On a protocol-v3+ printer that
answers `0xD9`, the reply is discarded and the heartbeat times out. That is the likeliest cause of
missing status on newer models.

### Advanced1 response (`0xDD`)

Field offsets depend on the payload length. Everything before the listed offsets is unparsed.

| Length | Lid | Battery | Paper | Paper RFID |
| --- | --- | --- | --- | --- |
| 10 | `data[8]` | `data[9]` | — | — |
| 13 | `data[9]` | `data[10]` | `data[11]` | `data[12]` |
| 19 | `data[15]` | `data[16]` | `data[17]` | `data[18]` |
| 20 | — | — | `data[18]` | `data[19]` |

Polarity is not uniform across fields:

| Field | Convention |
| --- | --- |
| Lid | `0` means **closed** |
| Paper | `0` means **inserted** |
| Paper RFID | non-zero means **read succeeded** |

Length 9 is not part of the variants above, but this integration also accepts it and reads the lid
from `data[8]`.

### Models with inverted lid state

On these model IDs the lid bit is reversed and must be flipped after parsing:

```
272, 273, 274, 512, 513, 514, 1792, 2304, 2560, 3584, 3840, 4352, 5120
```

B3S_P, A8_P, S6_P, D11, Fust, D11S, B16, D110, D101, B18, H1, H1S, C1.

### Advanced2 response (`0xD9`)

Parsed by `PrinterClient._parse_heartbeat_advanced2`. From Task T2, temperature, ribbon state, WiFi RSSI,
voltage and lighting error are surfaced as diagnostic sensors and binary sensors when present.

A fixed layout with optional trailing fields, minimum 9 bytes. Much richer than Advanced1 — it is the
only variant that reports temperature and ribbon state.

| Offset | Size | Field | Convention |
| --- | --- | --- | --- |
| 0 | 2 | (unparsed) | |
| 2 | 1 | Battery charge level | 0–4 |
| 3 | 1 | Temperature | |
| 4 | 1 | Lid | `0` = closed |
| 5 | 1 | Paper | `0` = inserted |
| 6 | 1 | Paper RFID read | non-zero = success |
| 7 | 1 | Ribbon RFID read | non-zero = success |
| 8 | 1 | Ribbon | `0` = inserted |
| 9 | 2 | WiFi RSSI | if present |
| 11 | 1 | (skipped) | if present |
| 12 | 1 | Lighting error code | if present |
| 13 | 1 | Voltage state | if present |

The inverted-lid list does **not** apply here.

## 5. Print status (`0xA3`)

Send `01`, response is `0xB3`. Payload can be 4, 8 or 10 bytes; the first 4 are always the same.

```
+-----------+--------------------+-------------------+
| page: u16 | pagePrintProgress  | pageFeedProgress  |
+-----------+--------------------+-------------------+
```

| Field | Range | Meaning |
| --- | --- | --- |
| `page` | 0–n | Pages completed |
| `pagePrintProgress` | 0–100 | Imaging progress of the current page |
| `pageFeedProgress` | 0–100 | Feed-out progress of the current page |

On a 10-byte payload, `data[6]` is an error flag; non-zero means the job failed and the value is a
code from [protocol.md section 5](protocol.md#5-print-error-codes-0xdb).

Some models report `pageFeedProgress` as `0` even when finished. Taking the maximum of the two
non-zero values is the portable reading, which is what this integration does — it collapses both into
a single `progress` value and therefore cannot distinguish "imaging done" from "fully ejected".

## 6. Sound settings (`0x58`)

One command does both get and set. Payload is always 3 bytes:

```
+----------+------+-------+
| category | item | value |
+----------+------+-------+
```

| Category | Meaning |
| --- | --- |
| `0x01` | Set |
| `0x02` | Get state |

| Item | Sound |
| --- | --- |
| `0x01` | Bluetooth connection beep |
| `0x02` | Power on/off beep |

For a set, `value` is `0` or `1`. For a get, send `value = 1` and read the state from `data[2]` of the
`0x68` response. This integration implements get and set for the Bluetooth connection beep via the
Connection Sound switch.

## 7. Other state commands

**(not implemented here)** — listed so they are not mistaken for gaps in the protocol.

| Command | ID | Notes |
| --- | --- | --- |
| PrinterReset | `0x28` | Clears settings such as sound. Response `0x38` |
| CalibrateHeight | `0x59` | Response `0x69` |
| LabelPositioningCalibration | `0x8E` | Response `0x8F`, `data[0] == 1` on success. Values 1–2 make B1 eject roughly 15 cm of paper |
| PrintTestPage | `0x5A` | Response `0x6A` |
| PrinterLog | `0x05` | Response `0x06` |
| GetKeyFunction | `0x09` | Hardware button mapping, response `0x0A` |
| GetPrintQuality | `0x0D` | Request and response share the ID |
| GetCurrentTimeFormat | `0x12` | Response `0x11` |
| AntiFake | `0x0B` | Genuine-consumable check. `01` long form, `02` short form. Response `0x0C` |

## 8. What this integration exposes

Read at every coordinator refresh:

| Entity source | Command |
| --- | --- |
| Model, serial, software/hardware version | `PrinterInfo` keys 8, 11, 9, 12 |
| Battery level | `PrinterInfo` key 10 |
| Lid closed, paper present, RFID readable | `Heartbeat` Advanced1 |

Known gaps:

- Heartbeat Advanced2 is never requested, so temperature, ribbon state, WiFi RSSI and voltage are
  unavailable even on models that report them.
- `PrinterStatusData` (`0xA5`) is never sent, so protocol version and colour support are unknown, and
  the print sequence is chosen from the model ID table instead.
- `pageFeedProgress` is merged into a single progress value.
- RFID tag contents are read by `get_rfid()` but not surfaced as entities. See [rfid.md](rfid.md).
