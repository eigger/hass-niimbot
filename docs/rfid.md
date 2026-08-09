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
tell which of the two tags failed. `heartbeat()` accepts `0xD9` and the parser reads both fields, but
`ribbon_rfidreadstate` is not carried into an entity yet.

There is a third gate the app applies and this integration does not: RFID reading was shipped by
firmware update, and the vendor's device database lists the firmware versions on which it does **not**
work per model (`rfidNotSupportVersions`). See
[app-gap-analysis.md](app-gap-analysis.md#a4-firmware-version-gated-capabilities-are-ignored) for the
list. On those units every poll spends a full read timeout on a command that cannot be answered.

## 2. Commands

| Request | Name | Response | Tag |
| --- | --- | --- | --- |
| `0x1A` | RfidInfo | `0x1B` | Label / paper |
| `0x1C` | RfidInfo2 | `0x1D` | Ribbon |
| `0x54` | RfidSuccessTimes | `0x64` | Read success counters |
| `0x70` | WriteRFID | `0x71` | Write tag contents |

Both info commands send `01` as payload and return the same structure, and both are implemented
(`get_rfid` / `get_rfid2`, sharing `_parse_rfid_payload`).

```
55 55 1A 01 01 1A AA AA
      ^^ ^^ ^^ ^^
      |  |  |  +-- bcc = 0x1A ^ 0x01 ^ 0x01
      |  |  +----- data = 0x01
      |  +-------- len = 1
      +----------- cmd = 0x1A (RfidInfo)
```

`RfidSuccessTimes` and `WriteRFID` are **not implemented in this integration.**

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

Both were present until 3.0.0 and are fixed in `_parse_rfid_payload`; they are recorded here because
any reimplementation walks into them.

**Presence check.** Testing `data[0] == 0` reads the first byte of the UUID, not a presence flag. A
valid tag whose UUID starts with a zero byte is then reported as absent. Test the payload *length*
instead (`len(data) <= 1`).

**Trailing `capacity`.** Parsing the tail with `struct.unpack(">HHB", data[idx:])` requires exactly 5
remaining bytes. On a model that appends the optional `capacity` field there are 7, and the call
raises `struct.error`. Slice explicitly and treat anything beyond as optional:

```python
total_len, used_len, type_ = struct.unpack(">HHB", data[idx:idx + 5])
idx += 5
capacity = struct.unpack(">H", data[idx:idx + 2])[0] if len(data) >= idx + 2 else None
```

### Units of `total_len` / `used_len`

Depends on the consumable:

- **Die-cut label rolls** — a count of labels. A 50 x 30 mm roll typically reports around 230.
- **Continuous stock, ribbon, heat-shrink tubing** — a length. The scale factor is unconfirmed.

`used_len` is written back to the tag by the printer as it prints, which is why
`WriteRfidFail (0x14)` exists as an error code. A client does not need to maintain the counter itself.

### What `barcode` gets you, and what label size is available offline

`barcode` identifies the label SKU. Mapping it to physical dimensions requires the vendor's product
catalogue, which lives in their cloud service — **there is no local lookup.**

This is worth stating precisely, because "read the loaded label's size without internet" is the first
thing anyone wants from an RFID tag:

- **The tag carries no dimensions.** The payload in section 3 is uuid, barcode, serial, `total_len`,
  `used_len`, `type` and an optional `capacity`. There is no width, height or pitch field, on any
  model. Nothing is being missed by the parser — the bytes are not there.
- **The app does not get size from the tag either.** It looks the SKU up against
  `/labels/:id/consumable-attributes` and caches the result; `labelWidth` / `labelHeight` belong to
  the cloud label object, not to anything the printer said.
- **The one offline catalogue the app ships covers C1 only.**
  `flutter_assets/packages/niimbot_cache_manager/assets/c1_consumableCode.json` holds 35 SKUs of
  heat-shrink tubing and wire marker sleeve (materials 53 and 54) with `height` and a four-value
  margin. It is a C1 tube picker, not a general catalogue, and it is keyed by material rather than by
  SKU.

What *is* available with no network, and is enough for most automations:

| Value | Source | Note |
| --- | --- | --- |
| Max print width / length in mm | Vendor device DB, per model | Printer capability, not the loaded roll |
| Settable label width range | `widthSetStart` / `widthSetEnd` | Same |
| Per-material print margins | `blindZone`, per model + paper type | `left\|right\|top\|bottom` in mm |
| Printable area | `PrinterInfo` key 15 | Already the Print Area sensor; layout unconfirmed |
| Labels remaining / used / total | RFID tag | Quantity, not geometry |
| Material and label type | RFID `type` + `PrinterInfo` key 3 | Section 4 |

So locally the useful property of a roll is identity, not geometry: the same barcode means the same
label. A practical pattern is to record the barcode once and let the user associate their own
width/height with it — that mapping then works offline forever and survives roll swaps.

One unconfirmed lead worth testing on hardware: if `capacity` is a roll *length* while `total_len` is
a label *count*, then `capacity / total_len` is the label pitch, which would give the height of a
die-cut label with no lookup at all. Both fields are already parsed and exposed as attributes on the
Labels Remaining sensor, so this can be checked against a roll of known size without writing any code.

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

**The material reading is the more likely one.** The app's own device database
(`assets/DevicesModule_en.json` in NIIMBOT 6.6.5) models every consumable as a *material* containing
one or more *label types* — the label-type codes are children of the material code, not the same
field. The bundled C1 catalogue (`c1_consumableCode.json`) is then keyed by material code, using `53`
and `54` as its two top-level keys, which are heat-shrink tubing and wire marker sleeve in the table
below. That is the enumeration the vendor indexes consumables by.

It is still inference: no tag observed by this project has returned a value above 11, which is where
the two readings would visibly diverge. The decisive test on real hardware is to load black-mark stock
made of plain thermal synthetic paper. Under the label-type reading the tag reports `2`; under the
material reading it reports `1`. Comparing against `PrinterInfo` key 3 (the label type the printer
itself reports) on the same stock resolves it.

Previously `model.py:consumable_type_name()` mapped the byte through the 1–11 label-type table only,
so materials such as transparent thermal (19) rendered as `Unknown(19)`. From Task T1,
`model.py:material_name()` maps the byte through the material table below to present
`consumable_type` and `ribbon_type` sensors, while `PrinterInfo` key 3 remains the authoritative `labeltype`.

Material enumeration:

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

Built as of 3.0.0, for both the label tag (`0x1A`) and the ribbon tag (`0x1C`):

- Labels / Ribbon Remaining (`total_len - used_len`), Used, Total and Usage percentage
- Label SKU, Consumable Type, Tag UUID, with `serial` and `capacity` as attributes
- Roll change detection — a changed `uuid` fires `niimbot_roll_changed`
- Entities are created from the model's RFID class, so an RFID-less model creates none of them

Still open:

- `type` is rendered through the material table (Task T1)
- No pre-print validation — the print service does not refuse when the roll is spent
- No firmware gate, so models on an RFID-incapable firmware still pay a timeout per poll (section 1)

Things that will bite anyone reimplementing this:

- On a model without RFID, `get_rfid()` returns `None` or times out. Gate on the model's RFID class
  first.
- An open lid means no read. Failing on some poll cycles is normal, so hold the last known value
  rather than going unavailable.
- Third-party labels have no tag and always return `None`.
- Fix the two parsing issues in section 3 before relying on this on unfamiliar hardware.

## 7. Unconfirmed

- Whether `type` is a label type or a material code (section 4) — evidence now favours material
- Scale factor of `total_len` / `used_len` for continuous, ribbon and tubing stock
- Payload of `RfidSuccessTimes` (`0x54`) and `WriteRFID` (`0x70`)
- Meaning of the optional `capacity` field versus `total_len` — if it is a length, it yields the label
  pitch (section 3)
- Mapping from `barcode` to physical label dimensions, which is a cloud-side lookup
