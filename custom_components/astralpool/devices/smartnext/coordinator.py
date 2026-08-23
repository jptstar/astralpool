"""Data update coordinator for SmartNext."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SmartNextApi, SmartNextCommunicationError
from .calibration_debug import async_read_calibration_debug
from .calibration_session import async_recover_interrupted_calibration
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SmartNextCoordinator(DataUpdateCoordinator[dict]):
    """Coordinate SmartNext polling."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: SmartNextApi,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self._calibration_recovery_checked = False

    async def _async_update_data(self) -> dict:
        try:
            # An options flow cannot survive an HA restart/reload. If a guided
            # pH/ORP session had disabled the logical flow inputs, restore their
            # saved state before normal polling resumes. Production deliberately
            # remains at 0 % after this emergency recovery.
            if not self._calibration_recovery_checked:
                await async_recover_interrupted_calibration(self.hass, self.api)
                self._calibration_recovery_checked = True

            data = await self.api.async_read_all()
            data.update(await async_read_calibration_debug(self.api, data))
            return data
        except SmartNextCommunicationError as err:
            raise UpdateFailed(str(err)) from err
