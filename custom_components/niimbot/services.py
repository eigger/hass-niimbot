"""The niimbot.print / niimbot.refresh_info services.

Registered once per Home Assistant instance in async_setup(). Handlers resolve
the targeted config entries at call time, so a second printer does not replace
the handler of the first.

A call with no target keeps the previous behaviour when exactly one printer is
loaded. With two or more, the call must target a device, one of its entities,
or an area/label that contains them. Several targets run one after another:
a print holds the radio for the whole page, so overlapping jobs on one adapter
would only congest it.
"""

from __future__ import annotations

import base64
import inspect
import io
from collections.abc import Awaitable, Callable
from functools import partial

from homeassistant.components.image import Image
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.service import async_extract_config_entry_ids

from .ble import require_ble_device
from .const import DOMAIN
from .niimprint import PrinterError
from .niimprint.model import get_supported_label_type_codes, resolve_density
from .render import render_image
from .types import NiimbotConfigEntry

SERVICE_PRINT = "print"
SERVICE_REFRESH_INFO = "refresh_info"


async def _extract_config_entry_ids(hass: HomeAssistant, service: ServiceCall) -> set[str]:
    """Extract entry ids with the signature this Home Assistant has.

    2025.1 through 2025.9 require hass as the first argument. 2025.10 reads
    service.hass itself. Passing hass on that version warns on every print,
    and the argument is removed in 2026.10.
    """
    extract: Callable[..., Awaitable[set[str]]] = async_extract_config_entry_ids
    if "hass" in inspect.signature(async_extract_config_entry_ids).parameters:
        return await extract(hass, service)
    return await extract(service)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the domain services (once per HA instance)."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_PRINT,
        partial(_async_print, hass),
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_INFO,
        partial(_async_refresh_info, hass),
        supports_response=SupportsResponse.OPTIONAL,
    )


async def async_targeted_entries(
    hass: HomeAssistant, service: ServiceCall
) -> list[NiimbotConfigEntry]:
    """Resolve a service call to the loaded Niimbot entries it refers to.

    No target and a single loaded printer selects that printer, so existing
    automations that call the service with only a payload keep working.
    """
    entry_ids = await _extract_config_entry_ids(hass, service)
    loaded = {
        entry.entry_id: entry
        for entry in hass.config_entries.async_loaded_entries(DOMAIN)
    }
    if entry_ids:
        targets = [loaded[entry_id] for entry_id in sorted(entry_ids) if entry_id in loaded]
        if not targets:
            raise HomeAssistantError(
                "No loaded Niimbot printer matches the service target; "
                "target a Niimbot device, one of its entities, or its area/label."
            )
        return targets
    if len(loaded) == 1:
        return list(loaded.values())
    if not loaded:
        raise HomeAssistantError("No Niimbot printer is set up.")
    raise HomeAssistantError(
        "More than one Niimbot printer is set up; "
        "target a device or one of its entities."
    )


async def _run_targets(
    hass: HomeAssistant,
    service: ServiceCall,
    handler: Callable[[NiimbotConfigEntry], Awaitable[ServiceResponse]],
) -> ServiceResponse:
    """Run handler for each target.

    One target returns that handler's value directly, including its exception
    type. Several targets continue after a failure. Without a requested
    response those failures are raised together at the end; with
    ``return_response`` each address maps to its result or ``{"error": ...}``.
    """
    targets = await async_targeted_entries(hass, service)
    if len(targets) == 1:
        return await handler(targets[0])

    outcomes: dict[str, ServiceResponse] = {}
    errors: list[str] = []
    for entry in targets:
        address = entry.runtime_data.address
        try:
            outcomes[address] = await handler(entry)
        except HomeAssistantError as err:
            outcomes[address] = {"error": str(err)}
            errors.append(f"{address}: {err}")
    if errors and not service.return_response:
        raise HomeAssistantError("; ".join(errors))
    if not service.return_response:
        return None
    return outcomes


async def _async_print(hass: HomeAssistant, service: ServiceCall) -> ServiceResponse:
    """Print, or preview, on every targeted printer."""
    return await _run_targets(hass, service, partial(_print_one, hass, service))


