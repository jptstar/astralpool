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

# key/data key, French display name, Modbus coil, optional capability key.
# Unlike the buttons above, these are real read/write switches. They let a tester
# observe whether a volatile command auto-clears and explicitly force 0 -> 1.
RAW_CALIBRATION_SWITCHES: Final[
    tuple[tuple[str, str, int, str | None], ...]
] = (
    (
        "calibration_mode_raw",
        "Calibration TEST · Mode calibration (0x201)",
        COIL_CALIBRATION_MODE,
        None,
    ),
    (
        "calibration_response_reset_coil_raw",
        "Calibration TEST · État effacement réponse (0x203)",
        COIL_CALIBRATION_RESPONSE_RESET,
        None,
    ),
    (
        "ph_calibration_reset_coil_raw",
        "Calibration TEST · pH reset usine état (0x50C)",
        COIL_PH_CALIBRATION_RESET,
        "technology_ph_implemented",
    ),
    (
        "ph_calibration_ph7_coil_raw",
        "Calibration TEST · pH point 7.0 état (0x50D)",
        COIL_PH_CALIBRATION_PH7,
        "technology_ph_implemented",
    ),
    (
        "ph_calibration_ph4_coil_raw",
        "Calibration TEST · pH point 4.0 état (0x50E)",
        COIL_PH_CALIBRATION_PH4,
        "technology_ph_implemented",
    ),
    (
        "ph_calibration_fast_coil_raw",
        "Calibration TEST · pH rapide état (0x50F)",
        COIL_PH_CALIBRATION_FAST,
        "technology_ph_implemented",
    ),
    (
        "orp_calibration_reset_coil_raw",
        "Calibration TEST · ORP reset usine état (0x80C)",
        COIL_ORP_CALIBRATION_RESET,
        "technology_orp_implemented",
    ),
    (
        "orp_calibration_470mv_coil_raw",
        "Calibration TEST · ORP 470 mV état (0x80F)",
        COIL_ORP_CALIBRATION_470MV,
        "technology_orp_implemented",
    ),
    (
        "temperature_calibration_reset_coil_raw",
        "Calibration TEST · Température reset état (0xB0D)",
        COIL_TEMPERATURE_CALIBRATION_RESET,
        "technology_temperature_implemented",
    ),
    (
        "temperature_calibration_coil_raw",
        "Calibration TEST · Température calibrer état (0xB0F)",
        COIL_TEMPERATURE_CALIBRATION,
        "technology_temperature_implemented",
    ),
    (
        "salt_calibration_reset_coil_raw",
        "Calibration TEST · Salinité reset état (0xC0D)",
        COIL_SALT_CALIBRATION_RESET,
        "technology_salt_implemented",
    ),
    (
        "salt_calibration_coil_raw",
        "Calibration TEST · Salinité calibrer état (0xC0F)",
        COIL_SALT_CALIBRATION,
        "technology_salt_implemented",
    ),
)


async def async_read_calibration_debug(
    api: Any, capabilities: dict[str, Any]
) -> dict[str, Any]:
    """Read raw calibration registers and command-coil states."""
    response = (await api._read_input_registers(IR_CALIBRATION_RESPONSE, 1))[0]
    value = (await api._read_holding_registers(HR_CALIBRATION_VALUE, 1))[0]

    common = await api._read_coils(COIL_CALIBRATION_MODE, 3)
    data: dict[str, Any] = {
        "calibration_response_raw": int(response),
        "calibration_value_raw": int(value),
        "calibration_mode_raw": bool(common[0]),
        "calibration_response_reset_coil_raw": bool(common[2]),
    }

    if capabilities.get("technology_ph_implemented", False):
        ph = await api._read_coils(COIL_PH_CALIBRATION_RESET, 4)
        data.update(
            {
                "ph_calibration_reset_coil_raw": bool(ph[0]),
                "ph_calibration_ph7_coil_raw": bool(ph[1]),
                "ph_calibration_ph4_coil_raw": bool(ph[2]),
                "ph_calibration_fast_coil_raw": bool(ph[3]),
            }
        )

    if capabilities.get("technology_orp_implemented", False):
        orp = await api._read_coils(COIL_ORP_CALIBRATION_RESET, 4)
        data.update(
            {
                "orp_calibration_reset_coil_raw": bool(orp[0]),
                "orp_calibration_470mv_coil_raw": bool(orp[3]),
            }
        )

    if capabilities.get("technology_temperature_implemented", False):
        temperature = await api._read_coils(COIL_TEMPERATURE_CALIBRATION_RESET, 3)
        data.update(
            {
                "temperature_calibration_reset_coil_raw": bool(temperature[0]),
                "temperature_calibration_coil_raw": bool(temperature[2]),
            }
        )

    if capabilities.get("technology_salt_implemented", False):
        salt = await api._read_coils(COIL_SALT_CALIBRATION_RESET, 3)
        data.update(
            {
                "salt_calibration_reset_coil_raw": bool(salt[0]),
                "salt_calibration_coil_raw": bool(salt[2]),
            }
        )

    return data
