"""Tests for the hardware-validated Smart Next temperature calibration."""

import ast
from pathlib import Path


MODULE = Path(
    "custom_components/astralpool/devices/smartnext/temperature_calibration.py"
)


def _source() -> str:
    return MODULE.read_text(encoding="utf-8")


def test_temperature_calibration_sequence_is_reference_then_b0f() -> None:
    """Keep the hardware-validated HR 0x22 -> B0F -> 15 s order."""
    source = _source()
    assert "raw_value = round(reference_temperature * 10)" in source
    register_write = "await api.async_write_register(HR_CALIBRATION_VALUE, raw_value)"
    calibration_write = "await api.async_write_coil(COIL_TEMPERATURE_CALIBRATION, True)"
    wait = "await asyncio.sleep(TEMPERATURE_CALIBRATION_DELAY_SECONDS)"
    assert source.index(register_write) < source.index(calibration_write) < source.index(wait)


def test_temperature_factory_reset_is_b0d_then_15_seconds() -> None:
    """Keep the hardware-validated B0D -> 15 s factory reset sequence."""
    source = _source()
    reset_write = (
        "await api.async_write_coil(COIL_TEMPERATURE_CALIBRATION_RESET, True)"
    )
    wait = "await asyncio.sleep(TEMPERATURE_CALIBRATION_DELAY_SECONDS)"
    function = source.split("async def async_reset_temperature_calibration", 1)[1]
    assert function.index(reset_write) < function.index(wait)


def test_temperature_calibration_delay_is_exactly_15_seconds() -> None:
    """The real controller needs 15 seconds before the new value is applied."""
    tree = ast.parse(_source())
    assignments = {
        target.id: node.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and isinstance(node.value, ast.Constant)
        for target in [node.target]
    }
    assert assignments["TEMPERATURE_CALIBRATION_DELAY_SECONDS"] == 15.0
