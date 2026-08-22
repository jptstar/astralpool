"""Buttons for SmartNext."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .calibration_debug import RAW_CALIBRATION_BUTTONS
from .entity import SmartNextEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up SmartNext buttons."""
    coordinator = entry.runtime_data
    entities: list[ButtonEntity] = [
        SmartNextPhPumpStopResetButton(
            coordinator,
            entry.entry_id,
            entry.data["host"],
        )
    ]

    for key, name, coil, capability in RAW_CALIBRATION_BUTTONS:
        if capability is not None and not coordinator.data.get(capability, False):
            continue
        entities.append(
            SmartNextRawCalibrationButton(
                coordinator,
                entry.entry_id,
                entry.data["host"],
                key,
                name,
                coil,
            )
        )

    async_add_entities(entities)


class SmartNextPhPumpStopResetButton(SmartNextEntity, ButtonEntity):
    """Rearm the pH pump-stop."""

    _attr_translation_key = "reset_ph_pump_stop"

    def __init__(self, coordinator, entry_id: str, host: str) -> None:
        super().__init__(coordinator, entry_id, host)
        self._attr_unique_id = f"{entry_id}_reset_ph_pump_stop"

    async def async_press(self) -> None:
        await self.coordinator.api.async_reset_ph_pump_stop()
        await self.coordinator.async_request_refresh()


class SmartNextRawCalibrationButton(SmartNextEntity, ButtonEntity):
    """Write a raw documented calibration command coil to 1."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:flask-outline"

    def __init__(
        self,
        coordinator,
        entry_id: str,
        host: str,
        key: str,
        name: str,
        coil: int,
    ) -> None:
        super().__init__(coordinator, entry_id, host)
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_name = name
        self._coil = coil

    async def async_press(self) -> None:
        """Send only the raw 1 command; do not add a hidden release step."""
        await self.coordinator.api.async_write_coil(self._coil, True)
        await self.coordinator.async_request_refresh()
