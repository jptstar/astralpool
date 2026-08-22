"""Raw Smart Next calibration points for protocol validation."""

from __future__ import annotations

from typing import Any, Final

# Common calibration workflow.
COIL_CALIBRATION_MODE: Final = 0x201
COIL_CALIBRATION_RESPONSE_RESET: Final = 0x203
HR_CALIBRATION_VALUE: Final = 0x22
IR_CALIBRATION_RESPONSE: Final = 0x22

# pH calibration commands.
COIL_PH_CALIBRATION_RESET: Final = 0x50C
COIL_PH_CALIBRATION_PH7: Final = 0x50D
COIL_PH_CALIBRATION_PH4: Final = 0x50E
COIL_PH_CALIBRATION_FAST: Final = 0x50F

# ORP calibration commands.
COIL_ORP_CALIBRATION_RESET: Final = 0x80C
COIL_ORP_CALIBRATION_470MV: Final = 0x80F

# Temperature calibration commands.
COIL_TEMPERATURE_CALIBRATION_RESET: Final = 0xB0D
COIL_TEMPERATURE_CALIBRATION: Final = 0xB0F

# Salinity calibration commands.
COIL_SALT_CALIBRATION_RESET: Final = 0xC0D
COIL_SALT_CALIBRATION: Final = 0xC0F

CALIBRATION_RESPONSE_MEANINGS: Final[dict[int, str]] = {
    0: "Aucune réponse",
    1: "Calibration OK",
    2: "E2 · valeur trop éloignée",
    3: "E3 · mesure instable",
    4: "Calibration indisponible",
    5: "Appareil en initialisation",
    16: "Premier point OK",
}

# key, French display name, Modbus coil, optional capability key.
RAW_CALIBRATION_BUTTONS: Final[tuple[tuple[str, str, int, str | None], ...]] = (
    (
        "calibration_response_reset_raw",
        "Calibration TEST · Effacer réponse (0x203)",
        COIL_CALIBRATION_RESPONSE_RESET,
        None,
    ),
    (
        "ph_calibration_reset_raw",
        "Calibration TEST · pH reset usine (0x50C)",
        COIL_PH_CALIBRATION_RESET,
        "technology_ph_implemented",
    ),
    (
        "ph_calibration_ph7_raw",
        "Calibration TEST · pH point 7.0 (0x50D)",
        COIL_PH_CALIBRATION_PH7,
        "technology_ph_implemented",
    ),
    (
        "ph_calibration_ph4_raw",
        "Calibration TEST · pH point 4.0 (0x50E)",
        COIL_PH_CALIBRATION_PH4,
        "technology_ph_implemented",
    ),
    (
        "ph_calibration_fast_raw",
        "Calibration TEST · pH rapide (0x50F)",
        COIL_PH_CALIBRATION_FAST,
        "technology_ph_implemented",
    ),
    (
        "orp_calibration_reset_raw",
        "Calibration TEST · ORP reset usine (0x80C)",
        COIL_ORP_CALIBRATION_RESET,
        "technology_orp_implemented",
    ),
    (
        "orp_calibration_470mv_raw",
        "Calibration TEST · ORP 470 mV (0x80F)",
        COIL_ORP_CALIBRATION_470MV,
        "technology_orp_implemented",
    ),
    (
        "temperature_calibration_reset_raw",
        "Calibration TEST · Température reset (0xB0D)",
        COIL_TEMPERATURE_CALIBRATION_RESET,
        "technology_temperature_implemented",
    ),
    (
        "temperature_calibration_raw",
        "Calibration TEST · Température calibrer (0xB0F)",
        COIL_TEMPERATURE_CALIBRATION,
        "technology_temperature_implemented",
    ),
    (
        "salt_calibration_reset_raw",
        "Calibration TEST · Salinité reset (0xC0D)",
        COIL_SALT_CALIBRATION_RESET,
        "technology_salt_implemented",
    ),
    (
        "salt_calibration_raw",
        "Calibration TEST · Salinité calibrer (0xC0F)",
        COIL_SALT_CALIBRATION,
        "technology_salt_implemented",
    ),
)


async def async_read_calibration_debug(api: Any) -> dict[str, Any]:
    """Read the raw calibration points used during protocol validation."""
    response = (await api._read_input_registers(IR_CALIBRATION_RESPONSE, 1))[0]
    value = (await api._read_holding_registers(HR_CALIBRATION_VALUE, 1))[0]
    mode = (await api._read_coils(COIL_CALIBRATION_MODE, 1))[0]
    return {
        "calibration_response_raw": int(response),
        "calibration_value_raw": int(value),
        "calibration_mode_raw": bool(mode),
    }
