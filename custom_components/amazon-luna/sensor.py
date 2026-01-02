import logging
import aiohttp
from bs4 import BeautifulSoup
from datetime import timedelta
import re

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, SOURCE_URL

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor platform via Config Flow."""
    
    async def async_get_data():
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(SOURCE_URL, headers=headers, timeout=15) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    found_games = []

                    # 1. Target the main article body
                    content = soup.find('div', class_='entry-content') or soup
                    
                    # 2. Extract every string on the page and filter for games
                    # Most game titles are in <li> or <strong> tags this month
                    potential_elements = content.find_all(['li', 'strong', 'td'])
                    
                    for element in potential_elements:
                        text = element.get_text().strip()
                        
                        # Filtering Logic: Look for markers like 'Jan', 'Feb', or 'Luna'
                        # while avoiding generic menu items
                        if (len(text) > 3 and len(text) < 50 and 
                            not any(x in text.lower() for x in ["click", "follow", "share", "comment"])):
                            
                            # Clean the title (remove bullets, dates, and extra metadata)
                            clean_title = re.split(r'–| - |\.| on ', text)[0].replace("•", "").strip()
                            
                            if len(clean_title) > 2:
                                found_games.append({
                                    "title": clean_title,
                                    "image": "https://luna.amazon.com/favicon.ico"
                                })

                    # Deduplicate the list
                    unique_games = []
                    seen = set()
                    for g in found_games:
                        if g['title'] not in seen:
                            unique_games.append(g)
                            seen.add(g['title'])
                    
                    return unique_games

        except Exception as e:
            raise UpdateFailed(f"Scraper error: {e}")

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
        self._attr_unique_id = "amazon_luna_free_games_v4"

    @property
    def native_value(self):
        return len(self.coordinator.data) if self.coordinator.data else 0

    @property
    def extra_state_attributes(self):
        return {"games": self.coordinator.data}

    @property
    def icon(self):
        return "mdi:controller-classic"
