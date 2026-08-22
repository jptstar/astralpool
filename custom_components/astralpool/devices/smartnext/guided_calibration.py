"""Hardware-validated Smart Next pH and ORP calibration workflows."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Final

from .calibration_debug import (
    COIL_CALIBRATION_MODE,
    COIL_CALIBRATION_RESPONSE_RESET,
    COIL_ORP_CALIBRATION_470MV,
    COIL_ORP_CALIBRATION_RESET,
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
    COIL_ELECTROLYSIS_EXTERNAL_CONTROL_ENABLE,
    COIL_ELECTROLYSIS_INTERNAL_ORP_CONTROL_ENABLE,
    COIL_FLOW_EXTERNAL_SENSOR_ENABLE,
    COIL_FLOW_INTERNAL_SENSOR_ENABLE,
    DI_ELECTROLYSIS_RUNNING,
    DI_FLOW_GENERAL,
    DI_TREATMENT_HALTED,
    HR_ELECTROLYSIS_CONTROL_WORD,
    HR_ELECTROLYSIS_NORMAL_SETPOINT,
    HR_FLOW_CONTROL_WORD,
    IR_ELECTROLYSIS_CURRENT,
    IR_ELECTROLYSIS_PRODUCTION,
)

CALIBRATION_RESPONSE_TIMEOUT_SECONDS: Final = 10.0
CALIBRATION_POLL_SECONDS: Final = 0.10
CALIBRATION_MODE_VERIFY_TIMEOUT_SECONDS: Final = 3.0
CALIBRATION_COMMAND_EDGE_SECONDS: Final = 0.05
CALIBRATION_MODE_MAX_REARM_SECONDS: Final = 10.0
OUTPUT_STOP_TIMEOUT_SECONDS: Final = 8.0
OUTPUT_STOP_POLL_SECONDS: Final = 0.25

RESPONSE_NONE: Final = 0
RESPONSE_OK: Final = 1
RESPONSE_E2: Final = 2
RESPONSE_E3: Final = 3
RESPONSE_UNAVAILABLE: Final = 4
RESPONSE_INITIALIZING: Final = 5
RESPONSE_FIRST_POINT_OK: Final = 16
RESPONSE_MODE_LOST: Final = -1


class GuidedCalibrationError(RuntimeError):
    """Raised when a guided calibration cannot maintain a safe state."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(slots=True)
class CalibrationSavedState:
    """Controller settings temporarily changed while the cell may be bypassed."""

    internal_flow_enabled: bool
    external_flow_enabled: bool
    normal_production_setpoint: int
    boost_enabled: bool
    cover_control_enabled: bool
    external_control_enabled: bool
    internal_orp_control_enabled: bool


async def async_read_calibration_response(api: Any) -> int:
    """Read the shared calibration response input register 0x22."""
    return int((await api._read_input_registers(IR_CALIBRATION_RESPONSE, 1))[0])


async def async_read_calibration_mode(api: Any) -> bool:
    """Read the real state of calibration-mode coil 0x201."""
    return bool((await api._read_coils(COIL_CALIBRATION_MODE, 1))[0])


async def _async_wait_for_mode(api: Any, expected: bool) -> bool:
    deadline = (
        asyncio.get_running_loop().time() + CALIBRATION_MODE_VERIFY_TIMEOUT_SECONDS
    )
    while asyncio.get_running_loop().time() < deadline:
        if await async_read_calibration_mode(api) is expected:
            return True
        await asyncio.sleep(CALIBRATION_POLL_SECONDS)
    return False


