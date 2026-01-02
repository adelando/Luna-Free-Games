from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from .const import DOMAIN

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Amazon Luna component."""
    hass.helpers.discovery.load_platform("sensor", DOMAIN, {}, config)
    return True
