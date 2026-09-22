# Troubleshooting

English | **[한국어](ko/troubleshooting.md)**

When a label does not print, the integration has usually already recorded why. This page is the order to look in: first the sensors that hold the last BLE session's breakdown, then the cases those sensors cannot see, then what to attach to an issue.

## Where to look

Open the printer's device page (**Settings → Devices & services → Niimbot → the printer**). Under *Diagnostic* there are four entities to read, in this order:

| Entity | What it tells you |
|---|---|
| **Last Failure** | When a BLE session last **failed**. Its *attributes* are the breakdown of that session — `operation`, `failed_stage`, `likely_cause`, `error`, the radio (`via`, `rssi`, `paths`) and the per-stage timings. They stay until the next failure, so a print that failed last night is still readable after this morning's polls succeeded. A status poll that never connects is **not** recorded here: the printer is usually just off or asleep between jobs. |
| **Last Error** | The printer's own error code from the last failed print (`CoverOpen`, `LackPaper`, `LowBattery`, …), with the same breakdown as attributes. A print that fails before the printer can answer (e.g. at `connect`) shows the exception name instead (`ConnectFailed`). |
| **Print Duration** | Seconds the **most recent** print took, success or not. Its *attributes* are the same breakdown for that print, attached when the job ends (while one runs — `is_printing: true` — it has only the elapsed time). Use it when the print you are debugging is the last one. |
| **Error Count** | How many sessions have failed since the integration was (re)loaded. A poll that finds the printer asleep does not count; a failed print, a poll that connected and then failed, or a `niimbot.refresh_info` that could not connect does. Rising while nothing is printing means polls are failing after the link is up — read Last Failure's `failed_stage` before reading anything into the number. |

