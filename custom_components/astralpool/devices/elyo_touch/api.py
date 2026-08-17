"""Async Modbus TCP API for AstralPool Pro Elyo Touch."""
from __future__ import annotations

import asyncio
from typing import Any

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import (
    ALARM_KEYS,
    COIL_HVAC_MODE_BIT1,
    COIL_HVAC_MODE_BIT2,
    COIL_POWER,
    COIL_PRESET_BIT10,
    COIL_PRESET_BIT11,
    COIL_PRESET_BIT9,
    HR_ALARM_COUNTERS_COUNT,
    HR_ALARM_COUNTERS_START,
    HR_COMPRESSOR_STARTS,
    HR_CONTROL_WORD,
    HR_HARDWARE_VERSION,
    HR_HP_CYCLES,
    HR_MODEL_PRODUCTION,
    HR_MODEL_SERIE_HIGH,
    HR_MODEL_SERIE_LOW,
    HR_PRODUCT_CODE_HIGH,
    HR_PRODUCT_CODE_LOW,
    HR_SOFTWARE_VERSION,
    HR_SYSTEM_TIME,
    HR_TEMPERATURE_SETPOINT,
    HR_TIMER_START,
    HR_TIMER_STOP,
    IR_ALARMS_1,
    IR_ALARMS_2,
    IR_AMBIENT_TEMPERATURE,
    IR_COIL_TEMPERATURE,
    IR_COMPRESSOR_CURRENT,
    IR_COMPRESSOR_FREQUENCY,
    IR_EXPANSION_VALVE_STEP,
    IR_FAN_SPEED,
    IR_GAS_EXHAUST_TEMPERATURE,
    IR_GAS_RETURN_TEMPERATURE,
    IR_INLET_TEMPERATURE,
    IR_OUTLET_TEMPERATURE,
    IR_STATUS,
)


class ElyoTouchCommunicationError(Exception):
    """Communication failure."""


