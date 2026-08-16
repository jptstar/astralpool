"""Base entity for ElyoTouch."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import ElyoTouchCoordinator


class ElyoTouchEntity(CoordinatorEntity[ElyoTouchCoordinator]):
    """Base class for ElyoTouch entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ElyoTouchCoordinator, entry_id: str, host: str) -> None:
        super().__init__(coordinator)
        device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name="AstralPool Pro Elyo Touch",
            configuration_url=f"http://{host}",
        )
        if firmware_version := coordinator.data.get("firmware_version"):
            device_info["sw_version"] = str(firmware_version)
        if hardware_version := coordinator.data.get("hardware_version"):
            device_info["hw_version"] = str(hardware_version)
        if serial_number := coordinator.data.get("serial_number"):
            device_info["serial_number"] = str(serial_number)
        self._attr_device_info = device_info
