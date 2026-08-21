"""Config flow for AstralPool devices."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TIMEOUT
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_DEVICE_TYPE,
    CONF_RECONNECT_DELAY,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DEFAULT_PORT,
    DEFAULT_RECONNECT_DELAY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DEFAULT_UNIT_IDS,
    DEVICE_NAMES,
    DEVICE_TYPE_ELYO_TOUCH,
    DEVICE_TYPE_SMARTNEXT,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .devices.elyo_touch.api import ElyoTouchApi, ElyoTouchCommunicationError
from .devices.smartnext.api import SmartNextApi, SmartNextCommunicationError

_UNIT_ID_SELECTOR = vol.All(
    NumberSelector(
        NumberSelectorConfig(
            min=0,
            max=247,
            step=1,
            mode=NumberSelectorMode.BOX,
        )
    ),
    vol.Coerce(int),
)


def _connection_schema(device_type: str, defaults: dict | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(
                CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            vol.Required(
                CONF_UNIT_ID,
                default=defaults.get(CONF_UNIT_ID, DEFAULT_UNIT_IDS[device_type]),
            ): _UNIT_ID_SELECTOR,
            vol.Required(
                CONF_TIMEOUT, default=defaults.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=60)),
            vol.Required(
                CONF_RECONNECT_DELAY,
                default=defaults.get(CONF_RECONNECT_DELAY, DEFAULT_RECONNECT_DELAY),
            ): vol.All(vol.Coerce(float), vol.Range(min=0, max=300)),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
            ),
        }
    )


def _connection_unique_id(device_type: str, data: dict) -> str:
    """Return the unique ID for one AstralPool Modbus endpoint."""
    return (
        f"{device_type}:"
        f"{data[CONF_HOST]}:"
        f"{data[CONF_PORT]}:"
        f"{data[CONF_UNIT_ID]}"
    )


async def _test_connection(device_type: str, data: dict) -> None:
    api_class = SmartNextApi if device_type == DEVICE_TYPE_SMARTNEXT else ElyoTouchApi
    api = api_class(
        host=data[CONF_HOST],
        port=data[CONF_PORT],
        timeout=data[CONF_TIMEOUT],
        reconnect_delay=data[CONF_RECONNECT_DELAY],
        unit_id=data[CONF_UNIT_ID],
    )
    try:
        await api.async_connect()
        await api.async_read_all()
    finally:
        await api.async_close()


class AstralPoolConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an AstralPool config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._device_type: str | None = None

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Select the AstralPool device family."""
        if user_input is not None:
            self._device_type = user_input[CONF_DEVICE_TYPE]
            return await self.async_step_connection()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_TYPE): vol.In(
                        {
                            DEVICE_TYPE_SMARTNEXT: DEVICE_NAMES[DEVICE_TYPE_SMARTNEXT],
                            DEVICE_TYPE_ELYO_TOUCH: DEVICE_NAMES[DEVICE_TYPE_ELYO_TOUCH],
                        }
                    )
                }
            ),
        )

    async def async_step_connection(self, user_input=None) -> ConfigFlowResult:
        """Configure and validate the selected device."""
        if self._device_type is None:
            return await self.async_step_user()

        reconfigure_entry = (
            self._get_reconfigure_entry()
            if self.source == SOURCE_RECONFIGURE
            else None
        )
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {CONF_DEVICE_TYPE: self._device_type, **user_input}
            unique_id = _connection_unique_id(self._device_type, user_input)

            if reconfigure_entry is not None:
                existing = self.hass.config_entries.async_entry_for_domain_unique_id(
                    DOMAIN, unique_id
                )
                if existing is not None and existing.entry_id != reconfigure_entry.entry_id:
                    return self.async_abort(reason="already_configured")
            else:
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

            try:
                await _test_connection(self._device_type, user_input)
            except (
                SmartNextCommunicationError,
                ElyoTouchCommunicationError,
                OSError,
                TimeoutError,
            ):
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                title = f"{DEVICE_NAMES[self._device_type]} {user_input[CONF_HOST]}"
                if reconfigure_entry is not None:
                    return self.async_update_reload_and_abort(
                        reconfigure_entry,
                        data=data,
                        options={},
                        title=title,
                        unique_id=unique_id,
                    )
                return self.async_create_entry(title=title, data=data)

        defaults = user_input
        if reconfigure_entry is not None and defaults is None:
            defaults = {
                CONF_HOST: reconfigure_entry.data[CONF_HOST],
                CONF_PORT: reconfigure_entry.data[CONF_PORT],
                CONF_UNIT_ID: reconfigure_entry.options.get(
                    CONF_UNIT_ID, reconfigure_entry.data[CONF_UNIT_ID]
                ),
                CONF_TIMEOUT: reconfigure_entry.options.get(
                    CONF_TIMEOUT, reconfigure_entry.data[CONF_TIMEOUT]
                ),
                CONF_RECONNECT_DELAY: reconfigure_entry.options.get(
                    CONF_RECONNECT_DELAY,
                    reconfigure_entry.data[CONF_RECONNECT_DELAY],
                ),
                CONF_SCAN_INTERVAL: reconfigure_entry.options.get(
                    CONF_SCAN_INTERVAL,
                    reconfigure_entry.data[CONF_SCAN_INTERVAL],
                ),
            }

        return self.async_show_form(
            step_id="connection",
            data_schema=_connection_schema(self._device_type, defaults),
            errors=errors,
            description_placeholders={"device_name": DEVICE_NAMES[self._device_type]},
        )

    async def async_step_reconfigure(self, user_input=None) -> ConfigFlowResult:
        """Reconfigure the Modbus endpoint for an existing AstralPool device."""
        entry = self._get_reconfigure_entry()
        self._device_type = entry.data[CONF_DEVICE_TYPE]
        return await self.async_step_connection(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return AstralPoolOptionsFlow(config_entry)


class AstralPoolOptionsFlow(config_entries.OptionsFlow):
    """Handle runtime-tunable AstralPool options."""

    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        """Manage communication options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {
            CONF_UNIT_ID: self._config_entry.options.get(
                CONF_UNIT_ID, self._config_entry.data[CONF_UNIT_ID]
            ),
            CONF_TIMEOUT: self._config_entry.options.get(
                CONF_TIMEOUT, self._config_entry.data[CONF_TIMEOUT]
            ),
            CONF_RECONNECT_DELAY: self._config_entry.options.get(
                CONF_RECONNECT_DELAY,
                self._config_entry.data[CONF_RECONNECT_DELAY],
            ),
            CONF_SCAN_INTERVAL: self._config_entry.options.get(
                CONF_SCAN_INTERVAL,
                self._config_entry.data[CONF_SCAN_INTERVAL],
            ),
        }

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UNIT_ID, default=defaults[CONF_UNIT_ID]
                    ): _UNIT_ID_SELECTOR,
                    vol.Required(
                        CONF_TIMEOUT, default=defaults[CONF_TIMEOUT]
                    ): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=60)),
                    vol.Required(
                        CONF_RECONNECT_DELAY,
                        default=defaults[CONF_RECONNECT_DELAY],
                    ): vol.All(vol.Coerce(float), vol.Range(min=0, max=300)),
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=defaults[CONF_SCAN_INTERVAL],
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                }
            ),
        )
