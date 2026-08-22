"""Final safety layer for guided Smart Next pH/ORP calibration."""

from __future__ import annotations

import asyncio
from typing import Final

import voluptuous as vol

from .api import SmartNextCommunicationError
from .guided_calibration import (
    RESPONSE_FIRST_POINT_OK,
    RESPONSE_OK,
    GuidedCalibrationError,
    async_begin_bypassed_calibration,
    async_confirm_filtration_stopped,
    async_restore_flow_sensors_immediately,
    async_trigger_orp_470,
    async_trigger_ph4,
    async_trigger_ph7,
)
from .guided_options import (
    SmartNextGuidedCalibrationOptionsMixin as _BaseGuidedCalibrationOptionsMixin,
)

STABILIZATION_SECONDS: Final = 60.0


class SmartNextGuidedCalibrationOptionsMixin(_BaseGuidedCalibrationOptionsMixin):
    """Apply the hardware-validated pH/ORP workflow and physical safeguards."""

    _ph7_stabilization_started: float | None = None
    _ph4_stabilization_started: float | None = None
    _orp_stabilization_started: float | None = None
    _calibration_chain_origin: str | None = None

    @staticmethod
    def _now() -> float:
        return asyncio.get_running_loop().time()

    @staticmethod
    def _remaining_seconds(started: float | None) -> int:
        if started is None:
            return int(STABILIZATION_SECONDS)
        remaining = STABILIZATION_SECONDS - (
            asyncio.get_running_loop().time() - started
        )
        return max(0, int(remaining + 0.999))

    async def _async_terminal_flow_restore(self, saved_state) -> str | None:
        """Restore flow sensors immediately after success/error and verify pH pump."""
        try:
            await async_restore_flow_sensors_immediately(
                self._config_entry.runtime_data.api, saved_state
            )
            await self._config_entry.runtime_data.async_request_refresh()
        except (SmartNextCommunicationError, OSError, TimeoutError):
            return "communication"
        except GuidedCalibrationError as err:
            return err.reason
        return None

    # ------------------------------------------------------------------
    # Common physical safety: filtration OFF must really stop pH dosing.
    # ------------------------------------------------------------------

    async def async_step_calibrate_ph_standard_filtration_off(self, user_input=None):
        if self._ph_saved_state is None:
            return await self.async_step_calibrate_ph_standard_prepare()
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("filtration_off", False):
                errors["base"] = "confirmation_required"
            else:
                try:
                    await async_confirm_filtration_stopped(
                        self._config_entry.runtime_data.api
                    )
                except (SmartNextCommunicationError, OSError, TimeoutError):
                    errors["base"] = "calibration_communication_failed"
                except GuidedCalibrationError as err:
                    errors["base"] = err.reason
                else:
                    return await self.async_step_calibrate_ph_standard_bypass_open()
        return self.async_show_form(
            step_id="calibrate_ph_standard_filtration_off",
            data_schema=vol.Schema(
                {vol.Required("filtration_off", default=False): bool}
            ),
            errors=errors,
        )

    async def async_step_calibrate_orp_filtration_off(self, user_input=None):
        if self._orp_saved_state is None:
            return await self.async_step_calibrate_orp_prepare()
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("filtration_off", False):
                errors["base"] = "confirmation_required"
            else:
                try:
                    await async_confirm_filtration_stopped(
                        self._config_entry.runtime_data.api
                    )
                except (SmartNextCommunicationError, OSError, TimeoutError):
                    errors["base"] = "calibration_communication_failed"
                except GuidedCalibrationError as err:
                    errors["base"] = err.reason
                else:
                    return await self.async_step_calibrate_orp_bypass_open()
        return self.async_show_form(
            step_id="calibrate_orp_filtration_off",
            data_schema=vol.Schema(
                {vol.Required("filtration_off", default=False): bool}
            ),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # pH Standard: explicit immersion + mandatory 60 s + stable checkbox.
    # ------------------------------------------------------------------

    async def async_step_calibrate_ph_standard_drain_pulse(self, user_input=None):
        """Finish hydraulic preparation; do not enter 0x201 yet."""
        if self._ph_saved_state is None:
            return await self.async_step_calibrate_ph_standard_prepare()
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("drain_done", False):
                errors["base"] = "confirmation_required"
            else:
                self._ph7_stabilization_started = None
                self._ph4_stabilization_started = None
                return await self.async_step_calibrate_ph_standard_ph7_immerse()
        return self.async_show_form(
            step_id="calibrate_ph_standard_drain_pulse",
            data_schema=vol.Schema({vol.Required("drain_done", default=False): bool}),
            errors=errors,
        )

    async def async_step_calibrate_ph_standard_ph7_immerse(self, user_input=None):
        if self._ph_saved_state is None:
            return await self.async_step_calibrate_ph_standard_prepare()
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("immersed", False):
                errors["base"] = "confirmation_required"
            else:
                self._ph7_stabilization_started = self._now()
                return await self.async_step_calibrate_ph_standard_ph7()
        return self.async_show_form(
            step_id="calibrate_ph_standard_ph7_immerse",
            data_schema=vol.Schema({vol.Required("immersed", default=False): bool}),
            errors=errors,
        )

    async def async_step_calibrate_ph_standard_ph7(self, user_input=None):
        """Block pH 7 validation until at least 60 seconds have elapsed."""
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
                    self._ph_last_error = "communication"
                    return await self.async_step_calibrate_ph_standard_error()
                except GuidedCalibrationError as err:
                    self._ph_last_error = err.reason
                    return await self.async_step_calibrate_ph_standard_error()

                self._ph7_stabilization_started = None
                if response == RESPONSE_FIRST_POINT_OK:
                    return await self.async_step_calibrate_ph_standard_ph4_immerse()

                # pH 7 errors are terminal on the real controller. Restore flow
                # supervision immediately because 0x201 may already be OFF.
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

    async def async_step_calibrate_ph_standard_ph4_immerse(self, user_input=None):
        if self._ph_saved_state is None:
            return await self.async_step_calibrate_ph_standard_prepare()
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("immersed", False):
                errors["base"] = "confirmation_required"
            else:
                self._ph4_stabilization_started = self._now()
                return await self.async_step_calibrate_ph_standard_ph4()
        return self.async_show_form(
            step_id="calibrate_ph_standard_ph4_immerse",
            data_schema=vol.Schema({vol.Required("immersed", default=False): bool}),
            errors=errors,
        )

    async def async_step_calibrate_ph_standard_ph4(self, user_input=None):
        """Block pH 4 validation until at least 60 seconds have elapsed."""
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
                    self._ph_last_error = "communication"
                    return await self.async_step_calibrate_ph_standard_error()
                except GuidedCalibrationError as err:
                    self._ph_last_error = err.reason
                    return await self.async_step_calibrate_ph_standard_error()

                self._ph4_stabilization_started = None
                safety_error = await self._async_terminal_flow_restore(
                    self._ph_saved_state
                )
                self._ph_last_error = safety_error
                if safety_error is not None:
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

    async def async_step_calibrate_ph_standard_error(self, user_input=None):
        """Never automatically re-enter 0x201 after a terminal pH result."""
        if self._ph_saved_state is None:
            return await self.async_step_calibrate_ph_standard_prepare()
        return self.async_show_menu(
            step_id="calibrate_ph_standard_error",
            menu_options={
                "calibrate_ph_standard_retry": "Recommencer depuis le point pH 7",
                "calibrate_ph_standard_restore": "Terminer et rétablir l’installation",
            },
            description_placeholders={"error": self._response_text(self._ph_last_error)},
        )

    async def async_step_calibrate_ph_standard_retry(self, user_input=None):
        """Restart pH only after the user explicitly chooses Retry."""
        if self._ph_saved_state is None:
            return await self.async_step_calibrate_ph_standard_prepare()
        self._ph_last_error = None
        self._ph7_stabilization_started = None
        self._ph4_stabilization_started = None
        return await self.async_step_calibrate_ph_standard_ph7_immerse()

    # ------------------------------------------------------------------
    # ORP: explicit immersion + mandatory 60 s + stable checkbox.
    # ------------------------------------------------------------------

    async def async_step_calibrate_orp_drain_pulse(self, user_input=None):
        """Finish ORP hydraulic preparation; do not enter 0x201 yet."""
        if self._orp_saved_state is None:
            return await self.async_step_calibrate_orp_prepare()
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("drain_done", False):
                errors["base"] = "confirmation_required"
            else:
                self._orp_stabilization_started = None
                return await self.async_step_calibrate_orp_immerse()
        return self.async_show_form(
            step_id="calibrate_orp_drain_pulse",
            data_schema=vol.Schema({vol.Required("drain_done", default=False): bool}),
            errors=errors,
        )

    async def async_step_calibrate_orp_immerse(self, user_input=None):
        if self._orp_saved_state is None:
            return await self.async_step_calibrate_orp_prepare()
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("immersed", False):
                errors["base"] = "confirmation_required"
            else:
                self._orp_stabilization_started = self._now()
                return await self.async_step_calibrate_orp_470()
        return self.async_show_form(
            step_id="calibrate_orp_immerse",
            data_schema=vol.Schema({vol.Required("immersed", default=False): bool}),
            errors=errors,
        )

    async def async_step_calibrate_orp_470(self, user_input=None):
        """Block 470 mV calibration until the probe has stabilized for 60 seconds."""
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
                    self._orp_last_error = "communication"
                    return await self.async_step_calibrate_orp_error()
                except GuidedCalibrationError as err:
                    self._orp_last_error = err.reason
                    return await self.async_step_calibrate_orp_error()

                self._orp_stabilization_started = None
                safety_error = await self._async_terminal_flow_restore(
                    self._orp_saved_state
                )
                self._orp_last_error = safety_error
                if safety_error is not None:
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

    async def async_step_calibrate_orp_error(self, user_input=None):
        """Never automatically re-enter 0x201 after a terminal ORP result."""
        if self._orp_saved_state is None:
            return await self.async_step_calibrate_orp_prepare()
        return self.async_show_menu(
            step_id="calibrate_orp_error",
            menu_options={
                "calibrate_orp_retry": "Réessayer à 470 mV",
                "calibrate_orp_restore": "Terminer et rétablir l’installation",
            },
            description_placeholders={"error": self._response_text(self._orp_last_error)},
        )

    async def async_step_calibrate_orp_retry(self, user_input=None):
        if self._orp_saved_state is None:
            return await self.async_step_calibrate_orp_prepare()
        self._orp_last_error = None
        self._orp_stabilization_started = None
        return await self.async_step_calibrate_orp_immerse()

    # ------------------------------------------------------------------
    # Chaining: calibrate the other probe without reopening the hydraulics.
    # ------------------------------------------------------------------

    async def async_step_calibrate_ph_standard_next_sensor(self, user_input=None):
        """After pH success, offer ORP while the cell is still isolated."""
        if self._ph_saved_state is None:
            return await self.async_step_calibrate_ph_standard_prepare()
        if not self._orp_available():
            return await self.async_step_calibrate_ph_standard_restore()
        return self.async_show_menu(
            step_id="calibrate_ph_standard_next_sensor",
            menu_options={
                "calibrate_ph_standard_chain_orp": "Oui · calibrer aussi le Redox / ORP",
                "calibrate_ph_standard_restore": "Non · terminer et rétablir l’installation",
            },
        )

    async def async_step_calibrate_ph_standard_chain_orp(self, user_input=None):
        """Reinstall the calibrated pH probe before removing the ORP probe."""
        if self._ph_saved_state is None:
            return await self.async_step_calibrate_ph_standard_prepare()
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("ph_reinstalled", False):
                errors["base"] = "confirmation_required"
            else:
                self._orp_saved_state = self._ph_saved_state
                self._ph_saved_state = None
                self._calibration_chain_origin = "ph"
                self._orp_stabilization_started = None
                return await self.async_step_calibrate_ph_standard_chain_orp_immerse()
        return self.async_show_form(
            step_id="calibrate_ph_standard_chain_orp",
            data_schema=vol.Schema(
                {vol.Required("ph_reinstalled", default=False): bool}
            ),
            errors=errors,
        )

    async def async_step_calibrate_ph_standard_chain_orp_immerse(
        self, user_input=None
    ):
        if self._orp_saved_state is None:
            return await self.async_step_calibrate_orp_prepare()
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("orp_immersed", False):
                errors["base"] = "confirmation_required"
            else:
                self._orp_stabilization_started = self._now()
                return await self.async_step_calibrate_orp_470()
        return self.async_show_form(
            step_id="calibrate_ph_standard_chain_orp_immerse",
            data_schema=vol.Schema(
                {vol.Required("orp_immersed", default=False): bool}
            ),
            errors=errors,
        )

    async def async_step_calibrate_orp_next_sensor(self, user_input=None):
        """After ORP success, offer pH while the cell is still isolated."""
        if self._orp_saved_state is None:
            return await self.async_step_calibrate_orp_prepare()
        if not self._ph_available():
            return await self.async_step_calibrate_orp_restore()
        return self.async_show_menu(
            step_id="calibrate_orp_next_sensor",
            menu_options={
                "calibrate_orp_chain_ph": "Oui · calibrer aussi le pH",
                "calibrate_orp_restore": "Non · terminer et rétablir l’installation",
            },
        )

    async def async_step_calibrate_orp_chain_ph(self, user_input=None):
        """Reinstall the calibrated ORP probe before removing the pH probe."""
        if self._orp_saved_state is None:
            return await self.async_step_calibrate_orp_prepare()
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
                return await self.async_step_calibrate_orp_chain_ph7_immerse()
        return self.async_show_form(
            step_id="calibrate_orp_chain_ph",
            data_schema=vol.Schema(
                {vol.Required("orp_reinstalled", default=False): bool}
            ),
            errors=errors,
        )

    async def async_step_calibrate_orp_chain_ph7_immerse(self, user_input=None):
        if self._ph_saved_state is None:
            return await self.async_step_calibrate_ph_standard_prepare()
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("ph_immersed", False):
                errors["base"] = "confirmation_required"
            else:
                self._ph7_stabilization_started = self._now()
                return await self.async_step_calibrate_ph_standard_ph7()
        return self.async_show_form(
            step_id="calibrate_orp_chain_ph7_immerse",
            data_schema=vol.Schema(
                {vol.Required("ph_immersed", default=False): bool}
            ),
            errors=errors,
        )
