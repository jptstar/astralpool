"""Tests for guided Smart Next maintenance procedures."""

import asyncio
import importlib.util
from pathlib import Path
import sys
import types

import pytest


ROOT = Path("custom_components/astralpool/devices/smartnext").resolve()


def _load_maintenance_module():
    package_name = "smartnext_maintenance_test"
    package = types.ModuleType(package_name)
    package.__path__ = [str(ROOT)]
    sys.modules[package_name] = package

    for module_name in ("const", "maintenance"):
        qualified_name = f"{package_name}.{module_name}"
        spec = importlib.util.spec_from_file_location(
            qualified_name, ROOT / f"{module_name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[qualified_name] = module
        spec.loader.exec_module(module)

    return sys.modules[f"{package_name}.maintenance"]


class FakeApi:
    def __init__(self) -> None:
        self.coil_writes: list[tuple[int, bool]] = []
        self.register_writes: list[tuple[int, int]] = []
        self.coils: dict[int, bool] = {}
        self.input_responses: list[int] = [0]
        self.discrete_responses: list[bool] = [True, False]
        self.discrete_reads: list[int] = []
        self.holding = [0, 1]

    async def async_write_coil(self, address: int, value: bool) -> None:
        self.coil_writes.append((address, value))
        self.coils[address] = value

    async def _read_coils(self, address: int, count: int) -> list[bool]:
        assert count == 1
        # Maintenance command coils are modeled as volatile one-shot commands.
        self.coils[address] = False
        return [False]

    async def _read_input_registers(self, address: int, count: int) -> list[int]:
        assert address == 0x22
        assert count == 1
        if len(self.input_responses) > 1:
            return [self.input_responses.pop(0)]
        return [self.input_responses[0]]

    async def _read_discrete_inputs(self, address: int, count: int) -> list[bool]:
        assert address == 0x202
        assert count == 1
        self.discrete_reads.append(address)
        if len(self.discrete_responses) > 1:
            return [self.discrete_responses.pop(0)]
        return [self.discrete_responses[0]]

    async def _read_holding_registers(self, address: int, count: int) -> list[int]:
        assert (address, count) == (0x10, 2)
        return list(self.holding)

    async def async_write_register(self, address: int, value: int) -> None:
        self.register_writes.append((address, value))


def test_configuration_reset_is_a_documented_one_shot_command() -> None:
    maintenance = _load_maintenance_module()
    api = FakeApi()

    result = asyncio.run(
        maintenance.async_run_config_reset(api, maintenance.ACTION_RESET_FLOW_CONFIG)
    )

    assert result == "ok"
    assert api.coil_writes == [(0x30C, True)]


def test_ph_calibration_reset_waits_for_treatment_halted() -> None:
    maintenance = _load_maintenance_module()
    api = FakeApi()
    api.input_responses = [0, 1]
    api.discrete_responses = [False, True, False]

    result = asyncio.run(
        maintenance.async_run_calibration_reset(
            api, maintenance.ACTION_RESET_PH_CALIBRATION
        )
    )

    assert result == "ok"
    assert api.coil_writes == [
        (0x203, True),
        (0x201, True),
        (0x50C, True),
        (0x201, False),
    ]
    assert len(api.discrete_reads) >= 3
    assert all(address == 0x202 for address in api.discrete_reads)


def test_temperature_and_salt_use_calibration_reset_bits_not_config_bits() -> None:
    maintenance = _load_maintenance_module()
    assert maintenance.CALIBRATION_RESET_COILS[
        maintenance.ACTION_RESET_TEMPERATURE_CALIBRATION
    ] == 0xB0D
    assert maintenance.CALIBRATION_RESET_COILS[
        maintenance.ACTION_RESET_SALT_CALIBRATION
    ] == 0xC0D


def test_temperature_reset_uses_same_confirmed_calibration_workflow() -> None:
    maintenance = _load_maintenance_module()
    api = FakeApi()
    api.input_responses = [0, 1]
    api.discrete_responses = [True, False]

    result = asyncio.run(
        maintenance.async_run_calibration_reset(
            api, maintenance.ACTION_RESET_TEMPERATURE_CALIBRATION
        )
    )

    assert result == "ok"
    assert (0xB0D, True) in api.coil_writes
    assert api.coil_writes.index((0x201, True)) < api.coil_writes.index((0xB0D, True))
    assert api.coil_writes[-1] == (0x201, False)


def test_calibration_error_still_leaves_calibration_mode() -> None:
    maintenance = _load_maintenance_module()
    api = FakeApi()
    api.input_responses = [0, 2]
    api.discrete_responses = [True, False]

    with pytest.raises(maintenance.SmartNextMaintenanceError, match="e2"):
        asyncio.run(
            maintenance.async_run_calibration_reset(
                api, maintenance.ACTION_RESET_ORP_CALIBRATION
            )
        )

    assert api.coil_writes[-1] == (0x201, False)


def test_watchdog_restart_is_only_armed_when_action_is_restart() -> None:
    maintenance = _load_maintenance_module()
    api = FakeApi()

    previous = asyncio.run(maintenance.async_arm_restart_watchdog(api))

    assert previous == 0
    assert api.register_writes == [(0x10, 60)]


def test_watchdog_restart_refuses_other_watchdog_behaviour() -> None:
    maintenance = _load_maintenance_module()
    api = FakeApi()
    api.holding = [0, 2]

    with pytest.raises(
        maintenance.SmartNextMaintenanceError, match="watchdog_not_restart"
    ):
        asyncio.run(maintenance.async_arm_restart_watchdog(api))

    assert api.register_writes == []
