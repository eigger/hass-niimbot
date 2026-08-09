# Printing Protocol

Image encoding, page setup and the per-generation command sequences. Framing and command IDs are in
[protocol.md](protocol.md).

## 1. Image format

Rows are sent one at a time as **1 bit per pixel, MSB first**, where a set bit means black (printed).

A row is `ceil(width / 8)` bytes. The width must not exceed the model's print head pixel count
(`printheadPixels` in `niimprint/model.py`) — that is the real limit, not the millimetre width in
[devices.md](devices.md).

This integration converts a PIL image with:

```python
img = ImageOps.invert(image.convert("L")).convert("1")
```

The invert is what maps "dark in the source image" to "set bit on the wire".

Rows are sent in increasing row order. Blank rows should be collapsed into `PrintEmptyRow` rather than
sent as zero-filled bitmap rows.

## 2. Row commands

### `PrintBitmapRow` (`0x85`)

```
+----------+------+------+------+---------+---------------+
| row: u16 | c0   | c1   | c2   | repeats | rowdata[...]  |
+----------+------+------+------+---------+---------------+
```

| Field | Size | Description |
| --- | --- | --- |
| `row` | 2 | Row index, 0-based |
| `c0` `c1` `c2` | 1 each | Black pixel counters, see below |
| `repeats` | 1 | How many times to print this row. Normally `1` |
| `rowdata` | `ceil(width/8)` | The row bitmap |

No response.

#### The three counter bytes

There are two encodings, and which one applies depends on whether the row fits into three equal
chunks.

**Split mode** — chunk size is `floor(printheadPixels / 8 / 3)` bytes. Used when the row data fits
within `chunkSize * 3` bytes. `c0`, `c1`, `c2` are the black pixel counts of the first, second and
third chunk.

**Total mode** — used when the row is wider than three chunks. The total black pixel count is spread
over the bytes instead:

```
c0 = 0x00
c1 = total & 0xFF
c2 = (total >> 8) & 0xFF
```

Note that this puts the low byte before the high byte, unlike every other multi-byte field in the
protocol.

**This integration always uses split mode with a hardcoded chunk size of 4 bytes**, which corresponds
to `printheadPixels = 96` (D11 class). On a wider printer — 384 px is 48 bytes per row — only the
first 12 bytes get counted and the counters are wrong. Printing still works, so firmware evidently
does not validate them strictly, but this is a real divergence from the specification above.

### `PrintEmptyRow` (`0x84`)

```
+----------+-------+
| row: u16 | count |
+----------+-------+
```

Skips `count` blank rows starting at `row`. No response.

`count` is one byte, so **255 rows maximum**; longer blank runs must be split across several packets.
On a large label with sparse content this is the single biggest transfer saving available.

### `PrintBitmapRowIndexed` (`0x83`)

Same header as `0x85`, but instead of the row bitmap the payload is a list of `u16` pixel column
indices — the coordinates of the black pixels.

```
5555 83 0e 007e 000400 01 0027 0028 0029 002a fa aaaa
        ^^ ^^^^ ^^^^^^ ^^ ^^^^^^^^^^^^^^^^^^^
        |  row  c0c1c2 |  four pixel indices: 39, 40, 41, 42
        len            repeats
```

**Only valid when the row has 6 or fewer black pixels.** Above that the printer may power itself off,
so a sender must count first and fall back to `0x85`.

Worth implementing for barcode and thin-line artwork, where most rows are nearly empty.
Implemented in `PrinterClient.set_bitmap_row_indexed`, with the count check and the `0x85` fallback.

### `PrinterCheckLine` (`0x86`)

```
+-----------+------+
| line: u16 | 0x01 |
+-----------+------+
```

A mid-transfer checkpoint, sent every 200 rows, answered with `0xD3`. It lets the sender confirm the
printer is keeping up instead of discovering an overflow at the end of the page.
Implemented in `PrinterClient.check_line`.

## 3. Page setup

### `PrintStart` (`0x01`)

Five payload lengths exist. The printer's generation decides which one it accepts.

| Length | Payload |
| --- | --- |
| 1 | `01` |
| 2 | `u16 totalPages` |
| 7 | `u16 totalPages` + `00 00 00 00` + `u8 pageColor` |
| 9 | `u16 totalPages` + `00 00 00 00` + `u8 pageColor` + `u8 speed` + `u8 flag` |

`totalPages` is a declaration, and on B1-class hardware it changes physical behaviour: with
`totalPages > 1` the paper parks at the print head after `PageEnd` and waits for the next page,
feeding out only after the last one.

The 9-byte variant's second-to-last byte is a speed or quality selector — this integration names it
`quality`, other implementations name it `speed`. The final byte's purpose is unknown.

### `SetPageSize` (`0x13`)

| Length | Payload |
| --- | --- |
| 2 | `u16 rows` |
| 4 | `u16 rows` + `u16 cols` |
| 6 | `u16 rows` + `u16 cols` + `u16 copies` |
| 9 | 6-byte form + `u16 cutHeight` + `u8 cutType` |
| 13 | 9-byte form + `00` + `u8 sendAll` + `u16 partHeight` |

