"""Binary sensors for SmartNext."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import SmartNextEntity


@dataclass(frozen=True, kw_only=True)
class SmartNextBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a SmartNext binary sensor."""

    data_key: str


PROBLEM_SENSORS = (
    "general_alarm",
    "flow_alarm",
    "internal_flow_alarm",
    "external_flow_switch_alarm",
    "electrolysis_check_cell_alarm",
    "electrolysis_low_conductivity_alarm",
    "electrolysis_high_conductivity_alarm",
    "ph_low_alarm",
    "ph_high_alarm",
    "ph_pump_stop_alarm",
    "ph_fuse_alarm",
    "orp_low_alarm",
    "orp_high_alarm",
    "temperature_low_alarm",
    "temperature_high_alarm",
    "salt_low_alarm",
    "salt_high_alarm",
    "ph_measure_unreliable",
    "orp_measure_unreliable",
    "temperature_measure_unreliable",
    "salt_measure_unreliable",
    "salt_current_insufficient",
    "salt_voltage_insufficient",
)

BINARY_SENSORS: tuple[SmartNextBinarySensorDescription, ...] = tuple(
    SmartNextBinarySensorDescription(
        key=key,
        translation_key=key,
        data_key=key,
        device_class=BinarySensorDeviceClass.PROBLEM,
    )
    for key in PROBLEM_SENSORS
) + (
    SmartNextBinarySensorDescription(
        key="treatment_halted",
        translation_key="treatment_halted",
        data_key="treatment_halted",
    ),
    SmartNextBinarySensorDescription(
        key="biopool_mode",
        translation_key="biopool_mode",
        data_key="biopool_mode",
    ),
    SmartNextBinarySensorDescription(
        key="electrolysis_running",
        translation_key="electrolysis_running",
        data_key="electrolysis_running",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    SmartNextBinarySensorDescription(
        key="electrolysis_reverse_polarity",
        translation_key="electrolysis_reverse_polarity",
        data_key="electrolysis_reverse_polarity",
    ),
    SmartNextBinarySensorDescription(
        key="cover_input",
        translation_key="cover_input",
        data_key="cover_input",
    ),
    SmartNextBinarySensorDescription(
        key="cover_active",
        translation_key="cover_active",
        data_key="cover_active",
    ),
    SmartNextBinarySensorDescription(
        key="ph_initializing",
        translation_key="ph_initializing",
        data_key="ph_initializing",
    ),
    SmartNextBinarySensorDescription(
        key="ph_dosing_active",
        translation_key="ph_dosing_active",
        data_key="ph_dosing_active",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up SmartNext binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        SmartNextBinarySensor(
            coordinator,
            entry.entry_id,
            entry.data["host"],
            description,
        )
        for description in BINARY_SENSORS
    )


class SmartNextBinarySensor(SmartNextEntity, BinarySensorEntity):
    """Representation of a SmartNext binary sensor."""

    entity_description: SmartNextBinarySensorDescription

    def __init__(self, coordinator, entry_id: str, host: str, description) -> None:
        super().__init__(coordinator, entry_id, host)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get(self.entity_description.data_key))
