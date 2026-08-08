# Reading Label Stock Info from RFID

Genuine NIIMBOT consumables carry an RFID tag. The printer reads it and will hand the contents over
on request, so a client can find out **which label is loaded and how much of it is left** without any
user input.

Framing and command IDs are in [protocol.md](protocol.md).

## Summary

```python
rfid = await printer.get_rfid()
# {'uuid': '1234567890abcdef', 'barcode': 'A1B2C3', 'serial': '...',
#  'total_len': 230, 'used_len': 12, 'type': 1}
```

| Field | What it tells you |
| --- | --- |
| `barcode` | Product code of the consumable — identifies the exact label SKU |
| `total_len` | Amount the roll shipped with |
| `used_len` | Amount consumed so far → **remaining = `total_len - used_len`** |
| `type` | Consumable type code (section 4) |
| `uuid` | Tag identity, used to detect a roll swap |
| `serial` | Production batch serial |

## 1. Checking support first

### Model

Models fall into four RFID classes. The class is a per-model property, listed in the RFID column of
[devices.md](devices.md).

| Class | Meaning |
| --- | --- |
| none | No tag reader |
| label | Tag on the label roll only |
| ribbon | Tag on the ribbon or cartridge only |
| label+ribbon | Separate tags on both |

Label-class models answer `RfidInfo` (`0x1A`). Ribbon-class models answer `RfidInfo2` (`0x1C`).
`label+ribbon` models answer both.

### Firmware

