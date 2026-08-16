"""Organized status and alarm entities for Pro Elyo Touch."""
from dataclasses import dataclass
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from .const import ALARM_KEYS
from .entity import ElyoTouchEntity

@dataclass(frozen=True, kw_only=True)
class ElyoTouchBinaryDescription(BinarySensorEntityDescription): data_key: str

STATUS = (
    ElyoTouchBinaryDescription(key="running", translation_key="running", data_key="running", device_class=BinarySensorDeviceClass.RUNNING),
    ElyoTouchBinaryDescription(key="compressor_running", translation_key="compressor_running", data_key="compressor_running", device_class=BinarySensorDeviceClass.RUNNING),
    ElyoTouchBinaryDescription(key="defrost", translation_key="defrost", data_key="defrost", device_class=BinarySensorDeviceClass.RUNNING),
    ElyoTouchBinaryDescription(key="filter_priority_mode", translation_key="filter_priority_mode", data_key="filter_priority_mode"),
    ElyoTouchBinaryDescription(key="timer_enabled", translation_key="timer_enabled", data_key="timer_enabled"),
    ElyoTouchBinaryDescription(key="alarm", translation_key="alarm", data_key="alarm", device_class=BinarySensorDeviceClass.PROBLEM),
)
ALARMS = tuple(ElyoTouchBinaryDescription(key=f"alarm_{key}", translation_key=f"alarm_{key}", data_key=f"alarm_{key}", device_class=BinarySensorDeviceClass.PROBLEM, entity_category=EntityCategory.DIAGNOSTIC) for key in ALARM_KEYS)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    c = entry.runtime_data; async_add_entities(ElyoTouchBinarySensor(c, entry.entry_id, entry.data["host"], d) for d in STATUS + ALARMS)
class ElyoTouchBinarySensor(ElyoTouchEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry_id, host, description):
        super().__init__(coordinator, entry_id, host); self.entity_description = description; self._attr_unique_id = f"{entry_id}_{description.key}"; self._attr_suggested_object_id = f"pro_elyo_touch_{description.key}"
    @property
    def is_on(self): return bool(self.coordinator.data.get(self.entity_description.data_key))
