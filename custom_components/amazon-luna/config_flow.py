from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN

class LunaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Amazon Luna."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step where the user enters their API Key."""
        errors = {}

        if user_input is not None:
            # You could add a validation check here to test the API key
            return self.async_create_entry(title="Amazon Luna Games", data=user_input)

        # This defines the UI form
        data_schema = vol.Schema({
            vol.Required("api_key"): str,
        })

        return self.async_show_form(
            step_id="user", 
            data_schema=data_schema, 
            errors=errors
        )
