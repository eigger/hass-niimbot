import os

from homeassistant.exceptions import HomeAssistantError
from homeassistant.components.recorder.history import get_significant_states

from imagespec import render, RenderContext, RenderError


def _make_context(hass, *, default_font, palette):
    def font_resolver(name):
        base_name = os.path.basename(name)
        
        # 1. Check local niimbot components fonts/ directory
        local_font_dir = os.path.join(os.path.dirname(__file__), "fonts")
        local_path = os.path.join(local_font_dir, base_name)
        if os.path.exists(local_path):
            return local_path

        # 2. Check Home Assistant www/fonts
        www_fonts_dir = hass.config.path("www/fonts")
        www_path = os.path.join(www_fonts_dir, base_name)
        if os.path.exists(www_path):
            return www_path

        return None

    def history_provider(entity_ids, start, end):
        return get_significant_states(
            hass,
            start_time=start,
            entity_ids=list(entity_ids),
            significant_changes_only=False,
            minimal_response=True,
            no_attributes=False,
        )

    return RenderContext(
        font_resolver=font_resolver,
        history_provider=history_provider,
        default_font=default_font,
        palette=palette,
    )


def customimage(entity_id, service, hass):
    try:
        return render(
            payload=service.data.get("payload", ""),
            width=service.data.get("width", 400),
            height=service.data.get("height", 240),
            rotate=service.data.get("rotate", 0),
            rotate_mode="image",    # label printer: variable size, drawing rotates
            background=service.data.get("background", "white"),
            context=_make_context(hass, default_font="ppb.ttf", palette=["black", "white"]),
        )
    except RenderError as err:
        raise HomeAssistantError(str(err)) from err
