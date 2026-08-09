"""Optional online lookup of label name/size from the NIIMBOT cloud catalogue.

Off by default (CONF_USE_CLOUD_LABEL_INFO). The RFID tag on a label roll carries no
dimensions on any model (see docs/rfid.md), so this is the only way to get a
human-readable name and physical size for the loaded roll. When enabled, only the
loaded label's product barcode is sent to print.niimbot.com — no serial number, tag
UUID, MAC address or Home Assistant instance identifier.

Endpoint contract verified manually against the live API (2026-08-09), not from the
app decompile:

    POST https://print.niimbot.com/api/template/getCloudTemplateByOneCode
    Headers: Content-Type: application/json, niimbot-user-agent: <must contain
             "AppVersionName/<semver>"> — a non-numeric AppVersionName value
             (e.g. "hass-niimbot") returns HTTP 500; too-low versions return 400.
    Body:    {"oneCode": "<barcode>"}
    Found:   200, body["data"] present with "width"/"height" (mm) and a "names" list
             of {languageCode, languageName, name}; not every language is populated.
    Unknown: 200, body has no "data" key at all (not a 404).

The niimbot-user-agent header is a client-identification requirement, not a login.
``Client/hass-niimbot`` identifies this integration; ``AppVersionName`` must still
be a numeric semver the catalogue accepts. This is an undocumented endpoint and may
change or disappear without notice; every failure mode here must degrade to "no
extra info", never to a broken entity.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TypedDict

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

# Bump when the on-disk schema or cache semantics change (e.g. v1 wrongly cached
# HTTP 500 as a permanent negative hit).
_STORE_VERSION = 2
_STORE_KEY = f"{DOMAIN}.label_cache"
# Re-check a barcode that returned no match at most this often, in case the
# catalogue gains an entry for it later. A confirmed match is cached forever.
_NEGATIVE_RECHECK_SECONDS = 7 * 24 * 3600


class LabelInfo(TypedDict):
    label_name: str | None
    label_width_mm: float | None
    label_height_mm: float | None
    preview_url: str | None


def _pick_name(data: dict) -> str | None:
    """Pick a display name from the per-language list.

    Coverage varies by SKU — some entries have every language, some only Chinese.
    Prefer English, then Korean, then the catalogue's own default name, then
    whatever is non-empty.
    """
    names = data.get("names") or []
    by_lang = {
        entry.get("languageCode"): entry.get("name")
        for entry in names
        if entry.get("name")
    }
    for lang in ("en", "ko"):
        if by_lang.get(lang):
            return by_lang[lang]
    if data.get("name"):
        return data["name"]
    return next(iter(by_lang.values()), None)


def _format_error(err: BaseException) -> str:
    """Human-readable error for logs/attributes (str(err) is often empty)."""
    text = str(err).strip()
    if text:
        return f"{type(err).__name__}: {text}"
    return f"{type(err).__name__}: {err!r}"


class LabelCloudLookup:
    """Resolves a label barcode to name/size/preview via the NIIMBOT cloud catalogue.

    Matches and definitive "not found" (HTTP 200, no data) are cached to disk.
    Transient failures (timeout, non-200, malformed body) are not cached so the
    next poll can retry. Callers should check ``last_result_definitive`` when
    ``get`` returns None to decide whether to suppress further lookups.
    """

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
            # OSError covers SSLError; str(SSLError) is often empty.
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

        return (
            LabelInfo(
                label_name=_pick_name(data),
                label_width_mm=data.get("width"),
                label_height_mm=data.get("height"),
                preview_url=data.get("previewImage"),
            ),
            True,
        )
