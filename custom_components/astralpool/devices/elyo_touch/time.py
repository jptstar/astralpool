"""Clock and timer controls for Pro Elyo Touch."""
from datetime import time
from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from .const import HR_SYSTEM_TIME, HR_TIMER_START, HR_TIMER_STOP
from .entity import ElyoTouchEntity

DESCRIPTIONS = (
    (TimeEntityDescription(key="system_time", translation_key="system_time", entity_category=EntityCategory.CONFIG), HR_SYSTEM_TIME),
    (TimeEntityDescription(key="timer_start", translation_key="timer_start", entity_category=EntityCategory.CONFIG), HR_TIMER_START),
    (TimeEntityDescription(key="timer_stop", translation_key="timer_stop", entity_category=EntityCategory.CONFIG), HR_TIMER_STOP),
)
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    c = entry.runtime_data; async_add_entities(ElyoTouchTime(c, entry.entry_id, entry.data["host"], d, a) for d, a in DESCRIPTIONS)
class ElyoTouchTime(ElyoTouchEntity, TimeEntity):
    def __init__(self, coordinator, entry_id, host, description, address):
        super().__init__(coordinator, entry_id, host); self.entity_description = description; self.address = address; self._attr_unique_id = f"{entry_id}_{description.key}"; self._attr_suggested_object_id = f"pro_elyo_touch_{description.key}"
    @property
    def native_value(self):
        minutes = self.coordinator.data.get(self.entity_description.key)
        return None if minutes is None else time(hour=minutes // 60, minute=minutes % 60)
    async def async_set_value(self, value):
        await self.coordinator.api.async_set_clock(self.address, value); await self.coordinator.async_request_refresh()
