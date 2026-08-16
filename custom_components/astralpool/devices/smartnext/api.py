"""Async Modbus TCP API for SmartNext."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import (
    COIL_ELECTROLYSIS_BOOST,
    COIL_ELECTROLYSIS_COVER_CONTROL_ENABLE,
    COIL_ELECTROLYSIS_EXTERNAL_CONTROL_ENABLE,
    COIL_ELECTROLYSIS_INTERNAL_ORP_CONTROL_ENABLE,
    COIL_ELECTROLYSIS_POLARITY_PERIOD_HIGH,
    COIL_ELECTROLYSIS_POLARITY_PERIOD_LOW,
    COIL_FLOW_EXTERNAL_SENSOR_ENABLE,
    COIL_FLOW_INTERNAL_SENSOR_ENABLE,
    COIL_PH_INTELLIGENT_DOSING_ENABLE,
    COIL_PH_PUMP_STOP_ENABLE,
    COIL_PH_PUMP_STOP_RESET,
    COIL_SALT_HIGH_ALARM_ENABLE,
    COIL_SALT_LOW_ALARM_ENABLE,
    COIL_TEMPERATURE_HIGH_ALARM_ENABLE,
    COIL_TEMPERATURE_LOW_ALARM_ENABLE,
    DI_COVER_ACTIVE,
    DI_COVER_INPUT,
    DI_ELECTROLYSIS_CHECK_CELL,
    DI_ELECTROLYSIS_EXTERNAL_CONTROL_INPUT,
    DI_ELECTROLYSIS_EXTERNAL_CONTROL_STOP,
    DI_ELECTROLYSIS_HIGH_CONDUCTIVITY,
    DI_ELECTROLYSIS_INTERNAL_ORP_STOP,
    DI_ELECTROLYSIS_LOW_CONDUCTIVITY,
    DI_ELECTROLYSIS_POLARITY,
    DI_ELECTROLYSIS_RUNNING,
    DI_FLOW_EXTERNAL_SWITCH,
    DI_FLOW_EXTERNAL_STATUS,
    DI_FLOW_GENERAL,
    DI_FLOW_INTERNAL,
    DI_FLOW_INTERNAL_STATUS,
    DI_GENERAL_ALARM,
    DI_ORP_HIGH_ALARM,
    DI_ORP_LOW_ALARM,
    DI_ORP_MEASURE_UNRELIABLE,
    DI_PH_DOSING,
    DI_PH_FUSE_ALARM,
    DI_PH_HIGH_ALARM,
    DI_PH_INITIALIZING,
    DI_PH_LOW_ALARM,
    DI_PH_MEASURE_UNRELIABLE,
    DI_PH_PUMP_STOP_ALARM,
    DI_SALT_CURRENT_INSUFFICIENT,
    DI_SALT_HIGH_ALARM,
    DI_SALT_LOW_ALARM,
    DI_SALT_MEASURE_UNRELIABLE,
    DI_SALT_VOLTAGE_INSUFFICIENT,
    DI_TEMPERATURE_HIGH_ALARM,
    DI_TEMPERATURE_LOW_ALARM,
    DI_TEMPERATURE_MEASURE_UNRELIABLE,
    DI_TREATMENT_HALTED,
    HR_ELECTROLYSIS_BOOST_REMAINING,
    HR_ELECTROLYSIS_CONTROL_WORD,
    HR_ELECTROLYSIS_COVER_SETPOINT,
    HR_ELECTROLYSIS_NORMAL_SETPOINT,
    HR_FIRMWARE_VERSION,
    HR_FLOW_CONTROL_WORD,
    HR_HARDWARE_VERSION,
    HR_ORP_SETPOINT,
    HR_PH_DOSAGE_LIMIT,
    HR_PH_INIT_TIME,
    HR_PH_OUTPUT_CONTROL_WORD,
    HR_PH_SETPOINT,
    HR_PRODUCT_CAPACITY,
    HR_PRODUCT_CODE_HIGH,
    HR_SALT_CONTROL_WORD,
    HR_SALT_MAX,
    HR_SALT_MIN,
    HR_SERIAL_HIGH,
    HR_SERIAL_LOW,
    HR_SERIAL_MIDDLE,
    HR_TECHNOLOGIES_IMPLEMENTED,
    HR_TEMPERATURE_CONTROL_WORD,
    HR_TEMPERATURE_MAX,
    HR_TEMPERATURE_MIN,
    HR_TECHNOLOGIES_ENABLED,
    IR_ELECTROLYSIS_CHLORINE_PRODUCTION,
    IR_ELECTROLYSIS_CURRENT,
    IR_ELECTROLYSIS_FUNCTIONAL_TARGET,
    IR_ELECTROLYSIS_PARTIAL_HOURS_LSB,
    IR_ELECTROLYSIS_PARTIAL_HOURS_MSB,
    IR_ELECTROLYSIS_PRODUCTION,
    IR_ELECTROLYSIS_TOTAL_HOURS_LSB,
    IR_ELECTROLYSIS_TOTAL_HOURS_MSB,
    IR_ELECTROLYSIS_VOLTAGE,
    IR_ORP,
    IR_PH,
    IR_PH_DOSAGE_ELAPSED,
    IR_PH_PARTIAL_HOURS,
    IR_PH_PUMP_OUTPUT,
    IR_PH_TOTAL_HOURS,
    IR_SALT,
    IR_TEMPERATURE,
    PH_INIT_ALLOWED_SECONDS,
    POLARITY_REVERSAL_ALLOWED_HOURS,
)

_LOGGER = logging.getLogger(__name__)


class SmartNextCommunicationError(Exception):
    """Raised when communication with SmartNext fails."""


class SmartNextApi:
    """SmartNext Modbus TCP client."""

    def __init__(
        self,
        host: str,
        port: int,
        timeout: float,
        reconnect_delay: float,
        unit_id: int,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.reconnect_delay = reconnect_delay
        self.unit_id = unit_id
        self._lock = asyncio.Lock()
        self._client = AsyncModbusTcpClient(
            host,
            port=port,
            timeout=timeout,
            reconnect_delay=reconnect_delay,
        )
        self._identification: dict[str, Any] | None = None

    @property
    def connected(self) -> bool:
        """Return whether the TCP client reports an active connection."""
        return bool(self._client.connected)

    async def async_connect(self) -> None:
        """Connect to the Modbus server."""
        try:
            connected = await self._client.connect()
        except (OSError, ModbusException) as err:
            raise SmartNextCommunicationError(str(err)) from err
        if not connected:
            raise SmartNextCommunicationError(
                f"Unable to connect to {self.host}:{self.port}"
            )

    async def async_close(self) -> None:
        """Close the Modbus connection."""
        self._client.close()

    @staticmethod
    def _check_response(response: Any, operation: str) -> Any:
        if response is None or response.isError():
            raise SmartNextCommunicationError(
                f"Modbus error while {operation}: {response!r}"
            )
        return response

    async def _ensure_connected(self) -> None:
        if not self._client.connected:
            await self.async_connect()

    async def _read_input_registers(self, address: int, count: int) -> list[int]:
        async with self._lock:
            await self._ensure_connected()
            try:
                response = await self._client.read_input_registers(
                    address, count=count, device_id=self.unit_id
                )
            except (OSError, ModbusException) as err:
                raise SmartNextCommunicationError(str(err)) from err
            self._check_response(response, f"reading input registers {address}:{count}")
            return list(response.registers)

    async def _read_holding_registers(self, address: int, count: int) -> list[int]:
        async with self._lock:
            await self._ensure_connected()
            try:
                response = await self._client.read_holding_registers(
                    address, count=count, device_id=self.unit_id
                )
            except (OSError, ModbusException) as err:
                raise SmartNextCommunicationError(str(err)) from err
            self._check_response(response, f"reading holding registers {address}:{count}")
            return list(response.registers)

    async def _read_discrete_inputs(self, address: int, count: int) -> list[bool]:
        async with self._lock:
            await self._ensure_connected()
            try:
                response = await self._client.read_discrete_inputs(
                    address, count=count, device_id=self.unit_id
                )
            except (OSError, ModbusException) as err:
                raise SmartNextCommunicationError(str(err)) from err
            self._check_response(response, f"reading discrete inputs {address}:{count}")
            return [bool(value) for value in response.bits[:count]]

    async def async_write_register(self, address: int, value: int) -> None:
        """Write one holding register."""
        if not 0 <= value <= 0xFFFF:
            raise ValueError(f"Register value out of range: {value}")
        async with self._lock:
            await self._ensure_connected()
            try:
                response = await self._client.write_register(
                    address, value, device_id=self.unit_id
                )
            except (OSError, ModbusException) as err:
                raise SmartNextCommunicationError(str(err)) from err
            self._check_response(response, f"writing holding register {address}")

    async def async_write_coil(self, address: int, value: bool) -> None:
        """Write one coil."""
        async with self._lock:
            await self._ensure_connected()
            try:
                response = await self._client.write_coil(
                    address, value, device_id=self.unit_id
                )
            except (OSError, ModbusException) as err:
                raise SmartNextCommunicationError(str(err)) from err
            self._check_response(response, f"writing coil {address}")

    @staticmethod
    def _uint16_to_int16(value: int) -> int:
        return value - 65536 if value > 32767 else value

    @staticmethod
    def _combine_u32(lsb: int, msb: int) -> int:
        return (msb << 16) | lsb

    @staticmethod
    def _combine_u48(high: int, middle: int, low: int) -> int:
        return (high << 32) | (middle << 16) | low

    @staticmethod
    def _decode_boost_minutes(value: int) -> int:
        """Decode the protocol's HH/MM byte layout into minutes."""
        return ((value >> 8) * 60) + (value & 0xFF)

    @staticmethod
    def _decode_polarity_period(control_word: int) -> int:
        """Decode electrolysis control-word bits 9..10."""
        code = (control_word >> 9) & 0b11
        return (2, 3, 4, 7)[code]

    async def _async_read_identification(self) -> dict[str, Any]:
        """Read immutable identification data once per API instance."""
        if self._identification is not None:
            return self._identification

        try:
            identification = await self._read_holding_registers(
                HR_PRODUCT_CODE_HIGH,
                HR_SERIAL_LOW - HR_PRODUCT_CODE_HIGH + 1,
            )
        except SmartNextCommunicationError as err:
            _LOGGER.debug("SmartNext identification registers unavailable: %s", err)
            self._identification = {}
            return self._identification

        def value(address: int) -> int:
            return identification[address - HR_PRODUCT_CODE_HIGH]

        serial = self._combine_u48(
            value(HR_SERIAL_HIGH),
            value(HR_SERIAL_MIDDLE),
            value(HR_SERIAL_LOW),
        )
        technologies_implemented = value(HR_TECHNOLOGIES_IMPLEMENTED)
        hardware_version = value(HR_HARDWARE_VERSION)
        firmware_version = value(HR_FIRMWARE_VERSION)

        self._identification = {
            "product_capacity": value(HR_PRODUCT_CAPACITY),
            "hardware_version": f"0x{hardware_version:04X}"
            if hardware_version
            else None,
            "firmware_version": f"0x{firmware_version:04X}"
            if firmware_version
            else None,
            "serial_number": f"{serial:012X}" if serial else None,
            "technologies_implemented": technologies_implemented,
            "technology_electrolysis_implemented": bool(
                technologies_implemented & (1 << 0)
            ),
            "technology_ph_implemented": bool(technologies_implemented & (1 << 1)),
            "technology_orp_implemented": bool(technologies_implemented & (1 << 2)),
            "technology_temperature_implemented": bool(
                technologies_implemented & (1 << 4)
            ),
            "technology_salt_implemented": bool(technologies_implemented & (1 << 5)),
        }
        return self._identification

    async def async_reset_ph_pump_stop(self) -> None:
        """Rearm the pH pump-stop using coil 0x56D."""
        await self.async_write_coil(COIL_PH_PUMP_STOP_RESET, True)
        await asyncio.sleep(0.2)
        await self.async_write_coil(COIL_PH_PUMP_STOP_RESET, False)

    async def async_read_all(self) -> dict[str, Any]:
        """Read the verified SmartNext v1.70 points."""
        data = dict(await self._async_read_identification())

        # Electrolysis input registers 0x41..0x45.
        electrolysis = await self._read_input_registers(0x41, 5)
        data["electrolysis_functional_target"] = electrolysis[
            IR_ELECTROLYSIS_FUNCTIONAL_TARGET - 0x41
        ]
        data["electrolysis_production"] = electrolysis[
            IR_ELECTROLYSIS_PRODUCTION - 0x41
        ]
        data["electrolysis_current"] = electrolysis[
            IR_ELECTROLYSIS_CURRENT - 0x41
        ] / 100
        data["electrolysis_voltage"] = electrolysis[
            IR_ELECTROLYSIS_VOLTAGE - 0x41
        ] / 100
        data["electrolysis_chlorine_production"] = electrolysis[
            IR_ELECTROLYSIS_CHLORINE_PRODUCTION - 0x41
        ]

        electrolysis_hours = await self._read_input_registers(0x48, 4)
        data["electrolysis_total_hours"] = self._combine_u32(
            electrolysis_hours[IR_ELECTROLYSIS_TOTAL_HOURS_LSB - 0x48],
            electrolysis_hours[IR_ELECTROLYSIS_TOTAL_HOURS_MSB - 0x48],
        )
        data["electrolysis_partial_hours"] = self._combine_u32(
            electrolysis_hours[IR_ELECTROLYSIS_PARTIAL_HOURS_LSB - 0x48],
            electrolysis_hours[IR_ELECTROLYSIS_PARTIAL_HOURS_MSB - 0x48],
        )

        # pH input registers.
        data["ph"] = (await self._read_input_registers(IR_PH, 1))[0] / 100
        ph_output = await self._read_input_registers(IR_PH_DOSAGE_ELAPSED, 2)
        data["ph_dosage_elapsed"] = ph_output[IR_PH_DOSAGE_ELAPSED - 0x57]
        data["ph_pump_output"] = ph_output[IR_PH_PUMP_OUTPUT - 0x57]
        ph_hours = await self._read_input_registers(IR_PH_TOTAL_HOURS, 2)
        data["ph_total_hours"] = ph_hours[IR_PH_TOTAL_HOURS - 0x5A]
        data["ph_partial_hours"] = ph_hours[IR_PH_PARTIAL_HOURS - 0x5A]

        data["orp"] = (await self._read_input_registers(IR_ORP, 1))[0]

        raw_temperature = (await self._read_input_registers(IR_TEMPERATURE, 1))[0]
        data["temperature"] = self._uint16_to_int16(raw_temperature) / 10

        data["salt"] = (await self._read_input_registers(IR_SALT, 1))[0] / 100

        # Device mode / writable configuration / thresholds.
        technologies_enabled = (
            await self._read_holding_registers(HR_TECHNOLOGIES_ENABLED, 1)
        )[0]
        data["technologies_enabled"] = technologies_enabled
        data["technology_electrolysis_enabled"] = bool(
            technologies_enabled & (1 << 0)
        )
        data["technology_ph_enabled"] = bool(technologies_enabled & (1 << 1))
        data["technology_orp_enabled"] = bool(technologies_enabled & (1 << 2))
        data["technology_temperature_enabled"] = bool(
            technologies_enabled & (1 << 4)
        )
        data["technology_salt_enabled"] = bool(technologies_enabled & (1 << 5))
        # Protocol v1.70: bit 9 = Biopool mode enabled.
        data["biopool_mode"] = bool(technologies_enabled & (1 << 9))

        flow_control = (
            await self._read_holding_registers(HR_FLOW_CONTROL_WORD, 1)
        )[0]
        data["internal_flow_sensor_enabled"] = bool(flow_control & (1 << 0))
        data["external_flow_sensor_enabled"] = bool(flow_control & (1 << 1))

        electrolysis_control = await self._read_holding_registers(
            HR_ELECTROLYSIS_CONTROL_WORD, 5
        )
        electrolysis_control_word = electrolysis_control[0]
        data["boost_mode"] = bool(electrolysis_control_word & (1 << 1))
        data["cover_control_enabled"] = bool(
            electrolysis_control_word & (1 << 2)
        )
        data["external_chlorine_control_enabled"] = bool(
            electrolysis_control_word & (1 << 4)
        )
        data["internal_orp_control_enabled"] = bool(
            electrolysis_control_word & (1 << 5)
        )
        data["polarity_reversal_period"] = self._decode_polarity_period(
            electrolysis_control_word
        )
        data["electrolysis_normal_setpoint"] = electrolysis_control[
            HR_ELECTROLYSIS_NORMAL_SETPOINT - HR_ELECTROLYSIS_CONTROL_WORD
        ]
        data["electrolysis_cover_setpoint"] = electrolysis_control[
            HR_ELECTROLYSIS_COVER_SETPOINT - HR_ELECTROLYSIS_CONTROL_WORD
        ]
        data["boost_remaining_time"] = self._decode_boost_minutes(
            electrolysis_control[
                HR_ELECTROLYSIS_BOOST_REMAINING - HR_ELECTROLYSIS_CONTROL_WORD
            ]
        )

        ph_config = await self._read_holding_registers(HR_PH_INIT_TIME, 4)
        data["ph_init_time"] = ph_config[0]
        ph_output_control = ph_config[HR_PH_OUTPUT_CONTROL_WORD - HR_PH_INIT_TIME]
        data["ph_intelligent_dosing_enabled"] = bool(
            ph_output_control & (1 << 6)
        )
        data["ph_pump_stop_enabled"] = bool(ph_output_control & (1 << 12))
        data["ph_setpoint"] = ph_config[HR_PH_SETPOINT - HR_PH_INIT_TIME] / 100
        data["ph_dosage_limit"] = ph_config[
            HR_PH_DOSAGE_LIMIT - HR_PH_INIT_TIME
        ]

        data["orp_setpoint"] = (
            await self._read_holding_registers(HR_ORP_SETPOINT, 1)
        )[0]

        temperature_config = await self._read_holding_registers(
            HR_TEMPERATURE_CONTROL_WORD, 4
        )
        temperature_control_word = temperature_config[0]
        data["temperature_low_alarm_enabled"] = bool(
            temperature_control_word & (1 << 11)
        )
        data["temperature_high_alarm_enabled"] = bool(
            temperature_control_word & (1 << 12)
        )
        data["temperature_min"] = temperature_config[
            HR_TEMPERATURE_MIN - HR_TEMPERATURE_CONTROL_WORD
        ] / 10
        data["temperature_max"] = temperature_config[
            HR_TEMPERATURE_MAX - HR_TEMPERATURE_CONTROL_WORD
        ] / 10

        salt_config = await self._read_holding_registers(HR_SALT_CONTROL_WORD, 4)
        salt_control_word = salt_config[0]
        data["salt_low_alarm_enabled"] = bool(salt_control_word & (1 << 11))
        data["salt_high_alarm_enabled"] = bool(salt_control_word & (1 << 12))
        data["salt_min"] = salt_config[HR_SALT_MIN - HR_SALT_CONTROL_WORD] / 100
        data["salt_max"] = salt_config[HR_SALT_MAX - HR_SALT_CONTROL_WORD] / 100

        # General status.
        general = await self._read_discrete_inputs(DI_GENERAL_ALARM, 3)
        data["general_alarm"] = general[0]
        data["treatment_halted"] = general[DI_TREATMENT_HALTED - DI_GENERAL_ALARM]

        # Alarm groups.
        flow = await self._read_discrete_inputs(DI_FLOW_GENERAL, 3)
        data["flow_alarm"] = flow[0]
        data["internal_flow_alarm"] = flow[1]
        data["external_flow_switch_alarm"] = flow[2]

        flow_status = await self._read_discrete_inputs(DI_FLOW_INTERNAL_STATUS, 3)
        data["internal_air_bubble_detected"] = flow_status[0]
        data["external_flow_switch_open"] = flow_status[
            DI_FLOW_EXTERNAL_STATUS - DI_FLOW_INTERNAL_STATUS
        ]

        electrolysis_alarm = await self._read_discrete_inputs(
            DI_ELECTROLYSIS_CHECK_CELL, 3
        )
        data["electrolysis_check_cell_alarm"] = electrolysis_alarm[0]
        data["electrolysis_low_conductivity_alarm"] = electrolysis_alarm[1]
        data["electrolysis_high_conductivity_alarm"] = electrolysis_alarm[2]

        ph_alarms = await self._read_discrete_inputs(DI_PH_LOW_ALARM, 8)
        data["ph_low_alarm"] = ph_alarms[0]
        data["ph_high_alarm"] = ph_alarms[1]
        data["ph_pump_stop_alarm"] = ph_alarms[
            DI_PH_PUMP_STOP_ALARM - DI_PH_LOW_ALARM
        ]
        data["ph_fuse_alarm"] = ph_alarms[DI_PH_FUSE_ALARM - DI_PH_LOW_ALARM]

        orp_alarms = await self._read_discrete_inputs(DI_ORP_LOW_ALARM, 2)
        data["orp_low_alarm"] = orp_alarms[0]
        data["orp_high_alarm"] = orp_alarms[1]

        temp_alarms = await self._read_discrete_inputs(DI_TEMPERATURE_LOW_ALARM, 2)
        data["temperature_low_alarm"] = temp_alarms[0]
        data["temperature_high_alarm"] = temp_alarms[1]

        salt_alarms = await self._read_discrete_inputs(DI_SALT_LOW_ALARM, 2)
        data["salt_low_alarm"] = salt_alarms[0]
        data["salt_high_alarm"] = salt_alarms[1]

        # Operating status.
        electrolysis_state = await self._read_discrete_inputs(
            DI_ELECTROLYSIS_RUNNING, 7
        )
        data["electrolysis_running"] = electrolysis_state[0]
        data["electrolysis_reverse_polarity"] = electrolysis_state[
            DI_ELECTROLYSIS_POLARITY - DI_ELECTROLYSIS_RUNNING
        ]
        data["cover_input"] = electrolysis_state[
            DI_COVER_INPUT - DI_ELECTROLYSIS_RUNNING
        ]
        data["cover_active"] = electrolysis_state[
            DI_COVER_ACTIVE - DI_ELECTROLYSIS_RUNNING
        ]
        data["external_chlorine_control_input"] = electrolysis_state[
            DI_ELECTROLYSIS_EXTERNAL_CONTROL_INPUT - DI_ELECTROLYSIS_RUNNING
        ]
        data["internal_orp_control_stop"] = electrolysis_state[
            DI_ELECTROLYSIS_INTERNAL_ORP_STOP - DI_ELECTROLYSIS_RUNNING
        ]
        data["external_control_stop"] = electrolysis_state[
            DI_ELECTROLYSIS_EXTERNAL_CONTROL_STOP - DI_ELECTROLYSIS_RUNNING
        ]

        ph_status = await self._read_discrete_inputs(DI_PH_INITIALIZING, 2)
        data["ph_initializing"] = ph_status[0]
        data["ph_measure_unreliable"] = ph_status[1]
        data["ph_dosing_active"] = (
            await self._read_discrete_inputs(DI_PH_DOSING, 1)
        )[0]

        data["orp_measure_unreliable"] = (
            await self._read_discrete_inputs(DI_ORP_MEASURE_UNRELIABLE, 1)
        )[0]
        data["temperature_measure_unreliable"] = (
            await self._read_discrete_inputs(DI_TEMPERATURE_MEASURE_UNRELIABLE, 1)
        )[0]

        salt_status = await self._read_discrete_inputs(
            DI_SALT_CURRENT_INSUFFICIENT, 3
        )
        data["salt_current_insufficient"] = salt_status[0]
        data["salt_measure_unreliable"] = salt_status[1]
        data["salt_voltage_insufficient"] = salt_status[2]

        return data

    async def async_set_temperature_min(self, value: float) -> None:
        await self.async_write_register(HR_TEMPERATURE_MIN, round(value * 10))

    async def async_set_temperature_max(self, value: float) -> None:
        await self.async_write_register(HR_TEMPERATURE_MAX, round(value * 10))

    async def async_set_ph(self, value: float) -> None:
        await self.async_write_register(HR_PH_SETPOINT, round(value * 100))

    async def async_set_ph_dosage_limit(self, value: float) -> None:
        await self.async_write_register(HR_PH_DOSAGE_LIMIT, round(value))

    async def async_set_ph_init_time(self, value: int) -> None:
        if value not in PH_INIT_ALLOWED_SECONDS:
            raise ValueError(
                f"Invalid pH initialization time {value}; "
                f"allowed values: {PH_INIT_ALLOWED_SECONDS}"
            )
        await self.async_write_register(HR_PH_INIT_TIME, value)

    async def async_set_orp(self, value: float) -> None:
        await self.async_write_register(HR_ORP_SETPOINT, round(value))

    async def async_set_electrolysis_normal(self, value: float) -> None:
        await self.async_write_register(HR_ELECTROLYSIS_NORMAL_SETPOINT, round(value))

    async def async_set_electrolysis_cover(self, value: float) -> None:
        await self.async_write_register(HR_ELECTROLYSIS_COVER_SETPOINT, round(value))

    async def async_set_internal_flow_sensor_enabled(self, enabled: bool) -> None:
        await self.async_write_coil(COIL_FLOW_INTERNAL_SENSOR_ENABLE, enabled)

    async def async_set_external_flow_sensor_enabled(self, enabled: bool) -> None:
        await self.async_write_coil(COIL_FLOW_EXTERNAL_SENSOR_ENABLE, enabled)

    async def async_set_boost_mode(self, enabled: bool) -> None:
        await self.async_write_coil(COIL_ELECTROLYSIS_BOOST, enabled)

    async def async_set_cover_control_enabled(self, enabled: bool) -> None:
        await self.async_write_coil(
            COIL_ELECTROLYSIS_COVER_CONTROL_ENABLE, enabled
        )

    async def async_set_external_chlorine_control_enabled(
        self, enabled: bool
    ) -> None:
        await self.async_write_coil(
            COIL_ELECTROLYSIS_EXTERNAL_CONTROL_ENABLE, enabled
        )

    async def async_set_internal_orp_control_enabled(self, enabled: bool) -> None:
        await self.async_write_coil(
            COIL_ELECTROLYSIS_INTERNAL_ORP_CONTROL_ENABLE, enabled
        )

    async def async_set_polarity_reversal_period(self, hours: int) -> None:
        if hours not in POLARITY_REVERSAL_ALLOWED_HOURS:
            raise ValueError(
                f"Invalid polarity reversal period {hours}; "
                f"allowed values: {POLARITY_REVERSAL_ALLOWED_HOURS}"
            )
        code = POLARITY_REVERSAL_ALLOWED_HOURS.index(hours)
        await self.async_write_coil(
            COIL_ELECTROLYSIS_POLARITY_PERIOD_LOW, bool(code & 0b01)
        )
        await self.async_write_coil(
            COIL_ELECTROLYSIS_POLARITY_PERIOD_HIGH, bool(code & 0b10)
        )

    async def async_set_ph_intelligent_dosing_enabled(self, enabled: bool) -> None:
        await self.async_write_coil(COIL_PH_INTELLIGENT_DOSING_ENABLE, enabled)

    async def async_set_ph_pump_stop_enabled(self, enabled: bool) -> None:
        await self.async_write_coil(COIL_PH_PUMP_STOP_ENABLE, enabled)

    async def async_set_temperature_low_alarm_enabled(self, enabled: bool) -> None:
        await self.async_write_coil(COIL_TEMPERATURE_LOW_ALARM_ENABLE, enabled)

    async def async_set_temperature_high_alarm_enabled(self, enabled: bool) -> None:
        await self.async_write_coil(COIL_TEMPERATURE_HIGH_ALARM_ENABLE, enabled)

    async def async_set_salt_low_alarm_enabled(self, enabled: bool) -> None:
        await self.async_write_coil(COIL_SALT_LOW_ALARM_ENABLE, enabled)

    async def async_set_salt_high_alarm_enabled(self, enabled: bool) -> None:
        await self.async_write_coil(COIL_SALT_HIGH_ALARM_ENABLE, enabled)
