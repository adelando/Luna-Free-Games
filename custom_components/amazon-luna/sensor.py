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
            # Amazon checks User-Agents strictly. This mimics a modern Chrome browser.
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(SOURCE_URL, headers=headers, timeout=20) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"Amazon returned status {response.status}")
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    found_games = []

                    # STRATEGY: Amazon uses 'aria-label' for their claim buttons.
                    # We look for any element that has an aria-label containing 'Claim'
                    for el in soup.find_all(attrs={"aria-label": True}):
                        label = el['aria-label']
                        
                        if "Claim " in label:
                            # Extract game name: "Claim Fallout 3" -> "Fallout 3"
                            game_title = label.replace("Claim ", "").strip()
                            
                            if 2 < len(game_title) < 60:
                                found_games.append({
                                    "title": game_title,
                                    "image": "https://luna.amazon.com/favicon.ico"
                                })

                    # FALLBACK: If labels fail, look for specific text patterns
                    if not found_games:
                        for span in soup.find_all('span'):
                            text = span.get_text().strip()
                            # Look for capitalized titles that aren't UI buttons
                            if 3 < len(text) < 40 and text[0].isupper():
                                if text not in ["Home", "Settings", "Library", "Play", "Sign In"]:
                                    found_games.append({"title": text, "image": "https://luna.amazon.com/favicon.ico"})

                    # Deduplicate
                    unique_games = list({v['title']:v for v in found_games}.values())
                    _LOGGER.debug("Luna Scraper found %s games", len(unique_games))
                    return unique_games

        except Exception as e:
            _LOGGER.error("Luna Scraper Error: %s", e)
            raise UpdateFailed(f"Error fetching Luna data: {e}")

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
        self._attr_unique_id = "amazon_luna_claims_v5"

    @property
    def native_value(self):
        return len(self.coordinator.data) if self.coordinator.data else 0

    @property
    def extra_state_attributes(self):
        return {"games": self.coordinator.data}

    @property
    def icon(self):
        return "mdi:amazon-alexa"

    @property
    def should_poll(self):
        return False

    async def async_added_to_hass(self):
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