async def async_rearm_calibration_mode(api: Any) -> None:
    """Activate 0x201 and verify the command promptly.

    This helper is used only when a calibration session is intentionally
    started or restarted. A terminal calibration response is deliberately not
    followed by an automatic re-arm: persistent 0 % electrolysis is the safety
    barrier while the probe and hydraulics are restored.
    """
    started = asyncio.get_running_loop().time()
    if not await async_read_calibration_mode(api):
        await api.async_write_coil(COIL_CALIBRATION_MODE, True)
    if not await _async_wait_for_mode(api, True):
        raise GuidedCalibrationError("calibration_mode_rearm_failed")
    if asyncio.get_running_loop().time() - started >= CALIBRATION_MODE_MAX_REARM_SECONDS:
        raise GuidedCalibrationError("calibration_mode_rearm_too_slow")


async def _async_command_edge(api: Any, coil: int) -> None:
    """Generate an explicit OFF -> ON edge for a volatile command coil."""
    await api.async_write_coil(coil, False)
    await asyncio.sleep(CALIBRATION_COMMAND_EDGE_SECONDS)
    await api.async_write_coil(coil, True)


async def async_clear_response_in_active_mode(api: Any, *, force: bool = False) -> None:
    """Clear IR 0x22 with 0x203 while 0x201 is already active."""
    if not await async_read_calibration_mode(api):
        raise GuidedCalibrationError("calibration_mode_not_active")
    if not force and await async_read_calibration_response(api) == RESPONSE_NONE:
        return

    await _async_command_edge(api, COIL_CALIBRATION_RESPONSE_RESET)
    deadline = asyncio.get_running_loop().time() + 2.0
    while asyncio.get_running_loop().time() < deadline:
        if await async_read_calibration_response(api) == RESPONSE_NONE:
            await api.async_write_coil(COIL_CALIBRATION_RESPONSE_RESET, False)
            return
        await asyncio.sleep(CALIBRATION_POLL_SECONDS)
    raise GuidedCalibrationError("calibration_response_not_cleared")


async def async_start_calibration_session(api: Any, *, force_clear: bool = False) -> None:
    """Enter 0x201, verify treatment halt, then ensure IR 0x22 is clear."""
    await async_rearm_calibration_mode(api)

    halted = bool((await api._read_discrete_inputs(DI_TREATMENT_HALTED, 1))[0])
    if not halted:
        raise GuidedCalibrationError("treatment_not_halted")

    if force_clear:
        await async_clear_response_in_active_mode(api, force=True)
        return

    deadline = asyncio.get_running_loop().time() + 1.5
    while asyncio.get_running_loop().time() < deadline:
        if await async_read_calibration_response(api) == RESPONSE_NONE:
            return
        await asyncio.sleep(CALIBRATION_POLL_SECONDS)

    await async_clear_response_in_active_mode(api)


async def _async_wait_for_response(api: Any, previous_response: int) -> int:
    """Capture a response, including the short-lived success value 1."""
    deadline = asyncio.get_running_loop().time() + CALIBRATION_RESPONSE_TIMEOUT_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        response = await async_read_calibration_response(api)
        if response != previous_response:
            return response

        if not await async_read_calibration_mode(api):
            response = await async_read_calibration_response(api)
            return response if response != previous_response else RESPONSE_MODE_LOST
        await asyncio.sleep(CALIBRATION_POLL_SECONDS)
    return RESPONSE_NONE


async def async_verify_electrolysis_stopped(api: Any) -> None:
    """Verify the independent 0 % safety after 0x201 has terminated."""
    deadline = asyncio.get_running_loop().time() + OUTPUT_STOP_TIMEOUT_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        production = int(
            (await api._read_input_registers(IR_ELECTROLYSIS_PRODUCTION, 1))[0]
        )
        current_raw = int(
            (await api._read_input_registers(IR_ELECTROLYSIS_CURRENT, 1))[0]
        )
        running = bool(
            (await api._read_discrete_inputs(DI_ELECTROLYSIS_RUNNING, 1))[0]
        )
        if production == 0 and current_raw == 0 and not running:
            return
        await asyncio.sleep(OUTPUT_STOP_POLL_SECONDS)
    raise GuidedCalibrationError("electrolysis_safety_lost")


