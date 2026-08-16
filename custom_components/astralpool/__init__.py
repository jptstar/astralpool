"""The AstralPool integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TIMEOUT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import RegistryEntryDisabler

from .const import (
    CONF_DEVICE_TYPE,
    CONF_RECONNECT_DELAY,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DEFAULT_RECONNECT_DELAY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DEVICE_TYPE_ELYO_TOUCH,
    DEVICE_TYPE_SMARTNEXT,
    PLATFORMS_BY_DEVICE_TYPE,
)
from .devices.elyo_touch.api import ElyoTouchApi, ElyoTouchCommunicationError
from .devices.elyo_touch.coordinator import ElyoTouchCoordinator
from .devices.smartnext.api import SmartNextApi, SmartNextCommunicationError
from .devices.smartnext.coordinator import SmartNextCoordinator

type AstralPoolCoordinator = SmartNextCoordinator | ElyoTouchCoordinator
type AstralPoolConfigEntry = ConfigEntry[AstralPoolCoordinator]


def _async_enable_integration_disabled_entities(
    hass: HomeAssistant, entry: AstralPoolConfigEntry
) -> None:
    """Enable entities that were disabled only by AstralPool defaults."""
    registry = er.async_get(hass)
    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if registry_entry.disabled_by == RegistryEntryDisabler.INTEGRATION:
            registry.async_update_entity(registry_entry.entity_id, disabled_by=None)


async def async_setup_entry(hass: HomeAssistant, entry: AstralPoolConfigEntry) -> bool:
    """Set up an AstralPool device from a config entry."""
    device_type = entry.data[CONF_DEVICE_TYPE]
    timeout = float(entry.options.get(CONF_TIMEOUT, entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)))
    reconnect_delay = float(
        entry.options.get(
            CONF_RECONNECT_DELAY,
            entry.data.get(CONF_RECONNECT_DELAY, DEFAULT_RECONNECT_DELAY),
        )
    )
    unit_id = int(entry.options.get(CONF_UNIT_ID, entry.data[CONF_UNIT_ID]))
    scan_interval = int(
        entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
    )

    if device_type == DEVICE_TYPE_SMARTNEXT:
        api = SmartNextApi(
            host=entry.data[CONF_HOST],
            port=entry.data[CONF_PORT],
            timeout=timeout,
            reconnect_delay=reconnect_delay,
            unit_id=unit_id,
        )
        coordinator = SmartNextCoordinator(hass, api, scan_interval)
    elif device_type == DEVICE_TYPE_ELYO_TOUCH:
        api = ElyoTouchApi(
            host=entry.data[CONF_HOST],
            port=entry.data[CONF_PORT],
            timeout=timeout,
            reconnect_delay=reconnect_delay,
            unit_id=unit_id,
        )
        coordinator = ElyoTouchCoordinator(hass, api, scan_interval)
    else:
        raise ValueError(f"Unsupported AstralPool device type: {device_type}")

    try:
        await api.async_connect()
        await coordinator.async_config_entry_first_refresh()
    except (SmartNextCommunicationError, ElyoTouchCommunicationError, OSError) as err:
        await api.async_close()
        raise ConfigEntryNotReady(str(err)) from err

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    _async_enable_integration_disabled_entities(hass, entry)

    await hass.config_entries.async_forward_entry_setups(
        entry, PLATFORMS_BY_DEVICE_TYPE[device_type]
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AstralPoolConfigEntry) -> bool:
    """Unload an AstralPool config entry."""
    device_type = entry.data[CONF_DEVICE_TYPE]
    unloaded = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS_BY_DEVICE_TYPE[device_type]
    )
    if unloaded:
        await entry.runtime_data.api.async_close()
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: AstralPoolConfigEntry) -> None:
    """Reload AstralPool when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
