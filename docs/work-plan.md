# Work Plan

Task orders for the open items in [improvement-plan.md](improvement-plan.md). Written to be picked up
cold: each task states the files, the change, the data it needs, the tests, and what "done" means.

Baseline: `master` at 3.0.0. Background for every task is in
[app-gap-analysis.md](app-gap-analysis.md); protocol facts are in [protocol.md](protocol.md),
[device-info.md](device-info.md), [printing.md](printing.md), [rfid.md](rfid.md) and
[devices.md](devices.md). **The docs are the specification — do not re-derive protocol behaviour from
the app or from other projects without updating the docs in the same change.**

---

## Rules that apply to every task

**One task per branch, one task per PR.** They are independent unless the dependency graph below says
otherwise.

**Never break an existing entity.** Entity `key` values are in the entity registry of every user's
install. Adding is safe; renaming or removing a key orphans entities and loses history. If a key must
change, it needs a migration, which is out of scope here — pick a new key instead.

**Translations come in threes.** Any new entity, service field or config option needs its
`translation_key` added to all of:

- `custom_components/niimbot/strings.json`
- `custom_components/niimbot/translations/en.json`
- `custom_components/niimbot/translations/ko.json`

Korean is a first-class language in this repo, not an afterthought. If you cannot write the Korean
string, say so in the PR rather than shipping English text under a `ko` key. Icons go in
`custom_components/niimbot/icons.json`.

**`[HW]` means you cannot verify it.** Several tasks touch behaviour that only a physical printer can
confirm. For those: implement behind the existing capability checks, keep the current behaviour as the
fallback path, never make the unverified path the default for hardware that works today, and list what
the maintainer has to check in the PR description. Do not claim an `[HW]` item is verified.

**Tests.** `tests/` runs without hardware. `tests/fake_transport.py` records written packets and
replays canned responses — extend it rather than mocking `PrinterClient`. Every task below lists the
tests it must add. Run `pytest` before opening the PR.

**Coordinator safety.** Anything added to the update path must not be able to raise into
`_async_update_method`. An exception there is caught and swallowed as "Unable to fetch data", which
silently freezes *every* entity — that class of bug is why phase 1 existed.

**Do not bump `manifest.json` version** in a task PR. The maintainer batches releases.

---

## Repository orientation

| Path | Role |
| --- | --- |
| `custom_components/niimbot/niimprint/printer.py` | `PrinterClient`: commands, framing, print sequences |
| `custom_components/niimbot/niimprint/parser.py` | `NiimbotDevice`: connection lifecycle, poll cycle, `BLEData` |
| `custom_components/niimbot/niimprint/model.py` | Model table, capability metadata, code→name mappings |
| `custom_components/niimbot/niimprint/packet.py` | BCC framing only; CRC32 framing is not implemented |
| `custom_components/niimbot/sensor.py` etc. | HA platforms; entities are built from capability at setup |
| `custom_components/niimbot/__init__.py` | `PLATFORMS` (line 44), services `print` and `refresh_info` |
| `custom_components/niimbot/config_flow.py` | `OPTIONS_SCHEMA` is shared by the config flow and the options flow |

The poll cycle lives in `NiimbotDevice.update_device`; per-connection settings are read once by
`_load_printer_info` and re-read by the `niimbot.refresh_info` service.

---

## Dependency graph

```
T1 ──┐
T2 ──┼── independent, do in any order
T5 ──┘
T3 ──── T4        (T4 wants the model entries from T3)
T6 ──── independent (new platform)
T7 ──── independent
T8 ──── do last; measure after T1–T7
T9 ──── independent, but read T1 first — it removes most of T9's motivation
```

Suggested order: **T1 → T2 → T3 → T4 → T5 → T6 → T7 → T9 → T8.**

---

## T1 — Render the RFID `type` byte as a material code [Done]

**Goal.** Stop showing `Unknown(19)` for transparent thermal stock and stop showing the wrong label
type for six other codes.

