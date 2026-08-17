"""Constants for the AstralPool integration."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "astralpool"

CONF_DEVICE_TYPE: Final = "device_type"
CONF_UNIT_ID: Final = "unit_id"
CONF_RECONNECT_DELAY: Final = "reconnect_delay"
CONF_SCAN_INTERVAL: Final = "scan_interval"

DEVICE_TYPE_SMARTNEXT: Final = "smartnext"
DEVICE_TYPE_ELYO_TOUCH: Final = "elyo_touch"

DEVICE_NAMES: Final = {
    DEVICE_TYPE_SMARTNEXT: "Smart Next",
    DEVICE_TYPE_ELYO_TOUCH: "Pro Elyo Touch",
}

DEFAULT_PORT: Final = 502
DEFAULT_TIMEOUT: Final = 5.0
DEFAULT_RECONNECT_DELAY: Final = 10.0
DEFAULT_SCAN_INTERVAL: Final = 5
DEFAULT_UNIT_IDS: Final = {
    DEVICE_TYPE_SMARTNEXT: 2,
    DEVICE_TYPE_ELYO_TOUCH: 9,
}

MIN_SCAN_INTERVAL: Final = 2
MAX_SCAN_INTERVAL: Final = 120

PLATFORMS_BY_DEVICE_TYPE: Final = {
    DEVICE_TYPE_SMARTNEXT: (
        Platform.SENSOR,
        Platform.BINARY_SENSOR,
        Platform.NUMBER,
        Platform.SELECT,
        Platform.SWITCH,
        Platform.BUTTON,
    ),
    DEVICE_TYPE_ELYO_TOUCH: (
        Platform.CLIMATE,
        Platform.SENSOR,
        Platform.BINARY_SENSOR,
        Platform.TIME,
    ),
}
