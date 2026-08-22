"""Guided maintenance procedures for Smart Next."""

from __future__ import annotations

import asyncio
from typing import Any, Final

from .const import (
    COIL_CALIBRATION_MODE,
    COIL_CALIBRATION_RESPONSE_RESET,
    COIL_FLOW_CONFIG_RESET,
    COIL_ORP_CALIBRATION_RESET,
    COIL_ORP_CONFIG_RESET,
    COIL_PH_CALIBRATION_RESET,
    COIL_PH_CONFIG_RESET,
    COIL_SALT_CALIBRATION_RESET,
    COIL_SALT_CONFIG_RESET,
    COIL_TEMPERATURE_CALIBRATION_RESET,
    COIL_TEMPERATURE_CONFIG_RESET,
    DI_TREATMENT_HALTED,
    HR_WATCHDOG_CONFIG,
    HR_WATCHDOG_TIME,
    IR_CALIBRATION_RESPONSE,
)

ACTION_RESET_FLOW_CONFIG: Final = "reset_flow_config"
ACTION_RESET_PH_CONFIG: Final = "reset_ph_config"
ACTION_RESET_PH_CALIBRATION: Final = "reset_ph_calibration"
ACTION_RESET_ORP_CONFIG: Final = "reset_orp_config"
ACTION_RESET_ORP_CALIBRATION: Final = "reset_orp_calibration"
ACTION_RESET_TEMPERATURE_CONFIG: Final = "reset_temperature_config"
ACTION_RESET_TEMPERATURE_CALIBRATION: Final = "reset_temperature_calibration"
ACTION_RESET_SALT_CONFIG: Final = "reset_salt_config"
ACTION_RESET_SALT_CALIBRATION: Final = "reset_salt_calibration"
ACTION_RESTART_DEVICE: Final = "restart_device"

CONFIG_RESET_COILS: Final = {
    ACTION_RESET_FLOW_CONFIG: COIL_FLOW_CONFIG_RESET,
    ACTION_RESET_PH_CONFIG: COIL_PH_CONFIG_RESET,
    ACTION_RESET_ORP_CONFIG: COIL_ORP_CONFIG_RESET,
    ACTION_RESET_TEMPERATURE_CONFIG: COIL_TEMPERATURE_CONFIG_RESET,
    ACTION_RESET_SALT_CONFIG: COIL_SALT_CONFIG_RESET,
}

CALIBRATION_RESET_COILS: Final = {
    ACTION_RESET_PH_CALIBRATION: COIL_PH_CALIBRATION_RESET,
    ACTION_RESET_ORP_CALIBRATION: COIL_ORP_CALIBRATION_RESET,
    ACTION_RESET_TEMPERATURE_CALIBRATION: COIL_TEMPERATURE_CALIBRATION_RESET,
    ACTION_RESET_SALT_CALIBRATION: COIL_SALT_CALIBRATION_RESET,
}

ACTION_CAPABILITIES: Final = {
    ACTION_RESET_PH_CONFIG: "technology_ph_implemented",
    ACTION_RESET_PH_CALIBRATION: "technology_ph_implemented",
    ACTION_RESET_ORP_CONFIG: "technology_orp_implemented",
    ACTION_RESET_ORP_CALIBRATION: "technology_orp_implemented",
    ACTION_RESET_TEMPERATURE_CONFIG: "technology_temperature_implemented",
    ACTION_RESET_TEMPERATURE_CALIBRATION: "technology_temperature_implemented",
    ACTION_RESET_SALT_CONFIG: "technology_salt_implemented",
    ACTION_RESET_SALT_CALIBRATION: "technology_salt_implemented",
}

CALIBRATION_RESPONSE_MESSAGES: Final = {
    1: "ok",
    2: "e2",
    3: "e3",
    4: "unavailable",
    5: "initializing",
    16: "first_point_ok",
}

WATCHDOG_RESTART_SECONDS: Final = 60
CALIBRATION_MODE_TIMEOUT: Final = 8.0
CALIBRATION_COMMAND_TIMEOUT: Final = 5.0
CALIBRATION_RESPONSE_TIMEOUT: Final = 20.0


