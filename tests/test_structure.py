"""Structure checks for the combined AstralPool integration."""

import ast
import json
from pathlib import Path


ROOT = Path("custom_components/astralpool")


def test_both_device_drivers_are_present() -> None:
    """Keep the two device implementations isolated under one HA domain."""
    assert (ROOT / "devices/smartnext/api.py").is_file()
    assert (ROOT / "devices/elyo_touch/api.py").is_file()
    assert (ROOT / "devices/smartnext/const.py").is_file()
    assert (ROOT / "devices/elyo_touch/const.py").is_file()


def test_config_flow_selects_device_before_connection() -> None:
    """The config flow must expose the device selector and connection step."""
    source = (ROOT / "config_flow.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    function_names = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)
    }
    assert "async_step_user" in function_names
    assert "async_step_connection" in function_names
    assert "DEVICE_TYPE_SMARTNEXT" in source
    assert "DEVICE_TYPE_ELYO_TOUCH" in source


def test_translations_contain_both_families() -> None:
    """Entity translations from both former integrations must be available."""
    strings = json.loads((ROOT / "strings.json").read_text(encoding="utf-8"))
    sensors = strings["entity"]["sensor"]
    binary = strings["entity"]["binary_sensor"]
    assert "electrolysis_production" in sensors
    assert "inlet_temperature" in sensors
    assert "general_alarm" in binary
    assert "alarm_water_flow_abnormal" in binary
