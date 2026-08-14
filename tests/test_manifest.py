"""Manifest compatibility checks."""

import json
from pathlib import Path


def test_pymodbus_matches_home_assistant_2026_8() -> None:
    """Keep the dependency aligned with Home Assistant's Modbus integration."""
    manifest = json.loads(
        Path("custom_components/smartnext/manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["requirements"] == ["pymodbus==3.13.1"]

