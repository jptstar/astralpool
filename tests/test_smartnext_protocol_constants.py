"""Protocol coverage checks for Smart Next inside AstralPool."""

import ast
from pathlib import Path


ROOT = Path("custom_components/astralpool/devices/smartnext")


def _constant_values() -> dict[str, object]:
    tree = ast.parse((ROOT / "const.py").read_text(encoding="utf-8"))
    values: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.AnnAssign) or not isinstance(node.target, ast.Name):
            continue
        try:
            values[node.target.id] = ast.literal_eval(node.value)
        except (TypeError, ValueError):
            continue
    return values


def test_safe_control_coil_addresses() -> None:
    constants = _constant_values()
    assert constants["COIL_FLOW_INTERNAL_SENSOR_ENABLE"] == 0x300
    assert constants["COIL_FLOW_EXTERNAL_SENSOR_ENABLE"] == 0x301
    assert constants["COIL_ELECTROLYSIS_BOOST"] == 0x401
    assert constants["COIL_ELECTROLYSIS_COVER_CONTROL_ENABLE"] == 0x402
    assert constants["COIL_ELECTROLYSIS_EXTERNAL_CONTROL_ENABLE"] == 0x404
    assert constants["COIL_ELECTROLYSIS_INTERNAL_ORP_CONTROL_ENABLE"] == 0x405
    assert constants["COIL_ELECTROLYSIS_POLARITY_PERIOD_LOW"] == 0x409
    assert constants["COIL_ELECTROLYSIS_POLARITY_PERIOD_HIGH"] == 0x40A
    assert constants["COIL_PH_INTELLIGENT_DOSING_ENABLE"] == 0x566
    assert constants["COIL_PH_PUMP_STOP_ENABLE"] == 0x56C
    assert constants["COIL_BIOPOOL_MODE_ENABLE"] == 0x0D9
    assert constants["COIL_ECO_MODE_ENABLE"] == 0x230B


def test_diagnostic_and_alarm_limit_register_addresses() -> None:
    constants = _constant_values()
    assert constants["HR_PRODUCT_CAPACITY"] == 0x05
    assert constants["HR_HARDWARE_VERSION"] == 0x07
    assert constants["HR_FIRMWARE_VERSION"] == 0x08
    assert constants["HR_SERIAL_HIGH"] == 0x09
    assert constants["HR_SERIAL_MIDDLE"] == 0x0A
    assert constants["HR_SERIAL_LOW"] == 0x0B
    assert constants["HR_ELECTROLYSIS_BOOST_REMAINING"] == 0x44
    assert constants["HR_PH_LOW_ALARM_LIMIT"] == 0x51
    assert constants["HR_PH_HIGH_ALARM_LIMIT"] == 0x52
    assert constants["HR_ORP_LOW_ALARM_LIMIT"] == 0x81
    assert constants["HR_ORP_HIGH_ALARM_LIMIT"] == 0x82
    assert constants["HR_SALT_MIN_V170"] == 0xC2
    assert constants["HR_SALT_MAX_V170"] == 0xC3
    assert constants["HR_SALT_MIN_V200"] == 0xC1
    assert constants["HR_SALT_MAX_V200"] == 0xC2
    assert constants["DI_FLOW_INTERNAL_STATUS"] == 0x300
    assert constants["DI_FLOW_EXTERNAL_STATUS"] == 0x302
    assert constants["DI_ELECTROLYSIS_EXTERNAL_CONTROL_INPUT"] == 0x404
    assert constants["DI_ELECTROLYSIS_INTERNAL_ORP_STOP"] == 0x405
    assert constants["DI_ELECTROLYSIS_EXTERNAL_CONTROL_STOP"] == 0x406


def test_polarity_reversal_period_encoding() -> None:
    periods = _constant_values()["POLARITY_REVERSAL_ALLOWED_HOURS"]
    assert periods == (2, 3, 4, 7)
    assert {period: (index & 1, (index >> 1) & 1) for index, period in enumerate(periods)} == {
        2: (0, 0),
        3: (1, 0),
        4: (0, 1),
        7: (1, 1),
    }


def test_unsafe_maintenance_writes_are_not_exposed() -> None:
    constants = (ROOT / "const.py").read_text(encoding="utf-8")
    api = (ROOT / "api.py").read_text(encoding="utf-8")
    for unsafe_name in ("CALIBRATION", "FACTORY_RESET", "TEST_MODE", "WATCHDOG"):
        assert unsafe_name not in constants
        assert f"async_set_{unsafe_name.lower()}" not in api