class SmartNextMaintenanceError(Exception):
    """Raised when a guided Smart Next maintenance procedure fails."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


async def _async_release_command(api: Any, coil: int, *, max_wait: float = 2.0) -> None:
    """Wait for a volatile command to self-clear, then clear it if needed."""
    deadline = asyncio.get_running_loop().time() + max_wait
    while asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(0.2)
        try:
            if not (await api._read_coils(coil, 1))[0]:
                return
        except Exception:  # noqa: BLE001 - best effort cleanup follows
            break
    await api.async_write_coil(coil, False)


async def _async_wait_treatment_halted(
    api: Any,
    expected: bool,
    *,
    timeout: float = CALIBRATION_MODE_TIMEOUT,
) -> None:
    """Wait until the controller confirms entering or leaving calibration mode."""
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        value = (await api._read_discrete_inputs(DI_TREATMENT_HALTED, 1))[0]
        if bool(value) is expected:
            return
        await asyncio.sleep(0.2)
    raise SmartNextMaintenanceError("timeout")


async def async_run_config_reset(api: Any, action: str) -> str:
    """Run one documented configuration reset command."""
    try:
        coil = CONFIG_RESET_COILS[action]
    except KeyError as err:
        raise SmartNextMaintenanceError("unsupported_action") from err

    await api.async_write_coil(coil, True)
    await _async_release_command(api, coil, max_wait=CALIBRATION_COMMAND_TIMEOUT)
    return "ok"


async def _async_clear_calibration_response(api: Any) -> None:
    """Clear the previous calibration response before a new command."""
    await api.async_write_coil(COIL_CALIBRATION_RESPONSE_RESET, True)
    await _async_release_command(api, COIL_CALIBRATION_RESPONSE_RESET, max_wait=1.0)

    deadline = asyncio.get_running_loop().time() + 2.0
    while asyncio.get_running_loop().time() < deadline:
        response = (await api._read_input_registers(IR_CALIBRATION_RESPONSE, 1))[0]
        if response == 0:
            return
        await asyncio.sleep(0.2)
    raise SmartNextMaintenanceError("response_not_cleared")


async def _async_wait_calibration_response(
    api: Any,
    *,
    timeout: float = CALIBRATION_RESPONSE_TIMEOUT,
) -> int:
    """Wait for the Smart Next calibration result register."""
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        response = (await api._read_input_registers(IR_CALIBRATION_RESPONSE, 1))[0]
        if response != 0:
            return response
        await asyncio.sleep(0.5)
    raise SmartNextMaintenanceError("timeout")


async def async_run_calibration_reset(api: Any, action: str) -> str:
    """Reset one calibration using the controller-confirmed calibration workflow."""
    try:
        command_coil = CALIBRATION_RESET_COILS[action]
    except KeyError as err:
        raise SmartNextMaintenanceError("unsupported_action") from err

    await _async_clear_calibration_response(api)
    await api.async_write_coil(COIL_CALIBRATION_MODE, True)

    result: str | None = None
    pending_error: SmartNextMaintenanceError | None = None
    try:
        # Do not send the reset while the Smart Next is merely transitioning into
        # calibration mode. Input 0x202 explicitly confirms that water treatment
        # has stopped and the controller is ready for calibration commands.
        await _async_wait_treatment_halted(api, True)

        await api.async_write_coil(command_coil, True)
        # The reset command is documented as volatile. Let the controller consume
        # and self-clear it before evaluating the calibration result.
        await _async_release_command(
            api,
            command_coil,
            max_wait=CALIBRATION_COMMAND_TIMEOUT,
        )

        response = await _async_wait_calibration_response(api)
        result = CALIBRATION_RESPONSE_MESSAGES.get(response)
        if result == "ok":
            pass
        elif result is None:
            pending_error = SmartNextMaintenanceError(
                f"unexpected_response_{response}"
            )
        else:
            pending_error = SmartNextMaintenanceError(result)
    except SmartNextMaintenanceError as err:
        pending_error = err
    finally:
        # Always leave calibration mode. The reset command should already be
        # released, but explicitly clear it if a communication/timing failure
        # interrupted the normal one-shot lifecycle.
        try:
            await _async_release_command(api, command_coil, max_wait=0.5)
        except Exception:  # noqa: BLE001 - continue with mandatory mode cleanup
            pass
        await api.async_write_coil(COIL_CALIBRATION_MODE, False)
        try:
            await _async_wait_treatment_halted(api, False)
        except SmartNextMaintenanceError as err:
            if pending_error is None:
                pending_error = err

    if pending_error is not None:
        raise pending_error
    if result != "ok":
        raise SmartNextMaintenanceError("timeout")
    return result


async def async_read_watchdog(api: Any) -> tuple[int, int]:
    """Return watchdog timeout and configured watchdog action."""
    values = await api._read_holding_registers(HR_WATCHDOG_TIME, 2)
    return int(values[0]), int(values[HR_WATCHDOG_CONFIG - HR_WATCHDOG_TIME])


async def async_arm_restart_watchdog(api: Any) -> int:
    """Arm the documented communication watchdog for a one-shot restart.

    The caller must stop all Modbus traffic immediately after this call and restore
    the returned previous watchdog timeout after the controller comes back online.
    """
    previous_timeout, watchdog_config = await async_read_watchdog(api)
    if watchdog_config != 1:
        raise SmartNextMaintenanceError("watchdog_not_restart")
    await api.async_write_register(HR_WATCHDOG_TIME, WATCHDOG_RESTART_SECONDS)
    return previous_timeout


async def async_restore_watchdog(api: Any, timeout: int) -> None:
    """Restore the previous watchdog timeout after a guided restart."""
    await api.async_write_register(HR_WATCHDOG_TIME, timeout)
