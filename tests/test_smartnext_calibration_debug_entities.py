"""Regression tests for raw Smart Next calibration test entities."""

import ast
from pathlib import Path


ROOT = Path("custom_components/astralpool/devices/smartnext")


def _constant_values() -> dict[str, int]:
    tree = ast.parse((ROOT / "calibration_debug.py").read_text(encoding="utf-8"))
    values: dict[str, int] = {}
    for node in tree.body:
        if not isinstance(node, ast.AnnAssign) or not isinstance(node.target, ast.Name):
            continue
        if node.value is None:
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
        if isinstance(value, int):
            values[node.target.id] = value
    return values


def test_raw_calibration_addresses_match_protocol_table() -> None:
    values = _constant_values()
    assert values["COIL_CALIBRATION_MODE"] == 0x201
    assert values["COIL_CALIBRATION_RESPONSE_RESET"] == 0x203
    assert values["HR_CALIBRATION_VALUE"] == 0x22
    assert values["IR_CALIBRATION_RESPONSE"] == 0x22
    assert values["COIL_PH_CALIBRATION_RESET"] == 0x50C
    assert values["COIL_PH_CALIBRATION_PH7"] == 0x50D
    assert values["COIL_PH_CALIBRATION_PH4"] == 0x50E
    assert values["COIL_PH_CALIBRATION_FAST"] == 0x50F
    assert values["COIL_ORP_CALIBRATION_RESET"] == 0x80C
    assert values["COIL_ORP_CALIBRATION_470MV"] == 0x80F
    assert values["COIL_TEMPERATURE_CALIBRATION_RESET"] == 0xB0D
    assert values["COIL_TEMPERATURE_CALIBRATION"] == 0xB0F
    assert values["COIL_SALT_CALIBRATION_RESET"] == 0xC0D
    assert values["COIL_SALT_CALIBRATION"] == 0xC0F


def test_raw_calibration_buttons_do_not_hide_a_release_step() -> None:
    source = (ROOT / "button.py").read_text(encoding="utf-8")
    raw_class = source.split("class SmartNextRawCalibrationButton", 1)[1]
    assert "async_write_coil(self._coil, True)" in raw_class
    assert "async_write_coil(self._coil, False)" not in raw_class


def test_calibration_debug_points_are_polled_with_coordinator() -> None:
    source = (ROOT / "coordinator.py").read_text(encoding="utf-8")
    assert "async_read_calibration_debug" in source
    assert "data.update(await async_read_calibration_debug(self.api, data))" in source