class ElyoTouchApi:
    """Modbus API for a Pro Elyo Touch heat pump."""

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
        """Return whether the Modbus client is connected."""
        return bool(self._client.connected)

    async def async_connect(self) -> None:
        """Connect to the gateway."""
        try:
            if not await self._client.connect():
                raise ElyoTouchCommunicationError(
                    f"Unable to connect to {self.host}:{self.port}"
                )
        except (OSError, ModbusException) as err:
            raise ElyoTouchCommunicationError(str(err)) from err

    async def async_close(self) -> None:
        """Close the Modbus client."""
        self._client.close()

    @staticmethod
    def _check(response: Any, operation: str) -> Any:
        if response is None or response.isError():
            raise ElyoTouchCommunicationError(
                f"Modbus error while {operation}: {response!r}"
            )
        return response

    async def _ensure(self) -> None:
        if not self._client.connected:
            await self.async_connect()

    async def _read(self, kind: str, address: int, count: int) -> list[int]:
        async with self._lock:
            await self._ensure()
            try:
                method = getattr(self._client, f"read_{kind}_registers")
                response = await method(
                    address,
                    count=count,
                    device_id=self.unit_id,
                )
            except (OSError, ModbusException) as err:
                raise ElyoTouchCommunicationError(str(err)) from err
            return list(
                self._check(
                    response,
                    f"reading {kind} registers {address}:{count}",
                ).registers
            )

    async def _ir(self, address: int, count: int) -> list[int]:
        return await self._read("input", address, count)

    async def _hr(self, address: int, count: int) -> list[int]:
        return await self._read("holding", address, count)

    async def _write_register(self, address: int, value: int) -> None:
        async with self._lock:
            await self._ensure()
            try:
                response = await self._client.write_register(
                    address,
                    value,
                    device_id=self.unit_id,
                )
            except (OSError, ModbusException) as err:
                raise ElyoTouchCommunicationError(str(err)) from err
            self._check(response, f"writing holding register {address}")

    async def _write_coil(self, address: int, value: bool) -> None:
        """Write one documented bit-addressable Pro Elyo control."""
        async with self._lock:
            await self._ensure()
            try:
                response = await self._client.write_coil(
                    address,
                    value,
                    device_id=self.unit_id,
                )
            except (OSError, ModbusException) as err:
                raise ElyoTouchCommunicationError(str(err)) from err
            self._check(response, f"writing coil {address}")

    @staticmethod
    def _s16(value: int) -> int:
        return value - 0x10000 if value & 0x8000 else value

    @staticmethod
    def _combine_serial(high: int, low: int) -> int:
        """Combine the documented Pro Elyo MODEL_Serie high/low words."""
        return (high << 16) | low

    @staticmethod
    def _control_hvac_mode(control_word: int) -> str | None:
        """Decode the requested HVAC mode from Control Word bits 1-2."""
        return {
            1: "cool",
            2: "heat",
            3: "auto",
        }.get((control_word >> 1) & 0b11)

    @staticmethod
    def _status_hvac_mode(status_word: int) -> str:
        """Decode Status bits 1-2 for diagnostics only.

        The Pro Elyo Modbus table explicitly marks this field as not coherent
        with the Control Word, so it must not be used as the selected HVAC mode.
        """
        return {
            0: "standby",
            1: "cool",
            2: "heat",
            3: "auto",
        }[(status_word >> 1) & 0b11]

    @staticmethod
    def _control_preset_mode(control_word: int) -> str | None:
        """Decode the requested inverter mode from Control Word bits 9-11."""
        return {
            1: "Silent",
            2: "Smart",
            3: "Turbo",
        }.get((control_word >> 9) & 0b111)

    @staticmethod
    def _active_preset_mode(status_word: int) -> str | None:
        """Decode the active inverter mode from Status bits 9-11."""
        return {
            1: "Silent",
            2: "Smart",
            3: "Turbo",
        }.get((status_word >> 9) & 0b111)

    @staticmethod
    def _hvac_action(status_word: int) -> str:
        """Return the real operating action from physical status bits.

        bit 8: heat-pump Stop/Start
        bit 5: defrost
        bit 6: compressor OFF/ON
        bit 4: four-way valve Heating/Cooling
        """
        running = bool(status_word & (1 << 8))
        if not running:
            return "off"
        if status_word & (1 << 5):
            return "defrosting"
        if not status_word & (1 << 6):
            return "idle"
        if status_word & (1 << 4):
            return "cooling"
        return "heating"

    async def async_set_temperature(self, value: float) -> None:
        # The Modbus table marks Status bits 1-2 as not coherent with the
        # Control Word. Use the selected mode from the Control Word to enforce
        # the documented 35 °C cooling / 40 °C heating limit.
        control = (await self._hr(HR_CONTROL_WORD, 1))[0]
        mode = (control >> 1) & 0b11
        maximum = 35 if mode == 1 else 40
        if not 15 <= value <= maximum:
            raise ValueError(
                f"Temperature must be between 15 and {maximum} °C"
            )
        await self._write_register(
            HR_TEMPERATURE_SETPOINT,
            round(value * 10),
        )

    async def async_set_power(self, enabled: bool) -> None:
        """Start or stop the heat pump through Control Word bit 8."""
        await self._write_coil(COIL_POWER, enabled)

    async def async_set_hvac_mode(self, mode: str) -> None:
        """Set Cool/Heat/Auto through the documented bit-addressable coils."""
        codes = {"cool": 1, "heat": 2, "auto": 3, "off": 0}
        if mode == "off":
            await self.async_set_power(False)
            return

        code = codes[mode]
        # Match the known-good Node-RED implementation: 0x211 and 0x212 are
        # the bit-addressable aliases for Control Word bits 1 and 2. Set the
        # selected mode before asserting Start so an idle unit never starts in
        # a stale mode.
        await self._write_coil(COIL_HVAC_MODE_BIT1, bool(code & 0b01))
        await self._write_coil(COIL_HVAC_MODE_BIT2, bool(code & 0b10))
        await self._write_coil(COIL_POWER, True)

    async def async_set_preset(self, preset: str) -> None:
        """Set Silent/Smart/Turbo through Control Word bits 9-11."""
        # Keep the old lowercase names as service-call aliases so existing
        # automations keep working while the Home Assistant UI uses the final
        # Silent / Smart / Turbo labels.
        codes = {"silent": 1, "smart": 2, "turbo": 3, "powerful": 3}
        code = codes[preset.strip().lower()]

        # The supplied Node-RED flow writes coils 0x219, 0x21A and 0x21B.
        # Clear the unsupported/TBD high bit first, then write the two defined
        # bits. This also avoids rewriting unrelated Control Word fields.
        await self._write_coil(COIL_PRESET_BIT11, bool(code & 0b100))
        await self._write_coil(COIL_PRESET_BIT9, bool(code & 0b001))
        await self._write_coil(COIL_PRESET_BIT10, bool(code & 0b010))

    async def async_set_clock(self, address: int, value: Any) -> None:
        await self._write_register(address, value.hour * 60 + value.minute)

    async def async_read_all(self) -> dict[str, Any]:
        identity = await self._hr(
            HR_PRODUCT_CODE_HIGH,
            HR_MODEL_PRODUCTION - HR_PRODUCT_CODE_HIGH + 1,
        )
        control = (await self._hr(HR_CONTROL_WORD, 1))[0]
        setpoint = (await self._hr(HR_TEMPERATURE_SETPOINT, 1))[0]
        counters = await self._hr(HR_HP_CYCLES, 2)
        clock = await self._hr(HR_SYSTEM_TIME, 1)
        timer = await self._hr(HR_TIMER_START, 2)
        try:
            alarm_counters = await self._hr(
                HR_ALARM_COUNTERS_START,
                HR_ALARM_COUNTERS_COUNT,
            )
        except ElyoTouchCommunicationError:
            alarm_counters = [None] * HR_ALARM_COUNTERS_COUNT

        status_and_alarm = await self._ir(IR_STATUS, 2)
        temps = await self._ir(IR_AMBIENT_TEMPERATURE, 3)
        alarm2 = (await self._ir(IR_ALARMS_2, 1))[0]
        technical = await self._ir(
            IR_EXPANSION_VALVE_STEP,
            IR_FAN_SPEED - IR_EXPANSION_VALVE_STEP + 1,
        )

        status, alarm1 = status_and_alarm
        serial = self._combine_serial(
            identity[HR_MODEL_SERIE_HIGH - HR_PRODUCT_CODE_HIGH],
            identity[HR_MODEL_SERIE_LOW - HR_PRODUCT_CODE_HIGH],
        )
        running = bool(status & (1 << 8))
        selected_hvac_mode = self._control_hvac_mode(control)
        selected_preset_mode = self._control_preset_mode(control)
        active_preset_mode = self._active_preset_mode(status)

        data: dict[str, Any] = {
            "product_code": (identity[0] << 16)
            | identity[HR_PRODUCT_CODE_LOW - HR_PRODUCT_CODE_HIGH],
            "hardware_version": str(
                identity[HR_HARDWARE_VERSION - HR_PRODUCT_CODE_HIGH]
            ),
            "firmware_version": str(
                identity[HR_SOFTWARE_VERSION - HR_PRODUCT_CODE_HIGH]
            ),
            "serial_number": f"{serial:08X}" if serial else None,
            "model_production": identity[
                HR_MODEL_PRODUCTION - HR_PRODUCT_CODE_HIGH
            ],
            "control_word": control,
            "status_word": status,
            "temperature_setpoint": setpoint / 10,
            "hp_cycles": counters[0],
            "compressor_starts": counters[1],
            "system_time": clock[0],
            "timer_start": timer[0],
            "timer_stop": timer[1],
            "ambient_temperature": self._s16(temps[0]) / 10,
            "inlet_temperature": self._s16(temps[1]) / 10,
            "outlet_temperature": self._s16(temps[2]) / 10,
            "expansion_valve_step": technical[0],
            "gas_return_temperature": self._s16(
                technical[
                    IR_GAS_RETURN_TEMPERATURE - IR_EXPANSION_VALVE_STEP
                ]
            )
            / 10,
            "coil_temperature": self._s16(
                technical[IR_COIL_TEMPERATURE - IR_EXPANSION_VALVE_STEP]
            )
            / 10,
            "gas_exhaust_temperature": self._s16(
                technical[
                    IR_GAS_EXHAUST_TEMPERATURE - IR_EXPANSION_VALVE_STEP
                ]
            )
            / 10,
            "compressor_current": technical[
                IR_COMPRESSOR_CURRENT - IR_EXPANSION_VALVE_STEP
            ],
            "compressor_frequency": technical[
                IR_COMPRESSOR_FREQUENCY - IR_EXPANSION_VALVE_STEP
            ],
            "fan_speed": technical[IR_FAN_SPEED - IR_EXPANSION_VALVE_STEP],
            "alarm": bool(status & 1),
            "filter_priority_mode": bool(status & (1 << 3)),
            "four_way_valve_cooling": bool(status & (1 << 4)),
            "defrost": bool(status & (1 << 5)),
            "compressor_running": bool(status & (1 << 6)),
            "running": running,
            "timer_enabled": bool(status & (1 << 12)),
            # Climate mode follows the reliable Control Word, but OFF follows
            # the real Start/Stop feedback from Status bit 8.
            "selected_hvac_mode": selected_hvac_mode,
            "reported_hvac_mode": self._status_hvac_mode(status),
            "hvac_mode": (
                "off" if not running else selected_hvac_mode
            ),
            # The climate preset is the selected/memorized Control Word value.
            # Active inverter feedback is retained separately because Status
            # can legitimately report 000 while the compressor is idle.
            "selected_preset_mode": selected_preset_mode,
            "preset_mode": selected_preset_mode,
            "active_preset_mode": active_preset_mode,
            "hvac_action": self._hvac_action(status),
        }

        for index, key in enumerate(ALARM_KEYS):
            word, bit = (
                (alarm1, index)
                if index < 16
                else (alarm2, index - 16)
            )
            data[f"alarm_{key}"] = bool(word & (1 << bit))
            data[f"alarm_count_{key}"] = alarm_counters[index]

        return data
