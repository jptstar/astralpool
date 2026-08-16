"""Binary sensor platform dispatcher for AstralPool."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_DEVICE_TYPE, DEVICE_TYPE_SMARTNEXT


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors for the selected AstralPool device."""
    if entry.data[CONF_DEVICE_TYPE] == DEVICE_TYPE_SMARTNEXT:
        from .devices.smartnext.binary_sensor import async_setup_entry as setup
    else:
        from .devices.elyo_touch.binary_sensor import async_setup_entry as setup
    await setup(hass, entry, async_add_entities)
