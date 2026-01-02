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
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(SOURCE_URL, headers=headers, timeout=15) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"Site returned status {response.status}")
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    found_games = []

                    # 1. Target the main article body ONLY (ignores sidebar/menus)
                    content_area = soup.find('div', class_='entry-content')
                    
                    if content_area:
                        # 2. Look for list items that are likely game titles
                        items = content_area.find_all('li')
                        for item in items:
                            text = item.get_text().strip()
                            
                            # 3. Filtering logic:
                            # Skip short menu links and common junk phrases
                            if len(text) < 5 or any(x in text.lower() for x in ["click here", "follow us", "subscribe"]):
                                continue
                                
                            # 4. Title Cleaning:
                            # Many lists look like "Game Title – Leaving Jan 1" or "Game Title. Release Date..."
                            # We split by common delimiters and take the first part
                            clean_title = text.split('–')[0].split('.')[0].split(' - ')[0].replace("- ", "").strip()
                            
                            # Final validation to ensure it's not a sentence
                            if len(clean_title) < 60:
                                found_games.append({
                                    "title": clean_title,
                                    "image": "https://luna.amazon.com/favicon.ico"
                                })

                    # Remove duplicates if any
                    unique_games = list({v['title']:v for v in found_games}.values())
                    
                    _LOGGER.debug("Luna Scraper: Found %s unique games", len(unique_games))
                    return unique_games

        except Exception as e:
            _LOGGER.error("Luna Scraper Error: %s", e)
            raise UpdateFailed(f"Error communicating with Luna source: {e}")

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
        return len(self.coordinator.data) if self.coordinator.data else 0

    @property
    def extra_state_attributes(self):
        return {"games": self.coordinator.data}

    @property
    def icon(self):
        return "mdi:controller-classic"

    @property
    def should_poll(self):
        return False

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
