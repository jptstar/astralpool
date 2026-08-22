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


def test_existing_device_can_be_reconfigured() -> None:
    """Allow changing the Modbus endpoint without deleting the config entry."""
    source = FLOW.read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)
    }

    assert "async_step_reconfigure" in functions
    assert "SOURCE_RECONFIGURE" in source
    assert "async_entry_for_domain_unique_id" in source
    assert "async_update_reload_and_abort" in source
    assert "unique_id=unique_id" in source
    assert "options={}" in source


def test_restart_is_deferred_until_options_flow_closes() -> None:
    """Never unload AstralPool while its own options request is still open."""
    source = FLOW.read_text(encoding="utf-8")
    assert "async_create_background_task" in source
    assert "self.async_abort(reason=\"restart_started\")" in source
    assert "await asyncio.sleep(1)" in source
    assert "_async_restart_smartnext_background" in source


def test_maintenance_uses_translatable_selector() -> None:
    """Maintenance actions must use frontend translations instead of hard-coded labels."""
    source = FLOW.read_text(encoding="utf-8")
    assert "SelectSelector" in source
    assert 'translation_key="maintenance_action"' in source
