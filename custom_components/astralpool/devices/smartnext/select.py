"""Select entities for SmartNext."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import SmartNextEntity

OPTIONS_TO_SECONDS = {
    "off": 0,
    "seconds_60": 60,
    "seconds_120": 120,
    "seconds_240": 240,
}
SECONDS_TO_OPTIONS = {value: key for key, value in OPTIONS_TO_SECONDS.items()}

POLARITY_OPTIONS_TO_HOURS = {
    "hours_2": 2,
    "hours_3": 3,
    "hours_4": 4,
    "hours_7": 7,
}
POLARITY_HOURS_TO_OPTIONS = {
    value: key for key, value in POLARITY_OPTIONS_TO_HOURS.items()
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up SmartNext select entities."""
    async_add_entities(
        [
            SmartNextPhInitializationSelect(
                entry.runtime_data,
                entry.entry_id,
                entry.data["host"],
            ),
            SmartNextPolarityReversalSelect(
                entry.runtime_data,
                entry.entry_id,
                entry.data["host"],
            ),
        ]
    )


class SmartNextPhInitializationSelect(SmartNextEntity, SelectEntity):
    """Select the pH initialization time."""

    _attr_translation_key = "ph_initialization_time"
    _attr_options = list(OPTIONS_TO_SECONDS)

    def __init__(self, coordinator, entry_id: str, host: str) -> None:
        super().__init__(coordinator, entry_id, host)
        self._attr_unique_id = f"{entry_id}_ph_initialization_time"

    @property
    def current_option(self) -> str | None:
        value = self.coordinator.data.get("ph_init_time")
        return SECONDS_TO_OPTIONS.get(value)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.api.async_set_ph_init_time(OPTIONS_TO_SECONDS[option])
        await self.coordinator.async_request_refresh()


class SmartNextPolarityReversalSelect(SmartNextEntity, SelectEntity):
    """Select the electrolysis polarity reversal period."""

    _attr_translation_key = "polarity_reversal_period"
    _attr_options = list(POLARITY_OPTIONS_TO_HOURS)
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = True

    def __init__(self, coordinator, entry_id: str, host: str) -> None:
        super().__init__(coordinator, entry_id, host)
        self._attr_unique_id = f"{entry_id}_polarity_reversal_period"

    @property
    def current_option(self) -> str | None:
        value = self.coordinator.data.get("polarity_reversal_period")
        return POLARITY_HOURS_TO_OPTIONS.get(value)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.api.async_set_polarity_reversal_period(
            POLARITY_OPTIONS_TO_HOURS[option]
        )
        await self.coordinator.async_request_refresh()
