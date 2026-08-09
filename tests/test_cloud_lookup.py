"""Tests for the optional online label lookup (T9).

Network and storage are faked at the module level (custom_components.niimbot.cloud
imports Store and async_get_clientsession by name, so patching those names is
enough) rather than exercising real aiohttp or Home Assistant's Store — this repo's
tests never require a network connection or a real Home Assistant install.
"""

import asyncio

import aiohttp

from custom_components.niimbot.cloud import (
    LabelCloudLookup,
    _pick_name,
    parse_label_data,
)


def run(coro):
    return asyncio.run(coro)


class FakeStore:
    """In-memory stand-in for homeassistant.helpers.storage.Store."""

    def __init__(self, initial: dict | None = None):
        self._data = initial or {}
        self.saved: list[dict] = []

    async def async_load(self):
        return dict(self._data) if self._data else None

    async def async_save(self, data):
        self._data = dict(data)
        self.saved.append(dict(data))


class FakeResponse:
    def __init__(self, status: int, body):
        self.status = status
        self._body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def json(self, content_type=None):
        return self._body


class RaisingResponse:
    """Simulates the request itself failing (timeout/connection error)."""

    def __init__(self, exc: Exception):
        self._exc = exc

    def __call__(self, *args, **kwargs):
        return self

    async def __aenter__(self):
        raise self._exc

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    def __init__(self, responder):
        """responder(barcode) -> FakeResponse-like async context manager."""
        self._responder = responder
        self.calls: list[str] = []

    def post(self, url, *, json, headers, timeout=None, **kwargs):
        self.calls.append(json["oneCode"])
        return self._responder(json["oneCode"])


def _lookup_with(monkeypatch, session: FakeSession, store: FakeStore) -> LabelCloudLookup:
    monkeypatch.setattr(
        "custom_components.niimbot.cloud.async_get_clientsession",
        lambda hass: session,
    )
    monkeypatch.setattr(
        "custom_components.niimbot.cloud.Store",
        lambda hass, version, key: store,
    )
    return LabelCloudLookup(hass=object())


SUCCESS_BODY = {
    "data": {
        "id": 80006400,
        "name": "T50*30-230",
        "names": [
            {"languageCode": "zh-cn", "name": "T50*30-230"},
            {"languageCode": "en", "name": "White 50x30"},
        ],
        "width": 50,
        "height": 30,
        "paccuracyName": 203,
        "paperType": 1,
        "rotate": 0,
        "previewImage": "https://oss-print.niimbot.com/preview.png",
        "barcode": "6972842748577",
    },
    "code": 1,
}

# Real B1 SKU shape: empty names[], sizes in labelNames, canvas rotated 270°.
B1_SKU_BODY = {
    "data": {
        "id": 154629949,
        "names": [],
        "labelNames": [
            {"languageCode": "zh-cn", "name": "T50*30-230白色"},
            {"languageCode": "en", "name": "T50*30-230WHITE-NM"},
            {"languageCode": "ko", "name": "T50*30-230WHITE"},
        ],
        "width": 30,
        "height": 50,
        "paccuracyName": 203,
        "paperType": 1,
        "consumableType": 1,
        "rotate": 270,
        "canvasRotate": 90,
        "margin": [0, 0, 0, 0],
        "previewImage": "https://oss-print.niimbot.com/preview.png",
        "thumbnail": "https://oss-print.niimbot.com/thumb.png",
        "backgroundImage": "https://oss-print.niimbot.com/bg.png",
        "barcode": "6971501227941",
        "version": "3.0.0",
    },
    "code": 1,
}

NOT_FOUND_BODY = {"code": 1, "status_code": 1, "message": "成功"}


def test_pick_name_prefers_english():
    assert _pick_name(SUCCESS_BODY["data"]) == "White 50x30"


def test_pick_name_falls_back_to_default_when_no_en_or_ko():
    data = {"name": "套装T50", "names": [{"languageCode": "zh-cn", "name": "套装T50"}]}
    assert _pick_name(data) == "套装T50"


def test_pick_name_skips_empty_language_entries():
    data = {
        "name": "fallback",
        "names": [
            {"languageCode": "ja", "name": ""},
            {"languageCode": "ko", "name": "한글 이름"},
        ],
    }
    assert _pick_name(data) == "한글 이름"


def test_pick_name_handles_no_names_at_all():
    assert _pick_name({}) is None


def test_pick_name_uses_label_names_when_names_empty():
    assert _pick_name(B1_SKU_BODY["data"]) == "T50*30-230WHITE-NM"


def test_parse_label_data_computes_pixels_and_print_size():
    info = parse_label_data(SUCCESS_BODY["data"])
    assert info["label_width_mm"] == 50
    assert info["label_height_mm"] == 30
    assert info["dpi"] == 203
    assert info["label_width_px"] == 400
    assert info["label_height_px"] == 240
    assert info["print_width_px"] == 400
    assert info["print_height_px"] == 240
    assert info["paper_type"] == 1


def test_parse_label_data_swaps_print_size_when_rotated():
    info = parse_label_data(B1_SKU_BODY["data"])
    assert info["label_name"] == "T50*30-230WHITE-NM"
    assert info["label_width_mm"] == 30
    assert info["label_height_mm"] == 50
    assert info["label_width_px"] == 240
    assert info["label_height_px"] == 400
    # rotate 270 → print bitmap is swapped vs catalogue canvas
    assert info["print_width_px"] == 400
    assert info["print_height_px"] == 240
    assert info["catalog_barcode"] == "6971501227941"
    assert info["label_names"]["ko"] == "T50*30-230WHITE"


