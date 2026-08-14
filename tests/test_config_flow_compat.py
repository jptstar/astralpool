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
