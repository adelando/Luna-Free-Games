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
            # Use a real browser User-Agent to avoid being blocked
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

                    # 1. Primary Strategy: Look for the 2026 List format
                    # Most game lists on Cloud Dosage are now in an entry-content div
                    content_area = soup.find('div', class_='entry-content')
                    if content_area:
                        items = content_area.find_all('li')
                        for item in items:
                            text = item.get_text().strip()
                            
                            # Clean up common formatting (e.g., "Game Title. Release Date: ...")
                            if "Release Date" in text or "Developer" in text:
                                # Split at the first period to get just the title
                                title = text.split(".")[0].replace("- ", "").strip()
                                found_games.append({
                                    "title": title,
                                    "image": "https://luna.amazon.com/favicon.ico"
                                })
                    
                    # 2. Fallback Strategy: If list items were empty, grab generic list items
                    if not found_games:
                        all_lis = soup.find_all('li')
                        for li in all_lis:
                            text = li.get_text().strip()
                            # Filter for reasonable title lengths to avoid menu links
                            if 3 < len(text) < 60:
                                found_games.append({
                                    "title": text,
                                    "image": "https://luna.amazon.com/favicon.ico"
                                })

                    _LOGGER.debug("Luna Scraper found %s games", len(found_games))
                    return found_games

        except Exception as e:
            _LOGGER.error("Luna Scraper Error: %s", e)
            raise UpdateFailed(f"Error communicating with Luna source: {e}")

    # Coordinator manages the 12-hour refresh cycle
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
    """Representation of the Luna Games Sensor."""

    def __init__(self, coordinator):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_name = "Amazon Luna Free Games"
        self._attr_unique_id = "amazon_luna_free_games_list"

    @property
    def native_value(self):
        """Return the number of games found."""
        if self.coordinator.data:
            return len(self.coordinator.data)
        return 0

    @property
    def extra_state_attributes(self):
        """Return the list of games as attributes."""
        return {"games": self.coordinator.data}

    @property
    def icon(self):
        """Icon for the sensor."""
        return "mdi:controller-classic"

    @property
    def should_poll(self):
        """No polling needed, coordinator handles it."""
        return False

    async def async_added_to_hass(self):
        """Connect to coordinator update signal."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the sensor data."""
        await self.coordinator.async_request_refresh()
