sed: --: No such file or directory
"""Data update coordinator for SmartNext."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SmartNextApi, SmartNextCommunicationError
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

    async def _async_update_data(self) -> dict:
        try:
            return await self.api.async_read_all()
        except SmartNextCommunicationError as err:
            raise UpdateFailed(str(err)) from err
