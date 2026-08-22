"""Sensors for SmartNext."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .calibration_debug import CALIBRATION_RESPONSE_MEANINGS
from .entity import SmartNextEntity


@dataclass(frozen=True, kw_only=True)
class SmartNextSensorDescription(SensorEntityDescription):
    """Describe a SmartNext sensor."""

    data_key: str


SENSORS: tuple[SmartNextSensorDescription, ...] = (
    SmartNextSensorDescription(
        key="calibration_response_raw",
        name="Calibration TEST · Réponse brute IR 0x22",
        data_key="calibration_response_raw",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
        icon="mdi:message-reply-text-outline",
    ),
    SmartNextSensorDescription(
        key="electrolysis_rated_capacity",
        translation_key="electrolysis_rated_capacity",
        data_key="product_capacity",
        native_unit_of_measurement="g/h",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SmartNextSensorDescription(
        key="boost_remaining_time",
        translation_key="boost_remaining_time",
        data_key="boost_remaining_time",
        native_unit_of_measurement=UnitOfTime.MINUTES,
    ),
    SmartNextSensorDescription(
        key="temperature",
        translation_key="temperature",
        data_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SmartNextSensorDescription(
        key="temperature_min",
        translation_key="temperature_min",
        data_key="temperature_min",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SmartNextSensorDescription(
        key="temperature_max",
        translation_key="temperature_max",
        data_key="temperature_max",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SmartNextSensorDescription(
        key="salt",
        translation_key="salt",
        data_key="salt",
        native_unit_of_measurement="g/L",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SmartNextSensorDescription(
        key="salt_min",
        translation_key="salt_min",
        data_key="salt_min",
        native_unit_of_measurement="g/L",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SmartNextSensorDescription(
        key="salt_max",
        translation_key="salt_max",
        data_key="salt_max",
        native_unit_of_measurement="g/L",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SmartNextSensorDescription(
        key="ph",
        translation_key="ph",
        data_key="ph",
        device_class=SensorDeviceClass.PH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SmartNextSensorDescription(
        key="ph_low_alarm_limit",
        translation_key="ph_low_alarm_limit",
        data_key="ph_low_alarm_limit",
        device_class=SensorDeviceClass.PH,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SmartNextSensorDescription(
        key="ph_high_alarm_limit",
        translation_key="ph_high_alarm_limit",
        data_key="ph_high_alarm_limit",
        device_class=SensorDeviceClass.PH,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SmartNextSensorDescription(
        key="ph_dosage_elapsed",
        translation_key="ph_dosage_elapsed",
        data_key="ph_dosage_elapsed",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SmartNextSensorDescription(
        key="ph_pump_output",
        translation_key="ph_pump_output",
        data_key="ph_pump_output",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SmartNextSensorDescription(
        key="ph_total_hours",
        translation_key="ph_total_hours",
        data_key="ph_total_hours",
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SmartNextSensorDescription(
        key="ph_partial_hours",
        translation_key="ph_partial_hours",
        data_key="ph_partial_hours",
        native_unit_of_measurement=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SmartNextSensorDescription(
        key="orp",
        translation_key="orp",
        data_key="orp",
        native_unit_of_measurement="mV",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SmartNextSensorDescription(
        key="orp_low_alarm_limit",
        translation_key="orp_low_alarm_limit",
        data_key="orp_low_alarm_limit",
        native_unit_of_measurement="mV",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SmartNextSensorDescription(
        key="orp_high_alarm_limit",
        translation_key="orp_high_alarm_limit",
        data_key="orp_high_alarm_limit",
        native_unit_of_measurement="mV",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SmartNextSensorDescription(
        key="electrolysis_functional_target",
        translation_key="electrolysis_functional_target",
        data_key="electrolysis_functional_target",
        native_unit_of_measurement=PERCENTAGE,
    ),
    SmartNextSensorDescription(
        key="electrolysis_production",
        translation_key="electrolysis_production",
        data_key="electrolysis_production",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SmartNextSensorDescription(
        key="electrolysis_current",
        translation_key="electrolysis_current",
        data_key="electrolysis_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SmartNextSensorDescription(
        key="electrolysis_voltage",
        translation_key="electrolysis_voltage",
        data_key="electrolysis_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SmartNextSensorDescription(
        key="electrolysis_chlorine_production",
        translation_key="electrolysis_chlorine_production",
        data_key="electrolysis_chlorine_production",
        native_unit_of_measurement="g/h",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SmartNextSensorDescription(
        key="electrolysis_total_hours",
        translation_key="electrolysis_total_hours",
        data_key="electrolysis_total_hours",
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SmartNextSensorDescription(
        key="electrolysis_partial_hours",
        translation_key="electrolysis_partial_hours",
        data_key="electrolysis_partial_hours",
        native_unit_of_measurement=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up SmartNext sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        SmartNextSensor(
            coordinator,
            entry.entry_id,
            entry.data["host"],
            description,
        )
        for description in SENSORS
    )


class SmartNextSensor(SmartNextEntity, SensorEntity):
    """Representation of a SmartNext sensor."""

    entity_description: SmartNextSensorDescription

    def __init__(self, coordinator, entry_id: str, host: str, description) -> None:
        super().__init__(coordinator, entry_id, host)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.get(self.entity_description.data_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose the documented meaning of the raw calibration response."""
        if self.entity_description.key != "calibration_response_raw":
            return None
        value = self.coordinator.data.get("calibration_response_raw")
        if value is None:
            return None
        return {
            "signification": CALIBRATION_RESPONSE_MEANINGS.get(
                int(value), f"Réponse inconnue {value}"
            )
        }
