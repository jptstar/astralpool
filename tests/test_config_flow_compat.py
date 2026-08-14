"""Compatibility checks for the Home Assistant config flow API."""

import ast
from pathlib import Path


def test_config_flow_uses_current_result_type() -> None:
    """Prevent reintroducing the removed data_entry_flow.FlowResult import."""
    source = Path("custom_components/smartnext/config_flow.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)

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
    source = Path("custom_components/smartnext/config_flow.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)

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

    assert {
        "NumberSelector",
        "NumberSelectorConfig",
        "NumberSelectorMode",
    } <= selector_imports
    assert box_modes
