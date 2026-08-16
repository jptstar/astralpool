"""Async Modbus TCP API for AstralPool Pro Elyo Touch."""
from __future__ import annotations
import asyncio
from typing import Any
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from .const import (
    ALARM_KEYS, HR_ALARM_COUNTERS_COUNT, HR_ALARM_COUNTERS_START,
    HR_COMPRESSOR_STARTS, HR_CONTROL_WORD, HR_HARDWARE_VERSION,
    HR_HP_CYCLES, HR_PRODUCT_CODE_HIGH, HR_PRODUCT_CODE_LOW, HR_SOFTWARE_VERSION,
    HR_SYSTEM_TIME, HR_TEMPERATURE_SETPOINT, HR_TIMER_START, HR_TIMER_STOP,
    IR_ALARMS_1, IR_ALARMS_2, IR_AMBIENT_TEMPERATURE,
    IR_COIL_TEMPERATURE, IR_COMPRESSOR_CURRENT, IR_COMPRESSOR_FREQUENCY,
    IR_EXPANSION_VALVE_STEP, IR_FAN_SPEED, IR_GAS_EXHAUST_TEMPERATURE,
    IR_GAS_RETURN_TEMPERATURE, IR_INLET_TEMPERATURE, IR_OUTLET_TEMPERATURE,
    IR_STATUS,
)

class ElyoTouchCommunicationError(Exception):
    """Communication failure."""

