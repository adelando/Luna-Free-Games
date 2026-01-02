from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN

class LunaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Amazon Luna."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step. No input required."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            # When the user clicks Submit, this creates the entry
            return self.async_create_entry(title="Amazon Luna Games", data={})

        # Return an empty schema to show a 'Submit' only form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({})
        )