To see the attributes: click the entity → ⋮ → **Attributes**, or in **Developer tools → States** search for the entity. In a template: `{{ state_attr('sensor.b21_123456_ddee03_last_failure', 'likely_cause') }}` (the id is the printer's advertised name plus the last six hex digits of its MAC).

Home Assistant also records the Print Duration attributes with each state change, so the history of that sensor has the breakdown of every print, not only the last failed one. Last Failure and Error Count start empty on a restart or reload; the history is where a failure from before it lives.

Two more entities help, but read them for what they are:

- **Connection** (binary) — on while the BLE link is up. With **Keep Connection** off that is only during a poll or a print; with it on, the link stays open between jobs, so *on* does not mean a job is running.
- **Print Progress** — the printer's own page/feed progress during a job. It stops where the job died; a failed print does not reach 100 %.

## Reading the attributes

The attributes are, in order. `failed_stage` is the shared name used across BLE integrations; `failed_detail` is the printer's own name for that stage, present only when the two differ.

| Attribute | Meaning |
|---|---|
| `operation` | `print`, `update` (the scheduled status poll), `refresh_info` (the `niimbot.refresh_info` action), `settings` (Auto Shutdown / Connection Sound), `calibrate`, `cancel`, `reset` or `test_page` (the buttons). |
| `success` | Whether the session completed. |
| `error`, `failed_stage`, `failed_detail`, `likely_cause` | Only on a failure: the exact message, the shared stage it escaped from, the printer's own name for that stage, and one sentence on what that usually means. |
| `via`, `via_type`, `rssi`, `paths` | The radio the link went over (a proxy or a local adapter), the printer's signal as that radio last saw it, and how many connectable radios currently see the printer. `paths: 1` means there is no other radio to fall back to. On a `connect` failure `via` is the radio that was tried. |
| `advertised_via` | Only when it differs from `via`: the radio whose advertisement was strongest, which is the one Home Assistant tries first. The link ending up elsewhere is a failover. |
| `connect_s`, `subscribe_s`, `prepare_s`, `info_s`, `transfer_s`, `finish_s`, `disconnect_s`, … | Seconds spent in each stage, in the order they ran. A stage that did not run is absent. `transfer_s` is the image transfer itself and the number to compare when tuning speed. |
| `reused_connection` | `true` when **Keep Connection** was on and the job ran over the link that was already open — no `connect_s` in that case. |
| `copies`, `density` | What the print was asked for. |
| `cancelled` | `true` when the job was stopped by `niimbot.cancel_print` or the printer's own cancel; not a failure. |
| `refresh_error` | The post-print status read (RFID / heartbeat) failed but the label had already printed. Informational. |

## Reading a failure

Start with `failed_stage` on Last Failure: it says how far the session got, in the shared vocabulary. `failed_detail` is the printer's name for the same stage. `likely_cause` is a reading of the stage, the error text and the radio situation; `error` is the exact message.

### Printer error codes

When the printer itself refused the job, `error` reads `Printer error: <Code>` and `likely_cause` names it directly. An `error` of `Unsupported request 0x..` is different: the printer NAKed a command this model or firmware does not implement (usually a button such as calibration or test page). The common codes:

| Code | Meaning | Do |
|---|---|---|
| `CoverOpen` | The label bay cover is open. | Close it and print again. |
| `LackPaper` / `PaperOutException` | No paper, or the paper did not feed. | Reload the roll, close the cover. |
| `LowBattery` / `BatteryException` | Too little charge to print, or a battery fault. | Charge the printer. |
| `WrongPaper` / `WrongRibbon` / `NoRibbon` / `UsedRibbon` | The consumable does not match the job or is missing. | Check the roll / ribbon; check `label_type` against the paper. |
| `Overheat` / `TemperatureLow` | The head is out of its temperature range. | Wait, then retry. |
| `PrinterBusy` | Another job is running (often the phone app). | Close the app or wait. |
| `ReceiveDataTimeout` | The printer waited too long for image data — a congested proxy. | Raise `wait_between_print_lines`; see `transfer` below. |

### `connect`

The link never came up.
- *For `operation: update` this is the printer's normal state.* Most models power off or sleep between jobs, so a poll that runs then fails here. It is not recorded on Last Failure and does not count. Look further only when a **print** fails the same way.
- *Check:* `rssi` and `paths`. `error` with *slot* = the proxy's connection slots are all in use. *settle* = the printer accepted the link and dropped it before it was established.
- *Do:* Turn the printer on. Weak `rssi` (below about −85 dBm): move the printer or add a proxy near it — with `paths: 1` there is also no other radio to fall back to. *slot*: fewer BLE devices per proxy, or another proxy.

### `session` (`failed_detail: subscribe`)

Connected, but the printer did not accept notifications, so no command could be answered.
- *Check:* Does it repeat every time?
- *Do:* Once: ignore, the next job usually succeeds. Every time: the proxy may be serving a stale GATT cache — restart the proxy.

### `session` (`failed_detail: prepare`)

Connected, but job setup failed before any image data was sent: the model could not be read, or the `label_type` is not one the model supports.
- *Check:* `error`. *not supported for printer model* = the requested `label_type` (or the one resolved from the cloud catalogue) is outside the model's list.
- *Do:* Pass a `label_type` from [devices.md](devices.md) for the model, or omit it. If the model came back as `UNKNOWN`, please [open an issue](https://github.com/eigger/hass-niimbot/issues) with the Protocol Version and Print Area sensor values.

### `session` (`failed_detail: info` / `settings` / `calibrate` / `cancel` / `reset` / `test_page`)

Connected, but the printer did not answer a status read, or rejected a setting or a button command.
- *Check:* `operation` says which. *Unsupported request* = the model does not implement that command.
- *Do:* A status read (`info`) is usually transient. A button or setting that fails every time on one model is a capability gap — worth an issue with the model name.

### `transfer`

Failed while the image was being sent. This is the one stage that points at link quality.
- *Check:* `rssi`, `via`, `transfer_s`, and whether it dies at the same point every time. `ReceiveDataTimeout` from the printer is the same problem seen from its side.
- *Do:* Once: move the printer or the proxy it used (`via`), or add one. Raise `wait_between_print_lines` (e.g. `0.02`) and lower `print_line_batch_size` (e.g. `8`) — see [Increasing print speed](../README.md#increasing-print-speed). Every time at the same point, on any setting: please [open an issue](https://github.com/eigger/hass-niimbot/issues) with the attributes.

### `finish`

The label was sent; only the status read afterwards (RFID remaining, heartbeat) failed.
- *Do:* Harmless on its own — check the label came out. Only the consumable sensors may be one job behind until the next poll. If the **next** job is refused with `PrinterBusy`, the printer did not close the previous one: power-cycle it.

### Quick checks

- **`rssi` is low but `paths` is 2 or more** — another radio might do better; Home Assistant connects through the strongest advertisement, so the alternative is only used after a failure. Check `via` to see which one was used.
- **Everything fails at `connect` right after adding a proxy** — the proxy must be `active: true` in both `esp32_ble_tracker` and `bluetooth_proxy` (see the [README](../README.md#important-notice)); a passive proxy sees the printer but cannot connect.
- **`error: ConnectFailed` on a print while the phone app is open** — most models accept one client. Close the app.
- **`reused_connection: true` and then `transfer` failures** — a link kept open across a long idle can go stale on some proxies. Turn **Keep Connection** off and compare.
- **Error Count climbs while nothing is printing** — a poll connected and then failed (`failed_stage: session`, `failed_detail: info`) — usually the proxy, see above; or a `refresh_info` action in an automation is running while the printer is off (it *is* counted, unlike the poll).

## What the attributes cannot show

Three kinds of problem never reach the failure sensors, because the session did not fail — or never happened.

**The print succeeded but the label is wrong.** `success: true`, and yet the label is blank, cut off, mirrored or at the wrong scale. The image reached the printer; the rendering or the model's print width is off. Look at **Last Label Made** (what was sent): if that is wrong, fix the payload — reproduce with `preview: true` from **Developer tools → Actions**. If the image is right but the print is scaled or shifted, the model's `printheadPixels` may be estimated — the log warns *uses an estimated printheadPixels value* once per model; please report what you see in an issue.

**The action itself errored before any BLE traffic.** A payload that does not render, a `density` or `label_type` outside the model's range (*is not supported for this printer*), or a printer no radio currently sees (*could not find printer with address …*): the action fails immediately with that message, and nothing is recorded on the session sensors. Check the action trace or the error shown in the UI.

**No session was attempted.** The status poll returns the cached values when no radio sees the printer, and logs a warning only. The sensors keep their last values; **Connection** stays off. Turn the printer on and wait one scan interval, or call `niimbot.refresh_info`.

## Intermittent failures

A print that fails only sometimes is the reason Last Failure keeps its attributes: look there, not at Print Duration, which already shows the later success. Its `failed_stage` and `rssi` at the time of failure are what matter. If failures cluster at one `via`, that proxy is the problem; if `paths` was 1 each time, a second radio would have given a fallback.

## What to attach to an issue

1. The **Last Failure** attributes (Developer tools → States → the entity → copy the attributes block) and, if the failure is not the latest print, the **Print Duration** attributes from the history around that time.
2. The printer model and the **Protocol Version** / **Print Area** sensor values.
3. Which radio the printer uses (`via` — proxy model and ESPHome version, or the adapter) if the failure is `connect` or `transfer`.
4. For a wrong-looking label: the **Last Label Made** image and a photo of the print.

Debug logging is rarely needed; if asked, add `custom_components.niimbot: debug` under `logger:` and reproduce once.
