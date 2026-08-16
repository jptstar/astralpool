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
