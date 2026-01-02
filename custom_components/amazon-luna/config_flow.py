from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN

class LunaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Amazon Luna."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step when user adds via UI."""
        # Check if already configured
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            # This creates the entry in the UI
            return self.async_create_entry(title="Amazon Luna Games", data={})

        # Show the empty form (just a 'Submit' button)
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))
