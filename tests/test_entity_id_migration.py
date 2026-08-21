"""Regression checks for AstralPool entity ID normalization."""

from pathlib import Path


INTEGRATION = Path("custom_components/astralpool/__init__.py")


def test_entity_ids_are_normalized_before_and_after_platform_setup() -> None:
    """Migrate old IDs and catch entities queued asynchronously by HA."""
    source = INTEGRATION.read_text(encoding="utf-8")
    setup = source.split("async def async_setup_entry", 1)[1]
    before_forward, after_forward = setup.split(
        "await hass.config_entries.async_forward_entry_setups", 1
    )

    assert "_async_normalize_entity_ids(hass, entry, device_type)" in before_forward
    assert "_async_normalize_entity_ids(hass, entry, device_type)" in after_forward
    assert (
        "hass.loop.call_soon(_async_normalize_entity_ids, hass, entry, device_type)"
        in after_forward
    )


def test_canonical_ids_do_not_include_integration_or_area_prefixes() -> None:
    """Keep object IDs device-focused and independent from HA areas."""
    source = INTEGRATION.read_text(encoding="utf-8")

    assert '"climate": {"climate": "pro_elyo_touch"}' in source
    assert '"ph": "smart_next_ph"' in source
    assert "local_piscine" not in source
    assert '"astralpool_pro_elyo_touch"' not in source
    assert '"astralpool_smart_next"' not in source
