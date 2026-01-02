import logging
import aiohttp
import re
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
            # We use an even more detailed header to mimic a real Desktop Browser
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/"
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(SOURCE_URL, headers=headers, timeout=20) as response:
                    if response.status != 200:
                        _LOGGER.error("Luna site returned status: %s", response.status)
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Log the HTML length for debugging
                    _LOGGER.debug("Luna Scraper: Received %s bytes of HTML", len(html))
                    
                    found_games = []

                    # STRATEGY: Look for ANY text block that contains "Release Date" or "Developer"
                    # This finds them even if they aren't in <li> tags (e.g. inside <div> or <p>)
                    potential_elements = soup.find_all(['li', 'p', 'div'], string=re.compile(r'Release Date|Developer|Publisher', re.I))

                    for element in potential_elements:
                        text = element.get_text().strip()
                        
                        # Clean the text: Usually "Game Name. Release Date: ..."
                        # We split by the first period or the word 'Release'
                        parts = re.split(r'\. | Release| –', text)
                        title = parts[0].replace("- ", "").strip()

                        if 3 < len(title) < 50:
                            found_games.append({
                                "title": title,
                                "image": "https://luna.amazon.com/favicon.ico"
                            })

                    # DEDUPLICATE
                    unique_list = list({v['title']:v for v in found_games}.values())
                    
                    if not unique_list:
                        _LOGGER.warning("Luna Scraper: Page loaded but no games found. Website structure may have changed.")
                    
                    return unique_list

        except Exception as e:
            _LOGGER.error("Luna Scraper Critical Error: %s", e)
            raise UpdateFailed(f"Error: {e}")

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
        self._attr_unique_id = "amazon_luna_free_games_list_v3" # New ID to force refresh

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
