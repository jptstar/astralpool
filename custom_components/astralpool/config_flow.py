"""Config flow for AstralPool devices."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
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

_SCAN_INTERVAL_SELECTOR = vol.All(
    NumberSelector(
        NumberSelectorConfig(
            min=MIN_SCAN_INTERVAL,
            max=MAX_SCAN_INTERVAL,
            step=1,
            mode=NumberSelectorMode.BOX,
        )
    ),
    vol.Coerce(int),
)


def _endpoint_schema(device_type: str, defaults: dict | None = None) -> vol.Schema:
    """Return the Modbus endpoint schema used by reconfiguration."""
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
        }
    )


def _connection_schema(device_type: str, defaults: dict | None = None) -> vol.Schema:
    """Return the complete schema used when adding a new device."""
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
            ): _SCAN_INTERVAL_SELECTOR,
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
    """Validate one AstralPool Modbus endpoint."""
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
        """Configure and validate a new AstralPool device."""
        if self._device_type is None:
            return await self.async_step_user()

        errors: dict[str, str] = {}
        if user_input is not None:
            data = {CONF_DEVICE_TYPE: self._device_type, **user_input}
            unique_id = _connection_unique_id(self._device_type, user_input)
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
                return self.async_create_entry(
                    title=f"{DEVICE_NAMES[self._device_type]} {user_input[CONF_HOST]}",
                    data=data,
                )

        return self.async_show_form(
            step_id="connection",
            data_schema=_connection_schema(self._device_type, user_input),
            errors=errors,
            description_placeholders={"device_name": DEVICE_NAMES[self._device_type]},
        )

    async def async_step_reconfigure(self, user_input=None) -> ConfigFlowResult:
        """Reconfigure the endpoint without duplicating communication options."""
        entry = self._get_reconfigure_entry()
        device_type = entry.data[CONF_DEVICE_TYPE]
        errors: dict[str, str] = {}

        if user_input is not None:
            unique_id = _connection_unique_id(device_type, user_input)
            existing = self.hass.config_entries.async_entry_for_domain_unique_id(
                DOMAIN, unique_id
            )
            if existing is not None and existing.entry_id != entry.entry_id:
                return self.async_abort(reason="already_configured")

            test_data = {
                **user_input,
                CONF_TIMEOUT: entry.options.get(
                    CONF_TIMEOUT, entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
                ),
                CONF_RECONNECT_DELAY: entry.options.get(
                    CONF_RECONNECT_DELAY,
                    entry.data.get(CONF_RECONNECT_DELAY, DEFAULT_RECONNECT_DELAY),
                ),
            }
            try:
                await _test_connection(device_type, test_data)
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
                # Unit ID used to be exposed in the options flow. Remove a legacy
                # override when endpoint reconfiguration succeeds so data becomes
                # the single source of truth for host, port and Unit ID.
                options = dict(entry.options)
                options.pop(CONF_UNIT_ID, None)
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input[CONF_PORT],
                        CONF_UNIT_ID: user_input[CONF_UNIT_ID],
                    },
                    options=options,
                    title=f"{DEVICE_NAMES[device_type]} {user_input[CONF_HOST]}",
                    unique_id=unique_id,
                )

        defaults = user_input or {
            CONF_HOST: entry.data[CONF_HOST],
            CONF_PORT: entry.data[CONF_PORT],
            CONF_UNIT_ID: entry.options.get(CONF_UNIT_ID, entry.data[CONF_UNIT_ID]),
        }
        return self.async_show_form(
            step_id="connection",
            data_schema=_endpoint_schema(device_type, defaults),
            errors=errors,
            description_placeholders={"device_name": DEVICE_NAMES[device_type]},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return AstralPoolOptionsFlow(config_entry)


class AstralPoolOptionsFlow(config_entries.OptionsFlow):
    """Handle runtime-tunable AstralPool communication options."""

    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        """Manage timeout, reconnect delay and polling interval."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {
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
                        CONF_TIMEOUT, default=defaults[CONF_TIMEOUT]
                    ): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=60)),
                    vol.Required(
                        CONF_RECONNECT_DELAY,
                        default=defaults[CONF_RECONNECT_DELAY],
                    ): vol.All(vol.Coerce(float), vol.Range(min=0, max=300)),
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=defaults[CONF_SCAN_INTERVAL],
                    ): _SCAN_INTERVAL_SELECTOR,
                }
            ),
        )
