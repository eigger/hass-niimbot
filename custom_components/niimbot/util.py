
def get_image_folder(hass):
    """Return the folder where images are stored."""
    return hass.config.path("www/niimbot")

def get_image_path(hass, entity_id):
    """Return the path to the image for a specific tag."""
    return hass.config.path("www/niimbot/niimbot."+ str(entity_id).lower() + ".jpg")