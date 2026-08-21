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
    source = FLOW.read_text(encoding="utf-8")
    assert "_UNIT_ID_SELECTOR" in source
    assert "mode=NumberSelectorMode.BOX" in source


def test_scan_interval_uses_a_numeric_box_selector() -> None:
    """Keep polling interval as a numeric box instead of a slider."""
    source = FLOW.read_text(encoding="utf-8")
    assert "_SCAN_INTERVAL_SELECTOR" in source
    assert source.count("mode=NumberSelectorMode.BOX") >= 2
    assert "): _SCAN_INTERVAL_SELECTOR" in source


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
    assert "_endpoint_schema" in source
    assert "async_entry_for_domain_unique_id" in source
    assert "async_update_reload_and_abort" in source
    assert "data_updates={" in source
    assert "unique_id=unique_id" in source
    assert "options.pop(CONF_UNIT_ID, None)" in source


def test_reconfigure_and_options_do_not_duplicate_settings() -> None:
    """Keep endpoint identity and runtime communication settings separate."""
    source = FLOW.read_text(encoding="utf-8")
    endpoint_schema = source.split("def _endpoint_schema", 1)[1].split(
        "def _connection_schema", 1
    )[0]
    options_flow = source.split("class AstralPoolOptionsFlow", 1)[1]

    assert "CONF_HOST" in endpoint_schema
    assert "CONF_PORT" in endpoint_schema
    assert "CONF_UNIT_ID" in endpoint_schema
    assert "CONF_TIMEOUT" not in endpoint_schema
    assert "CONF_RECONNECT_DELAY" not in endpoint_schema
    assert "CONF_SCAN_INTERVAL" not in endpoint_schema

    assert "CONF_UNIT_ID" not in options_flow
    assert "CONF_TIMEOUT" in options_flow
    assert "CONF_RECONNECT_DELAY" in options_flow
    assert "CONF_SCAN_INTERVAL" in options_flow
