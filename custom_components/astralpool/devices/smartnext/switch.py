"""Configuration switches for SmartNext."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import SmartNextEntity

Setter = Callable[[bool], Awaitable[None]]


@dataclass(frozen=True, kw_only=True)
class SmartNextSwitchDescription(SwitchEntityDescription):
    """Describe a SmartNext configuration switch."""

    data_key: str
    setter_name: str


SWITCHES: tuple[SmartNextSwitchDescription, ...] = (
    SmartNextSwitchDescription(
        key="boost_mode",
        translation_key="boost_mode",
        data_key="boost_mode",
        setter_name="async_set_boost_mode",
        entity_registry_enabled_default=True,
    ),
    SmartNextSwitchDescription(
        key="cover_control_enabled",
        translation_key="cover_control_enabled",
        data_key="cover_control_enabled",
        setter_name="async_set_cover_control_enabled",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SmartNextSwitchDescription(
        key="internal_orp_control_enabled",
        translation_key="internal_orp_control_enabled",
        data_key="internal_orp_control_enabled",
        setter_name="async_set_internal_orp_control_enabled",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SmartNextSwitchDescription(
        key="external_chlorine_control_enabled",
        translation_key="external_chlorine_control_enabled",
        data_key="external_chlorine_control_enabled",
        setter_name="async_set_external_chlorine_control_enabled",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SmartNextSwitchDescription(
        key="internal_flow_sensor_enabled",
        translation_key="internal_flow_sensor_enabled",
        data_key="internal_flow_sensor_enabled",
        setter_name="async_set_internal_flow_sensor_enabled",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SmartNextSwitchDescription(
        key="external_flow_sensor_enabled",
        translation_key="external_flow_sensor_enabled",
        data_key="external_flow_sensor_enabled",
        setter_name="async_set_external_flow_sensor_enabled",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SmartNextSwitchDescription(
        key="ph_intelligent_dosing_enabled",
        translation_key="ph_intelligent_dosing_enabled",
        data_key="ph_intelligent_dosing_enabled",
        setter_name="async_set_ph_intelligent_dosing_enabled",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SmartNextSwitchDescription(
        key="ph_pump_stop_enabled",
        translation_key="ph_pump_stop_enabled",
        data_key="ph_pump_stop_enabled",
        setter_name="async_set_ph_pump_stop_enabled",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SmartNextSwitchDescription(
        key="temperature_low_alarm_enabled",
        translation_key="temperature_low_alarm_enabled",
        data_key="temperature_low_alarm_enabled",
        setter_name="async_set_temperature_low_alarm_enabled",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SmartNextSwitchDescription(
        key="temperature_high_alarm_enabled",
        translation_key="temperature_high_alarm_enabled",
        data_key="temperature_high_alarm_enabled",
        setter_name="async_set_temperature_high_alarm_enabled",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SmartNextSwitchDescription(
        key="salt_low_alarm_enabled",
        translation_key="salt_low_alarm_enabled",
        data_key="salt_low_alarm_enabled",
        setter_name="async_set_salt_low_alarm_enabled",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SmartNextSwitchDescription(
        key="salt_high_alarm_enabled",
        translation_key="salt_high_alarm_enabled",
        data_key="salt_high_alarm_enabled",
        setter_name="async_set_salt_high_alarm_enabled",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up SmartNext switches."""
    coordinator = entry.runtime_data
    async_add_entities(
        SmartNextSwitch(
            coordinator,
            entry.entry_id,
            entry.data["host"],
            description,
        )
        for description in SWITCHES
    )


class SmartNextSwitch(SmartNextEntity, SwitchEntity):
    """Representation of a writable SmartNext switch."""

    entity_description: SmartNextSwitchDescription

    def __init__(self, coordinator, entry_id: str, host: str, description) -> None:
        super().__init__(coordinator, entry_id, host)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get(self.entity_description.data_key))

    async def _async_set_state(self, enabled: bool) -> None:
        setter: Setter = getattr(
            self.coordinator.api,
            self.entity_description.setter_name,
        )
        await setter(enabled)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set_state(False)
