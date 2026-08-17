"""Behavior tests for the Smart Next Modbus API without Home Assistant."""

import asyncio
import importlib.util
from pathlib import Path
import sys
import types


def _load_api_module():
    package_name = "smartnext_protocol_test"
    package_path = Path("custom_components/astralpool/devices/smartnext").resolve()

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


def test_read_all_decodes_verified_software_200_points() -> None:
    api_module = _load_api_module()
    api = api_module.SmartNextApi("127.0.0.1", 502, 5, 10, 2)

    holding = {
        (0x04, 8): [0x50, 12, 0x4037, 2, 200, 1, 2, 3],
        (0x0D, 1): [0x233],
        (0x30, 1): [0b01],
        (0x40, 5): [(1 << 1) | (1 << 2) | (1 << 4) | (1 << 5) | (3 << 9), 70, 50, 0, 0x011E],
        (0x51, 2): [650, 850],
        (0x55, 4): [60, (1 << 6) | (1 << 12), 740, 120],
        (0x81, 2): [600, 855],
        (0x87, 1): [720],
        (0xB0, 4): [(1 << 11) | (1 << 12), 0, 100, 330],
        (0xC0, 1): [(1 << 11) | (1 << 12)],
        (0xC1, 3): [250, 800, 0],
        (0xC1, 2): [250, 800],
    }
    inputs = {
        (0x41, 5): [70, 65, 1741, 2450, 17],
        (0x48, 4): [2, 1, 4, 0],
        (0x51, 1): [745],
        (0x57, 2): [120, 33],
        (0x5A, 2): [88, 12],
        (0x81, 1): [731],
        (0xB1, 1): [297],
        (0xC1, 1): [301],
    }
    discrete = {
        (0x200, 3): [True, False, False],
        (0x240, 3): [False, False, False],
        (0x300, 3): [True, False, True],
        (0x250, 3): [False, False, False],
        (0x260, 8): [False] * 8,
        (0x270, 2): [False, False],
        (0x280, 2): [False, False],
        (0x290, 2): [False, False],
        (0x400, 7): [True, False, True, True, True, True, False],
        (0x500, 2): [False, False],
        (0x560, 1): [True],
        (0x802, 1): [False],
        (0xB01, 1): [False],
        (0xC00, 3): [False, False, False],
    }

    async def read_holding(address: int, count: int) -> list[int]:
        return holding[(address, count)]

    async def read_input(address: int, count: int) -> list[int]:
        return inputs[(address, count)]

    async def read_discrete(address: int, count: int) -> list[bool]:
        return discrete[(address, count)]

    async def read_coils(address: int, count: int) -> list[bool]:
        assert (address, count) == (0x230B, 1)
        return [True]

    api._read_holding_registers = read_holding
    api._read_input_registers = read_input
    api._read_discrete_inputs = read_discrete
    api._read_coils = read_coils
    data = asyncio.run(api.async_read_all())

    assert data["product_capacity"] == 12
    assert data["hardware_version"] == "0x0002"
    assert data["firmware_version"] == "2.00"
    assert data["firmware_version_raw"] == 200
    assert data["serial_number"] == "000100020003"
    assert data["boost_mode"] is True
    assert data["boost_remaining_time"] == 90
    assert data["polarity_reversal_period"] == 7
    assert data["internal_flow_sensor_enabled"] is True
    assert data["external_flow_sensor_enabled"] is False
    assert data["ph_intelligent_dosing_enabled"] is True
    assert data["ph_pump_stop_enabled"] is True
    assert data["ph_low_alarm_limit"] == 6.5
    assert data["ph_high_alarm_limit"] == 8.5
    assert data["orp_low_alarm_limit"] == 600
    assert data["orp_high_alarm_limit"] == 855
    assert data["internal_air_bubble_detected"] is True
    assert data["external_flow_switch_open"] is True
    assert data["external_chlorine_control_input"] is True
    assert data["internal_orp_control_stop"] is True
    assert data["external_control_stop"] is False
    assert data["temperature"] == 29.7
    assert data["salt"] == 3.01
    assert data["salt_min"] == 2.5
    assert data["salt_max"] == 8.0
    assert data["eco_mode"] is True


def test_conductivity_layout_detection_supports_v170_and_v200() -> None:
    api_module = _load_api_module()
    detect = api_module.SmartNextApi._detect_salt_threshold_addresses
    assert detect([250, 800, 0]) == (0xC1, 0xC2)
    assert detect([0, 250, 800]) == (0xC2, 0xC3)


def test_firmware_version_decoder_supports_decimal_and_legacy_encoding() -> None:
    api_module = _load_api_module()
    decode = api_module.SmartNextApi._decode_firmware_version
    assert decode(170) == "1.70"
    assert decode(200) == "2.00"
    assert decode(0x0170) == "1.70"
    assert decode(0x0200) == "2.00"


def test_polarity_period_writes_only_its_two_documented_coils() -> None:
    api_module = _load_api_module()
    api = api_module.SmartNextApi("127.0.0.1", 502, 5, 10, 2)
    writes: list[tuple[int, bool]] = []

    async def write_coil(address: int, value: bool) -> None:
        writes.append((address, value))

    api.async_write_coil = write_coil
    asyncio.run(api.async_set_polarity_reversal_period(7))

    assert writes == [(0x409, True), (0x40A, True)]


def test_salt_limit_writes_follow_detected_layout() -> None:
    api_module = _load_api_module()
    api = api_module.SmartNextApi("127.0.0.1", 502, 5, 10, 2)
    api._salt_threshold_addresses_cache = (0xC1, 0xC2)
    writes: list[tuple[int, int]] = []

    async def write_register(address: int, value: int) -> None:
        writes.append((address, value))

    api.async_write_register = write_register
    asyncio.run(api.async_set_salt_min(2.5))
    asyncio.run(api.async_set_salt_max(8.0))
    assert writes == [(0xC1, 250), (0xC2, 800)]


def test_identification_is_optional_for_older_firmware() -> None:
    api_module = _load_api_module()
    api = api_module.SmartNextApi("127.0.0.1", 502, 5, 10, 2)

    async def unavailable(address: int, count: int) -> list[int]:
        raise api_module.SmartNextCommunicationError("illegal address")

    api._read_holding_registers = unavailable

    assert asyncio.run(api._async_read_identification()) == {}
    assert asyncio.run(api._async_read_identification()) == {}
