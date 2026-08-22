"""Regression tests for hardware-validated Smart Next pH/ORP workflows."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path("custom_components/astralpool/devices/smartnext")
GUIDED = ROOT / "guided_calibration.py"
SAFE_OPTIONS = ROOT / "guided_options_safe.py"
FINAL_OPTIONS = ROOT / "guided_options_final.py"
CONFIG_FLOW = Path("custom_components/astralpool/config_flow.py")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _function_source(source: str, name: str, next_name: str | None = None) -> str:
    start = source.index(f"async def {name}")
    if next_name is None:
        return source[start:]
    end = source.index(f"async def {next_name}", start)
    return source[start:end]


def test_validated_protocol_constants_are_present() -> None:
    source = _source(GUIDED)
    for constant in (
        "COIL_CALIBRATION_MODE",
        "COIL_CALIBRATION_RESPONSE_RESET",
        "COIL_PH_CALIBRATION_PH7",
        "COIL_PH_CALIBRATION_PH4",
        "COIL_PH_CALIBRATION_FAST",
        "COIL_ORP_CALIBRATION_470MV",
        "COIL_PH_CALIBRATION_RESET",
        "COIL_ORP_CALIBRATION_RESET",
    ):
        assert constant in source
    assert "RESPONSE_OK: Final = 1" in source
    assert "RESPONSE_E2: Final = 2" in source
    assert "RESPONSE_E3: Final = 3" in source
    assert "RESPONSE_UNAVAILABLE: Final = 4" in source
    assert "RESPONSE_INITIALIZING: Final = 5" in source
    assert "RESPONSE_FIRST_POINT_OK: Final = 16" in source


def test_ph_fast_is_201_203_then_hr22_x100_then_50f() -> None:
    source = _source(GUIDED)
    function = _function_source(source, "async_calibrate_ph_fast", "async_trigger_ph7")
    value = function.index("raw_value = round(reference_ph * 100)")
    start = function.index("await async_start_calibration_session(api, force_clear=True)")
    write = function.index("await api.async_write_register(HR_CALIBRATION_VALUE, raw_value)")
    trigger = function.index("await _async_command_edge(api, COIL_PH_CALIBRATION_FAST)")
    assert value < start < write < trigger


def test_standard_ph_and_orp_do_not_rearm_after_terminal_result() -> None:
    source = _source(GUIDED)
    ph4 = _function_source(source, "async_trigger_ph4", "async_restart_standard_ph_after_error")
    orp = _function_source(source, "async_trigger_orp_470", "async_restart_orp_after_error")
    assert "COIL_PH_CALIBRATION_PH4" in ph4
    assert "COIL_ORP_CALIBRATION_470MV" in orp
    assert "async_rearm_calibration_mode" not in ph4
    assert "async_rearm_calibration_mode" not in orp


def test_persistent_zero_and_real_ph_pump_safety_are_established() -> None:
    source = _source(GUIDED)
    prepare = _function_source(
        source,
        "async_prepare_bypassed_calibration",
        "async_confirm_filtration_stopped",
    )
    assert "COIL_PH_PUMP_STOP_ENABLE, True" in prepare
    assert "COIL_ELECTROLYSIS_BOOST, False" in prepare
    assert "COIL_ELECTROLYSIS_COVER_CONTROL_ENABLE, False" in prepare
    assert "COIL_ELECTROLYSIS_EXTERNAL_CONTROL_ENABLE, False" in prepare
    assert "COIL_ELECTROLYSIS_INTERNAL_ORP_CONTROL_ENABLE, False" in prepare
    assert "HR_ELECTROLYSIS_NORMAL_SETPOINT, 0" in prepare
    assert "async_verify_electrolysis_stopped(api)" in prepare
    assert "async_start_calibration_session" not in prepare

    verify_pump = _function_source(
        source,
        "async_verify_ph_pump_stopped",
        "_async_set_flow_sensors",
    )
    assert "IR_PH_PUMP_OUTPUT" in verify_pump
    assert "output == 0" in verify_pump
    assert "ph_pump_not_stopped" in verify_pump


def test_flow_inputs_are_disabled_only_after_201_is_confirmed() -> None:
    source = _source(GUIDED)
    begin = _function_source(
        source,
        "async_begin_bypassed_calibration",
        "async_restore_bypassed_calibration",
    )
    mode = begin.index("await async_rearm_calibration_mode(api)")
    halted = begin.index("treatment_not_halted")
    flow_off = begin.index("await _async_set_flow_sensors(api, False, False)")
    clear = begin.index("await async_clear_response_in_active_mode(api, force=True)")
    assert mode < halted < flow_off < clear


def test_flow_inputs_restore_immediately_after_every_terminal_exit() -> None:
    safe = _source(SAFE_OPTIONS)
    helper = _function_source(
        safe,
        "_async_terminal_flow_restore",
        "async_step_calibrate_ph_standard_filtration_off",
    )
    assert "async_restore_flow_sensors_immediately" in helper

    final = _source(FINAL_OPTIONS)
    failure_helper = _function_source(
        final,
        "_async_record_failure_and_restore",
        "async_step_calibrate_ph_standard_ph7",
    )
    assert "_async_terminal_flow_restore" in failure_helper
    for name, next_name in (
        ("async_step_calibrate_ph_standard_ph7", "async_step_calibrate_ph_standard_ph4"),
        ("async_step_calibrate_ph_standard_ph4", "async_step_calibrate_orp_470"),
        ("async_step_calibrate_orp_470", None),
    ):
        function = _function_source(final, name, next_name)
        assert "_async_terminal_flow_restore" in function or "_async_record_failure_and_restore" in function


def test_one_minute_stabilization_is_mandatory_for_ph7_ph4_and_orp() -> None:
    source = _source(SAFE_OPTIONS)
    tree = ast.parse(source)
    assignments = {
        node.target.id: node.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and isinstance(node.value, ast.Constant)
    }
    assert assignments["STABILIZATION_SECONDS"] == 60.0
    final = _source(FINAL_OPTIONS)
    for name, next_name in (
        ("async_step_calibrate_ph_standard_ph7", "async_step_calibrate_ph_standard_ph4"),
        ("async_step_calibrate_ph_standard_ph4", "async_step_calibrate_orp_470"),
        ("async_step_calibrate_orp_470", None),
    ):
        function = _function_source(final, name, next_name)
        assert "STABILIZATION_SECONDS" in function
        assert "measurement_not_confirmed_stable" in function


def test_retry_is_explicit_and_errors_never_rearm_201_automatically() -> None:
    safe = _source(SAFE_OPTIONS)
    ph_error = _function_source(
        safe,
        "async_step_calibrate_ph_standard_error",
        "async_step_calibrate_ph_standard_retry",
    )
    orp_error = _function_source(
        safe,
        "async_step_calibrate_orp_error",
        "async_step_calibrate_orp_retry",
    )
    assert "async_rearm_calibration_mode" not in ph_error
    assert "async_rearm_calibration_mode" not in orp_error
    assert "calibrate_ph_standard_retry" in ph_error
    assert "calibrate_orp_retry" in orp_error


def test_success_offers_other_probe_without_repeating_hydraulic_preparation() -> None:
    safe = _source(SAFE_OPTIONS)
    tree = ast.parse(safe)
    methods = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)
    }
    assert {
        "async_step_calibrate_ph_standard_next_sensor",
        "async_step_calibrate_ph_standard_chain_orp",
        "async_step_calibrate_ph_standard_chain_orp_immerse",
        "async_step_calibrate_orp_next_sensor",
        "async_step_calibrate_orp_chain_ph",
        "async_step_calibrate_orp_chain_ph7_immerse",
    } <= methods

    final = _source(FINAL_OPTIONS)
    assert "async_step_calibrate_ph_standard_next_sensor" in final
    assert "async_step_calibrate_orp_next_sensor" in final


def test_mode_activation_must_be_verified_promptly() -> None:
    source = _source(GUIDED)
    tree = ast.parse(source)
    assignments = {
        node.target.id: node.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and isinstance(node.value, ast.Constant)
    }
    assert assignments["CALIBRATION_MODE_MAX_REARM_SECONDS"] == 10.0


def test_restore_keeps_production_zero_until_flow_is_confirmed() -> None:
    source = _source(GUIDED)
    restore = _function_source(
        source,
        "async_restore_bypassed_calibration",
        "async_calibrate_ph_fast",
    )
    flow = restore.index("await _async_set_flow_sensors")
    production = restore.index("HR_ELECTROLYSIS_NORMAL_SETPOINT")
    assert flow < production
    assert "flow_not_restored" in restore
    assert "COIL_PH_PUMP_STOP_ENABLE, saved.ph_pump_stop_enabled" in restore


def test_factory_resets_force_201_then_203_then_reset_command() -> None:
    source = _source(GUIDED)
    reset = _function_source(
        source,
        "_async_reset_calibration",
        "async_reset_ph_calibration",
    )
    start = reset.index("async_start_calibration_session(api, force_clear=True)")
    trigger = reset.index("await _async_command_edge(api, coil)")
    wait = reset.index("await _async_wait_for_response(api, RESPONSE_NONE)")
    assert start < trigger < wait


def test_config_flow_uses_final_fail_safe_guided_mixin() -> None:
    source = _source(CONFIG_FLOW)
    assert "from .devices.smartnext.guided_options_final import" in source
    assert "SmartNextGuidedCalibrationOptionsMixin" in source


def test_manual_drain_is_limited_to_two_seconds_in_ui_contract() -> None:
    strings = Path("custom_components/astralpool/strings.json").read_text(encoding="utf-8")
    french = Path("custom_components/astralpool/translations/fr.json").read_text(encoding="utf-8")
    assert "2 seconds" in strings
    assert "2 secondes" in french


def test_restore_menu_includes_ph_orp_and_temperature() -> None:
    source = _source(CONFIG_FLOW)
    function = source[source.index("async def async_step_restore_calibration"):]
    function = function[: function.index("async def async_step_calibrate_temperature")]
    assert 'menu["restore_ph_calibration"] = "pH"' in function
    assert 'menu["restore_orp_calibration"] = "Redox / ORP"' in function
    assert 'menu["restore_temperature_calibration"] = "Température"' in function
