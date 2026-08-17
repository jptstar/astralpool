"""Constants for AstralPool Pro Elyo Touch."""
from typing import Final

DOMAIN: Final = "astralpool"
CONF_UNIT_ID: Final = "unit_id"
CONF_RECONNECT_DELAY: Final = "reconnect_delay"
CONF_SCAN_INTERVAL: Final = "scan_interval"
DEFAULT_PORT: Final = 502
DEFAULT_TIMEOUT: Final = 5.0
DEFAULT_RECONNECT_DELAY: Final = 10.0
DEFAULT_UNIT_ID: Final = 9
DEFAULT_SCAN_INTERVAL: Final = 5
MIN_SCAN_INTERVAL: Final = 2
MAX_SCAN_INTERVAL: Final = 300
PLATFORMS: Final = ["climate", "sensor", "binary_sensor", "time"]
MANUFACTURER: Final = "AstralPool"
MODEL: Final = "Pro Elyo Touch"

HR_PRODUCT_CODE_HIGH: Final = 0x04
HR_PRODUCT_CODE_LOW: Final = 0x05
HR_HARDWARE_VERSION: Final = 0x07
HR_SOFTWARE_VERSION: Final = 0x08
HR_CONTROL_WORD: Final = 0x21
HR_TEMPERATURE_SETPOINT: Final = 0x24
HR_ALARM_COUNTERS_START: Final = 0x30
HR_ALARM_COUNTERS_COUNT: Final = 32
HR_SYSTEM_TIME: Final = 0x51
HR_TIMER_START: Final = 0x54
HR_TIMER_STOP: Final = 0x55
HR_HP_CYCLES: Final = 0x60
HR_COMPRESSOR_STARTS: Final = 0x61

# Bit-addressable aliases of Control Word 0x21. The supplied Pro Elyo table
# documents these as user-access controls, and the known-good Node-RED flow
# writes these coils directly.
COIL_HVAC_MODE_BIT1: Final = 0x211
COIL_HVAC_MODE_BIT2: Final = 0x212
COIL_POWER: Final = 0x218
COIL_PRESET_BIT9: Final = 0x219
COIL_PRESET_BIT10: Final = 0x21A
COIL_PRESET_BIT11: Final = 0x21B

IR_STATUS: Final = 0x00
IR_ALARMS_1: Final = 0x01
IR_AMBIENT_TEMPERATURE: Final = 0x07
IR_INLET_TEMPERATURE: Final = 0x08
IR_OUTLET_TEMPERATURE: Final = 0x09
IR_ALARMS_2: Final = 0x0E
IR_EXPANSION_VALVE_STEP: Final = 0x19
IR_GAS_RETURN_TEMPERATURE: Final = 0x1A
IR_COIL_TEMPERATURE: Final = 0x1B
IR_GAS_EXHAUST_TEMPERATURE: Final = 0x1C
IR_COMPRESSOR_CURRENT: Final = 0x1D
IR_COMPRESSOR_FREQUENCY: Final = 0x1E
IR_FAN_SPEED: Final = 0x1F

ALARM_KEYS: Final = (
    "inlet_sensor_failure", "outlet_sensor_failure", "heating_overheat",
    "gas_exhaust_too_high", "low_ambient_protection", "cooling_pipe_too_high",
    "low_pressure", "high_pressure", "ambient_sensor_failure", "water_flow_abnormal",
    "winter_antifreeze", "software_control_failure", "cooling_too_cold",
    "heating_coil_sensor_failure", "gas_return_sensor_failure", "current_detection_failure",
    "pfc_module_protection", "exhaust_temperature_failure", "main_drive_communication_failure",
    "eeprom_failure", "pfc_temperature_sensor_failure", "module_board_failure",
    "vdc_overvoltage", "compressor_overcurrent", "dc_fan_failure", "pfc_overtemperature",
    "input_power_failure", "controller_main_communication_failure", "vdc_undervoltage",
    "overcurrent", "drive_ambient_sensor_failure", "ipm_overtemperature",
)
