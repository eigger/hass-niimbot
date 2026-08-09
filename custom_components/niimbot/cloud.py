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
             "AppVersionName">
    Body:    {"oneCode": "<barcode>"}
    Found:   200, body["data"] present with "width"/"height" (mm) and a "names" list
             of {languageCode, languageName, name}; not every language is populated.
    Unknown: 200, body has no "data" key at all (not a 404).

The niimbot-user-agent header is a client-identification requirement, not a login —
this integration truthfully identifies itself rather than impersonating the official
app. This is an undocumented endpoint and may change or disappear without notice;
every failure mode here must degrade to "no extra info", never to a broken entity.
"""

from __future__ import annotations

import logging
import time
from typing import TypedDict

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

_ENDPOINT = "https://print.niimbot.com/api/template/getCloudTemplateByOneCode"
_TIMEOUT = aiohttp.ClientTimeout(total=10)
_CLIENT_HEADER = "AppVersionName/hass-niimbot"

_STORE_VERSION = 1
_STORE_KEY = "niimbot_label_cache"
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


class LabelCloudLookup:
    """Resolves a label barcode to name/size/preview via the NIIMBOT cloud catalogue.

    Every result is cached to disk per barcode, including "not found", so a given
    barcode triggers at most one network request per _NEGATIVE_RECHECK_SECONDS
    window (matches never expire). All failures — timeout, non-200, malformed body,
    no match — return None; callers must treat that the same as "no info available".
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store: Store = Store(hass, _STORE_VERSION, _STORE_KEY)
        self._cache: dict[str, dict] | None = None

    async def _load_cache(self) -> dict[str, dict]:
        if self._cache is None:
            self._cache = await self._store.async_load() or {}
        return self._cache

    async def get(self, barcode: str) -> LabelInfo | None:
        """Return label info for a barcode, using the on-disk cache when possible."""
        if not barcode:
            return None

        cache = await self._load_cache()
        entry = cache.get(barcode)
        if entry is not None:
            if entry.get("negative"):
                if time.time() - entry.get("checked_at", 0) < _NEGATIVE_RECHECK_SECONDS:
                    return None
            else:
                return entry.get("info")

        info = await self._fetch(barcode)
        cache[barcode] = (
            {"info": dict(info), "checked_at": time.time()}
            if info is not None
            else {"negative": True, "checked_at": time.time()}
        )
        await self._store.async_save(cache)
        return info

    async def _fetch(self, barcode: str) -> LabelInfo | None:
        session = async_get_clientsession(self._hass)
        try:
            async with session.post(
                _ENDPOINT,
                json={"oneCode": barcode},
                headers={"niimbot-user-agent": _CLIENT_HEADER},
                timeout=_TIMEOUT,
            ) as resp:
                if resp.status != 200:
                    _LOGGER.debug(
                        "Cloud label lookup for %s: HTTP %s", barcode, resp.status
                    )
                    return None
                body = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.debug("Cloud label lookup for %s failed: %s", barcode, err)
            return None
        except ValueError as err:
            _LOGGER.debug("Cloud label lookup for %s: bad response: %s", barcode, err)
            return None

        data = body.get("data") if isinstance(body, dict) else None
        if not data:
            _LOGGER.debug("Cloud label lookup for %s: no match", barcode)
            return None

        return LabelInfo(
            label_name=_pick_name(data),
            label_width_mm=data.get("width"),
            label_height_mm=data.get("height"),
            preview_url=data.get("previewImage"),
        )
