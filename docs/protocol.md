# NIIMBOT Bluetooth Protocol

Transport, packet framing and the full command ID table for NIIMBOT label printers.

| Document | Contents |
| --- | --- |
| **protocol.md** (this file) | Transport, packet framing, command ID tables |
| [device-info.md](device-info.md) | Connect handshake, printer info, heartbeat, status |
| [printing.md](printing.md) | Image encoding, print sequences, completion detection |
| [rfid.md](rfid.md) | Reading consumable info from RFID tags |
| [devices.md](devices.md) | Per-model codes and hardware limits |

## Status of this document

Everything with a concrete byte value is either implemented and verified in this integration
(`custom_components/niimbot/niimprint/`) or comes from the
[niimblue / niimbluelib](https://github.com/MultiMote/niimbluelib) reverse-engineering effort.

Commands that this integration does not implement are marked **(not implemented here)**. They are
documented because they are part of the same protocol and useful when extending the integration.

There is no single unified protocol. A common framing layer carries a command set that drifted
across hardware generations, so payload lengths and required sequences differ per model family. Where
that matters it is called out explicitly.

## 1. Transport

| Item | Value |
| --- | --- |
| Service UUID | `e7810a71-73ae-499d-8c15-faa9aef0c3f2` |
| Characteristic UUID | `bef8d6c9-9c21-4c9e-b632-bd58c1009f9f` |
| Direction | A single characteristic used for both write and notify |

Requests are GATT writes to that characteristic; responses arrive as notifications on the same
characteristic. There is no separate read characteristic.

Some older models expose classic Bluetooth SPP instead of BLE. The framing is identical, only the
transport differs. This integration implements BLE only.

### Receiving is not one-notification-per-packet

The printer does not align packets to notifications:

- Several packets can arrive in a single notification.
- One packet can be split across several notifications.
- Unsolicited packets (`0xD3`, `0xE0`) appear in the middle of a request/response exchange.

So notification data must be appended to a rolling buffer, and packets cut out of it by scanning for
the `55 55` header and using the length field. Overwriting the buffer on each notification loses
responses and desynchronises everything after it.

`BLETransport._notification_handler` accumulates, and `PrinterClient._recv` resynchronises by
searching for the next `55 55` and discarding leading garbage.

### Write flow control

Bitmap row commands (`0x83`, `0x84`, `0x85`) expect no response. Sending all of them as
write-without-response floods the link and drops packets; sending all of them as
write-with-response makes printing extremely slow. This integration sends
write-with-response once every `print_line_batch_size` rows and idles
`wait_between_print_lines` between rows. Both are user-configurable.

## 2. Packet framing

```
+------+------+------+------+-----------+------+------+------+
| 0x55 | 0x55 | cmd  | len  | data[len] | bcc  | 0xAA | 0xAA |
+------+------+------+------+-----------+------+------+------+
```

| Field | Size | Description |
| --- | --- | --- |
| Head | 2 | Always `55 55` |
| `cmd` | 1 | Request command ID, or response command ID |
| `len` | 1 | Length of `data`, max 255 |
| `data` | `len` | Payload. All multi-byte integers are **big-endian** |
| `bcc` | 1 | Checksum |
| Tail | 2 | Always `AA AA` |

Checksum is the XOR of `cmd`, `len` and every payload byte:

```python
bcc = cmd ^ len(data)
for b in data:
    bcc ^= b
```

Total packet size is always `len + 7`. That relation is what lets a receiver find packet boundaries.

### Connect packet exception

The `Connect` request (`0xC1`) is sent with an extra `0x03` byte prepended to the **entire framed
packet**, before the `55 55` head. No other command does this.

```
03 55 55 C1 01 01 C1 AA AA
```

### CRC32 framing variant

Firmware upload uses a different frame: a 16-bit chunk number after the command, and a 32-bit CRC32
instead of the 1-byte XOR.

```
+------+------+------+-------------+------+-----------+----------+------+------+
| 0x55 | 0x55 | cmd  | chunk: u16  | len  | data[len] | crc: u32 | 0xAA | 0xAA |
+------+------+------+-------------+------+-----------+----------+------+------+
```

The CRC32 is computed over `cmd`, the two chunk-number bytes, `len` and the payload. Used only by the
firmware commands in section 4.6. **(not implemented here)**

## 3. Request / response pairing

Most requests get exactly one response whose command ID is a fixed function of the request ID. There
is no sequence number, so an implementation has to match on the response ID and tolerate unsolicited
packets arriving in between.

The mapping is **not a uniform offset**. Roughly:

| Pattern | Examples |
| --- | --- |
| `+1` | `0x01`→`0x02`, `0x03`→`0x04`, `0x13`→`0x14`, `0x1A`→`0x1B`, `0xE3`→`0xE4`, `0xF3`→`0xF4` |
| `+16` (`0x10`) | `0x20`→`0x30`, `0x21`→`0x31`, `0x23`→`0x33`, `0x27`→`0x37`, `0x28`→`0x38`, `0x54`→`0x64`, `0x58`→`0x68`, `0x59`→`0x69`, `0x5A`→`0x6A`, `0xA3`→`0xB3`, `0xA5`→`0xB5` |
| Info request | `0x40` → `0x40 + key` |
| Irregular | `0x05`→`0x06`, `0x07`→`0x08`, `0x09`→`0x0A`, `0x0B`→`0x0C`, `0x12`→`0x11`, `0x86`→`0xD3`, `0x8E`→`0x8F`, `0xA2`→`0xB2`, `0xAF`→`0xBF`, `0xC1`→`0xC2`, `0xDA`→`0xD0` |

`Heartbeat` (`0xDC`) is the one request with **four** possible response IDs, selected by its payload.
See [device-info.md](device-info.md#4-heartbeat-0xdc).

Because of the irregular cases, treating the response ID as `request + offset` only works for the
subset a given client implements. This integration hardcodes the offset per command.

### Error and unsolicited responses

| Response ID | Meaning |
| --- | --- |
| `0x00` | Command not supported by this model or firmware |
| `0xDB` | Print error. `data[0]` is the error code (section 5) |
| `0xD3` | `PrinterCheckLine` response. Also emitted spontaneously by some models after `PageEnd` |
| `0xE0` | Page index notification. Emitted spontaneously as pages complete; `data` is a `u16` page number |
| `0xC6` | Reset timeout. Seen immediately before `0xD3` |

`0xDB` can arrive in response to a request that is merely out of order — for example `SetPageSize`
sent before the page was started — not only for physical faults.

## 4. Command IDs

### 4.1 Print flow

| Request | Name | Response | Payload | Notes |
| --- | --- | --- | --- | --- |
| `0x01` | PrintStart | `0x02` | 1 / 2 / 7 / 9 bytes | Variant depends on generation |
| `0x03` | PageStart | `0x04` | `01` | Omitted on 9-byte-generation models |
| `0x13` | SetPageSize | `0x14` | 2 / 4 / 6 / 9 / 13 bytes | Page geometry |
| `0x15` | PrintQuantity | `0x16` | `u16` | Copies. Not used when copies are in `SetPageSize` |
| `0x20` | PrintClear | `0x30` | `01` | Allow print buffer clear. Old D11 generation only |
| `0x83` | PrintBitmapRowIndexed | none | see [printing.md](printing.md) | Coordinate-list row. Only when ≤ 6 black pixels |
| `0x84` | PrintEmptyRow | none | `u16` row + `u8` count | Skip up to 255 blank rows |
| `0x85` | PrintBitmapRow | none | header + row bytes | Bitmap row |
| `0x86` | PrinterCheckLine | `0xD3` | `u16` line + `01` | Mid-transfer checkpoint, every 200 rows |
| `0xE3` | PageEnd | `0xE4` | `01` | |
| `0xF3` | PrintEnd | `0xF4` | `01` | `data[0] == 0` means refused |
| `0xDA` | CancelPrint | `0xD0` | `01` | **(not implemented here)** |

### 4.2 Settings

| Request | Name | Response | Payload | Notes |
| --- | --- | --- | --- | --- |
| `0x21` | SetDensity | `0x31` | `u8` | Range is per model, see [devices.md](devices.md) |
| `0x23` | SetLabelType | `0x33` | `u8` | Label type, section 6 |
| `0x27` | SetAutoShutdownTime | `0x37` | `u8` 1–4 | Auto Shutdown select entity |
| `0x28` | PrinterReset | `0x38` | `01` | Resets settings such as sound. **(not implemented here)** |
| `0x58` | SoundSettings | `0x68` | `category`, `item`, `value` | Connection Sound switch (get/set) |
| `0x59` | CalibrateHeight | `0x69` | `01` | **(not implemented here)** |
| `0x8E` | LabelPositioningCalibration | `0x8F` | `u8` | Feeds ~15 cm on B1 for values 1–2. **(not implemented here)** |

### 4.3 Information

| Request | Name | Response | Payload | Notes |
| --- | --- | --- | --- | --- |
| `0xC1` | Connect | `0xC2` | `01` | Needs the `0x03` prefix (section 2). **(not implemented here)** |
| `0x40` | PrinterInfo | `0x40+key` | `u8` key | 15 keys, see [device-info.md](device-info.md) |
| `0xA5` | PrinterStatusData | `0xB5` | `01` | Colour support and protocol version |
| `0xDC` | Heartbeat | `0xDD` `0xDE` `0xDF` `0xD9` | `u8` type | Live status |
| `0xA3` | PrintStatus | `0xB3` | `01` | Page and progress |
| `0x05` | PrinterLog | `0x06` | `01` | **(not implemented here)** |
| `0x07` | PrinterConfig2 | `0x08` | varies | Also carries set-time and compress-mode. **(not implemented here)** |
| `0x09` | GetKeyFunction | `0x0A` | `01` | Hardware button mapping. **(not implemented here)** |
| `0x0B` | AntiFake | `0x0C` | `u8` query type | Genuine-consumable check. `01` long, `02` short. **(not implemented here)** |
| `0x0D` | GetPrintQuality | `0x0D` | `01` | Request and response share an ID. **(not implemented here)** |
| `0x12` | GetCurrentTimeFormat | `0x11` | `01` | **(not implemented here)** |
| `0xAF` | PrinterConfig | `0xBF` | `01` | **(not implemented here)** |
| `0x5A` | PrintTestPage | `0x6A` | `01` | **(not implemented here)** |

### 4.4 RFID

| Request | Name | Response | Payload | Notes |
| --- | --- | --- | --- | --- |
| `0x1A` | RfidInfo | `0x1B` | `01` | Label/paper tag |
| `0x1C` | RfidInfo2 | `0x1D` | `01` | Ribbon tag |
| `0x54` | RfidSuccessTimes | `0x64` | `01` | Tag read success counters. **(not implemented here)** |
| `0x70` | WriteRFID | `0x71` | tag data | **(not implemented here)** |

Details in [rfid.md](rfid.md).

### 4.5 WiFi

| Request | Name | Response | Notes |
| --- | --- | --- | --- |
| `0xA2` | GetPrinterConfigurationWifi | `0xB2` | **(not implemented here)** |

WiFi-capable models also expose an entirely separate network transport, which this document does not
cover.

### 4.6 Firmware upgrade

All of these use the CRC32 framing from section 2. **(not implemented here)**

| Request | Name | Response | Notes |
| --- | --- | --- | --- |
| `0xF5` | StartFirmwareUpgrade | `0xF6` | Payload is `major`, `minor` |
| `0x91` | FirmwareCrc | none | CRC32 of the whole image |
| `0x9B` | FirmwareChunk | none | 200-byte chunks, indexed by chunk number |
| `0x9C` | FirmwareNoMoreChunks | none | |
| `0x92` | FirmwareCommit | none | |

| Response | Name | Meaning |
| --- | --- | --- |
| `0x90` | In_RequestFirmwareCrc | Printer asks for the CRC |
| `0x9A` | In_RequestFirmwareChunk | Printer asks for a specific chunk |
| `0x9D` | In_FirmwareCheckResult | `data[0] == 1` means the image verified |
| `0x9E` | In_FirmwareResult | `data[0] == 1` means the flash succeeded |

The printer drives the transfer: it requests chunk numbers rather than accepting a linear stream.

## 5. Print error codes (`0xDB`)

`data[0]` holds the code.

| Code | Name | Meaning |
| --- | --- | --- |
| `0x01` | CoverOpen | Lid is open |
| `0x02` | LackPaper | Out of paper |
| `0x03` | LowBattery | Battery too low |
| `0x04` | BatteryException | Battery fault |
| `0x05` | UserCancel | Cancelled at the printer |
| `0x06` | DataError | Malformed data |
| `0x07` | Overheat | Print head too hot |
| `0x08` | PaperOutException | Paper feed fault |
| `0x09` | PrinterBusy | Busy with another job |
| `0x0A` | NoPrinterHead | Print head missing |
| `0x0B` | TemperatureLow | Ambient temperature too low |
| `0x0C` | PrinterHeadLoose | Print head not seated |
| `0x0D` | NoRibbon | No ribbon |
| `0x0E` | WrongRibbon | Wrong ribbon type |
| `0x0F` | UsedRibbon | Ribbon already spent |
| `0x10` | WrongPaper | Wrong paper type |
| `0x11` | SetPaperFail | `SetLabelType` rejected |
| `0x12` | SetPrintModeFail | Print mode rejected |
| `0x13` | SetPrintDensityFail | `SetDensity` rejected |
| `0x14` | WriteRfidFail | Could not write usage back to the tag |
| `0x15` | SetMarginFail | Margin rejected |
| `0x16` | CommunicationException | Link fault |
| `0x17` | Disconnect | Disconnected |
| `0x18` | CanvasParameterError | Bad canvas parameters |
| `0x19` | RotationParameterException | Bad rotation |
| `0x1A` | JsonParameterException | Bad JSON parameters |
| `0x1B` | B3sAbnormalPaperOutput | B3S paper output fault |
| `0x1C` | ECheckPaper | Paper needs checking |
| `0x1D` | RfidTagNotWritten | Tag carries no data |
| `0x1E` | SetPrintDensityNoSupport | Density setting unsupported |
| `0x1F` | SetPrintModeNoSupport | Print mode unsupported |
| `0x20` | SetPrintLabelMaterialError | Bad label material code |
| `0x21` | SetPrintLabelMaterialNoSupport | Label material unsupported |
| `0x22` | NotSupportWrittenRfid | Model cannot write tags |
| `0x32` | IllegalPage | Invalid page |
| `0x33` | IllegalRibbonPage | Invalid ribbon page |
| `0x34` | ReceiveDataTimeout | Printer timed out waiting for data |
| `0x35` | NonDedicatedRibbon | Non-genuine ribbon |
| `0xFF` | Unknown | Catch-all used by this integration |

`0xFF` is not a wire value; this integration maps unrecognised codes onto it.

## 6. Label types (`SetLabelType`, `0x23`)

| Value | Name | Description |
| --- | --- | --- |
| 0 | Invalid | |
| 1 | WithGaps | Gap-sensed die-cut labels. Default for most models |
| 2 | Black | Positioned by a black mark on the liner |
| 3 | Continuous | Continuous stock, no gaps |
| 4 | Perforated | Perforated stock |
| 5 | Transparent | Transparent labels |
| 6 | PvcTag | Tags / nameplates |
| 10 | BlackMarkGap | Black mark plus gap |
| 11 | HeatShrinkTube | Heat-shrink tubing |

Which values a model accepts is in [devices.md](devices.md). Sending an unsupported value returns
`0xDB` with `SetPaperFail (0x11)` or `SetPrintLabelMaterialNoSupport (0x21)`.

**This integration always sends `1` (WithGaps)** when printing, and its `set_label_type` asserts
`1 <= n <= 3`, so 4, 5, 6, 10 and 11 cannot be sent at all.

## 7. Not yet documented

- Payload layout of `PrinterConfig` (`0xAF`) and `PrinterConfig2` (`0x07`)
- The set-print-mode command (thermal vs thermal-transfer) and the set-label-material command.
  Their rejection codes exist (`0x12`, `0x1F`, `0x20`, `0x21`) but the request IDs are unconfirmed
- Top margin command, referenced by `SetMarginFail (0x15)`
- `AntiFake` (`0x0B`) payload and response structure
- Colour printing. `pageColor` exists in `PrintStart`, and red/black stock exists, but the two-colour
  row format is unknown
- Cutter control on models that have one
