from unittest.mock import MagicMock
import pytest
from homeassistant.exceptions import HomeAssistantError
from custom_components.niimbot.imagegen import customimage


def test_customimage_simple():
    # Arrange
    service = MagicMock()
    service.data = {
        "payload": [
            {"type": "rectangle", "x_start": 0, "y_start": 0, "x_end": 100, "y_end": 50, "fill": "black"}
        ],
        "width": 400,
        "height": 240,
        "rotate": 0,
        "background": "white"
    }

    hass = MagicMock()
    # Mock hass.config.path to return a temporary/mock path
    hass.config.path = MagicMock(return_value="/tmp/mock_fonts")

    # Act
    image = customimage("dummy_entity", service, hass)

    # Assert
    assert image is not None
    assert image.size == (400, 240)


def test_customimage_render_error():
    # Arrange
    service = MagicMock()
    # Payload with an invalid element option or structure to trigger RenderError
    service.data = {
        "payload": [
            {"type": "rectangle", "x_start": "invalid_coord", "y_start": 0, "x_end": 100, "y_end": 50}
        ],
        "width": 400,
        "height": 240,
        "rotate": 0,
        "background": "white"
    }

    hass = MagicMock()
    hass.config.path = MagicMock(return_value="/tmp/mock_fonts")

    # Act / Assert
    with pytest.raises(HomeAssistantError):
        customimage("dummy_entity", service, hass)
