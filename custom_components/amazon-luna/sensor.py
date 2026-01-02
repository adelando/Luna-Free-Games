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
            # We use an updated User-Agent to ensure we aren't blocked by the server
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(SOURCE_URL, headers=headers, timeout=15) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"Site returned {response.status}")
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    found_games = []

                    # 1. Target EVERYTHING that looks like a list item on the whole page
                    # This is more robust if the container name changes
                    items = soup.find_all('li')
                    
                    for item in items:
                        text = item.get_text().strip()
                        
                        # 2. Logic: If it mentions 'Release Date' or 'Developer', it's a game entry
                        if "Release Date" in text or "Developer" in text:
                            # Split by common characters to isolate just the title
                            # e.g., "Batman. Release Date: 2024" -> "Batman"
                            for separator in ['.', '–', ' - ', ':']:
                                if separator in text:
                                    text = text.split(separator)[0]
                                    break
                            
                            clean_title = text.replace("- ", "").strip()
                            
                            # Sanity check: titles shouldn't be massive or tiny
                            if 2 < len(clean_title) < 70:
                                found_games.append({
                                    "title": clean_title,
                                    "image": "https://luna.amazon.com/favicon.ico"
                                })

                    # 3. Deduplicate (remove duplicates)
                    unique_list = []
                    seen_titles = set()
                    for game in found_games:
                        if game['title'] not in seen_titles:
                            unique_list.append(game)
                            seen_titles.add(game['title'])

                    _LOGGER.debug("Scraper found %s games after filtering", len(unique_list))
                    return unique_list

        except Exception as e:
            _LOGGER.error("Luna Scraper failed: %s", e)
            raise UpdateFailed(f"Could not reach game source: {e}")

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
        self._attr_unique_id = "amazon_luna_free_games_list_v2"

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
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