async def async_prepare_bypassed_calibration(api: Any) -> CalibrationSavedState:
    """Establish persistent 0 % production before any hydraulic manipulation."""
    flow_control = (await api._read_holding_registers(HR_FLOW_CONTROL_WORD, 1))[0]
    electrolysis_control = (
        await api._read_holding_registers(HR_ELECTROLYSIS_CONTROL_WORD, 2)
    )
    control_word = electrolysis_control[0]
    saved = CalibrationSavedState(
        internal_flow_enabled=bool(flow_control & (1 << 0)),
        external_flow_enabled=bool(flow_control & (1 << 1)),
        normal_production_setpoint=int(electrolysis_control[1]),
        boost_enabled=bool(control_word & (1 << 1)),
        cover_control_enabled=bool(control_word & (1 << 2)),
        external_control_enabled=bool(control_word & (1 << 4)),
        internal_orp_control_enabled=bool(control_word & (1 << 5)),
    )

    try:
        # Keep normal hydraulics until software safety has been established.
        await api.async_write_coil(COIL_FLOW_INTERNAL_SENSOR_ENABLE, False)
        await api.async_write_coil(COIL_FLOW_EXTERNAL_SENSOR_ENABLE, False)
        if saved.boost_enabled:
            await api.async_write_coil(COIL_ELECTROLYSIS_BOOST, False)
        if saved.cover_control_enabled:
            await api.async_write_coil(
                COIL_ELECTROLYSIS_COVER_CONTROL_ENABLE, False
            )
        if saved.external_control_enabled:
            await api.async_write_coil(
                COIL_ELECTROLYSIS_EXTERNAL_CONTROL_ENABLE, False
            )
        if saved.internal_orp_control_enabled:
            await api.async_write_coil(
                COIL_ELECTROLYSIS_INTERNAL_ORP_CONTROL_ENABLE, False
            )
        await api.async_write_register(HR_ELECTROLYSIS_NORMAL_SETPOINT, 0)
        await async_verify_electrolysis_stopped(api)
        return saved
    except Exception:
        await async_restore_bypassed_calibration(
            api,
            saved,
            verify_flow=False,
        )
        raise


async def async_begin_bypassed_calibration(api: Any) -> None:
    """Start the validated 0x201 -> 0x203 sequence after probe immersion."""
    await async_verify_electrolysis_stopped(api)
    await async_start_calibration_session(api, force_clear=True)


async def async_restore_bypassed_calibration(
    api: Any,
    saved: CalibrationSavedState,
    *,
    verify_flow: bool = True,
) -> None:
    """Restore flow supervision and finally restore electrolysis production.

    Do not re-enter 0x201 here. Real-hardware observation showed an ORP reading
    of 999 mV after a successful 470 mV calibration when 0x201 had been
    automatically re-armed during probe restoration. The independent 0 %
    production lock remains active until this function finishes.
    """
    await async_verify_electrolysis_stopped(api)

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
            raise GuidedCalibrationError("flow_not_restored")

    # The controller normally leaves 0x201 itself after success/error. Ensure it
    # is OFF before restoring any production source, but never re-arm it here.
    if await async_read_calibration_mode(api):
        await api.async_write_coil(COIL_CALIBRATION_MODE, False)
        if not await _async_wait_for_mode(api, False):
            raise GuidedCalibrationError("calibration_mode_not_released")

    await api.async_write_register(
        HR_ELECTROLYSIS_NORMAL_SETPOINT, saved.normal_production_setpoint
    )
    if saved.internal_orp_control_enabled:
        await api.async_write_coil(
            COIL_ELECTROLYSIS_INTERNAL_ORP_CONTROL_ENABLE, True
        )
    if saved.external_control_enabled:
        await api.async_write_coil(COIL_ELECTROLYSIS_EXTERNAL_CONTROL_ENABLE, True)
    if saved.cover_control_enabled:
        await api.async_write_coil(COIL_ELECTROLYSIS_COVER_CONTROL_ENABLE, True)
    if saved.boost_enabled:
        await api.async_write_coil(COIL_ELECTROLYSIS_BOOST, True)