def test_get_returns_none_for_empty_barcode():
    async def _test():
        lookup = LabelCloudLookup(hass=object())
        assert await lookup.get("") is None
        assert await lookup.get(None) is None

    run(_test())


def test_get_fetches_and_caches_on_success(monkeypatch):
    async def _test():
        store = FakeStore()

        def responder(barcode):
            return FakeResponse(200, SUCCESS_BODY)

        session = FakeSession(responder)
        lookup = _lookup_with(monkeypatch, session, store)

        info = await lookup.get("6972842748577")
        assert info["label_name"] == "White 50x30"
        assert info["label_width_mm"] == 50
        assert info["label_height_mm"] == 30
        assert info["label_width_px"] == 400
        assert info["label_height_px"] == 240
        assert info["print_width_px"] == 400
        assert info["print_height_px"] == 240
        assert info["preview_url"] == "https://oss-print.niimbot.com/preview.png"
        assert info["dpi"] == 203
        assert session.calls == ["6972842748577"]
        assert lookup.last_source == "network"

        # Second lookup for the same barcode must not hit the network again.
        info2 = await lookup.get("6972842748577")
        assert info2 == info
        assert session.calls == ["6972842748577"]
        assert lookup.last_source == "cache"
        assert store.saved, "result must have been persisted"

    run(_test())


def test_get_caches_negative_result_without_retry(monkeypatch):
    async def _test():
        store = FakeStore()

        def responder(barcode):
            return FakeResponse(200, NOT_FOUND_BODY)

        session = FakeSession(responder)
        lookup = _lookup_with(monkeypatch, session, store)

        assert await lookup.get("00000000000000") is None
        assert lookup.last_result_definitive is True
        assert session.calls == ["00000000000000"]

        # Still no match, still within the recheck window: no second call.
        assert await lookup.get("00000000000000") is None
        assert lookup.last_result_definitive is True
        assert session.calls == ["00000000000000"]

    run(_test())


def test_get_returns_none_on_non_200_without_caching(monkeypatch):
    async def _test():
        store = FakeStore()

        def responder(barcode):
            return FakeResponse(500, {"code": 500, "message": "系统异常"})

        session = FakeSession(responder)
        lookup = _lookup_with(monkeypatch, session, store)

        assert await lookup.get("02282280") is None
        assert lookup.last_result_definitive is False
        assert store.saved == []

        # Transient failures must be retryable on the next poll.
        assert await lookup.get("02282280") is None
        assert session.calls == ["02282280", "02282280"]

    run(_test())


def test_get_returns_none_on_client_error(monkeypatch):
    async def _test():
        store = FakeStore()
        session = FakeSession(RaisingResponse(aiohttp.ClientError("connection reset")))
        lookup = _lookup_with(monkeypatch, session, store)

        # Must not raise — a network failure degrades to "no info", never an error.
        assert await lookup.get("02282280") is None
        assert lookup.last_result_definitive is False
        assert lookup.last_error is not None
        assert "ClientError" in lookup.last_error
        assert store.saved == []

    run(_test())


def test_get_returns_none_on_empty_oserror(monkeypatch):
    async def _test():
        store = FakeStore()
        # SSLError/OSError often stringify to "" — must still be visible via last_error.
        session = FakeSession(RaisingResponse(OSError()))
        lookup = _lookup_with(monkeypatch, session, store)

        assert await lookup.get("02282280") is None
        assert lookup.last_result_definitive is False
        assert lookup.last_error == "OSError: OSError()"
        assert store.saved == []

    run(_test())


def test_get_returns_none_on_timeout(monkeypatch):
    async def _test():
        store = FakeStore()
        session = FakeSession(RaisingResponse(TimeoutError()))
        lookup = _lookup_with(monkeypatch, session, store)

        assert await lookup.get("02282280") is None
        assert lookup.last_result_definitive is False

    run(_test())


def test_get_returns_none_on_malformed_body(monkeypatch):
    async def _test():
        store = FakeStore()

        def responder(barcode):
            return FakeResponse(200, ["not", "a", "dict"])

        session = FakeSession(responder)
        lookup = _lookup_with(monkeypatch, session, store)

        assert await lookup.get("02282280") is None
        # 200 with a non-dict body: treat as non-definitive (do not cache).
        assert lookup.last_result_definitive is False
        assert store.saved == []

    run(_test())


def test_get_uses_preloaded_cache_without_any_network_call(monkeypatch):
    async def _test():
        store = FakeStore(
            initial={
                "6972842748577": {
                    "info": {
                        "label_name": "cached name",
                        "label_width_mm": 50,
                        "label_height_mm": 30,
                        "preview_url": None,
                    },
                    "checked_at": 0,
                }
            }
        )

        def responder(barcode):
            raise AssertionError("network must not be called for a cached SKU")

        session = FakeSession(responder)
        lookup = _lookup_with(monkeypatch, session, store)

        info = await lookup.get("6972842748577")
        assert info["label_name"] == "cached name"
        assert session.calls == []

    run(_test())
