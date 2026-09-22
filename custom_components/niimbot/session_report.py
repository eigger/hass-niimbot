"""The breakdown of one BLE session, as the diagnostic sensors publish it.

``SessionTrace`` records where the session spent its time and where it died.
``blesession`` turns that into the shared report — which radio the link went
over, and one sentence on what a failure most likely means. The sentences
that are specific to a Niimbot printer live here; the ones every BLE device
shares (a proxy with no free slot, a weak signal, a stack that stopped
answering) come from the library.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from blesession import SessionTrace, build_report, generic_cause, placement, stages
from blesession.hass import radio_facts

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

# PrinterError stringifies as "Printer error: <CodeName>".
_PRINTER_FAULTS: tuple[tuple[str, str], ...] = (
    ("coveropen", "The cover is open. Close it and print again."),
    ("lackpaper", "The printer is out of paper."),
    ("lowbattery", "The battery is too low to print."),
    ("batteryexception", "The printer reported a battery fault."),
    ("usercancel", "The print was cancelled on the printer."),
    ("dataerror", "The printer rejected the image data."),
    ("overheat", "The print head is too hot. Let it cool and retry."),
    (
        "paperoutexception",
        "Paper did not feed. Check the roll and that the cover is closed.",
    ),
    ("printerbusy", "The printer is busy with another job."),
    ("noprinterhead", "The print head was not detected. Reseat it and retry."),
    ("temperaturelow", "The printer is too cold to print."),
    ("printerheadloose", "The print head is loose. Reseat it and retry."),
    ("noribbon", "No ribbon is loaded."),
    ("wrongribbon", "The loaded ribbon does not match this job."),
    ("usedribbon", "The ribbon is used up."),
    ("wrongpaper", "The loaded paper does not match the selected label type."),
    (
        "communicationexception",
        "The printer reported a communication error on the link.",
    ),
    ("disconnect", "The printer dropped the link during the job."),
    (
        "receivedatatimeout",
        "The printer timed out waiting for image data. A congested proxy "
        "often causes this — raise the line delay if it repeats.",
    ),
    (
        "rfidtagnotwritten",
        "The printer could not write the RFID tag. The label may still have printed.",
    ),
)


def likely_cause(
    stage: str | None,
    detail: str | None,
    error: str,
    facts: Mapping[str, Any],
    operation: str,
) -> str:
    """One sentence on what a failed session most likely means.

    ``stage`` is the shared name (``connect``, ``transfer``, …) and ``detail``
    the printer's own (``prepare``, ``subscribe``, ``info``, …). Best effort —
    ``error`` keeps the exact detail. A ``None`` from the printer-specific
    table falls through to the shared sentences.
    """
    text = _printer_cause(stage, detail, error, facts, operation)
    if text is not None:
        return text
    shared = generic_cause(stage or detail, error, facts, noun="printer")
    if shared is not None:
        return shared
    return "The session failed before the first stage was reached; see error."


def _printer_cause(
    stage: str | None,
    detail: str | None,
    error: str,
    facts: Mapping[str, Any],
    operation: str,
) -> str | None:
    """The printer's own reading, or None where the shared sentence is the one."""
    err = error.lower()
    if "printer error:" in err:
        for token, sentence in _PRINTER_FAULTS:
            if token in err:
                return sentence
    if "unsupported request" in err:
        return (
            "The printer rejected the command. This model or firmware may not "
            "support it."
        )
    where = detail or stage
    advice = placement(facts, noun="printer")
    if where == stages.CONNECT:
        if operation == "update":
            return (
                "The printer could not be reached for a status poll. It is often "
                "off or asleep between jobs, so this on its own is normal; a print "
                "that fails the same way means it is out of range or the adapter "
                f"/ proxy is down.{advice}"
            )
        return (
            "The printer could not be reached. Turn it on and keep it in range of "
            f"the adapter or proxy.{advice}"
        )
    if where == "subscribe":
        return (
            "Connected, but the printer did not accept notifications. Usually "
            "transient; if it repeats, the proxy may be serving a stale GATT cache."
        )
    if where == "prepare":
        return (
            "The printer connected but job setup failed (model lookup or label "
            "type) before any image data was sent."
        )
    if where == "info":
        return (
            "The printer connected but did not answer a status read. Usually "
            f"transient.{advice}"
        )
    if where == stages.TRANSFER:
        return (
            "The link failed while the label was being sent. Once: move the "
            "printer closer or raise the line delay. Every time at the same "
            f"point: please open an issue.{advice}"
        )
    if where == stages.FINISH:
        return (
            "The label was sent; only the status read afterwards failed. "
            "Harmless unless the next job is refused."
        )
    if where == "calibrate":
        return "Calibration did not finish. Check that paper is loaded and the cover is closed."
    if where == "cancel":
        return "The printer did not accept the cancel command."
    if where == "reset":
        return "The printer did not accept the settings reset."
    if where == "test_page":
        return "The printer did not print the test page."
    return None


def build_session_report(
    hass: HomeAssistant,
    address: str,
    *,
    operation: str,
    trace: SessionTrace | None,
    exc: BaseException | None,
) -> dict[str, Any]:
    """Assemble the attributes for one finished session.

    Outcome first, then the radio, then the stage timings, in the order
    ``blesession.build_report`` fixes so the same keys mean the same thing
    on every integration.
    """
    trace = trace if trace is not None else SessionTrace()
    return build_report(
        operation=operation,
        trace=trace,
        exc=exc,
        facts=radio_facts(hass, address, trace.link),
        cause=lambda stage, detail, error, facts: likely_cause(
            stage, detail, error, facts, operation
        ),
        noun="printer",
    )
