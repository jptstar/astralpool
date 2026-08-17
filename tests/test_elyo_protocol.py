"""Basic behavior tests for the Pro Elyo Touch Modbus API without Home Assistant."""

import asyncio
import importlib.util
from pathlib import Path
import sys
import types


def _load_api_module():
    package_name = "elyo_protocol_test"
    package_path = Path("custom_components/astralpool/devices/elyo_touch").resolve()

    package = types.ModuleType(package_name)
    package.__path__ = [str(package_path)]
    sys.modules[package_name] = package

    pymodbus = types.ModuleType("pymodbus")
    pymodbus_client = types.ModuleType("pymodbus.client")
    pymodbus_exceptions = types.ModuleType("pymodbus.exceptions")

    class DummyClient:
        def __init__(self, *args, **kwargs) -> None:
            self.connected = True

    pymodbus_client.AsyncModbusTcpClient = DummyClient
    pymodbus_exceptions.ModbusException = Exception
    sys.modules["pymodbus"] = pymodbus
    sys.modules["pymodbus.client"] = pymodbus_client
    sys.modules["pymodbus.exceptions"] = pymodbus_exceptions

    for module_name in ("const", "api"):
        qualified_name = f"{package_name}.{module_name}"
        spec = importlib.util.spec_from_file_location(
            qualified_name, package_path / f"{module_name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[qualified_name] = module
        spec.loader.exec_module(module)

    return sys.modules[f"{package_name}.api"]


def test_signed_register_conversion() -> None:
    api_module = _load_api_module()
    assert api_module.ElyoTouchApi._s16(250) == 250
    assert api_module.ElyoTouchApi._s16(0xFFF6) == -10


def test_heat_mode_updates_control_word_bits() -> None:
    api_module = _load_api_module()
    api = api_module.ElyoTouchApi("127.0.0.1", 502, 5, 10, 9)
    writes: list[tuple[int, int]] = []

    async def update_control(mask: int, value: int) -> None:
        writes.append((mask, value))

    api._update_control = update_control
    asyncio.run(api.async_set_hvac_mode("heat"))

    assert writes == [((0b11 << 1) | (1 << 8), (2 << 1) | (1 << 8))]


def test_control_word_is_authoritative_for_selected_hvac_mode() -> None:
    api_module = _load_api_module()
    api = api_module.ElyoTouchApi

    assert api._control_hvac_mode(1 << 1) == "cool"
    assert api._control_hvac_mode(2 << 1) == "heat"
    assert api._control_hvac_mode(3 << 1) == "auto"
    assert api._control_hvac_mode(0) is None

    # Status bits 1-2 remain available as diagnostics, but are intentionally
    # decoded separately because the Modbus table marks them as not coherent
    # with the Control Word.
    assert api._status_hvac_mode(0) == "standby"
    assert api._status_hvac_mode(1 << 1) == "cool"
    assert api._status_hvac_mode(2 << 1) == "heat"
    assert api._status_hvac_mode(3 << 1) == "auto"


def test_active_inverter_mode_has_no_fake_smart_fallback() -> None:
    api_module = _load_api_module()
    api = api_module.ElyoTouchApi

    assert api._active_preset_mode(1 << 9) == "silent"
    assert api._active_preset_mode(2 << 9) == "smart"
    assert api._active_preset_mode(3 << 9) == "powerful"
    assert api._active_preset_mode(0) is None
    assert api._active_preset_mode(7 << 9) is None


def test_real_hvac_action_uses_start_defrost_compressor_and_valve_bits() -> None:
    api_module = _load_api_module()
    action = api_module.ElyoTouchApi._hvac_action

    assert action(0) == "off"
    assert action(1 << 8) == "idle"
    assert action((1 << 8) | (1 << 6)) == "heating"
    assert action((1 << 8) | (1 << 6) | (1 << 4)) == "cooling"
    assert action((1 << 8) | (1 << 5) | (1 << 6) | (1 << 4)) == "defrosting"


def test_temperature_limit_uses_control_word_not_incoherent_status_bits() -> None:
    api_module = _load_api_module()
    api = api_module.ElyoTouchApi("127.0.0.1", 502, 5, 10, 9)
    writes: list[tuple[int, int]] = []

    async def read_holding(address: int, count: int) -> list[int]:
        assert address == api_module.HR_CONTROL_WORD
        assert count == 1
        # Cooling selected in Control Word.
        return [1 << 1]

    async def write_register(address: int, value: int) -> None:
        writes.append((address, value))

    api._hr = read_holding
    api._write_register = write_register

    asyncio.run(api.async_set_temperature(35))
    assert writes == [(api_module.HR_TEMPERATURE_SETPOINT, 350)]

    try:
        asyncio.run(api.async_set_temperature(36))
    except ValueError as err:
        assert "35" in str(err)
    else:
        raise AssertionError("Cooling setpoint above 35 °C should be rejected")
