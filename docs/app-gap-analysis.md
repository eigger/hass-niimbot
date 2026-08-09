# Gap Analysis against the NIIMBOT App (v6.6.5)

What the official app can do that this integration cannot, derived from a decompile of
`com.gengcon.android.jccloudprinter` (NIIMBOT 6.6.5) and compared against `master` at
version 3.0.0.

Related: [protocol.md](protocol.md) · [device-info.md](device-info.md) · [printing.md](printing.md) ·
[rfid.md](rfid.md) · [devices.md](devices.md) · [improvement-plan.md](improvement-plan.md)

## What the decompile does and does not give

The APK is packed with SecNeo, so `classes.dex` is a loader stub and the Java/Kotlin BLE SDK is not
readable. Two parts are readable and both are useful:

- **`assets/DevicesModule_en.json`** (identical to `flutter_assets/assets/config/printerList.json`) —
  the vendor's own device capability database, 79 models with model codes, DPI, print direction,
  density range, paper types, RFID class, cutter, WiFi and per-material metadata. This is the same
  table [devices.md](devices.md) was built from, one app version newer.
- **`lib/arm64-v8a/libapp.so`** — the Flutter AOT image. Dart class and endpoint names survive, so
  the cloud API surface and the feature set of the UI layer are visible even though the wire protocol
  is not.

Command IDs quoted below come from [protocol.md](protocol.md), not from this decompile.

---

## A. Gaps

### A1. 14 model codes added to `model.py` — **Resolved (T3)**

Previously `get_printer_meta_by_id()` returned `None` for these 14 model IDs. In Task T3, all 14 model codes were added to `PrinterModel`, `modelsLibrary`, and `_CAPABILITIES_BY_ID` with estimated `printheadPixels` values:

| Code | Model | DPI | Dir | Width mm | Max len | Paper types | RFID | Density | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3840 | H1 | 203 | 90 | 15 | 200 | 1, 5 | label | 1-3/2 | D11-class |
| 4098 | B1 SE | 203 | 0 | 54 | 350 | 1, 2, 5 | label | 1-5/3 | B1 series |
| 4352 | H1S | 203 | 90 | 15 | 200 | 1, 3, 5 | label | 1-3/2 | D11-class |
| 4610 | EP2M_H | 300 | 0 | (200) | 200 | 1, 5, 2, 10 | label+ribbon | 1-5/3 | M2 series, width field looks wrong |
| 4868 | K3_ITD | 203 | 0 | 82 | 300 | 1, 2, 5 | label | 1-5/3 | K3 series |
| 5120 | C1 | 300 | 90 | 50 | 50 | 3 | ribbon | 1-5/3 | tube printer |
| 5121 | EP1C | 300 | 90 | 50 | 50 | 3 | ribbon | 1-5/3 | C1 variant |
| 6144 | K2 | 203 | 0 | 60 | 300 | 1, 2, 5 | label | 1-5/3 | |
| 6400 | M3 | 300 | 0 | 78 | 350 | 1, 5, 2, 10 | label+ribbon | 1-5/3 | |
| 6402 | EP3M | 300 | 0 | 78 | 350 | 1, 5, 2, 10 | label+ribbon | 1-5/3 | M3 variant |
| 6656 | B4 | 203 | 0 | 108 | 350 | 1, 2, 5 | label | 1-5/3 | |
| 6657 | B4 Pro | 300 | 0 | 108 | 350 | 1, 2, 5 | label | 1-5/3 | WiFi + MQTT |
| 7168 | K4 | 203 | 0 | 82 | 300 | 1, 2, 5 | label | **1-15/7** | automatic cutter |
| 7424 | A1 Pro | 300 | **270** | 15 | 120 | 4, 3 | none | 1-5/3 | perforated/continuous only |

`printheadPixels` is the one field the vendor table does not carry. Across the 63 models already
modelled the ratio is stable per DPI — 203 dpi sits at 7.68–8.00 px/mm and 300 dpi at 11.34–11.87 —
so a same-series sibling is the best estimate (K4 → 656 from K3, B1 SE → 384 from B1, EP2M_H → 591
from M2_H). **[HW]** each one before trusting it.

Two smaller items in the same table:

