"""Translation coverage checks for the combined AstralPool integration."""

import json
from pathlib import Path


ROOT = Path("custom_components/astralpool")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_french_catalog_covers_every_source_entity() -> None:
    """Every source entity translation must have a French counterpart."""
    source = _load(ROOT / "strings.json")["entity"]
    french = _load(ROOT / "translations/fr.json")["entity"]
    assert french.keys() == source.keys()
    for platform, entities in source.items():
        assert french[platform].keys() == entities.keys()
        for key in entities:
            assert french[platform][key]["name"]


def test_select_states_match_between_source_and_french() -> None:
    """Stable select option keys must remain identical across languages."""
    source = _load(ROOT / "strings.json")["entity"]["select"]
    french = _load(ROOT / "translations/fr.json")["entity"]["select"]
    for key in ("ph_initialization_time", "polarity_reversal_period"):
        assert source[key]["state"].keys() == french[key]["state"].keys()


def test_maintenance_actions_are_fully_translated() -> None:
    """Guided maintenance procedure labels must be localized in French."""
    source = _load(ROOT / "strings.json")["selector"]["maintenance_action"]["options"]
    french = _load(ROOT / "translations/fr.json")["selector"]["maintenance_action"]["options"]
    assert french.keys() == source.keys()
    assert french["reset_ph_calibration"] == "pH · réinitialiser la calibration"
    assert french["reset_orp_calibration"] == "ORP · réinitialiser la calibration"
    assert french["restart_device"] == "Système · redémarrer le Smart Next"
