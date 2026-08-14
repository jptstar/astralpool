"""Entity organization checks for the Home Assistant device page."""

from pathlib import Path


def test_problem_entities_are_diagnostics() -> None:
    """Alarms and raw problem states belong in the Diagnostic section."""
    source = Path("custom_components/smartnext/binary_sensor.py").read_text(
        encoding="utf-8"
    )
    generated_problem_entities = source.split(
        "BINARY_SENSORS: tuple[SmartNextBinarySensorDescription, ...] =", 1
    )[1].split(") + (", 1)[0]

    assert "entity_category=EntityCategory.DIAGNOSTIC" in generated_problem_entities


def test_secondary_sensor_values_are_diagnostics() -> None:
    """Keep duplicate thresholds and counters out of the main Sensors card."""
    source = Path("custom_components/smartnext/sensor.py").read_text(encoding="utf-8")
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
    source = Path("custom_components/smartnext/switch.py").read_text(encoding="utf-8")
    boost = source.split('key="boost_mode"', 1)[1].split("),", 1)[0]
    advanced = source.split('key="cover_control_enabled"', 1)[1].split("),", 1)[0]

    assert "entity_category=" not in boost
    assert "entity_registry_enabled_default=True" in boost
    assert "entity_category=EntityCategory.CONFIG" in advanced
