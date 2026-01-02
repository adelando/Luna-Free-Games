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
            # We must use a precise User-Agent so Amazon doesn't serve an empty page
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(SOURCE_URL, headers=headers, timeout=20) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"Amazon error: {response.status}")
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    found_games = []

                    # Search through every element with an aria-label
                    # Amazon titles usually follow "Claim [Game Name]"
                    for el in soup.find_all(attrs={"aria-label": True}):
                        label = el['aria-label']
                        if "Claim " in label and len(label) < 60:
                            game_name = label.replace("Claim ", "").strip()
                            found_games.append({
                                "title": game_name,
                                "image": "https://luna.amazon.com/favicon.ico"
                            })

                    # Fallback: Scrape for titles in common containers
                    if not found_games:
                        for span in soup.find_all(['span', 'div', 'p']):
                            text = span.get_text().strip()
                            if 3 < len(text) < 40 and text[0].isupper():
                                # Filter UI noise
                                if text not in ["Home", "Settings", "Library", "Play", "Sign In"]:
                                    found_games.append({"title": text, "image": "https://luna.amazon.com/favicon.ico"})

                    # Deduplicate
                    return list({v['title']:v for v in found_games}.values())

        except Exception as e:
            _LOGGER.error("Luna Scraper failed: %s", e)
            raise UpdateFailed(f"Could not reach Luna: {e}")

    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, name="Luna Claims",
        update_method=async_get_data,
        update_interval=timedelta(hours=12),
    )

    await coordinator.async_config_entry_first_refresh()
    async_add_entities([LunaGamesSensor(coordinator)], True)

class LunaGamesSensor(SensorEntity):
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_name = "Amazon Luna Free Games"
        self._attr_unique_id = "luna_claims_v6"

    @property
    def native_value(self):
        return len(self.coordinator.data) if self.coordinator.data else 0

    @property
    def extra_state_attributes(self):
        return {"games": self.coordinator.data}

    @property
    def icon(self):
        return "mdi:amazon"

    @property
    def should_poll(self):
        return False

    async def async_added_to_hass(self):
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
