"""Base entity for SmartNext."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import SmartNextCoordinator


class SmartNextEntity(CoordinatorEntity[SmartNextCoordinator]):
    """Base class for SmartNext entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SmartNextCoordinator, entry_id: str, host: str) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name="SmartNext",
            configuration_url=f"http://{host}",
        )
