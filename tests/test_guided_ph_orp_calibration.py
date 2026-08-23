"""Regression tests for hardware-validated Smart Next pH/ORP workflows."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path("custom_components/astralpool/devices/smartnext")
GUIDED = ROOT / "guided_calibration.py"
SESSION = ROOT / "calibration_session.py"
SAFE_OPTIONS = ROOT / "guided_options_safe.py"
FINAL_OPTIONS = ROOT / "guided_options_final.py"
COORDINATOR = ROOT / "coordinator.py"
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


def test_persistent_session_saves_original_state_before_flow_is_disabled() -> None:
    source = _source(SESSION)
    activate = _function_source(
        source,
        "async_activate_persistent_calibration",
        "async_prepare_persistent_calibration",
    )
    save = activate.index("await async_save_persistent_calibration(hass, api, saved)")
    zero = activate.index("await _async_hold_electrolysis_at_zero(api, saved)")
    flow_off = activate.index("await _async_set_flow_sensors(api, False, False)")
    assert save < zero < flow_off
    assert "COIL_PH_PUMP_STOP_ENABLE, True" in activate
    assert "async_verify_electrolysis_stopped(api)" in activate
    assert "async_verify_ph_pump_stopped(api)" in activate


def test_persistent_zero_disables_only_active_optional_electrolysis_controls() -> None:
    source = _source(SESSION)
    hold = _function_source(
        source,
        "_async_hold_electrolysis_at_zero",
        "_async_set_flow_sensors",
    )
    assert "COIL_ELECTROLYSIS_BOOST, False" in hold
    assert "COIL_ELECTROLYSIS_COVER_CONTROL_ENABLE, False" in hold
    assert "COIL_ELECTROLYSIS_EXTERNAL_CONTROL_ENABLE, False" in hold
    assert "COIL_ELECTROLYSIS_INTERNAL_ORP_CONTROL_ENABLE, False" in hold
    assert "HR_ELECTROLYSIS_NORMAL_SETPOINT, 0" in hold


def test_flow_inputs_stay_disabled_after_normal_terminal_result() -> None:
    source = _source(FINAL_OPTIONS)
    terminal = _function_source(
        source,
        "_async_terminal_flow_restore",
        "async_remove",
    )
    assert "Keep flow disabled after terminal results" in terminal
    assert "async_verify_electrolysis_stopped" in terminal
    assert "async_verify_ph_pump_stopped" in terminal

    ph4 = _function_source(
        source,
        "async_step_calibrate_ph_standard_ph4",
        "async_step_calibrate_orp_470",
    )
    orp = _function_source(
        source,
        "async_step_calibrate_orp_470",
        "async_step_calibrate_ph_standard_retry",
    )
    assert "_async_terminal_flow_restore" in ph4
    assert "_async_terminal_flow_restore" in orp


def test_cancelled_flow_restores_saved_flow_sensors_and_keeps_zero_production() -> None:
    final = _source(FINAL_OPTIONS)
    remove = final[final.index("def async_remove"): final.index("async def async_step_calibrate_ph_standard_prepare")]
    assert "async_restore_interrupted_flow_sensors_until_success" in remove

    session = _source(SESSION)
    restore = _function_source(
        session,
        "async_restore_interrupted_flow_sensors",
        "async_restore_interrupted_flow_sensors_until_success",
    )
    zero = restore.index("await _async_hold_electrolysis_at_zero(api, saved)")
    flow = restore.index("await _async_set_flow_sensors")
    clear = restore.index("await async_clear_persistent_calibration(hass, api)")
    assert zero < flow < clear
    assert "saved.internal_flow_enabled" in restore
    assert "saved.external_flow_enabled" in restore


def test_startup_recovers_flow_after_interrupted_home_assistant_session() -> None:
    source = _source(COORDINATOR)
    assert "async_recover_interrupted_calibration" in source
    update = _function_source(source, "_async_update_data")
    recovery = update.index("await async_recover_interrupted_calibration")
    read_all = update.index("await self.api.async_read_all()")
    assert recovery < read_all


def test_real_output_guard_restores_flow_if_pump_or_electrolysis_starts() -> None:
    source = _source(FINAL_OPTIONS)
    guard = _function_source(
        source,
        "_async_calibration_guard",
        "_async_guard_error_result",
    )
    assert "IR_ELECTROLYSIS_PRODUCTION" in guard
    assert "IR_ELECTROLYSIS_CURRENT" in guard
    assert "DI_ELECTROLYSIS_RUNNING" in guard
    assert "IR_PH_PUMP_OUTPUT" in guard
    assert "async_restore_interrupted_flow_sensors_until_success" in guard


def test_201_is_started_before_probe_removal_and_stabilization() -> None:
    source = _source(FINAL_OPTIONS)
    ph = _function_source(
        source,
        "async_step_calibrate_ph_standard_drain_pulse",
        "async_step_calibrate_orp_drain_pulse",
    )
    orp = _function_source(
        source,
        "async_step_calibrate_orp_drain_pulse",
        "async_step_calibrate_ph_standard_ph7",
    )
    assert ph.index("async_begin_bypassed_calibration") < ph.index(
        "async_step_calibrate_ph_standard_ph7_immerse"
    )
    assert orp.index("async_begin_bypassed_calibration") < orp.index(
        "async_step_calibrate_orp_immerse"
    )


def test_one_minute_stabilization_is_mandatory_for_ph7_ph4_and_orp() -> None:
    safe = _source(SAFE_OPTIONS)
    tree = ast.parse(safe)
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
        ("async_step_calibrate_orp_470", "async_step_calibrate_ph_standard_retry"),
    ):
        function = _function_source(final, name, next_name)
        assert "STABILIZATION_SECONDS" in function
        assert "measurement_not_confirmed_stable" in function


def test_retry_is_explicit_and_starts_a_fresh_201_session() -> None:
    source = _source(FINAL_OPTIONS)
    ph_retry = _function_source(
        source,
        "async_step_calibrate_ph_standard_retry",
        "async_step_calibrate_orp_retry",
    )
    orp_retry = _function_source(
        source,
        "async_step_calibrate_orp_retry",
        "async_step_calibrate_ph_standard_chain_orp",
    )
    for function in (ph_retry, orp_retry):
        assert "async_activate_persistent_calibration" in function
        assert "async_begin_bypassed_calibration" in function


def test_second_probe_gets_a_fresh_201_session_before_removal() -> None:
    source = _source(FINAL_OPTIONS)
    ph_to_orp = _function_source(
        source,
        "async_step_calibrate_ph_standard_chain_orp",
        "async_step_calibrate_orp_chain_ph",
    )
    orp_to_ph = _function_source(
        source,
        "async_step_calibrate_orp_chain_ph",
        "async_step_calibrate_ph_standard_restore_filtration",
    )
    for function in (ph_to_orp, orp_to_ph):
        assert "async_activate_persistent_calibration" in function
        assert "async_begin_bypassed_calibration" in function


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
    assert "async_step_calibrate_ph_standard_chain_orp" in final
    assert "async_step_calibrate_orp_chain_ph" in final


def test_restore_keeps_production_zero_until_saved_flow_is_restored() -> None:
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


def test_final_restore_clears_persistent_recovery_only_after_success() -> None:
    source = _source(FINAL_OPTIONS)
    ph = _function_source(
        source,
        "async_step_calibrate_ph_standard_restore_filtration",
        "async_step_calibrate_orp_restore_filtration",
    )
    orp = _function_source(source, "async_step_calibrate_orp_restore_filtration")
    assert "if self._ph_saved_state is None" in ph
    assert "async_clear_persistent_calibration" in ph
    assert "if self._orp_saved_state is None" in orp
    assert "async_clear_persistent_calibration" in orp


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
