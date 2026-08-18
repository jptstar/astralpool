"""The AstralPool integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TIMEOUT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import RegistryEntryDisabler

from .const import (
    CONF_DEVICE_TYPE,
    CONF_RECONNECT_DELAY,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DEFAULT_RECONNECT_DELAY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DEVICE_TYPE_ELYO_TOUCH,
    DEVICE_TYPE_SMARTNEXT,
    PLATFORMS_BY_DEVICE_TYPE,
)
from .devices.elyo_touch.api import ElyoTouchApi, ElyoTouchCommunicationError
from .devices.elyo_touch.coordinator import ElyoTouchCoordinator
from .devices.smartnext.api import SmartNextApi, SmartNextCommunicationError
from .devices.smartnext.coordinator import SmartNextCoordinator

type AstralPoolCoordinator = SmartNextCoordinator | ElyoTouchCoordinator
type AstralPoolConfigEntry = ConfigEntry[AstralPoolCoordinator]


_CANONICAL_ENTITY_OBJECT_IDS: dict[str, dict[str, dict[str, str]]] = {
    DEVICE_TYPE_SMARTNEXT: {
        "sensor": {
  "electrolysis_rated_capacity": "smart_next_electrolysis_rated_capacity",
  "boost_remaining_time": "smart_next_electrolysis_boost_remaining",
  "temperature": "smart_next_water_temperature",
  "temperature_min": "smart_next_temperature_low_limit",
  "temperature_max": "smart_next_temperature_high_limit",
  "salt": "smart_next_salinity",
  "salt_min": "smart_next_salinity_low_limit",
  "salt_max": "smart_next_salinity_high_limit",
  "ph": "smart_next_ph",
  "ph_low_alarm_limit": "smart_next_ph_alarm_low_limit",
  "ph_high_alarm_limit": "smart_next_ph_alarm_high_limit",
  "ph_dosage_elapsed": "smart_next_ph_dosage_elapsed",
  "ph_pump_output": "smart_next_ph_pump_output",
  "ph_total_hours": "smart_next_ph_dosage_total_hours",
  "ph_partial_hours": "smart_next_ph_dosage_partial_hours",
  "orp": "smart_next_orp",
  "orp_low_alarm_limit": "smart_next_orp_alarm_low_limit",
  "orp_high_alarm_limit": "smart_next_orp_alarm_high_limit",
  "electrolysis_functional_target": "smart_next_electrolysis_active_target",
  "electrolysis_production": "smart_next_electrolysis_production",
  "electrolysis_current": "smart_next_electrolysis_current",
  "electrolysis_voltage": "smart_next_electrolysis_voltage",
  "electrolysis_chlorine_production": "smart_next_electrolysis_chlorine_production",
  "electrolysis_total_hours": "smart_next_electrolysis_total_hours",
  "electrolysis_partial_hours": "smart_next_electrolysis_partial_hours",
        },
        "binary_sensor": {
  "general_alarm": "smart_next_alarm_system_general",
  "flow_alarm": "smart_next_alarm_flow_general",
  "internal_flow_alarm": "smart_next_alarm_flow_internal",
  "external_flow_switch_alarm": "smart_next_alarm_flow_external",
  "electrolysis_check_cell_alarm": "smart_next_alarm_electrolysis_check_cell",
  "electrolysis_low_conductivity_alarm": "smart_next_alarm_electrolysis_low_conductivity",
  "electrolysis_high_conductivity_alarm": "smart_next_alarm_electrolysis_high_conductivity",
  "ph_low_alarm": "smart_next_alarm_ph_low",
  "ph_high_alarm": "smart_next_alarm_ph_high",
  "ph_pump_stop_alarm": "smart_next_alarm_ph_pump_stop",
  "ph_fuse_alarm": "smart_next_alarm_ph_fuse",
  "orp_low_alarm": "smart_next_alarm_orp_low",
  "orp_high_alarm": "smart_next_alarm_orp_high",
  "temperature_low_alarm": "smart_next_alarm_temperature_low",
  "temperature_high_alarm": "smart_next_alarm_temperature_high",
  "salt_low_alarm": "smart_next_alarm_salinity_low",
  "salt_high_alarm": "smart_next_alarm_salinity_high",
  "ph_measure_unreliable": "smart_next_alarm_ph_unreliable",
  "orp_measure_unreliable": "smart_next_alarm_orp_unreliable",
  "temperature_measure_unreliable": "smart_next_alarm_temperature_unreliable",
  "salt_measure_unreliable": "smart_next_alarm_salinity_unreliable",
  "salt_current_insufficient": "smart_next_alarm_salinity_current_insufficient",
  "salt_voltage_insufficient": "smart_next_alarm_salinity_voltage_insufficient",
  "treatment_halted": "smart_next_alarm_system_treatment_halted",
  "internal_air_bubble_detected": "smart_next_status_internal_air_bubble",
  "external_flow_switch_open": "smart_next_status_external_flow_switch_open",
  "electrolysis_running": "smart_next_status_electrolysis_running",
  "electrolysis_reverse_polarity": "smart_next_status_electrolysis_reverse_polarity",
  "cover_input": "smart_next_status_cover_input",
  "cover_active": "smart_next_status_cover_active",
  "ph_initializing": "smart_next_status_ph_initializing",
  "ph_dosing_active": "smart_next_status_ph_dosing",
  "biopool_mode": "smart_next_status_biopool_mode",
  "external_chlorine_control_input": "smart_next_status_external_chlorine_input",
  "internal_orp_control_stop": "smart_next_status_internal_orp_stop",
  "external_control_stop": "smart_next_status_external_control_stop",
        },
        "number": {
  "temperature_min_setpoint": "smart_next_temperature_low_limit",
  "temperature_max_setpoint": "smart_next_temperature_high_limit",
  "salt_min_setpoint": "smart_next_salinity_low_limit",
  "salt_max_setpoint": "smart_next_salinity_high_limit",
  "ph_setpoint": "smart_next_ph_setpoint",
  "ph_dosage_limit": "smart_next_ph_pump_stop_duration",
  "orp_setpoint": "smart_next_orp_setpoint",
  "electrolysis_normal_setpoint": "smart_next_electrolysis_normal_production",
  "electrolysis_cover_setpoint": "smart_next_electrolysis_cover_production",
        },
        "select": {
  "ph_initialization_time": "smart_next_ph_initialization_duration",
  "polarity_reversal_period": "smart_next_electrolysis_polarity_reversal_period",
        },
        "switch": {
  "boost_mode": "smart_next_electrolysis_boost",
  "cover_control_enabled": "smart_next_cover_control",
  "internal_orp_control_enabled": "smart_next_internal_orp_control",
  "external_chlorine_control_enabled": "smart_next_external_chlorine_control",
  "internal_flow_sensor_enabled": "smart_next_internal_flow_sensor",
  "external_flow_sensor_enabled": "smart_next_external_flow_sensor",
  "ph_intelligent_dosing_enabled": "smart_next_ph_intelligent_dosing",
  "ph_pump_stop_enabled": "smart_next_ph_pump_stop",
  "temperature_low_alarm_enabled": "smart_next_temperature_low_alarm",
  "temperature_high_alarm_enabled": "smart_next_temperature_high_alarm",
  "salt_low_alarm_enabled": "smart_next_salinity_low_alarm",
  "salt_high_alarm_enabled": "smart_next_salinity_high_alarm",
  "biopool_mode_control": "smart_next_biopool_mode",
  "eco_mode": "smart_next_eco_mode",
        },
        "button": {"reset_ph_pump_stop": "smart_next_ph_pump_stop_reset"},
    },
    DEVICE_TYPE_ELYO_TOUCH: {
        "sensor": {
  "ambient_temperature": "pro_elyo_touch_ambient_temperature",
  "inlet_temperature": "pro_elyo_touch_inlet_water_temperature",
  "outlet_temperature": "pro_elyo_touch_outlet_water_temperature",
  "gas_return_temperature": "pro_elyo_touch_gas_return_temperature",
  "coil_temperature": "pro_elyo_touch_coil_temperature",
  "gas_exhaust_temperature": "pro_elyo_touch_gas_exhaust_temperature",
  "fan_speed": "pro_elyo_touch_fan_speed",
  "compressor_current": "pro_elyo_touch_compressor_current",
  "compressor_frequency": "pro_elyo_touch_compressor_frequency",
  "active_preset_mode": "pro_elyo_touch_active_inverter_mode",
  "expansion_valve_step": "pro_elyo_touch_expansion_valve_position",
  "hp_cycles": "pro_elyo_touch_heat_pump_cycles",
  "compressor_starts": "pro_elyo_touch_compressor_starts",
  "product_code": "pro_elyo_touch_product_code",
        },
        "binary_sensor": {
  "running": "pro_elyo_touch_status_running",
  "compressor_running": "pro_elyo_touch_status_compressor_running",
  "defrost": "pro_elyo_touch_status_defrost",
  "filter_priority_mode": "pro_elyo_touch_status_filter_priority",
  "timer_enabled": "pro_elyo_touch_status_timer_enabled",
  "alarm": "pro_elyo_touch_alarm_system_general",
        },
        "climate": {"climate": "pro_elyo_touch"},
        "time": {
  "system_time": "pro_elyo_touch_system_time",
  "timer_start": "pro_elyo_touch_timer_start",
  "timer_stop": "pro_elyo_touch_timer_stop",
        },
    },
}

_ELYOTOUCH_ALARM_ENTITY_SUFFIXES = {
    "inlet_sensor_failure": "water_inlet_temperature_sensor",
    "outlet_sensor_failure": "water_outlet_temperature_sensor",
    "heating_overheat": "heating_overheat",
    "gas_exhaust_too_high": "compressor_exhaust_temperature_high",
    "low_ambient_protection": "ambient_temperature_low",
    "cooling_pipe_too_high": "cooling_pipe_temperature_high",
    "low_pressure": "pressure_low",
    "high_pressure": "pressure_high",
    "ambient_sensor_failure": "ambient_temperature_sensor",
    "water_flow_abnormal": "water_flow",
    "winter_antifreeze": "winter_antifreeze",
    "software_control_failure": "software_control",
    "cooling_too_cold": "cooling_temperature_low",
    "heating_coil_sensor_failure": "heating_coil_sensor",
    "gas_return_sensor_failure": "gas_return_sensor",
    "current_detection_failure": "current_detection",
    "pfc_module_protection": "pfc_module_protection",
    "exhaust_temperature_failure": "exhaust_temperature_sensor",
    "main_drive_communication_failure": "inverter_communication",
    "eeprom_failure": "eeprom",
    "pfc_temperature_sensor_failure": "pfc_temperature_sensor",
    "module_board_failure": "inverter_module_board",
    "vdc_overvoltage": "vdc_overvoltage",
    "compressor_overcurrent": "compressor_overcurrent",
    "dc_fan_failure": "dc_fan",
    "pfc_overtemperature": "pfc_overtemperature",
    "input_power_failure": "input_power",
    "controller_main_communication_failure": "controller_communication",
    "vdc_undervoltage": "vdc_undervoltage",
    "overcurrent": "overcurrent",
    "drive_ambient_sensor_failure": "inverter_ambient_temperature_sensor",
    "ipm_overtemperature": "ipm_overtemperature",
}
for _alarm_key, _suffix in _ELYOTOUCH_ALARM_ENTITY_SUFFIXES.items():
    _CANONICAL_ENTITY_OBJECT_IDS[DEVICE_TYPE_ELYO_TOUCH]["binary_sensor"][f"alarm_{_alarm_key}"] = f"pro_elyo_touch_alarm_{_suffix}"
    _CANONICAL_ENTITY_OBJECT_IDS[DEVICE_TYPE_ELYO_TOUCH]["sensor"][f"alarm_count_{_alarm_key}"] = f"pro_elyo_touch_alarm_count_{_suffix}"


def _async_normalize_entity_ids(
    hass: HomeAssistant, entry: AstralPoolConfigEntry, device_type: str
) -> None:
    """Normalize AstralPool entity IDs while preserving unique IDs."""
    registry = er.async_get(hass)
    prefix = f"{entry.entry_id}_"
    platform_map = _CANONICAL_ENTITY_OBJECT_IDS.get(device_type, {})
    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if not registry_entry.unique_id.startswith(prefix):
  continue
        key = registry_entry.unique_id[len(prefix):]
        domain = registry_entry.entity_id.split(".", 1)[0]
        object_id = platform_map.get(domain, {}).get(key)
        if object_id is None:
  continue
        new_entity_id = f"{domain}.{object_id}"
        if registry_entry.entity_id == new_entity_id:
  continue
        existing = registry.async_get(new_entity_id)
        if existing is not None and existing.id != registry_entry.id:
  continue
        registry.async_update_entity(registry_entry.entity_id, new_entity_id=new_entity_id)


def _async_enable_integration_disabled_entities(
    hass: HomeAssistant, entry: AstralPoolConfigEntry
) -> None:
    """Enable entities that were disabled only by AstralPool defaults."""
    registry = er.async_get(hass)
    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if registry_entry.disabled_by == RegistryEntryDisabler.INTEGRATION:
            registry.async_update_entity(registry_entry.entity_id, disabled_by=None)


async def async_setup_entry(hass: HomeAssistant, entry: AstralPoolConfigEntry) -> bool:
    """Set up an AstralPool device from a config entry."""
    device_type = entry.data[CONF_DEVICE_TYPE]
    timeout = float(entry.options.get(CONF_TIMEOUT, entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)))
    reconnect_delay = float(
        entry.options.get(
            CONF_RECONNECT_DELAY,
            entry.data.get(CONF_RECONNECT_DELAY, DEFAULT_RECONNECT_DELAY),
        )
    )
    unit_id = int(entry.options.get(CONF_UNIT_ID, entry.data[CONF_UNIT_ID]))
    scan_interval = int(
        entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
    )

    if device_type == DEVICE_TYPE_SMARTNEXT:
        api = SmartNextApi(
            host=entry.data[CONF_HOST],
            port=entry.data[CONF_PORT],
            timeout=timeout,
            reconnect_delay=reconnect_delay,
            unit_id=unit_id,
        )
        coordinator = SmartNextCoordinator(hass, api, scan_interval)
    elif device_type == DEVICE_TYPE_ELYO_TOUCH:
        api = ElyoTouchApi(
            host=entry.data[CONF_HOST],
            port=entry.data[CONF_PORT],
            timeout=timeout,
            reconnect_delay=reconnect_delay,
            unit_id=unit_id,
        )
        coordinator = ElyoTouchCoordinator(hass, api, scan_interval)
    else:
        raise ValueError(f"Unsupported AstralPool device type: {device_type}")

    try:
        await api.async_connect()
        await coordinator.async_config_entry_first_refresh()
    except (SmartNextCommunicationError, ElyoTouchCommunicationError, OSError) as err:
        await api.async_close()
        raise ConfigEntryNotReady(str(err)) from err

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    _async_enable_integration_disabled_entities(hass, entry)

    await hass.config_entries.async_forward_entry_setups(
        entry, PLATFORMS_BY_DEVICE_TYPE[device_type]
    )
    _async_normalize_entity_ids(hass, entry, device_type)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AstralPoolConfigEntry) -> bool:
    """Unload an AstralPool config entry."""
    device_type = entry.data[CONF_DEVICE_TYPE]
    unloaded = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS_BY_DEVICE_TYPE[device_type]
    )
    if unloaded:
        await entry.runtime_data.api.async_close()
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: AstralPoolConfigEntry) -> None:
    """Reload AstralPool when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
