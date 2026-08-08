# Implementation Plan: Sensors and Print Pipeline

Derived from the protocol reference in [protocol.md](protocol.md), [device-info.md](device-info.md),
[printing.md](printing.md), [rfid.md](rfid.md) and [devices.md](devices.md), compared against the
current implementation.

Baseline: `master` at version 2.3.1.

## Implementation progress

| Phase | Status | Notes |
| --- | --- | --- |
| 1 Correctness | **Done** | Timeout/`PrinterTimeout`, Advanced2 heartbeat fallback, RFID parse fixes, battery None guard |
| 2 RFID sensors | **Done** (label) | Remaining/used/total/usage/SKU/type/UUID + `niimbot_roll_changed`; ribbon (2.5) still **[HW]** |
| 3 Device info | Partial | 3.5 last error done; 3.1/3.2/3.3/3.4/3.6 not started |
| 4 Print pipeline | Partial | 4.1–4.3 row encoding done; 4.4–4.8 not started |
| 5 Model coverage | Partial | RFID/density meta + 5.3/5.4 done; 5.1 missing models + 5.2 generation field not started |

Work is grouped into five phases. **Phase 1 is bug fixing and should land before anything else** —
several of the items below are latent crashes that silently disable the whole coordinator update, so
new sensors built on top of the current data flow would inherit them.

Items marked **[HW]** cannot be validated without a physical printer. Implement them behind the
existing model/capability checks, keep the previous behaviour as fallback, and list them for the
maintainer to confirm.

---

## Phase 1 — Correctness

### 1.1 Heartbeat with no battery field crashes the entire update

`parser.py:204`

```python
self.ble_data.sensors["battery"] = _battery_percentage(heartbeat["powerlevel"], self.ble_data.model)
```

`PrinterClient.heartbeat` only sets `powerlevel` for payload lengths 10, 13 and 19. For lengths 20
and 9 — and for any length not in the `match` — it stays `None`. `_battery_percentage` then evaluates
`float(None) * 25.0` and raises `TypeError`.

That exception propagates to `_async_update_method`, which catches everything and returns the previous
`ble_data`. Net effect: on any model whose heartbeat is 20 or 9 bytes, **every** sensor silently stops
updating and the log only says "Unable to fetch data".

Fix:

- `_battery_percentage` returns `None` when `powerlevel is None`.
- Only assign `sensors["battery"]` when a value was obtained, so the entity goes unknown rather than
  poisoning the refresh.
- Add a `case _:` to the `match` in `PrinterClient.heartbeat` that logs the unrecognised length and
  the raw payload at debug level. Unknown lengths are the main lead for adding model support.

### 1.2 Timeout handling in `_transceive`

`printer.py:537`. Two separate problems.

**Unguarded `None`.** `heartbeat()` does `len(packet.data)` without checking the return value, and
`start_print`, `set_label_type`, `set_label_density` and friends all index `packet.data[0]` the same
way. `_transceive` returns `None` when it completes its six iterations having received packets but none
matching `respcode` — which is exactly what happens during printing, when unsolicited `0xD3` status
packets keep `_recv()` returning early. So the `None` path is reachable in normal operation and turns
into `AttributeError`.

Same pattern in `parser.py:167`: `int(self.ble_data.devicetype)` where `get_info` may have returned
`None`.

**A 30-second stall per attempt.** `BLETransport.read` calls `read_notify(30)`, so when nothing
arrives at all, `_recv()` raises `asyncio.TimeoutError` after 30 s rather than returning empty. That
escapes `_transceive` directly — so the timeout is 30 s in the simple case, but when the printer
answers with a packet the caller isn't matching (see 1.3), the first iteration returns quickly and the
second blocks the full 30 s.

The stall happens inside `NiimbotDevice.lock`, so a heartbeat that goes unmatched blocks prints for
that whole window.

Fix:

- Return a typed failure instead of `None`. A `PrinterTimeout(RuntimeError)` raised at the end of
  `_transceive` lets callers distinguish "printer did not answer" from "printer answered with an
  error", and removes the need to guard every call site individually.
- Make the read timeout a parameter with a much shorter default for status commands. 30 s is
  appropriate for a print acknowledgement, not for a heartbeat on a 600 s poll cycle.
