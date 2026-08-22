"""Hardware-guided Smart Next pH calibration procedures."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Final

from .calibration_debug import (
    COIL_CALIBRATION_RESPONSE_RESET,
    COIL_PH_CALIBRATION_FAST,
    COIL_PH_CALIBRATION_PH4,
    COIL_PH_CALIBRATION_PH7,
    COIL_PH_CALIBRATION_RESET,
    HR_CALIBRATION_VALUE,
    IR_CALIBRATION_RESPONSE,
)
from .const import (
    COIL_ELECTROLYSIS_BOOST,
    COIL_ELECTROLYSIS_COVER_CONTROL_ENABLE,
    COIL_FLOW_EXTERNAL_SENSOR_ENABLE,
    COIL_FLOW_INTERNAL_SENSOR_ENABLE,
    DI_ELECTROLYSIS_RUNNING,
    DI_FLOW_GENERAL,
    HR_ELECTROLYSIS_CONTROL_WORD,
    HR_ELECTROLYSIS_NORMAL_SETPOINT,
    HR_FLOW_CONTROL_WORD,
    IR_ELECTROLYSIS_CURRENT,
    IR_ELECTROLYSIS_PRODUCTION,
)

PH_RESPONSE_TIMEOUT_SECONDS: Final = 12.0
PH_RESPONSE_POLL_SECONDS: Final = 0.25
PH_OUTPUT_STOP_TIMEOUT_SECONDS: Final = 10.0
PH_OUTPUT_STOP_POLL_SECONDS: Final = 0.5
PH_FACTORY_RESET_DELAY_SECONDS: Final = 2.0


@dataclass(slots=True)
class PhStandardSavedState:
    """Smart Next state temporarily changed by a standard pH calibration."""

    internal_flow_enabled: bool
    external_flow_enabled: bool
    normal_production_setpoint: int
    boost_enabled: bool
    cover_control_enabled: bool


async def _read_response(api: Any) -> int:
    return int((await api._read_input_registers(IR_CALIBRATION_RESPONSE, 1))[0])


async def async_clear_calibration_response(api: Any) -> None:
    """Clear the previous calibration result before starting a new operation."""
    await api.async_write_coil(COIL_CALIBRATION_RESPONSE_RESET, True)
    deadline = asyncio.get_running_loop().time() + 3.0
    while asyncio.get_running_loop().time() < deadline:
        if await _read_response(api) == 0:
            return
        await asyncio.sleep(PH_RESPONSE_POLL_SECONDS)


async def async_trigger_ph_calibration(api: Any, coil: int) -> int:
    """Trigger one pH calibration command and return the Smart Next result code."""
    await async_clear_calibration_response(api)
    await api.async_write_coil(coil, True)

    deadline = asyncio.get_running_loop().time() + PH_RESPONSE_TIMEOUT_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        response = await _read_response(api)
        if response != 0:
            return response
        await asyncio.sleep(PH_RESPONSE_POLL_SECONDS)
    return 0


async def async_calibrate_ph_fast(api: Any, reference_ph: float) -> int:
    """Run Fast pH calibration without changing flow or electrolysis settings."""
    raw_value = round(reference_ph * 100)
    if not 0 <= raw_value <= 1200:
        raise ValueError(f"pH calibration value out of range: {reference_ph}")

    await async_clear_calibration_response(api)
    await api.async_write_register(HR_CALIBRATION_VALUE, raw_value)
    await api.async_write_coil(COIL_PH_CALIBRATION_FAST, True)

    deadline = asyncio.get_running_loop().time() + PH_RESPONSE_TIMEOUT_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        response = await _read_response(api)
        if response != 0:
            return response
        await asyncio.sleep(PH_RESPONSE_POLL_SECONDS)
    return 0


async def async_reset_ph_calibration(api: Any) -> int:
    """Restore the factory pH calibration and return the controller result if any."""
    await async_clear_calibration_response(api)
    await api.async_write_coil(COIL_PH_CALIBRATION_RESET, True)
    await asyncio.sleep(PH_FACTORY_RESET_DELAY_SECONDS)
    return await _read_response(api)


async def async_prepare_standard_ph_calibration(api: Any) -> PhStandardSavedState:
    """Safely stop electrolysis before the user isolates the cell hydraulically.

    The real-hardware sequence requires the logical flow sensors to be disabled
    before the production setpoint can be changed to 0 %. Physical water flow
    must still be present while this preparation runs.
    """
    flow_control = (await api._read_holding_registers(HR_FLOW_CONTROL_WORD, 1))[0]
    electrolysis_control = (
        await api._read_holding_registers(HR_ELECTROLYSIS_CONTROL_WORD, 2)
    )
    control_word = electrolysis_control[0]
    saved = PhStandardSavedState(
        internal_flow_enabled=bool(flow_control & (1 << 0)),
        external_flow_enabled=bool(flow_control & (1 << 1)),
        normal_production_setpoint=int(electrolysis_control[1]),
        boost_enabled=bool(control_word & (1 << 1)),
        cover_control_enabled=bool(control_word & (1 << 2)),
    )

    # Order validated by the user on the physical controller: disable both
    # logical flow sensors first, then production can be set to 0 %.
    await api.async_write_coil(COIL_FLOW_INTERNAL_SENSOR_ENABLE, False)
    await api.async_write_coil(COIL_FLOW_EXTERNAL_SENSOR_ENABLE, False)

    # Remove known production overrides before applying the 0 % normal target.
    if saved.boost_enabled:
        await api.async_write_coil(COIL_ELECTROLYSIS_BOOST, False)
    if saved.cover_control_enabled:
        await api.async_write_coil(COIL_ELECTROLYSIS_COVER_CONTROL_ENABLE, False)
    await api.async_write_register(HR_ELECTROLYSIS_NORMAL_SETPOINT, 0)

    deadline = asyncio.get_running_loop().time() + PH_OUTPUT_STOP_TIMEOUT_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        production = int((await api._read_input_registers(IR_ELECTROLYSIS_PRODUCTION, 1))[0])
        current_raw = int((await api._read_input_registers(IR_ELECTROLYSIS_CURRENT, 1))[0])
        running = bool((await api._read_discrete_inputs(DI_ELECTROLYSIS_RUNNING, 1))[0])
        if production == 0 and current_raw == 0 and not running:
            return saved
        await asyncio.sleep(PH_OUTPUT_STOP_POLL_SECONDS)

    # The hydraulic bypass has not yet been touched, so safely restore the
    # original controller settings if electrolysis did not stop as expected.
    await async_restore_standard_ph_calibration(api, saved, verify_flow=False)
    raise RuntimeError("electrolysis_not_stopped")


async def async_restore_standard_ph_calibration(
    api: Any,
    saved: PhStandardSavedState,
    *,
    verify_flow: bool = True,
) -> None:
    """Restore flow supervision first, then the previous production settings."""
    await api.async_write_coil(
        COIL_FLOW_INTERNAL_SENSOR_ENABLE, saved.internal_flow_enabled
    )
    await api.async_write_coil(
        COIL_FLOW_EXTERNAL_SENSOR_ENABLE, saved.external_flow_enabled
    )

    if verify_flow and (saved.internal_flow_enabled or saved.external_flow_enabled):
        await asyncio.sleep(1.0)
        flow_alarm = bool((await api._read_discrete_inputs(DI_FLOW_GENERAL, 1))[0])
        if flow_alarm:
            # Keep production at zero. The user can correct the hydraulic bypass
            # and retry the final restore step without risking a dry cell.
            raise RuntimeError("flow_not_restored")

    await api.async_write_register(
        HR_ELECTROLYSIS_NORMAL_SETPOINT, saved.normal_production_setpoint
    )
    if saved.cover_control_enabled:
        await api.async_write_coil(COIL_ELECTROLYSIS_COVER_CONTROL_ENABLE, True)
    if saved.boost_enabled:
        await api.async_write_coil(COIL_ELECTROLYSIS_BOOST, True)
