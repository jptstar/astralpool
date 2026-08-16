"""Compatibility checks for the Home Assistant config flow API."""

import ast
from pathlib import Path


FLOW = Path("custom_components/astralpool/config_flow.py")


def test_config_flow_uses_current_result_type() -> None:
    """Prevent reintroducing the removed data_entry_flow.FlowResult import."""
    tree = ast.parse(FLOW.read_text(encoding="utf-8"))
    imports = {
        (node.module, alias.name)
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert ("homeassistant.config_entries", "ConfigFlowResult") in imports
    assert ("homeassistant.data_entry_flow", "FlowResult") not in imports


def test_unit_id_uses_a_numeric_box_selector() -> None:
    """Keep the Modbus Unit ID as a numeric box instead of a slider."""
    tree = ast.parse(FLOW.read_text(encoding="utf-8"))
    selector_imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "homeassistant.helpers.selector"
        for alias in node.names
    }
    box_modes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "NumberSelectorMode"
        and node.attr == "BOX"
    ]
    assert {"NumberSelector", "NumberSelectorConfig", "NumberSelectorMode"} <= selector_imports
    assert box_modes


def test_device_selection_precedes_connection_step() -> None:
    """Require a device choice before Modbus connection parameters are shown."""
    source = FLOW.read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)
    }
    assert {"async_step_user", "async_step_connection"} <= functions
    assert "CONF_DEVICE_TYPE" in source
    assert "DEVICE_TYPE_SMARTNEXT" in source
    assert "DEVICE_TYPE_ELYO_TOUCH" in source
