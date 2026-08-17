"""Tests for alarm presentation and polling interval configuration."""

from pathlib import Path


INTEGRATION_ROOT = Path("custom_components/astralpool")
SMARTNEXT_ROOT = INTEGRATION_ROOT / "devices" / "smartnext"


def test_polling_interval_is_configurable_from_two_seconds_to_two_minutes() -> None:
    """Keep the user-facing polling range at 2..120 seconds."""
    constants = (INTEGRATION_ROOT / "const.py").read_text(encoding="utf-8")
    config_flow = (INTEGRATION_ROOT / "config_flow.py").read_text(encoding="utf-8")

    assert "MIN_SCAN_INTERVAL: Final = 2" in constants
    assert "MAX_SCAN_INTERVAL: Final = 120" in constants
    assert "vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)" in config_flow


def test_treatment_halted_uses_problem_device_class() -> None:
    """Treatment halt must use the red problem-state presentation in HA."""
    source = (SMARTNEXT_ROOT / "binary_sensor.py").read_text(encoding="utf-8")
    block = source.split('key="treatment_halted"', 1)[1].split("),", 1)[0]

    assert "device_class=BinarySensorDeviceClass.PROBLEM" in block
