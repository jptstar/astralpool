"""Tests for guided Smart Next pH calibration primitives."""

from __future__ import annotations

import ast
from pathlib import Path


PH = Path("custom_components/astralpool/devices/smartnext/ph_calibration.py")
TEMP = Path("custom_components/astralpool/devices/smartnext/temperature_calibration.py")
FLOW = Path("custom_components/astralpool/config_flow.py")


def test_ph_protocol_uses_documented_points() -> None:
    source = PH.read_text(encoding="utf-8")
    assert "COIL_PH_CALIBRATION_PH7" in source
    assert "COIL_PH_CALIBRATION_PH4" in source
    assert "COIL_PH_CALIBRATION_FAST" in source
    assert "COIL_PH_CALIBRATION_RESET" in source
    assert "HR_CALIBRATION_VALUE" in source
    assert "IR_CALIBRATION_RESPONSE" in source
    assert "reference_ph * 100" in source


def test_standard_ph_preparation_disables_flow_before_zero_production() -> None:
    source = PH.read_text(encoding="utf-8")
    internal = source.index("COIL_FLOW_INTERNAL_SENSOR_ENABLE, False")
    external = source.index("COIL_FLOW_EXTERNAL_SENSOR_ENABLE, False")
    production = source.index("HR_ELECTROLYSIS_NORMAL_SETPOINT, 0")
    assert internal < production
    assert external < production
    assert "production == 0 and current_raw == 0 and not running" in source


def test_standard_ph_restore_enables_flow_before_production() -> None:
    source = PH.read_text(encoding="utf-8")
    restore_function = source[source.index("async def async_restore_standard_ph_calibration"):]
    internal = restore_function.index("COIL_FLOW_INTERNAL_SENSOR_ENABLE")
    external = restore_function.index("COIL_FLOW_EXTERNAL_SENSOR_ENABLE")
    production = restore_function.index("HR_ELECTROLYSIS_NORMAL_SETPOINT")
    assert internal < production
    assert external < production
    assert "flow_not_restored" in restore_function


def test_temperature_delays_are_shortened() -> None:
    source = TEMP.read_text(encoding="utf-8")
    assert "TEMPERATURE_CALIBRATION_DELAY_SECONDS: Final = 5.0" in source
    assert "TEMPERATURE_RESET_DELAY_SECONDS: Final = 2.0" in source


def test_config_flow_contains_ph_fast_and_standard_steps() -> None:
    tree = ast.parse(FLOW.read_text(encoding="utf-8"))
    functions = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)
    }
    assert {
        "async_step_calibrate_ph",
        "async_step_calibrate_ph_fast",
        "async_step_calibrate_ph_standard_prepare",
        "async_step_calibrate_ph_standard_bypass",
        "async_step_calibrate_ph_standard_ph7",
        "async_step_calibrate_ph_standard_ph4",
        "async_step_calibrate_ph_standard_restore",
        "async_step_restore_ph_calibration",
    } <= functions
