import logging
import aiohttp
from bs4 import BeautifulSoup
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from .const import SOURCE_URL

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=12)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensor platform."""
    async_add_entities([LunaGamesSensor()], True)

class LunaGamesSensor(SensorEntity):
    def __init__(self):
        self._attr_name = "Amazon Luna Free Games"
        self._attr_unique_id = "amazon_luna_free_games_list"
        self._state = 0
        self._games = []

    @property
    def native_value(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return {"games": self._games}

    @property
    def icon(self):
        return "mdi:controller-classic"

    async def async_update(self):
        """Fetch data from the source."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(SOURCE_URL, timeout=10) as response:
                    if response.status != 200:
                        _LOGGER.error("Failed to fetch Luna games")
                        return
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Targeting the specific list structure on Cloud Dosage
                    game_elements = soup.select("ul.wp-block-list li")
                    
                    found_games = []
                    for element in game_elements:
                        title = element.get_text().strip()
                        if title:
                            found_games.append({
                                "title": title,
                                "image": "https://luna.amazon.com/favicon.ico" # Generic icon
                            })

                    self._games = found_games
                    self._state = len(found_games)
                    
        except Exception as e:
            _LOGGER.error("Error updating Luna games: %s", e)
n