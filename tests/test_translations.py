"""Tests for translation files validity and completeness."""

import json
import os

COMPONENT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "custom_components", "niimbot"
)
STRINGS_PATH = os.path.join(COMPONENT_DIR, "strings.json")
EN_PATH = os.path.join(COMPONENT_DIR, "translations", "en.json")
KO_PATH = os.path.join(COMPONENT_DIR, "translations", "ko.json")

EXPECTED_OPTION_KEYS = {
    "scan_interval",
    "wait_between_each_print_line",
    "confirm_every_nth_print_line",
    "keep_connection",
    "use_cloud_label_info",
}


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_json_files_are_valid():
    """Test that all translation and strings JSON files load without error."""
    strings = _load_json(STRINGS_PATH)
    en = _load_json(EN_PATH)
    ko = _load_json(KO_PATH)

    assert isinstance(strings, dict)
    assert isinstance(en, dict)
    assert isinstance(ko, dict)


def test_config_flow_options_and_descriptions_are_complete():
    """Test that all options and data descriptions exist for config steps and options flow."""
    for path in (STRINGS_PATH, EN_PATH, KO_PATH):
        data = _load_json(path)

        # Check config.step.user
        user_data = data["config"]["step"]["user"]["data"]
        user_desc = data["config"]["step"]["user"]["data_description"]
        assert EXPECTED_OPTION_KEYS.issubset(set(user_data.keys()))
        assert EXPECTED_OPTION_KEYS == set(user_desc.keys())
        assert "address" in user_data

        # Check config.step.bluetooth_confirm
        bt_data = data["config"]["step"]["bluetooth_confirm"]["data"]
        bt_desc = data["config"]["step"]["bluetooth_confirm"]["data_description"]
        assert EXPECTED_OPTION_KEYS == set(bt_data.keys())
        assert EXPECTED_OPTION_KEYS == set(bt_desc.keys())

        # Check options.step.init
        opt_data = data["options"]["step"]["init"]["data"]
        opt_desc = data["options"]["step"]["init"]["data_description"]
        assert EXPECTED_OPTION_KEYS == set(opt_data.keys())
        assert EXPECTED_OPTION_KEYS == set(opt_desc.keys())


def test_korean_translation_has_no_typos():
    """Test that Korean translation does not contain known typos."""
    with open(KO_PATH, "r", encoding="utf-8") as f:
        ko_text = f.read()
    assert "니밤봇" not in ko_text
