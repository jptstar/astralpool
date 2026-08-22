"""Buttons for SmartNext."""

from __future__ import annotations

import asyncio

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    COIL_FLOW_CONFIG_RESET,
    COIL_ORP_CALIBRATION_RESET,
    COIL_ORP_CONFIG_RESET,
    COIL_PH_CALIBRATION_RESET,
    COIL_PH_CONFIG_RESET,
    COIL_SALT_CONFIG_RESET,
    COIL_TEMPERATURE_CONFIG_RESET,
)
from .entity import SmartNextEntity

_RESET_BUTTONS: tuple[tuple[str, str, int, str | None], ...] = (
    ("reset_flow_config", "Flow · reset configuration", COIL_FLOW_CONFIG_RESET, None),
    (
        "reset_ph_config",
        "pH · reset configuration",
        COIL_PH_CONFIG_RESET,
        "technology_ph_implemented",
    ),
    (
        "reset_ph_calibration",
        "pH · reset calibration",
        COIL_PH_CALIBRATION_RESET,
        "technology_ph_implemented",
    ),
    (
        "reset_orp_config",
        "ORP · reset configuration",
        COIL_ORP_CONFIG_RESET,
        "technology_orp_implemented",
    ),
    (
        "reset_orp_calibration",
        "ORP · reset calibration",
        COIL_ORP_CALIBRATION_RESET,
        "technology_orp_implemented",
    ),
    (
        "reset_temperature_config",
        "Temperature · reset configuration",
        COIL_TEMPERATURE_CONFIG_RESET,
        "technology_temperature_implemented",
    ),
    (
        "reset_salt_config",
        "Salinity · reset configuration",
        COIL_SALT_CONFIG_RESET,
        "technology_salt_implemented",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up SmartNext buttons."""
    coordinator = entry.runtime_data
    host = entry.data["host"]
    entities: list[ButtonEntity] = [
        SmartNextPhPumpStopResetButton(coordinator, entry.entry_id, host)
    ]

    for key, name, coil, capability in _RESET_BUTTONS:
        if capability is not None and not coordinator.data.get(capability, False):
            continue
        entities.append(
            SmartNextMaintenanceResetButton(
                coordinator,
                entry.entry_id,
                host,
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


class SmartNextMaintenanceResetButton(SmartNextEntity, ButtonEntity):
    """Run one documented Smart Next maintenance reset command."""

    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:restore"

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
        """Pulse the documented volatile reset coil."""
        await self.coordinator.api.async_write_coil(self._coil, True)
        await asyncio.sleep(0.2)
        await self.coordinator.api.async_write_coil(self._coil, False)
        await self.coordinator.async_request_refresh()
