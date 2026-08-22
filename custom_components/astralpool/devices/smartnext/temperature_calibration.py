"""Hardware-validated Smart Next temperature calibration procedures."""

from __future__ import annotations

import asyncio
from typing import Any, Final

from .calibration_debug import (
    COIL_TEMPERATURE_CALIBRATION,
    COIL_TEMPERATURE_CALIBRATION_RESET,
    HR_CALIBRATION_VALUE,
)

TEMPERATURE_CALIBRATION_DELAY_SECONDS: Final = 5.0
TEMPERATURE_RESET_DELAY_SECONDS: Final = 2.0


async def async_calibrate_temperature(api: Any, reference_temperature: float) -> None:
    """Calibrate the temperature sensor to a reference value.

    Validated on real Smart Next hardware:
    1. write the reference temperature x10 to holding register 0x22;
    2. trigger temperature calibration coil 0xB0F;
    3. wait 5 seconds for the controller to apply the calibration.
    """
    raw_value = round(reference_temperature * 10)
    if not 0 <= raw_value <= 0xFFFF:
        raise ValueError(f"Temperature calibration value out of range: {reference_temperature}")

    await api.async_write_register(HR_CALIBRATION_VALUE, raw_value)
    await api.async_write_coil(COIL_TEMPERATURE_CALIBRATION, True)
    await asyncio.sleep(TEMPERATURE_CALIBRATION_DELAY_SECONDS)


async def async_reset_temperature_calibration(api: Any) -> None:
    """Restore the factory temperature calibration.

    Validated on real Smart Next hardware: trigger 0xB0D and wait 2 seconds
    before refreshing the displayed temperature.
    """
    await api.async_write_coil(COIL_TEMPERATURE_CALIBRATION_RESET, True)
    await asyncio.sleep(TEMPERATURE_RESET_DELAY_SECONDS)
