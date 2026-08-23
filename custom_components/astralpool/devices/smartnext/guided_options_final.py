"""Final fail-safe overrides for Smart Next pH/ORP guided calibration."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol

from homeassistant.core import callback

from .api import SmartNextCommunicationError
from .calibration_session import (
    async_activate_persistent_calibration,
    async_clear_persistent_calibration,
    async_prepare_persistent_calibration,
    async_restore_interrupted_flow_sensors,
    async_restore_interrupted_flow_sensors_until_success,
    async_verify_active_probe_calibration,
)
from .const import (
    DI_ELECTROLYSIS_RUNNING,
    DOMAIN,
    IR_ELECTROLYSIS_CURRENT,
    IR_ELECTROLYSIS_PRODUCTION,
    IR_PH_PUMP_OUTPUT,
)
from .guided_calibration import (
    RESPONSE_FIRST_POINT_OK,
    RESPONSE_OK,
    GuidedCalibrationError,
    async_begin_bypassed_calibration,
    async_trigger_orp_470,
    async_trigger_ph4,
    async_trigger_ph7,
    async_verify_electrolysis_stopped,
    async_verify_ph_pump_stopped,
)
from .guided_options_safe import (
    STABILIZATION_SECONDS,
    SmartNextGuidedCalibrationOptionsMixin as _SafeGuidedCalibrationOptionsMixin,
)


class SmartNextGuidedCalibrationOptionsMixin(_SafeGuidedCalibrationOptionsMixin):
    """Keep flow inputs disabled for the complete pH Standard / ORP session.

    Flow supervision is restored only when the full hydraulic restoration has
    completed, or automatically if the options flow is cancelled/interrupted.
    A persistent recovery marker also allows startup recovery after an HA restart.
    """

    _calibration_guard_task: asyncio.Task[Any] | None = None
    _session_safety_error: str | None = None

    def _active_saved_state(self):
        return self._ph_saved_state or self._orp_saved_state

    def _stop_calibration_guard(self) -> None:
        task = self._calibration_guard_task
        if task is not None and not task.done():
            task.cancel()
        self._calibration_guard_task = None

    def _start_calibration_guard(self, saved_state) -> None:
        """Continuously watch real outputs while logical flow inputs are disabled."""
        self._stop_calibration_guard()
        self._session_safety_error = None
        self._calibration_guard_task = self.hass.async_create_background_task(
            self._async_calibration_guard(saved_state),
            f"{DOMAIN}: Smart Next calibration safety guard",
        )

    async def _async_calibration_guard(self, saved_state) -> None:
        """Restore flow supervision immediately if a real output becomes active."""
        api = self._config_entry.runtime_data.api
        while True:
            try:
                electrolysis = await api._read_input_registers(
                    IR_ELECTROLYSIS_PRODUCTION, 2
                )
                running = bool(
                    (await api._read_discrete_inputs(DI_ELECTROLYSIS_RUNNING, 1))[0]
                )
                ph_pump_output = int(
                    (await api._read_input_registers(IR_PH_PUMP_OUTPUT, 1))[0]
                )
            except asyncio.CancelledError:
                raise
            except (SmartNextCommunicationError, OSError, TimeoutError):
                # Recovery state is persistent. If communication is temporarily
                # unavailable, keep trying; cancellation/startup recovery uses
                # the same saved state once the controller is reachable again.
                await asyncio.sleep(1.0)
                continue

            production = int(electrolysis[0])
            current_raw = int(
                electrolysis[IR_ELECTROLYSIS_CURRENT - IR_ELECTROLYSIS_PRODUCTION]
            )
            if production != 0 or current_raw != 0 or running:
                self._session_safety_error = "electrolysis_safety_lost"
            elif ph_pump_output != 0:
                self._session_safety_error = "ph_pump_not_stopped"
            else:
                await asyncio.sleep(1.0)
                continue

            await async_restore_interrupted_flow_sensors_until_success(
                self.hass, api, saved_state
            )
            return

    async def _async_guard_error_result(self):
        """Route a background safety trip back to the relevant guided error menu."""
        reason = self._session_safety_error
        if reason is None:
            return None
        self._session_safety_error = None
        if self._ph_saved_state is not None:
            self._ph_last_error = reason
            return await self.async_step_calibrate_ph_standard_error()
        if self._orp_saved_state is not None:
            self._orp_last_error = reason
            return await self.async_step_calibrate_orp_error()
        return None

    async def _async_confirmation_step(
        self,
        *,
        step_id: str,
        field: str,
        user_input,
        next_step,
    ):
        guard_result = await self._async_guard_error_result()
        if guard_result is not None:
            return guard_result
        return await super()._async_confirmation_step(
            step_id=step_id,
            field=field,
            user_input=user_input,
            next_step=next_step,
        )

    async def _async_terminal_flow_restore(self, saved_state) -> str | None:
        """Keep flow disabled after terminal results while checking real outputs.

        Unlike the previous safety layer, a normal terminal calibration result
        does not restore flow supervision. It remains disabled until the end of
        the guided procedure so pH/ORP values stay visible. If the real pH pump
        or electrolysis cannot be confirmed stopped, flow supervision is restored
        immediately as a fail-safe exception.
        """
        try:
            await async_verify_electrolysis_stopped(
                self._config_entry.runtime_data.api
            )
            await async_verify_ph_pump_stopped(self._config_entry.runtime_data.api)
        except (SmartNextCommunicationError, OSError, TimeoutError):
            self.hass.async_create_background_task(
                async_restore_interrupted_flow_sensors_until_success(
                    self.hass,
                    self._config_entry.runtime_data.api,
                    saved_state,
                ),
                f"{DOMAIN}: restore Smart Next flow sensors",
            )
            return "communication"
        except GuidedCalibrationError as err:
            try:
                await async_restore_interrupted_flow_sensors(
                    self.hass,
                    self._config_entry.runtime_data.api,
                    saved_state,
                )
            except (
                SmartNextCommunicationError,
                GuidedCalibrationError,
                OSError,
                TimeoutError,
            ):
                self.hass.async_create_background_task(
                    async_restore_interrupted_flow_sensors_until_success(
                        self.hass,
                        self._config_entry.runtime_data.api,
                        saved_state,
                    ),
                    f"{DOMAIN}: restore Smart Next flow sensors",
                )
            return err.reason
        return None

    @callback
    def async_remove(self) -> None:
        """Restore flow supervision if the user cancels/closes an active assistant."""
        saved_state = self._active_saved_state()
        self._stop_calibration_guard()
        if saved_state is not None:
            self.hass.async_create_background_task(
                async_restore_interrupted_flow_sensors_until_success(
                    self.hass,
                    self._config_entry.runtime_data.api,
                    saved_state,
                ),
                f"{DOMAIN}: recover cancelled Smart Next calibration",
            )
        super().async_remove()

    # ------------------------------------------------------------------
    # Persistent preparation: production 0 %, Pump Stop ON, flow inputs OFF.
    # ------------------------------------------------------------------

    async def async_step_calibrate_ph_standard_prepare(self, user_input=None):
        if not self._ph_available():
            return self.async_abort(reason="maintenance_unsupported")
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("confirm", False):
                errors["base"] = "confirmation_required"
            else:
                try:
                    self._ph_saved_state = await async_prepare_persistent_calibration(
                        self.hass, self._config_entry.runtime_data.api
                    )
                    self._ph_last_error = None
                    self._ph7_stabilization_started = None
                    self._ph4_stabilization_started = None
                    self._start_calibration_guard(self._ph_saved_state)
                    await self._config_entry.runtime_data.async_request_refresh()
                except (SmartNextCommunicationError, OSError, TimeoutError):
                    errors["base"] = "calibration_communication_failed"
                except GuidedCalibrationError as err:
                    errors["base"] = err.reason
                else:
                    return await self.async_step_calibrate_ph_standard_filtration_off()
        return self.async_show_form(
            step_id="calibrate_ph_standard_prepare",
            data_schema=vol.Schema({vol.Required("confirm", default=False): bool}),
            errors=errors,
        )

    async def async_step_calibrate_orp_prepare(self, user_input=None):
        if not self._orp_available():
            return self.async_abort(reason="maintenance_unsupported")
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("confirm", False):
                errors["base"] = "confirmation_required"
            else:
                try:
                    self._orp_saved_state = await async_prepare_persistent_calibration(
                        self.hass, self._config_entry.runtime_data.api
                    )
                    self._orp_last_error = None
                    self._orp_stabilization_started = None
                    self._start_calibration_guard(self._orp_saved_state)
                    await self._config_entry.runtime_data.async_request_refresh()
                except (SmartNextCommunicationError, OSError, TimeoutError):
                    errors["base"] = "calibration_communication_failed"
                except GuidedCalibrationError as err:
                    errors["base"] = err.reason
                else:
                    return await self.async_step_calibrate_orp_filtration_off()
        return self.async_show_form(
            step_id="calibrate_orp_prepare",
            data_schema=vol.Schema({vol.Required("confirm", default=False): bool}),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Start 0x201 before the probe is removed, then keep it through stability.
    # ------------------------------------------------------------------

    async def async_step_calibrate_ph_standard_drain_pulse(self, user_input=None):
        if self._ph_saved_state is None:
            return await self.async_step_calibrate_ph_standard_prepare()
        guard_result = await self._async_guard_error_result()
        if guard_result is not None:
            return guard_result
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("drain_done", False):
                errors["base"] = "confirmation_required"
            else:
                try:
                    await async_begin_bypassed_calibration(
                        self._config_entry.runtime_data.api
                    )
                    await self._config_entry.runtime_data.async_request_refresh()
                except (SmartNextCommunicationError, OSError, TimeoutError):
                    self._ph_last_error = "communication"
                    return await self.async_step_calibrate_ph_standard_error()
                except GuidedCalibrationError as err:
                    self._ph_last_error = err.reason
                    return await self.async_step_calibrate_ph_standard_error()
                self._ph7_stabilization_started = None
                self._ph4_stabilization_started = None
                return await self.async_step_calibrate_ph_standard_ph7_immerse()
        return self.async_show_form(
            step_id="calibrate_ph_standard_drain_pulse",
            data_schema=vol.Schema({vol.Required("drain_done", default=False): bool}),
            errors=errors,
        )

    async def async_step_calibrate_orp_drain_pulse(self, user_input=None):
        if self._orp_saved_state is None:
            return await self.async_step_calibrate_orp_prepare()
        guard_result = await self._async_guard_error_result()
        if guard_result is not None:
            return guard_result
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("drain_done", False):
                errors["base"] = "confirmation_required"
            else:
                try:
                    await async_begin_bypassed_calibration(
                        self._config_entry.runtime_data.api
                    )
                    await self._config_entry.runtime_data.async_request_refresh()
                except (SmartNextCommunicationError, OSError, TimeoutError):
                    self._orp_last_error = "communication"
                    return await self.async_step_calibrate_orp_error()
                except GuidedCalibrationError as err:
                    self._orp_last_error = err.reason
                    return await self.async_step_calibrate_orp_error()
                self._orp_stabilization_started = None
                return await self.async_step_calibrate_orp_immerse()
        return self.async_show_form(
            step_id="calibrate_orp_drain_pulse",
            data_schema=vol.Schema({vol.Required("drain_done", default=False): bool}),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Calibration commands: never silently re-arm 0x201 after a terminal result.
    # ------------------------------------------------------------------

    async def async_step_calibrate_ph_standard_ph7(self, user_input=None):
        if self._ph_saved_state is None:
            return await self.async_step_calibrate_ph_standard_prepare()
        if self._ph7_stabilization_started is None:
            return await self.async_step_calibrate_ph_standard_ph7_immerse()
        guard_result = await self._async_guard_error_result()
        if guard_result is not None:
            return guard_result

        errors: dict[str, str] = {}
        if user_input is not None:
            elapsed = self._now() - self._ph7_stabilization_started
            if elapsed < STABILIZATION_SECONDS:
                errors["base"] = "stabilization_wait"
            elif not user_input.get("stable", False):
                errors["base"] = "measurement_not_confirmed_stable"
            else:
                try:
                    await async_verify_active_probe_calibration(
                        self._config_entry.runtime_data.api,
                        clear_response=True,
                    )
                    response = await async_trigger_ph7(
                        self._config_entry.runtime_data.api
                    )
                    await self._config_entry.runtime_data.async_request_refresh()
                except (SmartNextCommunicationError, OSError, TimeoutError):
                    self._ph_last_error = "communication"
                    return await self.async_step_calibrate_ph_standard_error()
                except GuidedCalibrationError as err:
                    self._ph_last_error = err.reason
                    return await self.async_step_calibrate_ph_standard_error()

                self._ph7_stabilization_started = None
                if response == RESPONSE_FIRST_POINT_OK:
                    return await self.async_step_calibrate_ph_standard_ph4_immerse()

                safety_error = await self._async_terminal_flow_restore(
                    self._ph_saved_state
                )
                self._ph_last_error = safety_error or response
                return await self.async_step_calibrate_ph_standard_error()

        current = self._config_entry.runtime_data.data.get("ph")
        current_text = (
            f"{float(current):.2f}" if isinstance(current, (int, float)) else "—"
        )
        return self.async_show_form(
            step_id="calibrate_ph_standard_ph7",
            data_schema=vol.Schema({vol.Required("stable", default=False): bool}),
            errors=errors,
            description_placeholders={
                "current_ph": current_text,
                "remaining": str(self._remaining_seconds(self._ph7_stabilization_started)),
            },
        )

    async def async_step_calibrate_ph_standard_ph4(self, user_input=None):
        if self._ph_saved_state is None:
            return await self.async_step_calibrate_ph_standard_prepare()
        if self._ph4_stabilization_started is None:
            return await self.async_step_calibrate_ph_standard_ph4_immerse()
        guard_result = await self._async_guard_error_result()
        if guard_result is not None:
            return guard_result

        errors: dict[str, str] = {}
        if user_input is not None:
            elapsed = self._now() - self._ph4_stabilization_started
            if elapsed < STABILIZATION_SECONDS:
                errors["base"] = "stabilization_wait"
            elif not user_input.get("stable", False):
                errors["base"] = "measurement_not_confirmed_stable"
            else:
                try:
                    await async_verify_active_probe_calibration(
                        self._config_entry.runtime_data.api
                    )
                    response = await async_trigger_ph4(
                        self._config_entry.runtime_data.api
                    )
                except (SmartNextCommunicationError, OSError, TimeoutError):
                    self._ph_last_error = "communication"
                    return await self.async_step_calibrate_ph_standard_error()
                except GuidedCalibrationError as err:
                    self._ph_last_error = err.reason
                    return await self.async_step_calibrate_ph_standard_error()

                self._ph4_stabilization_started = None
                safety_error = await self._async_terminal_flow_restore(
                    self._ph_saved_state
                )
                if safety_error is not None:
                    self._ph_last_error = safety_error
                    return await self.async_step_calibrate_ph_standard_error()
                if response == RESPONSE_OK:
                    if self._calibration_chain_origin == "orp":
                        self._calibration_chain_origin = None
                        return await self.async_step_calibrate_ph_standard_restore()
                    return await self.async_step_calibrate_ph_standard_next_sensor()

                self._ph_last_error = response
                return await self.async_step_calibrate_ph_standard_error()

        current = self._config_entry.runtime_data.data.get("ph")
        current_text = (
            f"{float(current):.2f}" if isinstance(current, (int, float)) else "—"
        )
        return self.async_show_form(
            step_id="calibrate_ph_standard_ph4",
            data_schema=vol.Schema({vol.Required("stable", default=False): bool}),
            errors=errors,
            description_placeholders={
                "current_ph": current_text,
                "remaining": str(self._remaining_seconds(self._ph4_stabilization_started)),
            },
        )

    async def async_step_calibrate_orp_470(self, user_input=None):
        if self._orp_saved_state is None:
            return await self.async_step_calibrate_orp_prepare()
        if self._orp_stabilization_started is None:
            return await self.async_step_calibrate_orp_immerse()
        guard_result = await self._async_guard_error_result()
        if guard_result is not None:
            return guard_result

        errors: dict[str, str] = {}
        if user_input is not None:
            elapsed = self._now() - self._orp_stabilization_started
            if elapsed < STABILIZATION_SECONDS:
                errors["base"] = "stabilization_wait"
            elif not user_input.get("stable", False):
                errors["base"] = "measurement_not_confirmed_stable"
            else:
                try:
                    await async_verify_active_probe_calibration(
                        self._config_entry.runtime_data.api,
                        clear_response=True,
                    )
                    response = await async_trigger_orp_470(
                        self._config_entry.runtime_data.api
                    )
                except (SmartNextCommunicationError, OSError, TimeoutError):
                    self._orp_last_error = "communication"
                    return await self.async_step_calibrate_orp_error()
                except GuidedCalibrationError as err:
                    self._orp_last_error = err.reason
                    return await self.async_step_calibrate_orp_error()

                self._orp_stabilization_started = None
                safety_error = await self._async_terminal_flow_restore(
                    self._orp_saved_state
                )
                if safety_error is not None:
                    self._orp_last_error = safety_error
                    return await self.async_step_calibrate_orp_error()
                if response == RESPONSE_OK:
                    if self._calibration_chain_origin == "ph":
                        self._calibration_chain_origin = None
                        return await self.async_step_calibrate_orp_restore()
                    return await self.async_step_calibrate_orp_next_sensor()

                self._orp_last_error = response
                return await self.async_step_calibrate_orp_error()

        current = self._config_entry.runtime_data.data.get("orp")
        current_text = str(int(current)) if isinstance(current, (int, float)) else "—"
        return self.async_show_form(
            step_id="calibrate_orp_470",
            data_schema=vol.Schema({vol.Required("stable", default=False): bool}),
            errors=errors,
            description_placeholders={
                "current_orp": current_text,
                "remaining": str(self._remaining_seconds(self._orp_stabilization_started)),
            },
        )

    # ------------------------------------------------------------------
    # Explicit retry / second probe = fresh 0x201 session before probe removal.
    # ------------------------------------------------------------------

    async def async_step_calibrate_ph_standard_retry(self, user_input=None):
        if self._ph_saved_state is None:
            return await self.async_step_calibrate_ph_standard_prepare()
        try:
            await async_activate_persistent_calibration(
                self.hass,
                self._config_entry.runtime_data.api,
                self._ph_saved_state,
            )
            self._start_calibration_guard(self._ph_saved_state)
            await async_begin_bypassed_calibration(self._config_entry.runtime_data.api)
        except (SmartNextCommunicationError, OSError, TimeoutError):
            self._ph_last_error = "communication"
            return await self.async_step_calibrate_ph_standard_error()
        except GuidedCalibrationError as err:
            self._ph_last_error = err.reason
            return await self.async_step_calibrate_ph_standard_error()
        self._ph_last_error = None
        self._ph7_stabilization_started = None
        self._ph4_stabilization_started = None
        return await self.async_step_calibrate_ph_standard_ph7_immerse()

    async def async_step_calibrate_orp_retry(self, user_input=None):
        if self._orp_saved_state is None:
            return await self.async_step_calibrate_orp_prepare()
        try:
            await async_activate_persistent_calibration(
                self.hass,
                self._config_entry.runtime_data.api,
                self._orp_saved_state,
            )
            self._start_calibration_guard(self._orp_saved_state)
            await async_begin_bypassed_calibration(self._config_entry.runtime_data.api)
        except (SmartNextCommunicationError, OSError, TimeoutError):
            self._orp_last_error = "communication"
            return await self.async_step_calibrate_orp_error()
        except GuidedCalibrationError as err:
            self._orp_last_error = err.reason
            return await self.async_step_calibrate_orp_error()
        self._orp_last_error = None
        self._orp_stabilization_started = None
        return await self.async_step_calibrate_orp_immerse()

    async def async_step_calibrate_ph_standard_chain_orp(self, user_input=None):
        if self._ph_saved_state is None:
            return await self.async_step_calibrate_ph_standard_prepare()
        guard_result = await self._async_guard_error_result()
        if guard_result is not None:
            return guard_result
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("ph_reinstalled", False):
                errors["base"] = "confirmation_required"
            else:
                self._orp_saved_state = self._ph_saved_state
                self._ph_saved_state = None
                self._calibration_chain_origin = "ph"
                self._orp_stabilization_started = None
                try:
                    await async_activate_persistent_calibration(
                        self.hass,
                        self._config_entry.runtime_data.api,
                        self._orp_saved_state,
                    )
                    self._start_calibration_guard(self._orp_saved_state)
                    await async_begin_bypassed_calibration(
                        self._config_entry.runtime_data.api
                    )
                except (SmartNextCommunicationError, OSError, TimeoutError):
                    self._orp_last_error = "communication"
                    return await self.async_step_calibrate_orp_error()
                except GuidedCalibrationError as err:
                    self._orp_last_error = err.reason
                    return await self.async_step_calibrate_orp_error()
                return await self.async_step_calibrate_ph_standard_chain_orp_immerse()
        return self.async_show_form(
            step_id="calibrate_ph_standard_chain_orp",
            data_schema=vol.Schema(
                {vol.Required("ph_reinstalled", default=False): bool}
            ),
            errors=errors,
        )

    async def async_step_calibrate_orp_chain_ph(self, user_input=None):
        if self._orp_saved_state is None:
            return await self.async_step_calibrate_orp_prepare()
        guard_result = await self._async_guard_error_result()
        if guard_result is not None:
            return guard_result
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("orp_reinstalled", False):
                errors["base"] = "confirmation_required"
            else:
                self._ph_saved_state = self._orp_saved_state
                self._orp_saved_state = None
                self._calibration_chain_origin = "orp"
                self._ph7_stabilization_started = None
                self._ph4_stabilization_started = None
                try:
                    await async_activate_persistent_calibration(
                        self.hass,
                        self._config_entry.runtime_data.api,
                        self._ph_saved_state,
                    )
                    self._start_calibration_guard(self._ph_saved_state)
                    await async_begin_bypassed_calibration(
                        self._config_entry.runtime_data.api
                    )
                except (SmartNextCommunicationError, OSError, TimeoutError):
                    self._ph_last_error = "communication"
                    return await self.async_step_calibrate_ph_standard_error()
                except GuidedCalibrationError as err:
                    self._ph_last_error = err.reason
                    return await self.async_step_calibrate_ph_standard_error()
                return await self.async_step_calibrate_orp_chain_ph7_immerse()
        return self.async_show_form(
            step_id="calibrate_orp_chain_ph",
            data_schema=vol.Schema(
                {vol.Required("orp_reinstalled", default=False): bool}
            ),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Final hydraulic restoration: restore flow first, then production.
    # ------------------------------------------------------------------

    async def async_step_calibrate_ph_standard_restore_filtration(
        self, user_input=None
    ):
        if user_input is not None and user_input.get("filtration_on", False):
            self._stop_calibration_guard()
        result = await super().async_step_calibrate_ph_standard_restore_filtration(
            user_input
        )
        if self._ph_saved_state is None:
            await async_clear_persistent_calibration(
                self.hass, self._config_entry.runtime_data.api
            )
        return result

    async def async_step_calibrate_orp_restore_filtration(self, user_input=None):
        if user_input is not None and user_input.get("filtration_on", False):
            self._stop_calibration_guard()
        result = await super().async_step_calibrate_orp_restore_filtration(user_input)
        if self._orp_saved_state is None:
            await async_clear_persistent_calibration(
                self.hass, self._config_entry.runtime_data.api
            )
        return result
