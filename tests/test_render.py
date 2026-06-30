from unittest.mock import MagicMock
import pytest
from homeassistant.exceptions import HomeAssistantError
from custom_components.niimbot.render import render_image


def test_render_image_simple():
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
    image = render_image("dummy_entity", service, hass)

    # Assert
    assert image is not None
    assert image.size == (400, 240)


def test_render_image_render_error():
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
        render_image("dummy_entity", service, hass)


def test_render_image_dither():
    # Arrange
    hass = MagicMock()
    hass.config.path = MagicMock(return_value="/tmp/mock_fonts")

    # 1. Render without dither (flat)
    service_no_dither = MagicMock()
    service_no_dither.data = {
        "payload": [
            {"type": "rectangle", "x_start": 0, "y_start": 0, "x_end": 10, "y_end": 10, "fill": "#808080", "outline": "#808080"}
        ],
        "width": 10,
        "height": 10,
        "rotate": 0,
        "background": "white",
        "dither": False
    }
    img_no_dither = render_image("dummy_entity", service_no_dither, hass)

    # 2. Render with dither
    service_dither = MagicMock()
    service_dither.data = {
        "payload": [
            {"type": "rectangle", "x_start": 0, "y_start": 0, "x_end": 10, "y_end": 10, "fill": "#808080", "outline": "#808080"}
        ],
        "width": 10,
        "height": 10,
        "rotate": 0,
        "background": "white",
        "dither": True
    }
    img_dither = render_image("dummy_entity", service_dither, hass)

    # Assert
    w, h = img_no_dither.size
    pixels_no_dither = [img_no_dither.getpixel((x, y)) for y in range(h) for x in range(w)]
    unique_no_dither = set(pixels_no_dither)
    assert len(unique_no_dither) == 1

    pixels_dither = [img_dither.getpixel((x, y)) for y in range(h) for x in range(w)]
    unique_dither = set(pixels_dither)
    assert (0, 0, 0) in unique_dither
    assert (255, 255, 255) in unique_dither
