"""Climate control for AstralPool Pro Elyo Touch."""
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from .entity import ElyoTouchEntity

PRESETS = ["silent", "smart", "powerful"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([ElyoTouchClimate(entry.runtime_data, entry.entry_id, entry.data["host"])])

class ElyoTouchClimate(ElyoTouchEntity, ClimateEntity):
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.AUTO]
    _attr_preset_modes = PRESETS
    _attr_min_temp = 15
    _attr_max_temp = 40
    _attr_target_temperature_step = 1
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE | ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF

    def __init__(self, coordinator, entry_id, host):
        super().__init__(coordinator, entry_id, host); self._attr_unique_id = f"{entry_id}_climate"; self._attr_suggested_object_id = "pro_elyo_touch"
    @property
    def current_temperature(self): return self.coordinator.data.get("inlet_temperature")
    @property
    def target_temperature(self): return self.coordinator.data.get("temperature_setpoint")
    @property
    def hvac_mode(self): return HVACMode(self.coordinator.data.get("hvac_mode", "off"))
    @property
    def preset_mode(self): return self.coordinator.data.get("preset_mode")
    @property
    def max_temp(self): return 35 if self.hvac_mode == HVACMode.COOL else 40
    async def async_set_temperature(self, **kwargs):
        await self.coordinator.api.async_set_temperature(kwargs["temperature"]); await self.coordinator.async_request_refresh()
    async def async_set_hvac_mode(self, hvac_mode):
        await self.coordinator.api.async_set_hvac_mode(hvac_mode); await self.coordinator.async_request_refresh()
    async def async_set_preset_mode(self, preset_mode):
        await self.coordinator.api.async_set_preset(preset_mode); await self.coordinator.async_request_refresh()
    async def async_turn_on(self): await self.async_set_hvac_mode(HVACMode.AUTO)
    async def async_turn_off(self): await self.async_set_hvac_mode(HVACMode.OFF)