`rows` is height in pixels, `cols` is width in pixels.

The 4-byte form misbehaves on B1-class printers: the first page comes out blank, or the printer emits
many copies. Use the 6-byte form there. On D110-class hardware the 4-byte form is fine.

Once copies are carried in `SetPageSize`, `PrintQuantity` (`0x15`) is not sent.

Sending `SetPageSize` before the page has been started returns `0xDB`.

### `PrintQuantity` (`0x15`)

`u16` copies. Used by the generations whose `SetPageSize` has no copies field.

## 4. Print sequences

Getting the order wrong does not always produce an error. The common failure is the printer feeding a
label in and back out without imaging it, with the page counter not advancing.

### Old D11 generation

Models: D11, D11S.

```
SetDensity → SetLabelType → PrintStart(1b) → PrintClear
→ PageStart → SetPageSize(4b: rows, 0) → PrintQuantity
→ rows… → PageEnd → poll → PrintEnd
```

Two peculiarities: the width field is sent as `0`, and `PrintClear` (`0x20`) is required. No other
generation uses `PrintClear`.

### D110 generation

Models: D110, B21S, B21S_C2B.

```
SetDensity → SetLabelType → PrintStart(1b)
→ PageStart → SetPageSize(4b: rows, cols) → PrintQuantity
→ rows… → PageEnd → poll → PrintEnd
```

### V4 generation

Models: B1, B1 Pro, B21, B3S, etc. — default fallback for unrecognised models (unless protocol version >= 5).

```
SetDensity → SetLabelType → PrintStart(7b)
→ PageStart → SetPageSize(6b: rows, cols, copies)
→ rows… → PageEnd → poll → PrintEnd
```

### V5 / 9-byte generation

Models: D11_H, D11_PRO, B21_PRO, D110_M, B2_PRO.

```
SetDensity → SetLabelType → PrintStart(9b) → Heartbeat (reply ignored)
→ SetPageSize(9b) → rows… → PageEnd
→ wait 1 s → poll → PrintEnd → Heartbeat (reply ignored)
```

Two things are specific to this generation:

- **No `PageStart`.** Sending it is not part of the sequence.
- **A heartbeat must be injected after `PrintStart`**, and its reply is deliberately not awaited.
  Without it the job never starts.

## 5. Detecting completion

Three approaches exist, in decreasing order of reliability.

### Page index notifications (`0xE0`)

The printer emits `0xE0` unsolicited as each page completes, with a `u16` page number. Waiting for
`page == totalPages` is the most direct signal and needs no polling. Implemented in
`PrinterClient.wait_print_complete`, which drains `0xE0` first and keeps the `0xA3` poll below as the
fallback for models that never emit it.

### Polling `PrintStatus` (`0xA3`)

Poll until `page` reaches the expected count and both progress values read 100.

**The stale-progress trap:** immediately after `PageEnd`, B1-class printers still report the *previous*
job's `progress = 100`. Acting on it sends `PrintEnd` too early, which aborts the page — the label
feeds in and back out unprinted and the counter does not advance.

The workaround is to require evidence that the new page actually started before accepting a 100:

```
started = False
loop:
    status = PrintStatus()
    if status.progress < 100: started = True
    if status.page >= 1 or (started and status.progress >= 100): break
```

This is what `print_image_b1` does, with a 30-second timeout as a backstop.

### Polling `PrintEnd` (`0xF3`)

`PrintEnd` returns `data[0] == 0` while the printer is not ready to end the job, and `1` once it is.
Calling it in a loop doubles as both the poll and the final command. The other generations in this
integration use this pattern, with a 5-second timeout.

## 6. Throughput

Row commands are fire-and-forget, which is what makes printing fast and also what makes it fragile:
too many unacknowledged writes and the BLE link drops packets mid-page.

This integration exposes two knobs:

| Option | Effect |
| --- | --- |
| `print_line_batch_size` | One write-with-response every N rows; the rest are write-without-response |
| `wait_between_print_lines` | Idle time inserted after each row |

Lower `wait_between_print_lines` and raise `print_line_batch_size` for speed; do the opposite if pages
come out with missing bands.

`PrintEmptyRow` batching, identical-row coalescing through `repeats` and `PrintBitmapRowIndexed`
(section 2) are all in use, so the remaining per-page cost is dominated by round-trips rather than by
bytes.

## 7. Known limitations of this integration

- `SetLabelType` is a print-service parameter validated as 1–11, but it is not checked against the
  model's own `paperTypes`, so an unsupported value is rejected by the printer instead of locally.
- `CancelPrint` (`0xDA`) and the 2-byte and 13-byte page-size variants are unimplemented.
- Colour and greyscale printing are unsupported. `pageColor` is always `0` and rendering is 1-bit,
  even on models whose Colour Support sensor reports otherwise.
- Print margins are ignored. The vendor publishes a per-model, per-paper-type `blindZone`, and
  rendering edge to edge can clip near the leading edge on black-mark stock.
- Flow control is static. Per-write latency is measured but not used to adapt the batch size.