- Deduct elapsed time across iterations so the total wait is bounded by one budget rather than six
  independent 30 s waits.

### 1.3 Protocol v3+ printers never answer the heartbeat we send

`printer.py:615` sends `HEARTBEAT` with payload `\x01` (Advanced1), and `_transceive` derives its
expected response as `reqcode + 1` — so it matches `0xDD` and nothing else. Printers on protocol
version 3 and above reply on `0xD9` (Advanced2) instead. That packet is received, fails the `respcode`
check, and is dropped; the next iteration then stalls for the full 30 s read timeout from 1.2 before
the update fails.

See [device-info.md](device-info.md#4-heartbeat-0xdc) for the request types and the Advanced2 payload
layout.

Fix:

- Extend `_transceive` (or add a variant) to accept a **set** of acceptable response codes.
- `heartbeat()` accepts any of `0xDD`, `0xDE`, `0xDF`, `0xD9` and dispatches parsing on the response
  code rather than on payload length alone.
- Add `_parse_heartbeat_advanced2()` for `0xD9` using the fixed-offset layout. Note the inverted-lid
  model list does **not** apply to Advanced2.
- Cache which heartbeat type worked on the device object and prefer it on subsequent polls.

**[HW]** No Advanced2 device is available to verify against. Keep Advanced1 as the first attempt so
current hardware is unaffected, and fall back to `\x04` only after Advanced1 fails.

### 1.4 `get_rfid()` parsing

`printer.py:586`. Two defects, both detailed in [rfid.md](rfid.md#two-bugs-to-avoid):

- Presence is tested as `data[0] == 0`, which is the first byte of the UUID. A tag whose UUID starts
  with `00` is reported as absent. The correct test is a payload length of 1.
- `struct.unpack(">HHB", data[idx:])` requires exactly 5 trailing bytes. Models that append the
  optional `capacity` field send 7, and the call raises `struct.error`.

Fix: slice explicitly, parse `capacity` only when bytes remain, and return it in the dict.

### 1.5 `paperstate` polarity is probably inverted

`binary_sensor.py:46` comments `paperstate != 0 means paper is present`, but the protocol convention
is the opposite of that — for the paper field `0` means *inserted*, the same inversion the lid field
uses. See [device-info.md](device-info.md#advanced1-response-0xdd).

**[HW]** Do not flip this blindly. Add a debug log of the raw `paperstate` value alongside the lid
value in `parser.py`, and have the maintainer confirm with the printer open and closed, loaded and
empty. Then apply the fix and use the existing `NiimbotBinarySensorEntityDescription.inverted` field
for it.

### 1.6 Dead code

- `NiimbotBinarySensorEntityDescription.inverted` is declared and never read. Either use it (1.5) or
  drop it.
- `sensor.py:41-68` — six commented-out `SensorEntityDescription` blocks.
- `parser.py:178-198` — the `get_info` calls that would populate `density`, `printspeed`, `labeltype`,
  `languagetype` and `autoshutdowntime` are commented out, so the five `if ... is not None` blocks
  below them are unreachable. Phase 3 replaces this properly; remove it here or fold it into 3.1.

**Acceptance for Phase 1:** coordinator refresh no longer raises on any heartbeat length; a heartbeat
timeout produces a distinguishable log line; `get_rfid()` handles 5- and 7-byte tails and a
zero-leading UUID.

---

## Phase 2 — Consumable (RFID) sensors

The highest-value addition. `get_rfid()` already works but is wired to nothing, so the roll's
remaining-label count is sitting one function call away.

### 2.1 Gate on capability

`model.py`'s `PrinterModelMeta` currently carries `model`, `id`, `dpi`, `printDirection`,
`printheadPixels` and `paperTypes`. Several items in this plan need fields that are not there yet
(RFID class here, density range in 5.3, print generation in 5.2), so extend the TypedDict once:

```python
class RfidClass(Enum):
    NONE = "none"
    LABEL = "label"
    RIBBON = "ribbon"
    LABEL_RIBBON = "label_ribbon"

class PrinterModelMeta(TypedDict):
    ...                          # existing fields
    rfid: RfidClass
    densityMin: int
    densityMax: int
    densityDefault: int
    generation: PrintGeneration  # see 5.2
```

Every value except `generation` is in [devices.md](devices.md); there are 60-odd entries, so populate
them by script rather than by hand and keep the table as the source of truth.

Skip the `RfidInfo` call entirely for `NONE` models — otherwise every poll spends a full read timeout
on a command the printer will never answer.

### 2.2 Read the tag in `update_device`

In `parser.py`, after the heartbeat:

- Skip when the model's RFID class is `NONE`.
- Skip when `rfidreadstate` is present and falsy — the lid is open or no stock is loaded.
- Call `get_rfid()` inside its own `try`/`except` so a tag failure never takes the refresh down.
- **Retain the previous tag data on failure.** An open lid must not make the remaining-labels sensor
  go unavailable; that would break history and any automation that reacts to a threshold.
- Store into new `sensors` keys and pre-seed them in `NiimbotDevice.__init__`, because both platforms
  create entities from the keys present in `sensors` at setup time.

### 2.3 New sensors

| Entity | Source | Notes |
| --- | --- | --- |
| Labels Remaining | `total_len - used_len` | `state_class=MEASUREMENT`, no unit. The headline sensor |
| Labels Used | `used_len` | `state_class=TOTAL_INCREASING` |
| Labels Total | `total_len` | Diagnostic; changes only on roll swap |
| Consumable Usage | `used_len / total_len * 100` | `%`, `MEASUREMENT` |
| Label SKU | `barcode` | Diagnostic, text state |
| Consumable Type | `type` | Diagnostic. Map through the table in [rfid.md](rfid.md#4-consumable-type-code-type) |
| Tag UUID | `uuid` | Diagnostic, `entity_registry_enabled_default=False` |

Put `serial` (batch number) and `capacity` on the Labels Remaining sensor as attributes rather than
creating entities for them.

Guard the percentage against `total_len == 0`.

### 2.4 Roll-change detection

Track the last seen `uuid` on the device object. When it changes, fire a `niimbot_roll_changed` event
carrying the old and new barcode plus the new total. This is what makes "notify me when I load a new
roll" and "reset my consumption counter" possible in automations.

### 2.5 Ribbon tag

For `LABEL_RIBBON` and `RIBBON` models, add `RfidInfo2` (`0x1C`, response `0x1D`, same payload
structure) and a parallel set of ribbon entities.

**[HW]** No ribbon-class hardware available. Implement `get_rfid2()` sharing the parse routine with
`get_rfid()`, keep it behind the capability gate, and leave the entities out of the default set until
confirmed.

**Acceptance:** on a label-class printer with genuine stock, Labels Remaining reports a plausible
count and decrements as pages print; opening the lid does not make it unavailable; an RFID-less model
creates none of these entities and shows no added latency per poll.

---

## Phase 3 — Device information sensors

### 3.1 Settings read via `PrinterInfo`

Replace the commented-out block from 1.6 with a real implementation. All of these are one `0x40` call
each; see [device-info.md](device-info.md#3-printer-info-0x40).

| Entity | Key | Notes |
| --- | --- | --- |
| Print Density | 1 | Diagnostic. Compare with the model's range from [devices.md](devices.md) |
| Print Speed | 2 | Diagnostic |
| Label Type | 3 | Map through the label type table. Also the reference value for resolving the `type` ambiguity in 2.3 |
| Auto Shutdown | 7 | Index 1–4, not minutes. Present as the index with the typical minutes as an attribute |
| Battery Level | 10 | See 3.2 |
| Bluetooth MAC | 13 | Diagnostic, disabled by default. Bytes are reversed |
| Print Area | 15 | **[HW]** payload layout unverified |

These are settings, not live state. Read them once and cache like `serial_number` is cached today, and
add a `niimbot.refresh_info` service to force a re-read. Polling seven extra commands every 600 s on a
battery printer is not worth it.

Language (key 6) has no known value mapping — skip it rather than exposing a raw integer.

### 3.2 Battery from the authoritative source

`_battery_percentage` currently derives the percentage from the heartbeat's `powerlevel` and
special-cases `B1_PRO` as a direct 0–100 value.

`PrinterInfo` key 10 is the documented charge level and is a clean 0–4 bucket
([device-info.md](device-info.md#batterychargelevel-key-10)). Prefer it, fall back to the heartbeat
field, and keep the `B1_PRO` special case since it is empirically established.

Expose the raw bucket as an attribute so the 25 % quantisation is visible rather than looking like a
precise reading.

### 3.3 Live state from Heartbeat Advanced2

Once 1.3 lands, these become available on protocol-v3+ models. Create them only when the Advanced2
parse actually produced a value.

| Entity | Platform | Notes |
| --- | --- | --- |
| Print Head Temperature | sensor | `TEMPERATURE`. Unit unconfirmed, assume °C |
| Ribbon Loaded | binary_sensor | `0` means inserted |
| Ribbon RFID Readable | binary_sensor | non-zero means success |
| WiFi Signal | sensor | `SIGNAL_STRENGTH`, dBm, diagnostic |
| Voltage State | sensor | Diagnostic, raw value |
| Lighting Error Code | sensor | Diagnostic, raw value |

**[HW]** All six.

### 3.4 Protocol version and colour support

`PrinterStatusData` (`0xA5` → `0xB5`) yields the protocol version and a colour-support flag
([device-info.md](device-info.md#2-protocol-version-printerstatusdata-0xa5)).

Two reasons to add it: it is the correct way to pick the heartbeat variant in 1.3, and it is a better
signal than the model-ID table for choosing a print sequence in 5.2.

Read once at connect, expose as diagnostic sensors, cache on the device object.

### 3.5 Last error

Nothing surfaces `0xDB` today; a failed print raises and the code is lost to the log.

Add a diagnostic sensor holding the last `PrinterErrorCodeEnum` name with a timestamp attribute, set
from the `PrinterError` handler in `parser.print_image`. This is the difference between a user
reporting "printing failed" and reporting `LackPaper`.

### 3.6 Live print progress

`GET_PRINT_STATUS` is already polled during printing but the value is discarded. Surface it as a
progress sensor (`%`) updated through the same callback mechanism
`NiimbotPrintDurationSensor` uses for its 1-second timer.

Keep `page`/`pagePrintProgress`/`pageFeedProgress` separate internally rather than collapsing to a
single max as `get_print_status` does now — the collapse is what forces the stale-progress workaround
in 4.4.

---

## Phase 4 — Print pipeline

Ordered by benefit-to-risk. 4.1 and 4.2 are the significant wins.

### 4.1 Row de-duplication via `repeats`

`PrintBitmapRow` and `PrintEmptyRow` both carry a `repeats` byte, and `set_image` always sends `1`.
Blank runs are already collapsed through `PrintEmptyRow`, but **identical non-blank rows are not.**

Typical label artwork — borders, solid bars, block text, barcodes — contains long runs of identical
rows. Coalescing them into a single packet with `repeats = n` (cap 255) removes those packets outright,
and because throughput here is dominated by per-packet round-trips rather than bytes, the saving is
close to linear in rows removed.

Low risk: same command, same layout, a field the protocol already defines.

### 4.2 `PrintBitmapRowIndexed` (`0x83`)

For rows with 6 or fewer black pixels, send pixel indices instead of the full row bitmap
([printing.md](printing.md#printbitmaprowindexed-0x83)). On a 384-pixel printer that is 48 bytes
replaced by at most 12.

Mostly-empty rows dominate text and barcode labels, so this compounds with 4.1.

**Hard constraint: above 6 black pixels the printer may power itself off.** Count first, and fall back
to `0x85` whenever the count exceeds 6 or the printhead pixel count is unknown. Put the threshold in a
named constant and cover the boundary (exactly 6, exactly 7) with unit tests.

### 4.3 Fix the bitmap counter bytes

`set_image` computes the three counters over the first 12 bytes of the row in 4-byte chunks, which is
correct only for a 96-pixel print head. Every wider model gets counters describing a fraction of the
row ([printing.md](printing.md#the-three-counter-bytes)).

Implement both documented modes, selecting on `printheadPixels` (already present in
`PrinterModelMeta`):

- **split** when the row fits in `floor(printheadPixels / 8 / 3) * 3` bytes — per-chunk counts.
- **total** otherwise — `[0x00, total & 0xFF, total >> 8]`. Note the low byte precedes the high byte,
  unlike every other multi-byte field.

Printing currently works with wrong counters, so treat this as correctness rather than a fix for a
visible symptom, and keep the old behaviour reachable behind a flag in case a model does validate them.

### 4.4 Completion detection via `0xE0`

Printers emit `0xE0` unsolicited as each page completes, carrying a `u16` page number
([printing.md](printing.md#page-index-notifications-0xe0)).

Waiting for that beats polling: it removes the poll traffic, removes the 0.5 s poll granularity from
every print, and sidesteps the stale-progress trap that `print_image_b1` works around with a 30-second
timeout and a `started` flag.

Implement as: register interest in `0xE0` in `BLETransport`, wait for `page == total`, and keep the
existing poll loop as the fallback path with a shorter timeout. Do not remove the polling code — not
all models emit `0xE0`.

### 4.5 Multi-copy printing

Every print currently declares one page and one copy, so N labels means N full BLE sequences including
reconnect.

The protocol carries copies natively: `PrintQuantity` (`0x15`) on the older generations, and the
copies field of the 6-byte and 9-byte `SetPageSize` on the newer ones. `PrintStart`'s `totalPages`
also has to be declared, and on B1-class hardware it changes the paper's parking behaviour between
pages.

Add a `copies` parameter to the `niimbot.print` service, defaulting to 1. This is a user-visible
feature and needs a `services.yaml` and translations update.

### 4.6 Flow control defaults and adaptation

`DEFAULT_WAIT_BETWEEN_EACH_PRINT_LINE` is 50 ms with `DEFAULT_CONFIRM_EVERY_NTH_PRINT_LINE = 1`. A
300-row label therefore spends 15 seconds purely idling, on top of a blocking round-trip for every
single row.

Two steps:

1. Lower the defaults for models known to tolerate it, keyed off the model meta rather than globally.
   Existing users' explicit settings must be preserved.
2. Measure per-write latency — `PrinterClient._timings` already collects it — and adapt the batch size
   during the page, backing off when latency rises. Start conservative and only widen.

Once 4.1 and 4.2 reduce the packet count, the per-row cost matters proportionally more, so do those
first and re-measure before tuning defaults.

### 4.7 `PrinterCheckLine` (`0x86`)

A checkpoint every 200 rows, answered with `0xD3`, that confirms the printer is keeping up instead of
letting an overflow surface as a corrupted page. Useful mainly as a diagnostic while working on 4.6.

### 4.8 Connection reuse

With `keep_connection` enabled, `update_device` and `print_image` each construct a fresh
`PrinterClient` and call `start_notify`/`stop_notify` — including a hardcoded 0.5 s sleep in
`start_notify` — on every coordinator refresh and every print.

Hold one `PrinterClient` on the device object for the lifetime of the connection and keep notifications
subscribed. Saves roughly a second per operation and removes a class of packet-buffer desync at the
subscribe boundary.

---

## Phase 5 — Model coverage and capability model

### 5.1 Add the 17 missing model IDs

Listed in [devices.md](devices.md#models-missing-from-modelpy). Unrecognised IDs resolve to `UNKNOWN`,
which routes to the old D11 sequence — the wrong sequence for all of them, producing blank or failed
prints on C1, K2, K4, M3, B4, B1 SE, H1 and H1S among others.

DPI, print width and label types come from [devices.md](devices.md). `printheadPixels` and print
direction are not in that table and have to be inferred from the closest same-series model, so
**[HW]** confirmation is needed per model.

### 5.2 Choose the print sequence from capability, not a model list

`PrinterClient.print_image` dispatches on hardcoded model tuples, so every new model needs a code
change in the right branch and an unlisted model silently falls through `else` to `print_image_b1`
or, for `UNKNOWN`, to the oldest D11 sequence.

Move the generation into `PrinterModelMeta` as an explicit field, and prefer the protocol version from
3.4 when it is known. Then an unknown model can pick a sane default from its protocol version instead
of falling back to the oldest sequence.

Note the existing method names do not line up with [printing.md](printing.md#4-print-sequences), which
will cause confusion when mapping models to generations:

| Method | Actually implements |
| --- | --- |
| `print_image_d11_v1` | Old D11 |
| `print_image_d110` | D110 |
| `print_image_b1` | V4 (`start_print_v4` + 6-byte `SetPageSize`) |
| `print_image_d110m_v4` | V5 / 9-byte (`start_print_9b` + 9-byte `SetPageSize`) |

Rename them to match the documented generation names as part of this change.

### 5.3 Lift the artificial parameter limits

- `set_label_density` asserts `1 <= n <= 5`. Real ranges reach 1–15 (B32, K4) and 1–20 (T2S). Validate
  against the model's range from 2.1 instead of a constant.
- `set_label_type` asserts `1 <= n <= 3`, and all four print sequences hardcode `set_label_type(1)`.
  That makes continuous, transparent, tag, black-mark-gap and heat-shrink stock unreachable — even
  though `PrinterModelMeta.paperTypes` already records exactly which ones each model accepts. Expose a
  `label_type` service parameter validated against `paperTypes`, defaulting to the model's first entry
  rather than to a hardcoded `1`.

Both need `services.yaml` and translation updates.

### 5.4 Create entities from capability, not from first-refresh data

Both platforms build their entity list from the keys present in `coordinator.data.sensors` at setup.
That works today only because `NiimbotDevice.__init__` pre-seeds the four known keys with `None`. Any
new key added in Phases 2 and 3 must be pre-seeded too, or the entity is silently never created.

Drive entity creation from the model's capability meta instead. This is a prerequisite for Phase 2 and
3 being reliable rather than a cleanup.

---

## Suggested sequencing

| Step | Content | Depends on |
| --- | --- | --- |
| 1 | Phase 1 in full | — |
| 2 | 5.4 capability-driven entity creation | 1 |
| 3 | 2.1–2.4 RFID label sensors | 2 |
| 4 | 4.1, 4.2, 4.3 row encoding | 1 |
| 5 | 3.1, 3.2, 3.5, 3.6 info and diagnostics | 2 |
| 6 | 5.1, 5.2, 5.3 model coverage and limits | 2 |
| 7 | 4.4–4.8 print flow | 4 |
| 8 | 2.5, 3.3 ribbon and Advanced2 | **[HW]** |

Phases 2 and 4 are independent and can proceed in parallel after step 2.

## Testing notes

`tests/` currently covers `render.py` only, with no protocol-level tests. Everything in Phase 1 and
Phase 4 is unit-testable without hardware and should get coverage as it lands:

- Packet build/parse round-trip, including checksum and the `len + 7` size relation.
- `get_rfid()` against synthetic payloads: 1-byte (no tag), 5-byte tail, 7-byte tail with `capacity`,
  UUID starting with `00`.
- Heartbeat parsing for lengths 9, 10, 13, 19, 20, an unknown length, and an Advanced2 payload.
- Row encoding: blank-run collapsing, the 255-repeat boundary, identical-row coalescing (4.1), the
  6-pixel indexed-packet boundary (4.2), and both counter modes (4.3).
- Sequence assertions per generation — that the 9-byte path omits `PageStart` and injects the
  fire-and-forget heartbeat, that the Old D11 path sends `PrintClear` and a height-only `SetPageSize`.

A fake transport that records written packets and replays canned responses makes all of the above
possible and is worth building first.

## Items needing hardware confirmation

| Item | What to check |
| --- | --- |
| 1.5 | Raw `paperstate` with paper loaded vs empty |
| 1.3 / 3.3 | Whether any available printer answers `0xD9` |
| 2.3 | Whether `type` is a label type or a material code — compare against `PrinterInfo` key 3 on black-mark stock |
| 2.3 | Units of `total_len` on a known roll (label count vs length) |
| 2.5 | Ribbon tag on a `label+ribbon` model |
| 3.1 | `Print Area` (key 15) payload layout |
| 3.3 | Temperature unit and scale |
| 4.3 | Whether any model rejects wrong counter bytes |
| 4.4 | Which models emit `0xE0` |
| 5.1 | `printheadPixels` and print direction for the 17 added models |