RFID reading was added by firmware update on several models, so a supported model on old firmware
still returns nothing. Read the firmware version with `PrinterInfo` key 9
([device-info.md](device-info.md#softwareversion--hardwareversion-keys-9-12)) — but note that the
version encoding is ambiguous, so this is a weak gate.

### Right now

The heartbeat reports whether the tag is currently readable. A lid that is open, missing stock, or a
read still in progress all show up as not-readable.

```python
hb = await printer.heartbeat()
if hb["rfidreadstate"]:
    rfid = await printer.get_rfid()
```

`rfidreadstate` is only present when the Advanced1 heartbeat payload is 13, 19 or 20 bytes
([device-info.md](device-info.md#advanced1-response-0xdd)). On models that return 9 or 10 bytes the
field does not exist — just issue `RfidInfo` and treat a null result as "not available".

The Advanced2 heartbeat reports paper and ribbon RFID success separately, which is the only way to
tell which of the two tags failed. This integration never requests Advanced2.

## 2. Commands

| Request | Name | Response | Tag |
| --- | --- | --- | --- |
| `0x1A` | RfidInfo | `0x1B` | Label / paper |
| `0x1C` | RfidInfo2 | `0x1D` | Ribbon |
| `0x54` | RfidSuccessTimes | `0x64` | Read success counters |
| `0x70` | WriteRFID | `0x71` | Write tag contents |

Both info commands send `01` as payload and return the same structure.

```
55 55 1A 01 01 1A AA AA
      ^^ ^^ ^^ ^^
      |  |  |  +-- bcc = 0x1A ^ 0x01 ^ 0x01
      |  |  +----- data = 0x01
      |  +-------- len = 1
      +----------- cmd = 0x1A (RfidInfo)
```

`RfidInfo2`, `RfidSuccessTimes` and `WriteRFID` are **not implemented in this integration.**

## 3. Response layout

A **1-byte payload means no tag** — no stock loaded, non-genuine stock, or lid open. Otherwise the
payload is variable-length:

```
offset  size            field
------  --------------  --------------------------------------------
0       8               uuid              tag identity
8       1               barcode_len
9       barcode_len     barcode           product code, ASCII
+0      1               serial_len
+1      serial_len      serial            batch serial, ASCII
+0      2               total_len         u16, big-endian
+2      2               used_len          u16, big-endian
+4      1               type              consumable type code
+5      2               capacity          u16, optional — not sent by all models
```

Both strings are length-prefixed, so the trailing fields have no fixed offset and the payload has to
be walked sequentially.

### Two bugs to avoid

**Presence check.** This integration tests `data[0] == 0`, i.e. the first byte of the UUID. Checking
the payload *length* instead (`len(data) == 1`) is correct — a valid tag whose UUID happens to start
with a zero byte would otherwise be reported as absent.

**Trailing `capacity`.** This integration parses the tail with `struct.unpack(">HHB", data[idx:])`,
which requires exactly 5 remaining bytes. On a model that appends the optional `capacity` field there
are 7, and the call raises `struct.error`. The fix is to slice explicitly and treat anything beyond as
optional:

```python
total_len, used_len, type_ = struct.unpack(">HHB", data[idx:idx + 5])
idx += 5
capacity = struct.unpack(">H", data[idx:idx + 2])[0] if len(data) >= idx + 2 else None
```

Current implementation: [`printer.py`](../custom_components/niimbot/niimprint/printer.py)

```586:593:custom_components/niimbot/niimprint/printer.py
    async def get_rfid(self):
        packet = await self._transceive(RequestCodeEnum.GET_RFID, b"\x01")
        data = packet.data

        if data[0] == 0:
            return None
        uuid = data[0:8].hex()
        idx = 8
```

### Units of `total_len` / `used_len`

Depends on the consumable:

- **Die-cut label rolls** — a count of labels. A 50 x 30 mm roll typically reports around 230.
- **Continuous stock, ribbon, heat-shrink tubing** — a length. The scale factor is unconfirmed.

`used_len` is written back to the tag by the printer as it prints, which is why
`WriteRfidFail (0x14)` exists as an error code. A client does not need to maintain the counter itself.

### What `barcode` gets you

`barcode` identifies the label SKU. Mapping it to physical dimensions requires the vendor's product
catalogue, which lives in their cloud service — **there is no local lookup.**

So locally the useful property is identity, not geometry: the same barcode means the same label. A
practical pattern is to record the barcode once and let the user associate their own width/height
with it.

## 4. Consumable type code (`type`)

This single byte is **ambiguous** and worth being careful about.

The common interpretation is that it is a label type, using the same enumeration as `SetLabelType`:

| Value | Label type |
| --- | --- |
| 1 | WithGaps |
| 2 | Black |
| 3 | Continuous |
| 4 | Perforated |
| 5 | Transparent |
| 6 | PvcTag |
| 10 | BlackMarkGap |
| 11 | HeatShrinkTube |

But the field is named for the *consumable*, and there is a much broader material enumeration in the
NIIMBOT ecosystem that also starts at 1 and shares several low values (1 = general thermal synthetic
paper, 5 = transparent PET). For ordinary gap and transparent labels the two readings coincide, which
is why the ambiguity has not been settled.

A way to tell them apart on real hardware: load black-mark stock made of plain thermal synthetic
paper. Under the label-type reading the tag reports `2`; under the material reading it reports `1`.
Comparing against `PrinterInfo` key 3 (the label type the printer itself reports) on the same stock
resolves it.

Material enumeration, for reference:

| Code | Material | Print method |
| --- | --- | --- |
| 1 | Thermal synthetic paper, general | Thermal |
| 2 | Tag / nameplate | Thermal transfer |
| 3 | PP synthetic paper | Thermal or transfer |
| 4 | Thermal card stock | Thermal |
| 5 | Transparent PET | Thermal or transfer |
| 6 | Coated paper | Thermal transfer |
| 7 | Coated card stock | Thermal transfer |
| 8 | Matte silver PET | Thermal transfer |
| 9 | White PET | Thermal transfer |
| 10 | White PVC | Thermal transfer |
| 11 | Triple-resistant thermal paper (water, oil, abrasion) | Thermal |
| 12 | PP card stock | Thermal transfer |
| 13 | Transparent PE | Thermal or transfer |
| 14 | White PE | Thermal transfer |
| 15 | Pearlescent synthetic paper | Thermal transfer |
| 18 | Matte black PET | Thermal transfer |
| 19 | Transparent thermal | Thermal |
| 21 | Hot stamping foil | Thermal transfer |
| 22 | Transparent PP, cable wrap | — |
| 23 | White cryogenic (liquid nitrogen) | Thermal transfer |
| 28 | Thermal synthetic paper, red imaging | Thermal |
| 29 | Thermal synthetic paper, red/black | Thermal |
| 31 | Thermal synthetic paper, low temperature | Thermal |
| 35 | PET card stock | Thermal transfer |
| 37 | Satin ribbon | Thermal transfer |
| 53 | Heat-shrink tubing | Thermal transfer |
| 54 | Wire marker sleeve | Thermal transfer |
| 55 | Transparent PP, general | Thermal transfer |
| 64 | Thermal synthetic paper, thick | Thermal |
| 65 | Thermal synthetic paper, writable | Thermal transfer |
| 67 | PP synthetic paper, writable | Thermal transfer |
| 70 | Thermal synthetic paper, greyscale | Thermal |
| 80 | Thermal synthetic paper, red/black, thick | Thermal |
| 93 | Matte white PET | Thermal transfer |
| 103 | Transparent PVC, electrostatic cling | Thermal transfer |
| 110 | Thermal synthetic paper, flexible | Thermal transfer |
| 129 | PVC tag | Thermal transfer |

New consumables get new codes, so this is not exhaustive.

Either way the code drives imaging: thermal versus thermal-transfer stock in the wrong printer is
rejected with `WrongPaper (0x10)` or `SetPrintLabelMaterialNoSupport (0x21)`.

## 5. RFID-related error codes

Subset of [protocol.md section 5](protocol.md#5-print-error-codes-0xdb).

| Code | Name | Meaning |
| --- | --- | --- |
| `0x0D` | NoRibbon | No ribbon loaded |
| `0x0E` | WrongRibbon | Ribbon type mismatch |
| `0x0F` | UsedRibbon | Ribbon already spent |
| `0x10` | WrongPaper | Paper type mismatch |
| `0x14` | WriteRfidFail | Could not write usage back to the tag |
| `0x1D` | RfidTagNotWritten | Tag carries no data |
| `0x22` | NotSupportWrittenRfid | Model cannot write tags |
| `0x35` | NonDedicatedRibbon | Non-genuine ribbon |

## 6. Using this in the integration

`get_rfid()` exists but **is not wired to any entity.** The only RFID-derived entity today is the
`rfidreadstate` binary sensor from the heartbeat (`binary_sensor.py`).

Worth building:

- **Remaining labels sensor** — `total_len - used_len`, which is directly actionable for reorder alerts
- **Usage percentage** — `used_len / total_len * 100`
- **Label type attribute** — `type` resolved through section 4
- **Roll change detection** — `uuid` changing means the stock was swapped
- **Pre-print validation** — refuse the print service when nothing is left

Things that will bite:

- On a model without RFID, `get_rfid()` returns `None` or times out. Gate on the model's RFID class
  first.
- An open lid means no read. Failing on some poll cycles is normal, so hold the last known value
  rather than going unavailable.
- Third-party labels have no tag and always return `None`.
- Fix the two parsing issues in section 3 before relying on this on unfamiliar hardware.

## 7. Unconfirmed

- Whether `type` is a label type or a material code (section 4)
- Scale factor of `total_len` / `used_len` for continuous, ribbon and tubing stock
- Payload of `RfidSuccessTimes` (`0x54`) and `WriteRFID` (`0x70`)
- Meaning of the optional `capacity` field versus `total_len`
- Mapping from `barcode` to physical label dimensions, which is a cloud-side lookup
