sed: --: No such file or directory
"""Writable SmartNext settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import SmartNextEntity

Setter = Callable[[float], Awaitable[None]]


@dataclass(frozen=True, kw_only=True)
class SmartNextNumberDescription(NumberEntityDescription):
    """Describe a SmartNext number."""

    data_key: str
    setter_name: str


NUMBERS: tuple[SmartNextNumberDescription, ...] = (
    SmartNextNumberDescription(
        key="temperature_min_setpoint",
        translation_key="temperature_min_setpoint",
        data_key="temperature_min",
        setter_name="async_set_temperature_min",
        native_min_value=0,
        native_max_value=60,
        native_step=0.1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    SmartNextNumberDescription(
        key="temperature_max_setpoint",
        translation_key="temperature_max_setpoint",
        data_key="temperature_max",
        setter_name="async_set_temperature_max",
        native_min_value=0,
        native_max_value=60,
        native_step=0.1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    SmartNextNumberDescription(
        key="ph_setpoint",
        translation_key="ph_setpoint",
        data_key="ph_setpoint",
        setter_name="async_set_ph",
        native_min_value=6.5,
        native_max_value=8.5,
        native_step=0.01,
    ),
    SmartNextNumberDescription(
        key="ph_dosage_limit",
        translation_key="ph_dosage_limit",
        data_key="ph_dosage_limit",
        setter_name="async_set_ph_dosage_limit",
        native_min_value=0,
        native_max_value=120,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
    ),
    SmartNextNumberDescription(
        key="orp_setpoint",
        translation_key="orp_setpoint",
        data_key="orp_setpoint",
        setter_name="async_set_orp",
        native_min_value=300,
        native_max_value=850,
        native_step=1,
        native_unit_of_measurement="mV",
    ),
    SmartNextNumberDescription(
        key="electrolysis_normal_setpoint",
        translation_key="electrolysis_normal_setpoint",
        data_key="electrolysis_normal_setpoint",
        setter_name="async_set_electrolysis_normal",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
    ),
    SmartNextNumberDescription(
        key="electrolysis_cover_setpoint",
        translation_key="electrolysis_cover_setpoint",
        data_key="electrolysis_cover_setpoint",
        setter_name="async_set_electrolysis_cover",
        native_min_value=10,
        native_max_value=90,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up SmartNext number entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        SmartNextNumber(
            coordinator,
            entry.entry_id,
            entry.data["host"],
            description,
        )
        for description in NUMBERS
    )


class SmartNextNumber(SmartNextEntity, NumberEntity):
    """Representation of a writable SmartNext setting."""

    entity_description: SmartNextNumberDescription

    def __init__(self, coordinator, entry_id: str, host: str, description) -> None:
        super().__init__(coordinator, entry_id, host)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.data.get(self.entity_description.data_key)
        return float(value) if value is not None else None

    @property
    def native_min_value(self) -> float:
        """Return the protocol-valid minimum for the active operating mode."""
        biopool = bool(self.coordinator.data.get("biopool_mode"))

        if self.entity_description.key == "ph_setpoint":
            return 6.5 if biopool else 7.0
        if self.entity_description.key == "orp_setpoint":
            return 300.0 if biopool else 600.0

        return float(self.entity_description.native_min_value)

    @property
    def native_max_value(self) -> float:
        """Return the protocol-valid maximum for the active operating mode."""
        if self.entity_description.key == "ph_setpoint":
            return 8.5 if self.coordinator.data.get("biopool_mode") else 7.8

        return float(self.entity_description.native_max_value)

    async def async_set_native_value(self, value: float) -> None:
        if value < self.native_min_value or value > self.native_max_value:
            raise ValueError(
                f"{self.entity_description.key} value {value} outside "
                f"active-mode range {self.native_min_value}..{self.native_max_value}"
            )

        setter: Setter = getattr(
            self.coordinator.api,
            self.entity_description.setter_name,
        )
        await setter(value)
        await self.coordinator.async_request_refresh()
