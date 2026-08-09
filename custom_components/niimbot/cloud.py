"""Optional online lookup of label name/size from the NIIMBOT cloud catalogue.

Off by default (CONF_USE_CLOUD_LABEL_INFO). The RFID tag on a label roll carries no
dimensions on any model (see docs/rfid.md), so this is the only way to get a
human-readable name and physical size for the loaded roll. When enabled, only the
loaded label's product barcode is sent to print.niimbot.com — no serial number, tag
UUID, MAC address or Home Assistant instance identifier.

Parsed catalogue fields feed the Cloud Label Info sensor and, when the print
service omits width/height/label_type, supply defaults (print_*_px after applying
the catalogue rotate so the bitmap matches the physical label orientation).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, NotRequired, TypedDict

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_ENDPOINT = "https://print.niimbot.com/api/template/getCloudTemplateByOneCode"
_FETCH_TIMEOUT_SECONDS = 10
# AppVersionName must parse as a high-enough semver or the API returns 400/500.
_CLIENT_HEADER = "AppVersionName/6.6.5 Client/hass-niimbot"

# Bump when the on-disk LabelInfo schema changes so stale partial caches re-fetch.
_STORE_VERSION = 3
_STORE_KEY = f"{DOMAIN}.label_cache"
_NEGATIVE_RECHECK_SECONDS = 7 * 24 * 3600


class LabelInfo(TypedDict):
    label_name: str | None
    catalog_barcode: NotRequired[str | None]
    label_width_mm: float | None
    label_height_mm: float | None
    label_width_px: NotRequired[int | None]
    label_height_px: NotRequired[int | None]
    print_width_px: NotRequired[int | None]
    print_height_px: NotRequired[int | None]
    dpi: NotRequired[int | None]
    paper_type: NotRequired[int | None]
    consumable_type: NotRequired[int | None]
    rotate: NotRequired[int | None]
    canvas_rotate: NotRequired[int | None]
    margin: NotRequired[list[int] | None]
    preview_url: str | None
    thumbnail_url: NotRequired[str | None]
    background_image_url: NotRequired[str | None]
    content_thumbnail_url: NotRequired[str | None]
    template_id: NotRequired[int | None]
    origin_template_id: NotRequired[int | None]
    version: NotRequired[str | None]
    commodity_template: NotRequired[bool | None]
    is_cable: NotRequired[bool | None]
    cable_direction: NotRequired[int | None]
    cable_length: NotRequired[float | None]
    marketing_category_id: NotRequired[int | None]
    sticky: NotRequired[bool | None]
    has_vip_res: NotRequired[bool | None]
    label_names: NotRequired[dict[str, str] | None]


def _mm_to_px(mm: Any, dpi: int | None) -> int | None:
    if mm is None or not dpi:
        return None
    try:
        return max(1, round(float(mm) / 25.4 * int(dpi)))
    except (TypeError, ValueError):
        return None


def _pick_name(data: dict) -> str | None:
    """Pick a display name from names / labelNames / name.

    Prefer English, then Korean, then any non-empty entry, then ``name``.
    """
    by_lang: dict[str, str] = {}
    for entry in list(data.get("names") or []) + list(data.get("labelNames") or []):
        code = entry.get("languageCode")
        name = entry.get("name")
        if code and name:
            by_lang[code] = name
    for lang in ("en", "ko"):
        if by_lang.get(lang):
            return by_lang[lang]
    if data.get("name"):
        return data["name"]
    return next(iter(by_lang.values()), None)


def parse_label_data(data: dict) -> LabelInfo:
    """Map a catalogue ``data`` object to LabelInfo (no network)."""
    width_mm = data.get("width")
    height_mm = data.get("height")
    dpi_raw = data.get("paccuracyName")
    try:
        dpi = int(dpi_raw) if dpi_raw is not None else None
    except (TypeError, ValueError):
        dpi = None

    rotate = data.get("rotate")
    try:
        rotate_i = int(rotate) if rotate is not None else None
    except (TypeError, ValueError):
        rotate_i = None

    width_px = _mm_to_px(width_mm, dpi)
    height_px = _mm_to_px(height_mm, dpi)
    # Catalogue canvas may be rotated vs the print bitmap (e.g. 30×50 @ 270 → 400×240).
    if rotate_i in (90, 270) and width_px is not None and height_px is not None:
        print_width_px, print_height_px = height_px, width_px
    else:
        print_width_px, print_height_px = width_px, height_px

    label_names: dict[str, str] = {}
    for entry in list(data.get("names") or []) + list(data.get("labelNames") or []):
        code = entry.get("languageCode")
        name = entry.get("name")
        if code and name:
            label_names[code] = name

    margin = data.get("margin")
    if margin is not None and not isinstance(margin, list):
        margin = None

    return LabelInfo(
        label_name=_pick_name(data),
        catalog_barcode=data.get("barcode"),
        label_width_mm=width_mm,
        label_height_mm=height_mm,
        label_width_px=width_px,
        label_height_px=height_px,
        print_width_px=print_width_px,
        print_height_px=print_height_px,
        dpi=dpi,
        paper_type=data.get("paperType"),
        consumable_type=data.get("consumableType"),
        rotate=rotate_i,
        canvas_rotate=data.get("canvasRotate"),
        margin=margin,
        preview_url=data.get("previewImage"),
        thumbnail_url=data.get("thumbnail"),
        background_image_url=data.get("backgroundImage"),
        content_thumbnail_url=data.get("contentThumbnail"),
        template_id=data.get("id"),
        origin_template_id=data.get("originTemplateId"),
        version=data.get("version"),
        commodity_template=data.get("commodityTemplate"),
        is_cable=data.get("isCable"),
        cable_direction=data.get("cableDirection"),
        cable_length=data.get("cableLength"),
        marketing_category_id=data.get("marketingCategoryId"),
        sticky=data.get("sticky"),
        has_vip_res=data.get("hasVipRes"),
        label_names=label_names or None,
    )


def _format_error(err: BaseException) -> str:
    """Human-readable error for logs/attributes (str(err) is often empty)."""
    text = str(err).strip()
    if text:
        return f"{type(err).__name__}: {text}"
    return f"{type(err).__name__}: {err!r}"


class LabelCloudLookup:
    """Resolves a label barcode to name/size/preview via the NIIMBOT cloud catalogue."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store: Store = Store(hass, _STORE_VERSION, _STORE_KEY)
        self._cache: dict[str, dict] | None = None
        self.last_result_definitive: bool = False
        self.last_source: str | None = None  # "cache" | "network"
        self.last_error: str | None = None

    async def _load_cache(self) -> dict[str, dict]:
        if self._cache is None:
            try:
                self._cache = await self._store.async_load() or {}
            except Exception as err:  # noqa: BLE001 — cache is optional
                _LOGGER.warning(
                    "Failed to load cloud label cache: %s", _format_error(err)
                )
                self._cache = {}
        return self._cache

    async def get(self, barcode: str) -> LabelInfo | None:
        """Return label info for a barcode, using the on-disk cache when possible."""
        self.last_result_definitive = False
        self.last_source = None
        self.last_error = None
        if not barcode:
            self.last_result_definitive = True
            return None

        cache = await self._load_cache()
        entry = cache.get(barcode)
        if entry is not None:
            if entry.get("negative"):
                if time.time() - entry.get("checked_at", 0) < _NEGATIVE_RECHECK_SECONDS:
                    self.last_result_definitive = True
                    self.last_source = "cache"
                    return None
            else:
                self.last_result_definitive = True
                self.last_source = "cache"
                return entry.get("info")

        info, definitive = await self._fetch(barcode)
        self.last_result_definitive = definitive
        self.last_source = "network"
        if not definitive:
            return None

        cache[barcode] = (
            {"info": dict(info), "checked_at": time.time()}
            if info is not None
            else {"negative": True, "checked_at": time.time()}
        )
        try:
            await self._store.async_save(cache)
        except Exception as err:  # noqa: BLE001 — still return the network result
            _LOGGER.warning(
                "Failed to persist cloud label cache: %s", _format_error(err)
            )
        return info

    async def _fetch(self, barcode: str) -> tuple[LabelInfo | None, bool]:
        """Return (info, definitive). definitive is False for retryable failures."""
        session = async_get_clientsession(self._hass)
        try:
            async with asyncio.timeout(_FETCH_TIMEOUT_SECONDS):
                async with session.post(
                    _ENDPOINT,
                    json={"oneCode": barcode},
                    headers={
                        "Content-Type": "application/json",
                        "niimbot-user-agent": _CLIENT_HEADER,
                    },
                ) as resp:
                    if resp.status != 200:
                        self.last_error = f"HTTP {resp.status}"
                        _LOGGER.warning(
                            "Cloud label lookup for %s: %s", barcode, self.last_error
                        )
                        return None, False
                    body = await resp.json(content_type=None)
        except TimeoutError as err:
            self.last_error = _format_error(err)
            _LOGGER.warning(
                "Cloud label lookup for %s timed out: %s", barcode, self.last_error
            )
            return None, False
        except (aiohttp.ClientError, OSError) as err:
            self.last_error = _format_error(err)
            _LOGGER.warning(
                "Cloud label lookup for %s failed: %s",
                barcode,
                self.last_error,
                exc_info=True,
            )
            return None, False
        except Exception as err:  # noqa: BLE001 — never raise into the poll loop
            self.last_error = _format_error(err)
            _LOGGER.warning(
                "Cloud label lookup for %s unexpected error: %s",
                barcode,
                self.last_error,
                exc_info=True,
            )
            return None, False

        if not isinstance(body, dict):
            self.last_error = "bad response: not a dict"
            _LOGGER.warning("Cloud label lookup for %s: %s", barcode, self.last_error)
            return None, False

        data = body.get("data")
        if not data:
            _LOGGER.debug("Cloud label lookup for %s: no match", barcode)
            return None, True

        return parse_label_data(data), True
