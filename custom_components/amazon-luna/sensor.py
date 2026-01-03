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
    async def async_get_data():
        try:
            # We must mimic a very specific browser profile to get the correct data
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(SOURCE_URL, headers=headers, timeout=20) as response:
                    html = await response.text()
                    
                    # If we see this, Amazon is blocking the scraper or redirecting to login
                    if "Sign In" in html and len(html) < 5000:
                        _LOGGER.error("Luna page redirected to login. Scraping failed.")
                        return []

                    soup = BeautifulSoup(html, 'html.parser')
                    found_games = []

                    # STRATEGY 1: Look for the hidden JSON metadata (SEO data)
                    # Amazon usually puts game titles here for search engines
                    for script in soup.find_all('script'):
                        content = script.string if script.string else ""
                        # We look for game title patterns inside the Javascript blocks
                        matches = re.findall(r'"title":"([^"]+)"', content)
                        for match in matches:
                            if len(match) > 2 and match not in ["Home", "Settings"]:
                                found_games.append({"title": match, "image": "https://luna.amazon.com/favicon.ico"})

                    # STRATEGY 2: Scrape Aria Labels (Accessibility labels)
                    # Even if JS isn't run, some labels are in the static HTML source
                    for el in soup.find_all(attrs={"aria-label": True}):
                        label = el['aria-label']
                        if "Play " in label or "Claim " in label:
                            title = label.replace("Play ", "").replace("Claim ", "").strip()
                            found_games.append({"title": title, "image": "https://luna.amazon.com/favicon.ico"})

                    # Final cleaning: remove common junk
                    blacklist = ["Luna", "Prime", "Privacy", "Terms", "Support", "Help"]
                    unique_games = []
                    seen = set()
                    for g in found_games:
                        if g['title'] not in seen and not any(b == g['title'] for b in blacklist):
                            unique_games.append(g)
                            seen.add(g['title'])

                    return unique_games

        except Exception as e:
            _LOGGER.error("Luna Scraper failed: %s", e)
            return []

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
        self._attr_unique_id = "luna_standard_v1"

    @property
    def native_value(self):
        return len(self.coordinator.data) if self.coordinator.data else 0

    @property
    def extra_state_attributes(self):
        return {"games": self.coordinator.data}

    @property
    def icon(self):
        return "mdi:amazon"
