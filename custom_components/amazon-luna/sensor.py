import logging
import aiohttp
from bs4 import BeautifulSoup
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, SOURCE_URL

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    async def async_get_data():
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(SOURCE_URL, headers=headers, timeout=20) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    found_games = []

                    # Scrape aria-labels for "Claim [Game Name]"
                    for el in soup.find_all(attrs={"aria-label": True}):
                        label = el['aria-label']
                        if "Claim " in label:
                            title = label.replace("Claim ", "").strip()
                            found_games.append({"title": title, "image": "https://luna.amazon.com/favicon.ico"})

                    # Deduplicate
                    return list({v['title']:v for v in found_games}.values())
        except Exception as e:
            raise UpdateFailed(f"Scraper error: {e}")

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
        self._attr_unique_id = "luna_claims_v7" # ID change to force fresh state

    @property
    def native_value(self):
        return len(self.coordinator.data) if self.coordinator.data else 0

    @property
    def extra_state_attributes(self):
        return {"games": self.coordinator.data}

    @property
    def icon(self):
        return "mdi:amazon"
