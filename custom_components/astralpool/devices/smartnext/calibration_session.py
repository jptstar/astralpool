"""Persistent safety session for guided Smart Next pH/ORP calibration."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .api import SmartNextCommunicationError
from .const import (
    COIL_ELECTROLYSIS_BOOST,
    COIL_ELECTROLYSIS_COVER_CONTROL_ENABLE,
    COIL_ELECTROLYSIS_EXTERNAL_CONTROL_ENABLE,
    COIL_ELECTROLYSIS_INTERNAL_ORP_CONTROL_ENABLE,
    COIL_FLOW_EXTERNAL_SENSOR_ENABLE,
    COIL_FLOW_INTERNAL_SENSOR_ENABLE,
    COIL_PH_PUMP_STOP_ENABLE,
    DI_TREATMENT_HALTED,
    DOMAIN,
    HR_ELECTROLYSIS_CONTROL_WORD,
    HR_ELECTROLYSIS_NORMAL_SETPOINT,
    HR_FLOW_CONTROL_WORD,
    HR_PH_OUTPUT_CONTROL_WORD,
)
from .guided_calibration import (
    CalibrationSavedState,
    GuidedCalibrationError,
    async_clear_response_in_active_mode,
    async_read_calibration_mode,
    async_verify_electrolysis_stopped,
    async_verify_ph_pump_stopped,
)

_LOGGER = logging.getLogger(__name__)
_STORAGE_VERSION = 1
_STORE_CACHE_KEY = f"{DOMAIN}_calibration_recovery_stores"
_RECOVERY_RETRY_SECONDS = 10.0


def _endpoint_id(api: Any) -> str:
    """Return a stable, non-sensitive identifier for one Modbus endpoint."""
    endpoint = f"{api.host}:{api.port}:{api.unit_id}".encode()
    return hashlib.sha256(endpoint).hexdigest()[:16]


def _store(hass: HomeAssistant, api: Any) -> Store:
    """Return the per-controller recovery store."""
    stores: dict[str, Store] = hass.data.setdefault(_STORE_CACHE_KEY, {})
    endpoint_id = _endpoint_id(api)
    if endpoint_id not in stores:
        stores[endpoint_id] = Store(
            hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.calibration_recovery_{endpoint_id}",
        )
    return stores[endpoint_id]


def _serialize(saved: CalibrationSavedState) -> dict[str, Any]:
    return {
        "internal_flow_enabled": saved.internal_flow_enabled,
        "external_flow_enabled": saved.external_flow_enabled,
        "normal_production_setpoint": saved.normal_production_setpoint,
        "boost_enabled": saved.boost_enabled,
        "cover_control_enabled": saved.cover_control_enabled,
        "external_control_enabled": saved.external_control_enabled,
        "internal_orp_control_enabled": saved.internal_orp_control_enabled,
        "ph_pump_stop_enabled": saved.ph_pump_stop_enabled,
    }


def _deserialize(data: dict[str, Any]) -> CalibrationSavedState:
    return CalibrationSavedState(
        internal_flow_enabled=bool(data["internal_flow_enabled"]),
        external_flow_enabled=bool(data["external_flow_enabled"]),
        normal_production_setpoint=int(data["normal_production_setpoint"]),
        boost_enabled=bool(data["boost_enabled"]),
        cover_control_enabled=bool(data["cover_control_enabled"]),
        external_control_enabled=bool(data["external_control_enabled"]),
        internal_orp_control_enabled=bool(data["internal_orp_control_enabled"]),
        ph_pump_stop_enabled=bool(data["ph_pump_stop_enabled"]),
    )


async def async_load_persistent_calibration(
    hass: HomeAssistant, api: Any
) -> CalibrationSavedState | None:
    """Load a pending calibration recovery state, if any."""
    payload = await _store(hass, api).async_load()
    if not isinstance(payload, dict):
        return None
    saved = payload.get("saved")
    if not isinstance(saved, dict):
        return None
    try:
        return _deserialize(saved)
    except (KeyError, TypeError, ValueError):
        _LOGGER.error("Invalid Smart Next calibration recovery state")
        return None


async def async_save_persistent_calibration(
    hass: HomeAssistant, api: Any, saved: CalibrationSavedState
) -> None:
    """Persist the original state before any flow-sensor write."""
    await _store(hass, api).async_save({"saved": _serialize(saved)})


async def async_clear_persistent_calibration(hass: HomeAssistant, api: Any) -> None:
    """Clear the recovery marker after a confirmed safe exit."""
    await _store(hass, api).async_remove()


async def _async_read_saved_state(api: Any) -> CalibrationSavedState:
    """Capture every controller setting temporarily changed by calibration."""
    flow_control = (await api._read_holding_registers(HR_FLOW_CONTROL_WORD, 1))[0]
    electrolysis_control = (
        await api._read_holding_registers(HR_ELECTROLYSIS_CONTROL_WORD, 2)
    )
    ph_control = (await api._read_holding_registers(HR_PH_OUTPUT_CONTROL_WORD, 1))[0]
    control_word = electrolysis_control[0]
    return CalibrationSavedState(
        internal_flow_enabled=bool(flow_control & (1 << 0)),
        external_flow_enabled=bool(flow_control & (1 << 1)),
        normal_production_setpoint=int(electrolysis_control[1]),
        boost_enabled=bool(control_word & (1 << 1)),
        cover_control_enabled=bool(control_word & (1 << 2)),
        external_control_enabled=bool(control_word & (1 << 4)),
        internal_orp_control_enabled=bool(control_word & (1 << 5)),
        ph_pump_stop_enabled=bool(ph_control & (1 << 12)),
    )


async def _async_hold_electrolysis_at_zero(
    api: Any, saved: CalibrationSavedState
) -> None:
    """Keep electrolysis inhibited independently of calibration mode."""
    if saved.boost_enabled:
        await api.async_write_coil(COIL_ELECTROLYSIS_BOOST, False)
    if saved.cover_control_enabled:
        await api.async_write_coil(COIL_ELECTROLYSIS_COVER_CONTROL_ENABLE, False)
    if saved.external_control_enabled:
        await api.async_write_coil(COIL_ELECTROLYSIS_EXTERNAL_CONTROL_ENABLE, False)
    if saved.internal_orp_control_enabled:
        await api.async_write_coil(
            COIL_ELECTROLYSIS_INTERNAL_ORP_CONTROL_ENABLE, False
        )
    await api.async_write_register(HR_ELECTROLYSIS_NORMAL_SETPOINT, 0)


async def _async_set_flow_sensors(api: Any, internal: bool, external: bool) -> None:
    await api.async_write_coil(COIL_FLOW_INTERNAL_SENSOR_ENABLE, internal)
    await api.async_write_coil(COIL_FLOW_EXTERNAL_SENSOR_ENABLE, external)


async def _async_verify_flow_sensor_state(
    api: Any, internal: bool, external: bool
) -> None:
    states = await api._read_coils(COIL_FLOW_INTERNAL_SENSOR_ENABLE, 2)
    if states[0] is not internal or states[1] is not external:
        raise GuidedCalibrationError("flow_not_restored")


async def async_activate_persistent_calibration(
    hass: HomeAssistant,
    api: Any,
    saved: CalibrationSavedState,
) -> None:
    """Apply the long-lived safety state used for probe-removal calibration.

    The original state is persisted first. Electrolysis is then held at 0 %,
    Pump Stop is enabled, and both logical flow inputs are disabled for the
    complete guided pH Standard / ORP session.
    """
    await async_save_persistent_calibration(hass, api, saved)
    await api.async_write_coil(COIL_PH_PUMP_STOP_ENABLE, True)
    await _async_hold_electrolysis_at_zero(api, saved)
    await async_verify_electrolysis_stopped(api)
    await _async_set_flow_sensors(api, False, False)
    await _async_verify_flow_sensor_state(api, False, False)
    await async_verify_ph_pump_stopped(api)


async def async_prepare_persistent_calibration(
    hass: HomeAssistant, api: Any
) -> CalibrationSavedState:
    """Capture the original state and start a persistent safe calibration session."""
    saved = await _async_read_saved_state(api)
    try:
        await async_activate_persistent_calibration(hass, api, saved)
    except Exception:
        # No hydraulic manipulation has been authorized yet. Restore the flow
        # configuration immediately if preparation itself cannot complete.
        try:
            await async_restore_interrupted_flow_sensors(hass, api, saved)
        except Exception:  # noqa: BLE001
            _LOGGER.exception(
                "Unable to restore Smart Next flow sensors after preparation failure"
            )
        raise
    return saved


async def async_verify_active_probe_calibration(
    api: Any, *, clear_response: bool = False
) -> None:
    """Verify that the already-started 0x201 session is still safe and active."""
    await async_verify_electrolysis_stopped(api)
    await async_verify_ph_pump_stopped(api)
    if not await async_read_calibration_mode(api):
        raise GuidedCalibrationError("calibration_mode_lost")
    halted = bool((await api._read_discrete_inputs(DI_TREATMENT_HALTED, 1))[0])
    if not halted:
        raise GuidedCalibrationError("treatment_not_halted")
    if clear_response:
        await async_clear_response_in_active_mode(api, force=True)


async def async_restore_interrupted_flow_sensors(
    hass: HomeAssistant,
    api: Any,
    saved: CalibrationSavedState | None = None,
) -> None:
    """Restore saved flow supervision while deliberately keeping production at 0 %.

    This is the fail-safe exit used when the options flow is cancelled,
    interrupted or removed. Pump Stop is intentionally left enabled and normal
    production is intentionally left at 0 % because the hydraulic state cannot
    be assumed to be normal after an interrupted assistant.
    """
    if saved is None:
        saved = await async_load_persistent_calibration(hass, api)
    if saved is None:
        return

    await _async_hold_electrolysis_at_zero(api, saved)
    await _async_set_flow_sensors(
        api, saved.internal_flow_enabled, saved.external_flow_enabled
    )
    await _async_verify_flow_sensor_state(
        api, saved.internal_flow_enabled, saved.external_flow_enabled
    )
    await async_clear_persistent_calibration(hass, api)


async def async_restore_interrupted_flow_sensors_until_success(
    hass: HomeAssistant,
    api: Any,
    saved: CalibrationSavedState | None = None,
) -> None:
    """Retry fail-safe flow restoration until communication is available again."""
    while True:
        current = saved or await async_load_persistent_calibration(hass, api)
        if current is None:
            return
        try:
            await async_restore_interrupted_flow_sensors(hass, api, current)
        except asyncio.CancelledError:
            raise
        except (
            SmartNextCommunicationError,
            GuidedCalibrationError,
            OSError,
            TimeoutError,
        ) as err:
            _LOGGER.warning(
                "Smart Next calibration flow recovery pending: %s", err
            )
            await asyncio.sleep(_RECOVERY_RETRY_SECONDS)
            continue
        return


async def async_recover_interrupted_calibration(
    hass: HomeAssistant, api: Any
) -> bool:
    """Recover flow supervision left disabled by an interrupted HA session."""
    saved = await async_load_persistent_calibration(hass, api)
    if saved is None:
        return False
    try:
        await async_restore_interrupted_flow_sensors(hass, api, saved)
    except (OSError, TimeoutError) as err:
        raise SmartNextCommunicationError(str(err)) from err
    _LOGGER.warning(
        "Recovered Smart Next flow sensors after an interrupted calibration; "
        "electrolysis remains at 0 %% until explicitly restored"
    )
    return True
