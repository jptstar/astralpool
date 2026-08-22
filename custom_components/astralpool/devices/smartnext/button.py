"""Buttons for SmartNext."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import SmartNextEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up SmartNext buttons."""
    async_add_entities(
        [
            SmartNextPhPumpStopResetButton(
                entry.runtime_data,
                entry.entry_id,
                entry.data["host"],
            )
        ]
    )


class SmartNextPhPumpStopResetButton(SmartNextEntity, ButtonEntity):
    """Rearm the pH pump-stop."""

    _attr_translation_key = "reset_ph_pump_stop"

    def __init__(self, coordinator, entry_id: str, host: str) -> None:
        super().__init__(coordinator, entry_id, host)
        self._attr_unique_id = f"{entry_id}_reset_ph_pump_stop"

    async def async_press(self) -> None:
        await self.coordinator.api.async_reset_ph_pump_stop()
        await self.coordinator.async_request_refresh()
