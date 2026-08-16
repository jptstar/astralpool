"""Organized sensors for Pro Elyo Touch."""
from dataclasses import dataclass
from typing import Any
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent, UnitOfFrequency, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from .const import ALARM_KEYS
from .entity import ElyoTouchEntity

@dataclass(frozen=True, kw_only=True)
class ElyoTouchSensorDescription(SensorEntityDescription): data_key: str

def temp(key, diagnostic=False):
    return ElyoTouchSensorDescription(key=key, translation_key=key, data_key=key, native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT, entity_category=EntityCategory.DIAGNOSTIC if diagnostic else None)

SENSORS = (
    temp("ambient_temperature"), temp("inlet_temperature"), temp("outlet_temperature"),
    temp("gas_return_temperature", True), temp("coil_temperature", True), temp("gas_exhaust_temperature", True),
    ElyoTouchSensorDescription(key="fan_speed", translation_key="fan_speed", data_key="fan_speed", native_unit_of_measurement="rpm", state_class=SensorStateClass.MEASUREMENT),
    ElyoTouchSensorDescription(key="compressor_current", translation_key="compressor_current", data_key="compressor_current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT),
    ElyoTouchSensorDescription(key="compressor_frequency", translation_key="compressor_frequency", data_key="compressor_frequency", native_unit_of_measurement=UnitOfFrequency.HERTZ, device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT),
    ElyoTouchSensorDescription(key="expansion_valve_step", translation_key="expansion_valve_step", data_key="expansion_valve_step", entity_category=EntityCategory.DIAGNOSTIC),
    ElyoTouchSensorDescription(key="hp_cycles", translation_key="hp_cycles", data_key="hp_cycles", state_class=SensorStateClass.TOTAL_INCREASING, entity_category=EntityCategory.DIAGNOSTIC),
    ElyoTouchSensorDescription(key="compressor_starts", translation_key="compressor_starts", data_key="compressor_starts", state_class=SensorStateClass.TOTAL_INCREASING, entity_category=EntityCategory.DIAGNOSTIC),
    ElyoTouchSensorDescription(key="product_code", translation_key="product_code", data_key="product_code", entity_category=EntityCategory.DIAGNOSTIC),
) + tuple(
    ElyoTouchSensorDescription(key=f"alarm_count_{key}", translation_key=f"alarm_count_{key}", data_key=f"alarm_count_{key}", state_class=SensorStateClass.TOTAL_INCREASING, entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False)
    for key in ALARM_KEYS
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    c = entry.runtime_data; async_add_entities(ElyoTouchSensor(c, entry.entry_id, entry.data["host"], d) for d in SENSORS)
class ElyoTouchSensor(ElyoTouchEntity, SensorEntity):
    def __init__(self, coordinator, entry_id, host, description):
        super().__init__(coordinator, entry_id, host); self.entity_description = description; self._attr_unique_id = f"{entry_id}_{description.key}"; self._attr_suggested_object_id = f"pro_elyo_touch_{description.key}"
    @property
    def native_value(self) -> Any: return self.coordinator.data.get(self.entity_description.data_key)
