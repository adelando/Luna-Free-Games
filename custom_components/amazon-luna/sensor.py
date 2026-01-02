import logging
import aiohttp
from bs4 import BeautifulSoup
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, SOURCE_URL

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor platform via Config Flow."""
    
    async def async_get_data():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(SOURCE_URL, timeout=10) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    game_elements = soup.select("ul.wp-block-list li")
                    
                    found_games = []
                    for element in game_elements:
                        title = element.get_text().strip()
                        if title:
                            found_games.append({
                                "title": title,
                                "image": "https://luna.amazon.com/favicon.ico"
                            })
                    return found_games
        except Exception as e:
            raise UpdateFailed(f"Error communicating with Luna source: {e}")

    # Coordinator manages updates for us automatically
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Luna Games",
        update_method=async_get_data,
        update_interval=timedelta(hours=12),
    )

    await coordinator.async_config_entry_first_refresh()
    async_add_entities([LunaGamesSensor(coordinator)], True)

class LunaGamesSensor(SensorEntity):
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_name = "Amazon Luna Free Games"
        self._attr_unique_id = "amazon_luna_free_games_list"

    @property
    def native_value(self):
        return len(self.coordinator.data)

    @property
    def extra_state_attributes(self):
        return {"games": self.coordinator.data}

    @property
    def icon(self):
        return "mdi:controller-classic"

    @property
    def should_poll(self):
        return False

    async def async_added_to_hash(self):
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