**Why.** The `type` byte in the RFID payload is very likely a *material* code from a 37-value
enumeration, not a label type from the 1–11 set. Evidence and the full table:
[rfid.md §4](rfid.md#4-consumable-type-code-type).

**Files.**

- `custom_components/niimbot/niimprint/model.py` — `_LABEL_TYPE_NAMES`, `consumable_type_name()`
- `custom_components/niimbot/niimprint/parser.py` — `_apply_rfid_info` (~line 183), `_apply_ribbon_rfid_info`, `_load_printer_info` (~line 415)
- translations (three files) if new state strings are introduced

**Change.**

1. Add `_MATERIAL_NAMES: dict[int, str]` to `model.py` from the table in
   [rfid.md §4](rfid.md#4-consumable-type-code-type). Add `material_name(code)` returning the name or
   `f"Unknown({code})"`. Keep `consumable_type_name()` as the label-type mapping — do not repurpose
   it; both readings stay available.
2. `_apply_rfid_info` currently does this:

   ```python
   # Prefer the loaded tag's type over PrinterInfo LabelType — same code space.
   type_code = info.get("type")
   if type_code is not None:
       self.ble_data.labeltype = int(type_code)
       self.ble_data.sensors["labeltype"] = consumable_type_name(type_code)
   ```

   The comment's premise ("same code space") is what this task disproves. Stop overwriting
   `labeltype` from the tag. `PrinterInfo` key 3 is the authoritative label type and already populates
   that sensor in `_load_printer_info`. Route the tag's byte to the **consumable/material** sensor
   instead.
3. The label side has no material sensor today — the ribbon side has `ribbon_type`. Add a
   `consumable_type` sensor (new key, mirroring `ribbon_type`) fed by `material_name(type_code)`, and
   switch `ribbon_type` to `material_name` too. Keep `type_code` in the existing attributes so the raw
   value stays visible.

**Tests.** `tests/test_model.py` (new): `material_name` for 1, 19, 129, an unmapped code, and `None`.
A parser-level test that a tag read no longer changes `sensors["labeltype"]`.

**Acceptance.** A tag reporting 19 shows "Transparent Thermal Paper" on the consumable type sensor;
the `labeltype` sensor reflects `PrinterInfo` key 3 only; no existing entity key changes meaning
except `ribbon_type`, which gains coverage rather than losing it.

**`[HW]`.** The material reading is inference — no tag observed by this project has returned a value
above 11. The decisive test is in [rfid.md §4](rfid.md#4-consumable-type-code-type): black-mark stock
made of plain thermal paper reports `2` under the label-type reading and `1` under the material
reading. Note it in the PR as unconfirmed. Since both mappings agree on the common codes 1 and 5,
shipping this cannot regress ordinary gap or transparent stock.

---

## T2 — Surface the Advanced2 heartbeat fields [Done]

**Goal.** Stop computing six values per poll and throwing them away.

**Why.** `PrinterClient._parse_heartbeat_advanced2` (printer.py ~line 895) returns `temperature`,
`ribbon_rfidreadstate`, `ribbonstate`, `wifi_rssi`, `lighting_error` and `voltage_state`.
`update_device` copies four of the ten fields.

**Files.**

- `custom_components/niimbot/niimprint/parser.py` — the two heartbeat apply sites (~line 516 in
  `update_device`, ~line 608 in the print path)
- `custom_components/niimbot/sensor.py`, `custom_components/niimbot/binary_sensor.py`
- translations (three files), `icons.json`

**Change.** Copy the fields into `sensors` only when the key is present in the heartbeat dict, and
create the entities only when a value has actually been seen — protocol-v2 hardware must not gain six
`unknown` entities.

| Key | Platform | Class | Notes |
| --- | --- | --- | --- |
| `printhead_temperature` | sensor | `TEMPERATURE` | Unit unconfirmed, assume °C, diagnostic |
| `ribbonstate` | binary_sensor | — | `0` means inserted → use the existing `inverted` field |
| `ribbon_rfidreadstate` | binary_sensor | — | non-zero means readable |
| `wifi_rssi` | sensor | `SIGNAL_STRENGTH` | dBm, diagnostic |
| `voltage_state` | sensor | — | raw, diagnostic, disabled by default |
| `lighting_error` | sensor | — | raw, diagnostic, disabled by default |

Follow the deferred-creation pattern already in `sensor.py` (`_add_rfid_entities` plus the listener
that keeps checking until capability is known) rather than inventing a second mechanism.

**Tests.** Advanced2 payloads at each length boundary — 9, 11, 13 and 14 bytes — asserting which keys
appear. A short payload must produce no entities and no exception.

**Acceptance.** On an Advanced1 printer nothing changes at all. On an Advanced2 printer the six
entities appear with plausible values.

**`[HW]`.** All six. No Advanced2 device has been observed by this project; the parse offsets in
[device-info.md](device-info.md#advanced2-response-0xd9) are themselves unverified. Temperature unit
and scale are guesses.

---

## T3 — Add the 14 missing model IDs [Done]

**Goal.** Stop routing new hardware to the oldest print sequence.

**Why.** `get_printer_meta_by_id()` returns `None` for these codes, so `PrinterModel.UNKNOWN` is used
and `print_image` sends the Old D11 sequence — wrong for all of them. Three of the codes (3840, 4352,
5120) already appear in `INVERTED_LID_MODELS`, so the codebase half-knows about printers it cannot
print on.

**Files.** `custom_components/niimbot/niimprint/model.py` — `PrinterModel`, `modelsLibrary`,
`_CAPABILITIES_BY_ID`, `PrinterModelMeta`.

**Data.** Full capability rows are in
[app-gap-analysis.md §A1](app-gap-analysis.md#a1-14-model-codes-have-no-entry-in-modelpy) and
[devices.md](devices.md). Everything except `printheadPixels` is vendor-published and can be entered
as fact.

`printheadPixels` is **not** published anywhere. Measured ratios across the 63 modelled printers:
7.68–8.00 px/mm at 203 dpi, 11.34–11.87 px/mm at 300 dpi, and the head is often narrower than the
paper the model accepts. Starting estimates, each from the closest same-series sibling:

| Code | Model | Estimate | Basis | Confidence |
| --- | --- | --- | --- | --- |
| 3840 | H1 | 96 | D11 / D110 / B16 at 15 mm | low — could be 120 like B18 |
| 4098 | B1 SE | 384 | B1 (4096) | medium |
| 4352 | H1S | 96 | as H1 | low |
| 4610 | EP2M_H | 591 | M2_H (4608) | high — same series |
| 4868 | K3_ITD | 656 | K3 (4864) | high |
| 5120 | C1 | 178 | D11_H, 300 dpi at 15 mm | **lowest** — tube printer, geometry unlike anything modelled |
| 5121 | EP1C | 178 | as C1 | lowest |
| 6144 | K2 | 480 | K series at 8 px/mm, 60 mm | medium |
| 6400 | M3 | 851 | B32-class 300 dpi head | low — 920 also plausible |
| 6402 | EP3M | 851 | as M3 | low |
| 6656 | B4 | 832 | T2S at 107 mm | medium |
| 6657 | B4 Pro | 1248 | B4 scaled 203→300 dpi | low |
| 7168 | K4 | 656 | K3 (4864) | high |
| 7424 | A1 Pro | 178 | B18 at 15 mm scaled to 300 dpi | low |

**Change.** Add the enum members, the `modelsLibrary` entries and the `_CAPABILITIES_BY_ID` rows. Add
an optional `printheadPixelsEstimated: NotRequired[bool]` to `PrinterModelMeta`, set it on every entry
above, and have `print_image` log a warning once per job when it is set, naming the model and asking
the user to report whether output is correct. A wrong `printheadPixels` produces skewed or truncated
output; it does not damage hardware.

Two related notes to record in code comments, not to act on here:

- A1 Pro and B16 both declare print direction **270**, which `PrintDirection` cannot express. Model
  them as `LEFT` for now, with a comment. Resolving 270 vs 90 is `[HW]`.
- K4 is the first model with a density range of 1–15 default 7 and an automatic cutter. Density is
  handled by the existing range validation; the cutter is out of scope.

**Tests.** `get_printer_meta_by_id()` returns a complete meta for all 14 codes, with `rfid` and the
density triple populated. Assert `printheadPixelsEstimated` is set on exactly these entries.

**Acceptance.** All 14 resolve to a named model with correct DPI, direction, paper types, RFID class
and density range. No existing model's metadata changes.

**`[HW]`.** Every `printheadPixels` above, plus print direction 270. Do not present the estimates as
measured.

---

## T4 — Select the print sequence from capability, not a model tuple [Done]

**Goal.** An unrecognised printer should pick a sane sequence instead of the oldest one.

**Why.** `print_image` (printer.py ~line 273) dispatches on hardcoded model tuples. Every new model
needs a code change in the right branch, and anything unmatched falls to `print_image_b1` — or, for
`UNKNOWN`, to `print_image_d11_v1`, the Old D11 sequence.

**Depends on T3** for the model entries, though the mechanism can be built first.

**Files.** `custom_components/niimbot/niimprint/model.py`,
`custom_components/niimbot/niimprint/printer.py`.

**Change.**

1. Add `class PrintGeneration(Enum)` with `OLD_D11`, `D110`, `V4`, `V5`, and a required `generation`
   field on `PrinterModelMeta`. Populate it for every existing model from the current dispatch tuples —
   this part must be behaviour-preserving and is mechanical:

   | Generation | Models |
   | --- | --- |
   | `OLD_D11` | D11, D11S |
   | `D110` | D110, B21S, B21S_C2B |
   | `V5` | D11_H, D11_PRO, B21_PRO, D110_M, B2_PRO |
   | `V4` | everything else |

2. Rename the four methods to match [printing.md §4](printing.md#4-print-sequences), which the current
   names contradict: `print_image_d11_v1` → `print_image_old_d11`, `print_image_d110` unchanged,
   `print_image_b1` → `print_image_v4`, `print_image_d110m_v4` → `print_image_v5`. These are internal;
   no service or entity depends on the names.
3. Dispatch on `meta["generation"]`. When the model is unknown, fall back to the protocol version from
   `PrinterStatusData` — already read and cached — mapping `>= 5` → `V5`, `3`/`4` → `V4`. When neither
   is known, default to **`V4`** and log a warning naming the device type.

**Behaviour change to call out in the PR:** the `UNKNOWN` default moves from Old D11 to V4. This is
deliberate — every D11-era model is in the table, so what reaches `UNKNOWN` today is new hardware, for
which Old D11 is always wrong. A user with an unlisted *old* printer could regress; the warning log
line is how they will find out, and it must name the device type so the model can be added.

**Tests.** Sequence assertions per generation against `FakeTransport`: Old D11 sends `PrintClear` and a
height-only `SetPageSize`; V5 omits `PageStart` and injects the fire-and-forget heartbeat; V4 sends the
7-byte `PrintStart` and 6-byte `SetPageSize`. Plus: unknown model with protocol version 5 picks V5;
unknown model with no protocol version picks V4 and logs.

**Acceptance.** Every currently supported model sends byte-for-byte the same sequence as before the
change. Verify by asserting against captured packets, not by inspection.

---

## T5 — Skip RFID reads on firmware that cannot do RFID [Done]

**Goal.** Remove a guaranteed per-poll timeout on affected units.

**Why.** RFID reading arrived by firmware update. The vendor's device database lists, per model, the
firmware versions on which it does not work
([app-gap-analysis.md §A4](app-gap-analysis.md#a4-firmware-version-gated-capabilities-are-ignored)).
On those units `RfidInfo` is currently issued every poll and burns the full read budget.

**Files.** `custom_components/niimbot/niimprint/model.py`,
`custom_components/niimbot/niimprint/parser.py` (`_maybe_read_rfid`).

**Change.** Add `_RFID_UNSUPPORTED_FIRMWARE: dict[int, frozenset[str]]` keyed by model code, and
`rfid_supported_on_firmware(model_id, sw_version) -> bool`. `SOFTVERSION` is read as
`data[0] + data[1] / 100`, so format it back with `f"{int(v)}.{round((v - int(v)) * 100):02d}"` to
compare against the published strings. Unknown or unreadable version → assume supported, i.e. current
behaviour.

Log once per connection when the gate trips, at info level, naming the version — a user whose
consumable sensors are empty needs to be able to find out why.

**Data.** The lists are in the gap analysis. Note 512 appears twice (D11 and Hi-NB-D11) with slightly
different sets; take the union, since the version is what matters and the two share a code.

**Tests.** An affected model on an affected version issues no `RfidInfo` packet; the same model one
version up does; an unknown version does.

**Acceptance.** No behaviour change on any printer whose firmware is not in the lists.

---

## T6 — Printer action buttons [Done]

**Goal.** Expose the actions the app has and this integration does not.

**Files.** New `custom_components/niimbot/button.py`; `PLATFORMS` in `__init__.py` line 44;
`custom_components/niimbot/niimprint/printer.py` for the commands; translations (three files);
`icons.json`.

**Change.** Add the commands to `RequestCodeEnum` and a method per command on `PrinterClient`, then a
button entity each. All are single request/response pairs documented in
[protocol.md §4.3](protocol.md#43-settings-and-state) and
[device-info.md §7](device-info.md#7-other-state-commands).

| Command | Entity | Notes |
| --- | --- | --- |
| `0x8E` LabelPositioningCalibration | Calibrate Label Position | Response `0x8F`, `data[0] == 1` on success. Values 1–2 make B1 eject ~15 cm |
| `0x59` CalibrateHeight | Calibrate Roll Feed | Response `0x69` |
| `0xDA` CancelPrint | Cancel Print | Response `0xD0`. Enable only while a job is running |
| `0x28` PrinterReset | Reset Printer Settings | Response `0x38`. Clears settings such as sound |
| `0x5A` PrintTestPage | Print Test Page | Response `0x6A` |

Gate calibration on the model's `isSupportCalibration` — which is **not** currently in
`PrinterModelMeta` and has to be added from [devices.md](devices.md) as part of this task.

Cancel Print is the one with real ordering risk: it lands mid-transfer while `set_image` is writing
rows. Route it through the existing `NiimbotDevice.lock` and make the print loop check for
cancellation between rows rather than firing the packet from under it.

**Tests.** Each command builds the documented packet and parses the documented response. Cancel while
a fake print is in flight terminates the row loop without raising.

**Acceptance.** Buttons appear only on models that support the action; each reports failure through
`HomeAssistantError` rather than silently.

**`[HW]`.** All of them — every one moves paper or changes stored settings. `PrinterReset` in
particular is not undoable from software. Ship it with a confirmation-worthy name and say plainly in
the PR that it is unverified.

---

## T7 — Validate `label_type` against the model's paper types [Done]

**Goal.** Reject an unsupported label type locally instead of letting the printer reject it.

**Why.** The `label_type` print-service parameter is validated as 1–11 but not against the model's own
`paperTypes`, so an unsupported value comes back as `SetPrintLabelMaterialNoSupport (0x21)` after a
round-trip, mid-print.

**Files.** `custom_components/niimbot/niimprint/printer.py` (`set_label_type`, and the `label_type`
default in the four print sequences), `custom_components/niimbot/__init__.py` (`printservice`,
~line 216), `services.yaml`, translations.

**Change.** Validate against `meta["paperTypes"]` mapped through `label_type_code()`. When the caller
omits `label_type`, default to the model's **first** `paperTypes` entry rather than the hardcoded `1`.
Raise a clear `ValueError` naming the accepted values; `printservice` already converts that to
`HomeAssistantError`.

**Tests.** A model whose `paperTypes` excludes Continuous rejects `label_type: 3`; the default for a
PVC-tag-only model is 6, not 1.

**Acceptance.** No printer that works today receives a different label type than it does now — check
that each model's first `paperTypes` entry is the one currently being sent, and where it is not, say
so in the PR rather than silently changing it.

---

## T8 — Adaptive flow control

**Goal.** Stop paying a fixed per-row cost that the link does not need.

**Why.** Defaults are 10 ms between rows and a confirmation every 16 rows. `PrinterClient._timings`
already collects per-write latency and nothing reads it.

**Do this last.** T1–T7 change what goes over the link; measuring before they land measures the wrong
thing.

**Files.** `custom_components/niimbot/niimprint/printer.py` (`set_image`, `_pace_after_row`).

**Change.** Adapt the batch size during the page from observed latency: widen while writes stay fast,
back off immediately when latency rises or a `PrinterCheckLine` response is late. Start conservative.
The user's explicit `wait_between_print_lines` / `print_line_batch_size` values must remain a ceiling —
never exceed what the user configured, only stay under it.

**Tests.** With a fake transport reporting rising latency, the batch size decreases; with flat low
latency it increases to the configured ceiling and no further.

**Acceptance.** A page prints with the same packets in the same order; only the response-request
cadence differs. Report measured before/after timings for one real label in the PR.

---

## T9 — Optional online label lookup

**Goal.** Let users who want it resolve a label SKU to its name, size and preview image, without
making the integration depend on a cloud service.

**Read first.** [app-gap-analysis.md §B](app-gap-analysis.md#b-cloud-label-lookup-as-an-opt-in). Two
facts shape this task: the RFID tag carries **no** dimensions on any model, so this is the only route
to label geometry; and T1 delivers the material name offline, which is most of what users actually ask
for. If T1 has landed and nobody has asked for size since, consider whether this task is still wanted.

### T9.0 — Verification gate, do this before writing any code

The endpoints below were found in the app binary. The app sends `Authorization: Bearer …` and sits
behind `/oauth/*` login. **Whether any endpoint answers unauthenticated has not been tested.**

Make **one** unauthenticated `GET` to `https://print.niimbot.com/labels/{id}/consumable-attributes`
with a known SKU and record the status and body. Then stop and report:

- **If it answers with usable data** — continue to T9.1.
- **If it requires authentication** — stop. Do not add a username/password or token field to the
  config flow, do not scrape a token out of the app, do not proxy through a third party. Close the
  task with the finding recorded here and in the gap analysis. Asking Home Assistant users for their
  NIIMBOT credentials to display a label name is not a trade this integration makes.

Do not run the probe from within Home Assistant, do not loop it, and do not test with more than a
couple of SKUs.

### T9.1 — Implementation, only if T9.0 passed

**Files.** New `custom_components/niimbot/cloud.py`; `const.py`; `config_flow.py` (`OPTIONS_SCHEMA`);
`custom_components/niimbot/niimprint/parser.py` or a thin layer above it; `sensor.py`; translations.

**Option.**

```python
# const.py
CONF_USE_CLOUD_LABEL_INFO = "use_cloud_label_info"
DEFAULT_USE_CLOUD_LABEL_INFO = False
```

Add it to `OPTIONS_SCHEMA` in `config_flow.py` as a plain `bool`. Because that schema is shared, it
appears in the initial config flow, the bluetooth-confirm step and the options flow at once, which is
what we want. Existing entries keep the default and stay fully offline.

**Behaviour.**

- Default **off**. Nothing may reach the network unless the user turned it on.
- **Never block the coordinator.** The lookup does not run inside `update_device`. Trigger it from the
  roll-change path — `EVENT_ROLL_CHANGED` already fires when the tag UUID changes — and on the first
  poll after startup if the current SKU is not cached.
- **Cache per SKU on disk** with `homeassistant.helpers.storage.Store`, version 1, key
  `niimbot_label_cache`. A SKU that has been resolved once must never be fetched again. Cache negative
  results too, with a retry-after, so an unknown SKU does not retry every restart.
- **One attempt, 10 s total timeout, no retry loop.** Use
  `homeassistant.helpers.aiohttp_client.async_get_clientsession(hass)`.
- **Results go on attributes of the existing `label_sku` sensor** — `label_name`, `label_width_mm`,
  `label_height_mm`, `preview_url`. Do not create entities that exist only when the option is on;
  that makes the two configurations diverge and breaks dashboards when the option is toggled.
- **Failure is a debug log line.** No entity goes unavailable, no repair issue, no user-visible error.
  The integration must work exactly as it does today when the lookup fails.
- **Nothing but the SKU leaves the machine.** No serial number, no UUID, no MAC, no HA instance id.

**Strings.** The option's description in all three translation files must state plainly that enabling
it sends the loaded label's product code to a NIIMBOT server. Users choosing this integration for a
local-only setup are entitled to know before they tick the box, not after.

**Tests.** Lookup disabled → no HTTP call, with the session mocked to fail if touched. Enabled with a
cached SKU → no HTTP call. Enabled with an uncached SKU → one call, attributes populated. Timeout and
non-200 → attributes absent, no exception, entity still available.

**Acceptance.** With the option off, the integration's network behaviour is byte-identical to 3.0.0.
With it on, a known roll gains name and size attributes, and pulling the network cable changes nothing
except that those attributes stop updating.

**Out of scope.** Template/product catalogue sync, the shop endpoints, print statistics upload,
account login, and anything under `/oauth/*`.

---

## Reporting back

Each PR should state: what was implemented, what was verified and how, what is `[HW]`-unverified and
what the maintainer needs to check, and anything found along the way that contradicts the docs — with
the doc updated in the same PR. If a task turns out to be wrong or impossible as specified, say so and
stop; do not substitute a different change.