class ElyoTouchApi:
    def __init__(self, host: str, port: int, timeout: float, reconnect_delay: float, unit_id: int) -> None:
        self.host, self.port, self.timeout = host, port, timeout
        self.reconnect_delay, self.unit_id = reconnect_delay, unit_id
        self._lock = asyncio.Lock()
        self._client = AsyncModbusTcpClient(host, port=port, timeout=timeout, reconnect_delay=reconnect_delay)

    @property
    def connected(self) -> bool: return bool(self._client.connected)

    async def async_connect(self) -> None:
        try:
            if not await self._client.connect():
                raise ElyoTouchCommunicationError(f"Unable to connect to {self.host}:{self.port}")
        except (OSError, ModbusException) as err: raise ElyoTouchCommunicationError(str(err)) from err

    async def async_close(self) -> None: self._client.close()

    @staticmethod
    def _check(response: Any, operation: str) -> Any:
        if response is None or response.isError():
            raise ElyoTouchCommunicationError(f"Modbus error while {operation}: {response!r}")
        return response

    async def _ensure(self) -> None:
        if not self._client.connected: await self.async_connect()

    async def _read(self, kind: str, address: int, count: int) -> list[int]:
        async with self._lock:
            await self._ensure()
            try:
                method = getattr(self._client, f"read_{kind}_registers")
                response = await method(address, count=count, device_id=self.unit_id)
            except (OSError, ModbusException) as err: raise ElyoTouchCommunicationError(str(err)) from err
            return list(self._check(response, f"reading {kind} registers {address}:{count}").registers)

    async def _ir(self, address: int, count: int) -> list[int]: return await self._read("input", address, count)
    async def _hr(self, address: int, count: int) -> list[int]: return await self._read("holding", address, count)

    async def _write_register(self, address: int, value: int) -> None:
        async with self._lock:
            await self._ensure()
            try: response = await self._client.write_register(address, value, device_id=self.unit_id)
            except (OSError, ModbusException) as err: raise ElyoTouchCommunicationError(str(err)) from err
            self._check(response, f"writing holding register {address}")

    @staticmethod
    def _s16(value: int) -> int: return value - 0x10000 if value & 0x8000 else value

    async def _update_control(self, mask: int, value: int) -> None:
        current = (await self._hr(HR_CONTROL_WORD, 1))[0]
        await self._write_register(HR_CONTROL_WORD, (current & ~mask) | (value & mask))

    async def async_set_temperature(self, value: float) -> None:
        mode = (await self._ir(IR_STATUS, 1))[0] >> 1 & 0b11
        maximum = 35 if mode == 1 else 40
        if not 15 <= value <= maximum:
            raise ValueError(f"Temperature must be between 15 and {maximum} °C")
        await self._write_register(HR_TEMPERATURE_SETPOINT, round(value * 10))

    async def async_set_power(self, enabled: bool) -> None:
        await self._update_control(1 << 8, (1 << 8) if enabled else 0)

    async def async_set_hvac_mode(self, mode: str) -> None:
        codes = {"cool": 1, "heat": 2, "auto": 3, "off": 0}
        if mode == "off":
            await self.async_set_power(False)
            return
        await self._update_control((0b11 << 1) | (1 << 8), (codes[mode] << 1) | (1 << 8))

    async def async_set_preset(self, preset: str) -> None:
        codes = {"silent": 1, "smart": 2, "powerful": 3}
        await self._update_control(0b111 << 9, codes[preset] << 9)

    async def async_set_clock(self, address: int, value: Any) -> None:
        await self._write_register(address, value.hour * 60 + value.minute)

    async def async_read_all(self) -> dict[str, Any]:
        identity = await self._hr(HR_PRODUCT_CODE_HIGH, HR_SOFTWARE_VERSION - HR_PRODUCT_CODE_HIGH + 1)
        control = (await self._hr(HR_CONTROL_WORD, 1))[0]
        setpoint = (await self._hr(HR_TEMPERATURE_SETPOINT, 1))[0]
        counters = await self._hr(HR_HP_CYCLES, 2)
        clock = await self._hr(HR_SYSTEM_TIME, 1)
        timer = await self._hr(HR_TIMER_START, 2)
        try:
            alarm_counters = await self._hr(HR_ALARM_COUNTERS_START, HR_ALARM_COUNTERS_COUNT)
        except ElyoTouchCommunicationError:
            alarm_counters = [None] * HR_ALARM_COUNTERS_COUNT
        status_and_alarm = await self._ir(IR_STATUS, 2)
        temps = await self._ir(IR_AMBIENT_TEMPERATURE, 3)
        alarm2 = (await self._ir(IR_ALARMS_2, 1))[0]
        technical = await self._ir(IR_EXPANSION_VALVE_STEP, IR_FAN_SPEED - IR_EXPANSION_VALVE_STEP + 1)
        status, alarm1 = status_and_alarm
        operating_code = (status >> 1) & 0b11
        preset_code = (status >> 9) & 0b111
        data: dict[str, Any] = {
            "product_code": (identity[0] << 16) | identity[HR_PRODUCT_CODE_LOW - HR_PRODUCT_CODE_HIGH],
            "hardware_version": str(identity[HR_HARDWARE_VERSION - HR_PRODUCT_CODE_HIGH]),
            "firmware_version": str(identity[HR_SOFTWARE_VERSION - HR_PRODUCT_CODE_HIGH]),
            "control_word": control, "status_word": status,
            "temperature_setpoint": setpoint / 10,
            "hp_cycles": counters[0], "compressor_starts": counters[1],
            "system_time": clock[0], "timer_start": timer[0], "timer_stop": timer[1],
            "ambient_temperature": self._s16(temps[0]) / 10,
            "inlet_temperature": self._s16(temps[1]) / 10,
            "outlet_temperature": self._s16(temps[2]) / 10,
            "expansion_valve_step": technical[0],
            "gas_return_temperature": self._s16(technical[IR_GAS_RETURN_TEMPERATURE - IR_EXPANSION_VALVE_STEP]) / 10,
            "coil_temperature": self._s16(technical[IR_COIL_TEMPERATURE - IR_EXPANSION_VALVE_STEP]) / 10,
            "gas_exhaust_temperature": self._s16(technical[IR_GAS_EXHAUST_TEMPERATURE - IR_EXPANSION_VALVE_STEP]) / 10,
            "compressor_current": technical[IR_COMPRESSOR_CURRENT - IR_EXPANSION_VALVE_STEP],
            "compressor_frequency": technical[IR_COMPRESSOR_FREQUENCY - IR_EXPANSION_VALVE_STEP],
            "fan_speed": technical[IR_FAN_SPEED - IR_EXPANSION_VALVE_STEP],
            "alarm": bool(status & 1), "filter_priority_mode": bool(status & (1 << 3)),
            "four_way_valve_cooling": bool(status & (1 << 4)), "defrost": bool(status & (1 << 5)),
            "compressor_running": bool(status & (1 << 6)), "running": bool(status & (1 << 8)),
            "timer_enabled": bool(status & (1 << 12)),
            "hvac_mode": {0: "off", 1: "cool", 2: "heat", 3: "auto"}.get(operating_code, "off"),
            "preset_mode": {1: "silent", 2: "smart", 3: "powerful"}.get(preset_code, "smart"),
        }
        for index, key in enumerate(ALARM_KEYS):
            word, bit = (alarm1, index) if index < 16 else (alarm2, index - 16)
            data[f"alarm_{key}"] = bool(word & (1 << bit))
            data[f"alarm_count_{key}"] = alarm_counters[index]
        return data
