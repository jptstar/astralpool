"""Safety refinements for the guided Smart Next pH/ORP calibration UI."""

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
    async_trigger_orp_470,
    async_trigger_ph4,
    async_trigger_ph7,
)
from .guided_options import (
    SmartNextGuidedCalibrationOptionsMixin as _BaseGuidedCalibrationOptionsMixin,
)

STABILIZATION_SECONDS: Final = 60.0


class SmartNextGuidedCalibrationOptionsMixin(_BaseGuidedCalibrationOptionsMixin):
    """Apply hardware feedback discovered during final pH/ORP validation.

    Important safety rules:
    - terminal success/error is allowed to leave 0x201 OFF;
    - electrolysis stays independently locked at 0 % until hydraulics are restored;
    - 0x201 is only started again for an explicit retry;
    - pH 7, pH 4 and ORP 470 mV require at least 60 seconds of stabilization.
    """

    _ph7_stabilization_started: float | None = None
    _ph4_stabilization_started: float | None = None
    _orp_stabilization_started: float | None = None

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

    async def async_step_calibrate_ph_standard_drain_pulse(self, user_input=None):
        """Finish hydraulic preparation without entering 0x201 yet."""
        if self._ph_saved_state is None:
            return await self.async_step_calibrate_ph_standard_prepare()
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("drain_done", False):
                errors["base"] = "confirmation_required"
            else:
                self._ph7_stabilization_started = None
                self._ph4_stabilization_started = None
                return await self.async_step_calibrate_ph_standard_ph7()
        return self.async_show_form(
            step_id="calibrate_ph_standard_drain_pulse",
            data_schema=vol.Schema({vol.Required("drain_done", default=False): bool}),
            errors=errors,
        )

    async def async_step_calibrate_ph_standard_ph7(self, user_input=None):
        """Require a full 60-second pH 7 stabilization before 201/203/50D."""
        if self._ph_saved_state is None:
            return await self.async_step_calibrate_ph_standard_prepare()

        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("stable", False):
                errors["base"] = "confirmation_required"
            elif self._ph7_stabilization_started is None:
                # First confirmation means the cleaned probe is now immersed.
                # Keep 0x201 OFF during stabilization; the independent 0 % lock
                # already protects the isolated electrolyzer.
                self._ph7_stabilization_started = self._now()
                errors["base"] = "stabilization_wait"
            elif self._now() - self._ph7_stabilization_started < STABILIZATION_SECONDS:
                errors["base"] = "stabilization_wait"
            else:
                try:
                    # Enter calibration only after the one-minute stabilization.
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
                    self._ph4_stabilization_started = None
                    return await self.async_step_calibrate_ph_standard_ph4()
                self._ph_last_error = response
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
        """Require a full 60-second pH 4 stabilization before 0x50E."""
        if self._ph_saved_state is None:
            return await self.async_step_calibrate_ph_standard_prepare()

        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("stable", False):
                errors["base"] = "confirmation_required"
            elif self._ph4_stabilization_started is None:
                # 0x201 intentionally remains active after the accepted pH 7
                # first point (IR22 = 16), preserving the two-point session.
                self._ph4_stabilization_started = self._now()
                errors["base"] = "stabilization_wait"
            elif self._now() - self._ph4_stabilization_started < STABILIZATION_SECONDS:
                errors["base"] = "stabilization_wait"
            else:
                try:
                    response = await async_trigger_ph4(
                        self._config_entry.runtime_data.api
                    )
                    await self._config_entry.runtime_data.async_request_refresh()
                except (SmartNextCommunicationError, OSError, TimeoutError):
                    self._ph_last_error = "communication"
                    return await self.async_step_calibrate_ph_standard_error()
                except GuidedCalibrationError as err:
                    self._ph_last_error = err.reason
                    return await self.async_step_calibrate_ph_standard_error()

                self._ph4_stabilization_started = None
                if response == RESPONSE_OK:
                    # Do not re-arm 0x201 here. The controller has completed the
                    # calibration; persistent 0 % production protects restoration.
                    return await self.async_step_calibrate_ph_standard_restore()
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
        """Leave terminal 0x201 state untouched; persistent 0 % remains active."""
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
        """Restart only when the user explicitly chooses Retry."""
        if self._ph_saved_state is None:
            return await self.async_step_calibrate_ph_standard_prepare()
        self._ph_last_error = None
        self._ph7_stabilization_started = None
        self._ph4_stabilization_started = None
        # A fresh 0x201 -> 0x203 session will be started after the new pH 7
        # solution has stabilized for a full minute.
        return await self.async_step_calibrate_ph_standard_ph7()

    async def async_step_calibrate_orp_drain_pulse(self, user_input=None):
        """Finish ORP hydraulic preparation without entering 0x201 yet."""
        if self._orp_saved_state is None:
            return await self.async_step_calibrate_orp_prepare()
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("drain_done", False):
                errors["base"] = "confirmation_required"
            else:
                self._orp_stabilization_started = None
                return await self.async_step_calibrate_orp_470()
        return self.async_show_form(
            step_id="calibrate_orp_drain_pulse",
            data_schema=vol.Schema({vol.Required("drain_done", default=False): bool}),
            errors=errors,
        )

    async def async_step_calibrate_orp_470(self, user_input=None):
        """Require a full 60-second 470 mV stabilization before 201/203/80F."""
        if self._orp_saved_state is None:
            return await self.async_step_calibrate_orp_prepare()

        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("stable", False):
                errors["base"] = "confirmation_required"
            elif self._orp_stabilization_started is None:
                self._orp_stabilization_started = self._now()
                errors["base"] = "stabilization_wait"
            elif self._now() - self._orp_stabilization_started < STABILIZATION_SECONDS:
                errors["base"] = "stabilization_wait"
            else:
                try:
                    # Keep 0x201 OFF while the ORP probe stabilizes. Once the
                    # minute is complete, execute 201 -> 203 -> 80F immediately.
                    await async_begin_bypassed_calibration(
                        self._config_entry.runtime_data.api
                    )
                    response = await async_trigger_orp_470(
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
                if response == RESPONSE_OK:
                    # Critical: do not re-arm 0x201 after the accepted 470 mV
                    # calibration. The 0 % lock stays active until restoration.
                    return await self.async_step_calibrate_orp_restore()
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
        """Do not re-arm 0x201 after a terminal ORP error."""
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
        """Restart ORP only after an explicit user retry."""
        if self._orp_saved_state is None:
            return await self.async_step_calibrate_orp_prepare()
        self._orp_last_error = None
        self._orp_stabilization_started = None
        return await self.async_step_calibrate_orp_470()
