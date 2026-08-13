sed: --: No such file or directory
"""The SmartNext integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TIMEOUT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import SmartNextApi, SmartNextCommunicationError
from .const import (
    CONF_RECONNECT_DELAY,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DEFAULT_RECONNECT_DELAY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    PLATFORMS,
)
from .coordinator import SmartNextCoordinator

type SmartNextConfigEntry = ConfigEntry[SmartNextCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SmartNextConfigEntry) -> bool:
    """Set up SmartNext from a config entry."""
    api = SmartNextApi(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        timeout=float(entry.options.get(CONF_TIMEOUT, entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT))),
        reconnect_delay=float(
            entry.options.get(
                CONF_RECONNECT_DELAY,
                entry.data.get(CONF_RECONNECT_DELAY, DEFAULT_RECONNECT_DELAY),
            )
        ),
        unit_id=int(entry.options.get(CONF_UNIT_ID, entry.data[CONF_UNIT_ID])),
    )

    coordinator = SmartNextCoordinator(
        hass,
        api,
        int(
            entry.options.get(
                CONF_SCAN_INTERVAL,
                entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            )
        ),
    )

    try:
        await api.async_connect()
        await coordinator.async_config_entry_first_refresh()
    except (SmartNextCommunicationError, OSError) as err:
        await api.async_close()
        raise ConfigEntryNotReady(str(err)) from err

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SmartNextConfigEntry) -> bool:
    """Unload a SmartNext config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.api.async_close()
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: SmartNextConfigEntry) -> None:
    """Reload SmartNext when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
