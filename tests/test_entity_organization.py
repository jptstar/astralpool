"""Entity organization checks after the AstralPool merge."""

from pathlib import Path


ROOT = Path("custom_components/astralpool/devices/smartnext")
ELYO_ROOT = Path("custom_components/astralpool/devices/elyo_touch")
INTEGRATION_ROOT = Path("custom_components/astralpool")


def test_problem_entities_are_diagnostics() -> None:
    """Alarms and raw problem states belong in the Diagnostic section."""
    source = (ROOT / "binary_sensor.py").read_text(encoding="utf-8")
    generated = source.split(
        "BINARY_SENSORS: tuple[SmartNextBinarySensorDescription, ...] =", 1
    )[1].split(") + (", 1)[0]
    assert "entity_category=EntityCategory.DIAGNOSTIC" in generated


def test_secondary_sensor_values_are_diagnostics() -> None:
    """Keep duplicate thresholds and counters out of the main Sensors card."""
    source = (ROOT / "sensor.py").read_text(encoding="utf-8")
    diagnostic_keys = {
        "electrolysis_rated_capacity",
        "temperature_min",
        "temperature_max",
        "salt_min",
        "salt_max",
        "ph_dosage_elapsed",
        "ph_total_hours",
        "ph_partial_hours",
        "electrolysis_total_hours",
        "electrolysis_partial_hours",
    }
    for key in diagnostic_keys:
        description = source.split(f'key="{key}"', 1)[1].split("),", 1)[0]
        assert "entity_category=EntityCategory.DIAGNOSTIC" in description


def test_boost_remains_a_primary_control() -> None:
    """Boost is an everyday control, unlike advanced configuration switches."""
    source = (ROOT / "switch.py").read_text(encoding="utf-8")
    boost = source.split('key="boost_mode"', 1)[1].split("),", 1)[0]
    advanced = source.split('key="cover_control_enabled"', 1)[1].split("),", 1)[0]
    assert "entity_category=" not in boost
    assert "entity_registry_enabled_default=True" in boost
    assert "entity_category=EntityCategory.CONFIG" in advanced


def test_all_entities_are_enabled_by_default() -> None:
    """No AstralPool entity should opt out of the entity registry by default."""
    for root in (ROOT, ELYO_ROOT):
        for path in root.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            assert "entity_registry_enabled_default=False" not in source
            assert "_attr_entity_registry_enabled_default = False" not in source


def test_existing_integration_disabled_entities_are_reenabled() -> None:
    """Preserve user choices while clearing old integration defaults."""
    source = (INTEGRATION_ROOT / "__init__.py").read_text(encoding="utf-8")
    assert "RegistryEntryDisabler.INTEGRATION" in source
    assert "async_update_entity(registry_entry.entity_id, disabled_by=None)" in source