async def async_calibrate_ph_fast(api: Any, reference_ph: float) -> int:
    """Run validated Fast pH calibration with the probe left installed."""
    raw_value = round(reference_ph * 100)
    if not 0 <= raw_value <= 1200:
        raise ValueError(f"pH calibration value out of range: {reference_ph}")

    await async_start_calibration_session(api, force_clear=True)
    await api.async_write_register(HR_CALIBRATION_VALUE, raw_value)
    await _async_command_edge(api, COIL_PH_CALIBRATION_FAST)
    response = await _async_wait_for_response(api, RESPONSE_NONE)

    if await async_read_calibration_mode(api):
        await api.async_write_coil(COIL_CALIBRATION_MODE, False)
    return response


async def async_trigger_ph7(api: Any) -> int:
    """Run the first standard pH point; 16 means pH 7 was accepted."""
    if not await async_read_calibration_mode(api):
        raise GuidedCalibrationError("calibration_mode_not_active")
    if await async_read_calibration_response(api) != RESPONSE_NONE:
        await async_clear_response_in_active_mode(api)
    await _async_command_edge(api, COIL_PH_CALIBRATION_PH7)
    response = await _async_wait_for_response(api, RESPONSE_NONE)
    if response != RESPONSE_FIRST_POINT_OK:
        await async_verify_electrolysis_stopped(api)
    return response


async def async_trigger_ph4(api: Any) -> int:
    """Run the second pH point without re-entering 0x201 after completion."""
    if not await async_read_calibration_mode(api):
        raise GuidedCalibrationError("calibration_mode_not_active")
    if await async_read_calibration_response(api) != RESPONSE_FIRST_POINT_OK:
        raise GuidedCalibrationError("ph_first_point_missing")
    await _async_command_edge(api, COIL_PH_CALIBRATION_PH4)
    response = await _async_wait_for_response(api, RESPONSE_FIRST_POINT_OK)
    await async_verify_electrolysis_stopped(api)
    return response


async def async_restart_standard_ph_after_error(api: Any) -> None:
    """Explicitly start a new standard pH session after an error."""
    await async_verify_electrolysis_stopped(api)
    await async_start_calibration_session(api, force_clear=True)


async def async_trigger_orp_470(api: Any) -> int:
    """Run validated ORP calibration at 470 mV without terminal re-arm."""
    if not await async_read_calibration_mode(api):
        raise GuidedCalibrationError("calibration_mode_not_active")
    if await async_read_calibration_response(api) != RESPONSE_NONE:
        await async_clear_response_in_active_mode(api)
    await _async_command_edge(api, COIL_ORP_CALIBRATION_470MV)
    response = await _async_wait_for_response(api, RESPONSE_NONE)
    await async_verify_electrolysis_stopped(api)
    return response


async def async_restart_orp_after_error(api: Any) -> None:
    """Explicitly start a fresh 470 mV ORP session after an error."""
    await async_verify_electrolysis_stopped(api)
    await async_start_calibration_session(api, force_clear=True)


async def _async_reset_calibration(api: Any, coil: int) -> int:
    """Run the validated 0x201 -> 0x203 -> reset-coil sequence."""
    await async_start_calibration_session(api, force_clear=True)
    await _async_command_edge(api, coil)
    response = await _async_wait_for_response(api, RESPONSE_NONE)

    if await async_read_calibration_mode(api):
        await api.async_write_coil(COIL_CALIBRATION_MODE, False)
    return response


async def async_reset_ph_calibration(api: Any) -> int:
    """Restore factory pH calibration using the validated reset sequence."""
    return await _async_reset_calibration(api, COIL_PH_CALIBRATION_RESET)


async def async_reset_orp_calibration(api: Any) -> int:
    """Restore factory ORP calibration using the validated reset sequence."""
    return await _async_reset_calibration(api, COIL_ORP_CALIBRATION_RESET)
