"""Async Modbus TCP API for SmartNext."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import (
    COIL_PH_PUMP_STOP_RESET,
    DI_COVER_ACTIVE,
    DI_COVER_INPUT,
    DI_ELECTROLYSIS_CHECK_CELL,
    DI_ELECTROLYSIS_HIGH_CONDUCTIVITY,
    DI_ELECTROLYSIS_LOW_CONDUCTIVITY,
    DI_ELECTROLYSIS_POLARITY,
    DI_ELECTROLYSIS_RUNNING,
    DI_FLOW_EXTERNAL_SWITCH,
    DI_FLOW_GENERAL,
    DI_FLOW_INTERNAL,
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
    HR_ELECTROLYSIS_COVER_SETPOINT,
    HR_ELECTROLYSIS_NORMAL_SETPOINT,
    HR_ORP_SETPOINT,
    HR_PH_DOSAGE_LIMIT,
    HR_PH_INIT_TIME,
    HR_PH_SETPOINT,
    HR_SALT_MAX,
    HR_SALT_MIN,
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

    async def async_reset_ph_pump_stop(self) -> None:
        """Rearm the pH pump-stop using coil 0x56D."""
        await self.async_write_coil(COIL_PH_PUMP_STOP_RESET, True)
        await asyncio.sleep(0.2)
        await self.async_write_coil(COIL_PH_PUMP_STOP_RESET, False)

    async def async_read_all(self) -> dict[str, Any]:
        """Read the verified SmartNext v1.70 points."""
        data: dict[str, Any] = {}

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
        # Protocol v1.70: bit 9 = Biopool mode enabled.
        data["biopool_mode"] = bool(technologies_enabled & (1 << 9))

        electrolysis_setpoints = await self._read_holding_registers(0x41, 2)
        data["electrolysis_normal_setpoint"] = electrolysis_setpoints[
            HR_ELECTROLYSIS_NORMAL_SETPOINT - 0x41
        ]
        data["electrolysis_cover_setpoint"] = electrolysis_setpoints[
            HR_ELECTROLYSIS_COVER_SETPOINT - 0x41
        ]

        data["ph_init_time"] = (
            await self._read_holding_registers(HR_PH_INIT_TIME, 1)
        )[0]
        ph_config = await self._read_holding_registers(HR_PH_SETPOINT, 2)
        data["ph_setpoint"] = ph_config[HR_PH_SETPOINT - 0x57] / 100
        data["ph_dosage_limit"] = ph_config[HR_PH_DOSAGE_LIMIT - 0x57]

        data["orp_setpoint"] = (
            await self._read_holding_registers(HR_ORP_SETPOINT, 1)
        )[0]

        temp_limits = await self._read_holding_registers(HR_TEMPERATURE_MIN, 2)
        data["temperature_min"] = temp_limits[0] / 10
        data["temperature_max"] = temp_limits[1] / 10

        salt_limits = await self._read_holding_registers(HR_SALT_MIN, 2)
        data["salt_min"] = salt_limits[0] / 100
        data["salt_max"] = salt_limits[1] / 100

        # General status.
        general = await self._read_discrete_inputs(DI_GENERAL_ALARM, 3)
        data["general_alarm"] = general[0]
        data["treatment_halted"] = general[DI_TREATMENT_HALTED - DI_GENERAL_ALARM]

        # Alarm groups.
        flow = await self._read_discrete_inputs(DI_FLOW_GENERAL, 3)
        data["flow_alarm"] = flow[0]
        data["internal_flow_alarm"] = flow[1]
        data["external_flow_switch_alarm"] = flow[2]

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
            DI_ELECTROLYSIS_RUNNING, 4
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
