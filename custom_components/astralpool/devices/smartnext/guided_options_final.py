"""Final fail-safe overrides for Smart Next pH/ORP guided calibration."""

from __future__ import annotations

import voluptuous as vol

from .api import SmartNextCommunicationError
from .guided_calibration import (
    RESPONSE_FIRST_POINT_OK,
    RESPONSE_OK,
    GuidedCalibrationError,
    async_begin_bypassed_calibration,
    async_trigger_orp_470,
    async_trigger_ph4,
    async_trigger_ph7,
)
from .guided_options_safe import (
    STABILIZATION_SECONDS,
    SmartNextGuidedCalibrationOptionsMixin as _SafeGuidedCalibrationOptionsMixin,
)


class SmartNextGuidedCalibrationOptionsMixin(_SafeGuidedCalibrationOptionsMixin):
    """Guarantee immediate flow restoration even when Modbus actions fail."""

    async def _async_record_failure_and_restore(self, saved_state, reason) -> None:
        """Best-effort restore flow supervision before presenting an error."""
        safety_error = await self._async_terminal_flow_restore(saved_state)
        return safety_error or reason

    async def async_step_calibrate_ph_standard_ph7(self, user_input=None):
        if self._ph_saved_state is None:
            return await self.async_step_calibrate_ph_standard_prepare()
        if self._ph7_stabilization_started is None:
            return await self.async_step_calibrate_ph_standard_ph7_immerse()

        errors: dict[str, str] = {}
        if user_input is not None:
            elapsed = self._now() - self._ph7_stabilization_started
            if elapsed < STABILIZATION_SECONDS:
                errors["base"] = "stabilization_wait"
            elif not user_input.get("stable", False):
                errors["base"] = "measurement_not_confirmed_stable"
            else:
                try:
                    await async_begin_bypassed_calibration(
                        self._config_entry.runtime_data.api
                    )
                    response = await async_trigger_ph7(
                        self._config_entry.runtime_data.api
                    )
                    await self._config_entry.runtime_data.async_request_refresh()
                except (SmartNextCommunicationError, OSError, TimeoutError):
                    self._ph_last_error = await self._async_record_failure_and_restore(
                        self._ph_saved_state, "communication"
                    )
                    return await self.async_step_calibrate_ph_standard_error()
                except GuidedCalibrationError as err:
                    self._ph_last_error = await self._async_record_failure_and_restore(
                        self._ph_saved_state, err.reason
                    )
                    return await self.async_step_calibrate_ph_standard_error()

                self._ph7_stabilization_started = None
                if response == RESPONSE_FIRST_POINT_OK:
                    return await self.async_step_calibrate_ph_standard_ph4_immerse()

                self._ph_last_error = await self._async_record_failure_and_restore(
                    self._ph_saved_state, response
                )
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

        errors: dict[str, str] = {}
        if user_input is not None:
            elapsed = self._now() - self._ph4_stabilization_started
            if elapsed < STABILIZATION_SECONDS:
                errors["base"] = "stabilization_wait"
            elif not user_input.get("stable", False):
                errors["base"] = "measurement_not_confirmed_stable"
            else:
                try:
                    response = await async_trigger_ph4(
                        self._config_entry.runtime_data.api
                    )
                except (SmartNextCommunicationError, OSError, TimeoutError):
                    self._ph_last_error = await self._async_record_failure_and_restore(
                        self._ph_saved_state, "communication"
                    )
                    return await self.async_step_calibrate_ph_standard_error()
                except GuidedCalibrationError as err:
                    self._ph_last_error = await self._async_record_failure_and_restore(
                        self._ph_saved_state, err.reason
                    )
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

        errors: dict[str, str] = {}
        if user_input is not None:
            elapsed = self._now() - self._orp_stabilization_started
            if elapsed < STABILIZATION_SECONDS:
                errors["base"] = "stabilization_wait"
            elif not user_input.get("stable", False):
                errors["base"] = "measurement_not_confirmed_stable"
            else:
                try:
                    await async_begin_bypassed_calibration(
                        self._config_entry.runtime_data.api
                    )
                    response = await async_trigger_orp_470(
                        self._config_entry.runtime_data.api
                    )
                except (SmartNextCommunicationError, OSError, TimeoutError):
                    self._orp_last_error = await self._async_record_failure_and_restore(
                        self._orp_saved_state, "communication"
                    )
                    return await self.async_step_calibrate_orp_error()
                except GuidedCalibrationError as err:
                    self._orp_last_error = await self._async_record_failure_and_restore(
                        self._orp_saved_state, err.reason
                    )
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
