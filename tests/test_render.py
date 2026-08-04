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


def test_render_image_per_element_dither():
    """Service has no dither; use per-element dither for photos/charts only."""
    hass = MagicMock()
    hass.config.path = MagicMock(return_value="/tmp/mock_fonts")

    service_flat = MagicMock()
    service_flat.data = {
        "payload": [
            {"type": "rectangle", "x_start": 0, "y_start": 0, "x_end": 10, "y_end": 10, "fill": "#808080", "outline": "#808080"}
        ],
        "width": 10,
        "height": 10,
        "rotate": 0,
        "background": "white",
    }
    img_flat = render_image("dummy_entity", service_flat, hass)

    service_dither = MagicMock()
    service_dither.data = {
        "payload": [
            {
                "type": "rectangle",
                "x_start": 0,
                "y_start": 0,
                "x_end": 10,
                "y_end": 10,
                "fill": "#808080",
                "outline": "#808080",
                "dither": "floyd",
            }
        ],
        "width": 10,
        "height": 10,
        "rotate": 0,
        "background": "white",
    }
    img_dither = render_image("dummy_entity", service_dither, hass)

    w, h = img_flat.size
    unique_flat = {img_flat.getpixel((x, y)) for y in range(h) for x in range(w)}
    assert len(unique_flat) == 1

    unique_dither = {img_dither.getpixel((x, y)) for y in range(h) for x in range(w)}
    assert unique_dither == {(0, 0, 0), (255, 255, 255)}