- `printDirection` has a third value, `270`, used by A1 Pro and by **B16**, which `model.py` currently
  records as `LEFT` (= 90). Either 270 is equivalent to 90 for our rendering or B16 output is
  mirrored. **[HW]**
- Two density defaults disagree: JCB3S default 2 (we say 3) and Hi-D110 default 3 (we say 2). Both
  IDs are shared with other models, so this is cosmetic.

### A2. `type` in the RFID payload is a **material** code, not a label type

[rfid.md](rfid.md#4-consumable-type-code-type) flags this as unresolved. The app's device database
settles it: every model lists its consumables as a *material* (`parentProperty.code`) containing
*label types* (`childProperties.code`). The material enumeration reaches 129 and includes codes that
cannot be label types at all.

Two further pieces of evidence from this decompile: the bundled C1 catalogue
(`c1_consumableCode.json`) is keyed by material code — its two top-level keys are `53` and `54`, the
heat-shrink and wire-sleeve materials — and every model's `consumables` array nests label types inside
a material rather than beside it. It remains inference until a tag returns a value above 11, which is
the only place the two readings diverge.

`consumable_type_name()` maps the byte through the 1–11 label-type table, so a roll of transparent
thermal paper (material 19) currently shows as `Unknown(19)` and semi-gloss paper (6) shows as
`PvcTag`. The table is already written up in [rfid.md](rfid.md#4-consumable-type-code-type) — what is
missing is `model.py` using it. Repeated here in the app's own English wording, complete as of 6.6.5:

| Code | Material | Print mode |
| --- | --- | --- |
| 1 | Thermal Paper | direct thermal |
| 2 | PVC tag | thermal transfer |
| 3 | PP Paper | both |
| 4 | Thermal Paper - Cardboard | direct thermal |
| 5 | Transparent PET | both |
| 6 | Semi-gloss paper | thermal transfer |
| 7 | Semi-gloss cardboard | thermal transfer |
| 8 | Silver PET | thermal transfer |
| 9 | White PET | thermal transfer |
| 10 | White PVC | thermal transfer |
| 11 | Premium Thermal Paper | direct thermal |
| 12 | PP-Enhanced Cardstock | thermal transfer |
| 13 | Transparent PE | both |
| 14 | White PE | thermal transfer |
| 15 | Pearlized film | thermal transfer |
| 18 | Matt black PET | thermal transfer |
| 19 | Transparent Thermal Paper | direct thermal |
| 21 | Iron On Polyurethane Label | thermal transfer |
| 22 | Transparent PP Paper - Wraparound | — |
| 23 | White Nylon - Liquid nitrogen | thermal transfer |
| 28 | Thermal Paper - Red Text | direct thermal |
| 29 | Thermal Paper - Red and Black | direct thermal |
| 31 | Thermal Paper - Low Temp | direct thermal |
| 35 | PET Cardstock | thermal transfer |
| 37 | Silk Ribbon | thermal transfer |
| 53 | Heat-shrink tube | thermal transfer |
| 54 | Tube | thermal transfer |
| 55 | Transparent PP Paper | thermal transfer |
| 64 | Thermal Paper - Thick | direct thermal |
| 65 | Thermal Paper - Writable | thermal transfer |
| 67 | PP Paper - Writable | thermal transfer |
| 70 | Thermal Paper - Grayscale | direct thermal |
| 80 | Thermal Paper - Red and Black (thick) | direct thermal |
| 93 | Matte white PET | thermal transfer |
| 103 | Transparent PVC - Static Sticker | thermal transfer |
| 110 | Thermal Paper - Flexible | thermal transfer |
| 129 | PVC tag | thermal transfer |

The label-type child codes are unchanged from what `model.py` already has: 1 Gap, 2 Black,
3 Continuous, 4 Hole, 5 Transparent, 6 PVC tag, 10 Black mark gap, 11 Heat-shrink tube.

Suggested change: keep both readings. Report the material name for `type`, and keep
`PrinterInfo` key 3 as the authoritative label type (it already feeds the `labeltype` sensor).

### A3. Advanced2 heartbeat fields are parsed and then dropped

`PrinterClient._parse_heartbeat_advanced2()` returns `temperature`, `ribbon_rfidreadstate`,
`ribbonstate`, `wifi_rssi`, `lighting_error` and `voltage_state`. `NiimbotDevice.update_device()`
copies only `closingstate`, `paperstate`, `rfidreadstate` and the battery, so six values are computed
per poll and discarded. This is item 3.3 of [improvement-plan.md](improvement-plan.md), now cheap:
the parse already exists, only the sensor definitions and the capability gate are missing.

### A4. Firmware-version-gated capabilities are ignored

The device table carries `rfidNotSupportVersions` — firmware versions on which RFID reading does not
work despite the model being RFID-class. Seven entries are populated, some of them long:

| Model | Codes | Firmware versions without RFID |
| --- | --- | --- |
| D11 | 512 | 1.01, 1.04–1.09, 2.02, 2.03, 2.08, 2.16 |
| Hi-NB-D11 | 512 | 1.04, 1.08, 1.09, 2.02, 2.03, 2.08, 2.09, 2.14–2.16 |
| D41 / D61 / Dxx | — | similar 1.0x / 2.0x sets |
| B21S | 777 | 1.01–1.04, 2.01–2.09, 3.01, 5.01, 5.02, 6.00, 10.01, 20.01, 21.01, 30.01–33.01, 35.01 |
| B21-C2B | 771, 775 | same set as B21S |

We read `SOFTVERSION` (key 9) as `data[0] + data[1] / 100`, which formats back to exactly these
strings as `f"{major}.{minor:02d}"`. Gating the `RfidInfo` call on this list removes a guaranteed
timeout per poll on affected units. `wifiNotSupportVersions` exists for the same purpose on the WiFi
models.

### A5. Protocol commands still unimplemented

Confirmed against `RequestCodeEnum` in `printer.py`. Note that [protocol.md](protocol.md) is stale on
two rows: `RfidInfo2` (`0x1C`) and `PrinterStatusData` (`0xA5`) **are** implemented now.

| Command | Name | App feature it backs | Value here |
| --- | --- | --- | --- |
| `0x8E` | LabelPositioningCalibration | 라벨 위치 보정 / paper calibration | High — button entity, one of the most requested printer actions |
| `0x59` | CalibrateHeight | roll feed calibration | High — same |
| `0xDA` | CancelPrint | cancel a running job | High — no way to stop a bad print today |
| `0x28` | PrinterReset | factory reset of settings | Medium — button, needs a confirm |
| `0x5A` | PrintTestPage | test page | Medium — trivial button |
| `0x07` | PrinterConfig2 | `setPrinterTime`, compress mode | Medium — clock drift on models with a date element |
| `0x40` key 14 | PrintMode | direct thermal vs thermal transfer | Medium — pairs with the material table in A2 |
| `0x40` key 13 | BluetoothAddress | — | Low — diagnostic, disabled by default |
| `0x0B` | AntiFake | genuine-consumable check | Low |
| `0x54` | RfidSuccessTimes | tag read counters | Low — diagnostic |
| `0x09` | GetKeyFunction | hardware button mapping | Low |
| `0x0D` / `0x12` / `0x05` / `0xAF` | quality / time format / log / config | — | Low |
| `0x70` | WriteRFID | writing RFID data into labels | Out of scope — needs genuine tag signing |
| `0xA2` | GetPrinterConfigurationWifi | WiFi setup | Out of scope over BLE alone, see A6 |
| `0xF5` `0x91` `0x9B` `0x9C` `0x92` | firmware upgrade | OTA | See section C |

### A6. Whole feature areas with no counterpart here

- **WiFi / MQTT printers.** Three models in the table are WiFi-capable (B4 Pro is also MQTT), and the
  app has `getDeviceWifiConfig`, `setWifiModuleOTA`, `stopDiscoverWIFIPrinter`, `getMqttSessionByDevice`.
  This integration is BLE-only. Adding a network transport is a much larger change than any other
  item on this page and should be treated as a separate project.
- **Cutter.** `cutterType: AUTOMATIC` on K4, plus `getHalfCutSupport` / `setHalfCut` in the app.
  Nothing here models a cutter.
- **Grayscale and two-colour printing.** `isDeviceSupportGray16`, `isDeviceSupportDoubleColorPrint`,
  and materials 29/80 (red-and-black thermal paper). `render.py` is 1-bit only. The `colour_support`
  sensor already reports the flag, so the capability is visible but unusable.
- **Print margins (`blindZone`).** Every model/paper-type pair carries a four-value mm margin
  (`left|right|top|bottom`), e.g. B21_Pro gap paper `0.5|1.0|0.5|0.5`, B3S_P black-mark
  `6.0|1.0|0.0|0.0`. We render edge to edge, which is why content near the leading edge can clip on
  black-mark stock.

---

## B. Cloud label lookup as an opt-in

### Can label size be resolved offline? No — and not because of a parser gap

Worth answering first, because it decides how much the cloud option is actually worth.

- **The RFID tag has no dimension field.** The payload is uuid, barcode, serial, `total_len`,
  `used_len`, `type` and an optional `capacity` ([rfid.md §3](rfid.md#3-response-layout)). No width,
  height or pitch, on any model.
- **The app does not read size from the tag either.** It resolves the SKU against
  `/labels/:id/consumable-attributes` and caches; `labelWidth` / `labelHeight` are fields of the cloud
  label object.
- **The only offline catalogue in the APK covers C1.**
  `flutter_assets/packages/niimbot_cache_manager/assets/c1_consumableCode.json` has 35 SKUs of
  heat-shrink tubing and wire marker sleeve with `height` and a four-value margin. A tube picker, not
  a catalogue.

What *is* available offline is printer geometry rather than roll geometry: `maxPrintWidth` /
`maxPrintHeight`, the settable width range, per-material `blindZone` margins, and `PrinterInfo` key 15
(already the Print Area sensor). Plus quantity from the tag. The table in
[rfid.md](rfid.md#what-barcode-gets-you-and-what-label-size-is-available-offline) lists all of it.

One untested lead that would close the gap without any network: if `capacity` is a roll length while
`total_len` is a label count, `capacity / total_len` is the label pitch. Both values are already
exposed as attributes on the Labels Remaining sensor, so this is checkable against a roll of known
size with no code change.

### What the cloud adds over the tag

The tag itself already gives SKU (`barcode`), remaining/used counts, batch serial and the material
code. What it does **not** give is anything human-readable: label name, physical size, preview image.
[rfid.md](rfid.md#what-barcode-gets-you) states this correctly — geometry lives in the vendor
catalogue only.

Relevant endpoints found in `libapp.so`, on base host `https://print.niimbot.com`:

| Endpoint | Purpose |
| --- | --- |
| `/labels/:id/consumable-attributes` | Attributes of one label SKU |
| `/labels/tube/scanBarcode` | Barcode → tube consumable |
| `/labels/tube/spec-list`, `/labels/tube/categories` | Tube spec catalogue |
| `/rfid/machines`, `/rfid/machine/alias` | RFID-capable machine registry |
| `/system/statistics/paperUsedQuantity` | Server-side consumption stats |

Response shape, from the bundled C1 catalogue asset
(`packages/niimbot_cache_manager/assets/c1_consumableCode.json`), is `id`, `name`, `height`,
`margin[4]`, `size`, `previewImageUrl` on `oss-print.niimbot.com`.

### The blocker

The app's HTTP layer sends `Authorization: Bearer …` and the endpoints sit behind the account login
(`/oauth/*`). **Whether any of these answer unauthenticated has not been tested** — that needs a live
request, which is a decision for you, not something to assume. If they require a token, this feature
means asking Home Assistant users for NIIMBOT credentials, which is a poor trade for a label name.

### Recommendation

Do it in two independent pieces, and note that the first piece removes most of the motivation for the
second.

**B1 — offline enrichment, no option needed.** The material table already sits in
[rfid.md](rfid.md#4-consumable-type-code-type) and the model table in [devices.md](devices.md); what
is missing is code that uses them. Wiring the material table into `consumable_type_name()` turns
`Unknown(19)` into `Transparent Thermal Paper` and brings print mode with it, without a network call.
This is where most of the practical value is, and it does not help with size — nothing offline does,
see above.

**B2 — cloud lookup behind an explicit opt-in.** If you still want the SKU name and preview:

```python
CONF_USE_CLOUD_LABEL_INFO = "use_cloud_label_info"
DEFAULT_USE_CLOUD_LABEL_INFO = False   # local-only by default
```

Design constraints that matter for a local-first integration:

- Default **off**, added to `OPTIONS_SCHEMA` so it appears in both the initial config flow and the
  options flow, same as `CONF_KEEP_CONNECTION`. Existing entries keep the default and stay offline.
- Never block the coordinator on it. Look up only when `tag_uuid` changes — that event already
  exists as `niimbot_roll_changed` — and cache the result per SKU on disk (HA `Store`), so a roll that
  has been seen before never hits the network again.
- Every cloud-derived value goes on **attributes of the existing** `label_sku` sensor, not into new
  entities. Entities that only exist when the option is on make the two configurations diverge.
- A failed lookup is a debug log line and nothing else. No unavailable entities, no repair issue.
- The strings need a clear description in `strings.json` and `translations/*.json` saying that
  enabling it sends the loaded label's SKU to a NIIMBOT server.

If the endpoints turn out to need an account, stop at B1 rather than adding a credentials field.

---

## C. Firmware version check and update

### Where we already are

`SOFTVERSION` (key 9) and `HARDVERSION` (key 12) are read at connect and surfaced as `sw_version` /
`hw_version` on the HA device. So the *current* version is already shown. Two things are missing:
knowing whether it is the latest, and doing anything about it.

### Checking for a newer version — cloud only

The app calls `/firmware/upgradable/mix` and `/firmware/machineCascadeDetail` under the same
authenticated host as section B, and the response (`FirmwareInfo`) carries `downloadUrl`, an MD5 and
`isForceUpdate`. There is **no local way** to know the newest version — the vendor publishes no
public feed, and nothing in the APK embeds a version manifest.

So a "firmware is up to date / update available" sensor has exactly the same authentication problem
as B2, plus a worse failure mode: a stale or wrong answer about firmware invites a user to flash.

**Recommendation: do not build the check.** What is worth doing instead is A4 — use the version we
already read to gate capabilities, and mention the known-bad RFID firmware versions in the README so
a user with D11 on 2.08 understands why the consumable sensors are empty.

### Performing the update — technically possible, not advisable

The BLE side is fully documented in [protocol.md](protocol.md#46-firmware-upgrade): `StartFirmwareUpgrade`
(`0xF5`) with major/minor, then the printer drives the transfer by requesting the CRC (`0x90`) and
individual 200-byte chunks (`0x9A`), answered with `0x91` / `0x9B`, terminated by `0x9C` and `0x92`,
with `0x9D` / `0x9E` reporting verify and flash results. It uses the CRC32 framing from section 2,
which is **not implemented** — `packet.py` only does the BCC framing.

Against that:

1. **No image source.** The firmware binary is behind the authenticated cloud API. Nothing to flash.
2. **Bricking is not recoverable from HA.** The app's own strings — "connect the power to restart the
   printer before upgrading", "firmware needs to be reinstalled" — describe a process that assumes a
   service channel we do not have. A BLE dropout mid-transfer on a battery printer is a realistic
   Home Assistant scenario, not an edge case.
3. **The app itself refuses over WiFi** ("Firmware upgrades require Bluetooth. Wi-Fi not supported"),
   which says something about how much margin the process has.
4. HA's `update` platform expects install to be safe and idempotent. This is neither.

**Recommendation: do not implement OTA.** If you want the protocol knowledge preserved, the section in
[protocol.md](protocol.md) already does that. Should this ever be revisited, the prerequisite is the
CRC32 framing in `packet.py` plus a user-supplied local firmware file — never an automatic download.

---

## D. Suggested order

| # | Item | Section | Hardware needed |
| --- | --- | --- | --- |
| 1 | Material code table for `consumable_type_name()` | A2 | No |
| 2 | Advanced2 heartbeat sensors | A3 | To verify, not to write |
| 3 | 14 model entries, `printheadPixels` from siblings | A1 | Per model |
| 4 | Pick print sequence from protocol version, not the model tuple | A1 | Per model |
| 5 | RFID gating on `rfidNotSupportVersions` | A4 | Only on old firmware |
| 6 | Calibration buttons (`0x8E`, `0x59`) and CancelPrint (`0xDA`) | A5 | Yes |
| 7 | Offline label enrichment | B1 | No |
| 8 | Cloud lookup opt-in | B2 | No, but needs an auth decision |
| — | Firmware check / OTA | C | Not recommended |
| — | WiFi transport, cutter, grayscale, margins | A6 | Separate projects |
