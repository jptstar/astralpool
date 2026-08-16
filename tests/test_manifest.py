"""Manifest compatibility checks for the combined AstralPool integration."""

import json
from pathlib import Path


def test_manifest_domain_and_pymodbus() -> None:
    """Check the combined integration manifest."""
    manifest = json.loads(
        Path("custom_components/astralpool/manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["domain"] == "astralpool"
    assert manifest["name"] == "AstralPool"
    assert manifest["requirements"] == ["pymodbus==3.13.1"]
    assert manifest["config_flow"] is True