async def _print_one(
    hass: HomeAssistant, service: ServiceCall, entry: NiimbotConfigEntry
) -> ServiceResponse:
    """Render and print one entry. Raises HomeAssistantError on failure."""
    data = entry.runtime_data
    device = data.device
    cloud = device._cloud_label_attrs or {}
    render_defaults: dict = {}
    if cloud.get("print_width_px") is not None:
        render_defaults["width"] = int(cloud["print_width_px"])
    if cloud.get("print_height_px") is not None:
        render_defaults["height"] = int(cloud["print_height_px"])

    try:
        image = await hass.async_add_executor_job(
            render_image, entry.entry_id, service, hass, render_defaults
        )
    except Exception as err:
        raise ServiceValidationError("Failed to create image: %s" % err) from err

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    raw = buffer.read()
    data.image_coordinator.async_set_updated_data(
        (Image(content_type="image/png", content=raw), data.coordinator.data)
    )
    encoded = base64.b64encode(raw).decode("ascii")
    image_data = f"data:image/png;base64,{encoded}"

    if service.data.get("preview"):
        return {"image": image_data}

    # Validate label_type locally before opening a BLE connection.
    # Model metadata is populated by the coordinator and is available without
    # BLE. If the model is not yet known the check is skipped; the fallback
    # inside NiimbotDevice.print_image covers that.
    if "label_type" in service.data:
        requested_label_type = int(service.data["label_type"])
    elif cloud.get("paper_type") is not None:
        requested_label_type = int(cloud["paper_type"])
    else:
        requested_label_type = None
    model_meta = device.get_model_meta()
    if requested_label_type is not None and model_meta is not None:
        supported_types = get_supported_label_type_codes(model_meta)
        if requested_label_type not in supported_types:
            raise ServiceValidationError(
                f"Label type {requested_label_type} is not supported for this printer "
                f"(supported label types: {supported_types})"
            )

    # The selector allows 1-20 because a few models go that high, but most
    # stop at 5. Reject here instead of after connect, and let an omitted
    # value fall back to the model's own default.
    try:
        density = resolve_density(
            model_meta,
            int(service.data["density"]) if "density" in service.data else None,
        )
    except ValueError as err:
        raise ServiceValidationError(str(err)) from err

    ble_device = require_ble_device(hass, data.address)

    try:
        # Clear leftover 100% in the UI before the BLE job starts.
        device.begin_print_progress()
        data.coordinator.async_set_updated_data(device.ble_data)
        result = await device.print_image(
            ble_device,
            image,
            density=density,
            wait_between_print_lines=float(service.data["wait_between_print_lines"])
            if "wait_between_print_lines" in service.data
            else data.wait_between_each_print_line / 1000,
            print_line_batch_size=int(service.data["print_line_batch_size"])
            if "print_line_batch_size" in service.data
            else data.confirm_every_nth_print_line,
            label_type=requested_label_type,
            copies=int(service.data["copies"]) if "copies" in service.data else 1,
        )
        # Push post-print RFID / heartbeat updates into entities immediately.
        data.coordinator.async_set_updated_data(device.ble_data)
        result["image"] = image_data
        return result
    except (PrinterError, RuntimeError, ValueError, ConnectionError) as err:
        raise HomeAssistantError("Failed to print: %s" % err) from err


async def _async_refresh_info(hass: HomeAssistant, service: ServiceCall) -> ServiceResponse:
    """Re-read printer info on every targeted printer."""
    return await _run_targets(hass, service, partial(_refresh_one, hass))


async def _refresh_one(hass: HomeAssistant, entry: NiimbotConfigEntry) -> ServiceResponse:
    """Re-read one printer. Raises HomeAssistantError on failure."""
    data = entry.runtime_data
    device = data.device
    ble_device = require_ble_device(hass, data.address)
    try:
        refreshed = await device.refresh_info(ble_device)
        data.coordinator.async_set_updated_data(refreshed)
        return {
            "density": refreshed.density,
            "printspeed": refreshed.printspeed,
            "labeltype": refreshed.labeltype,
            "autoshutdowntime": refreshed.autoshutdowntime,
            "battery_bucket": device._info_battery_bucket,
        }
    except Exception as err:
        raise HomeAssistantError("Failed to refresh printer info: %s" % err) from err
