from homeassistant import config_entries
import voluptuous as os
from .const import DOMAIN

class LunaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Amazon Luna."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step when user adds via UI."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="Amazon Luna Games", data={})

        return self.async_show_form(step_id="user")
