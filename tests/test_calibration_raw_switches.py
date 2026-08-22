"""Tests for raw Smart Next calibration diagnostic switches."""

from pathlib import Path


DEBUG = Path("custom_components/astralpool/devices/smartnext/calibration_debug.py")
SWITCH = Path("custom_components/astralpool/devices/smartnext/switch.py")
COORDINATOR = Path("custom_components/astralpool/devices/smartnext/coordinator.py")


def test_raw_calibration_switches_cover_documented_commands() -> None:
    """Expose every calibration command needed for manual protocol testing."""
    source = DEBUG.read_text(encoding="utf-8")
    for address in (
        "0x201",
        "0x203",
        "0x50C",
        "0x50D",
        "0x50E",
        "0x50F",
        "0x80C",
        "0x80F",
        "0xB0D",
        "0xB0F",
        "0xC0D",
        "0xC0F",
    ):
        assert address in source
    assert "RAW_CALIBRATION_SWITCHES" in source


def test_raw_switches_are_read_write_entities() -> None:
    """Switch platform must use the raw coil table and support explicit OFF/ON."""
    source = SWITCH.read_text(encoding="utf-8")
    assert "RAW_CALIBRATION_SWITCHES" in source
    assert "coil_address=coil" in source
    assert "await self._async_set_state(True)" in source
    assert "await self._async_set_state(False)" in source


def test_coordinator_polls_raw_coil_states() -> None:
    """The entity state must reflect the actual coil readback, not the last command."""
    source = COORDINATOR.read_text(encoding="utf-8")
    assert "async_read_calibration_debug(self.api, data)" in source
    debug = DEBUG.read_text(encoding="utf-8")
    assert "api._read_coils(COIL_CALIBRATION_MODE, 3)" in debug
    assert "api._read_coils(COIL_PH_CALIBRATION_RESET, 4)" in debug
    assert "api._read_coils(COIL_ORP_CALIBRATION_RESET, 4)" in debug
    assert "api._read_coils(COIL_TEMPERATURE_CALIBRATION_RESET, 3)" in debug
    assert "api._read_coils(COIL_SALT_CALIBRATION_RESET, 3)" in debug
