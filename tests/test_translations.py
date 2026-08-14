"""Translation coverage checks."""

import ast
import json
from pathlib import Path


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_french_entity_names_cover_every_english_entity() -> None:
    """Ensure every English entity name has a French counterpart."""
    english = _load_json("custom_components/smartnext/translations/en.json")["entity"]
    french = _load_json("custom_components/smartnext/translations/fr.json")["entity"]

    assert french.keys() == english.keys()
    for platform, english_entities in english.items():
        assert french[platform].keys() == english_entities.keys()
        for key, english_translation in english_entities.items():
            assert french[platform][key]["name"]
            if english_translation["name"] not in {"pH", "ORP"}:
                assert french[platform][key]["name"] != english_translation["name"]


def test_entity_names_are_grouped_by_subsystem() -> None:
    """Keep alphabetical device-page sorting useful in both languages."""
    allowed_english_prefixes = {
        "Cover",
        "Electrolysis",
        "Flow",
        "ORP",
        "pH",
        "Salinity",
        "System",
        "Temperature",
    }
    allowed_french_prefixes = {
        "Couverture",
        "Débit",
        "ORP",
        "pH",
        "Salinité",
        "Système",
        "Température",
        "Électrolyse",
    }

    for filename, allowed_prefixes in (
        ("en.json", allowed_english_prefixes),
        ("fr.json", allowed_french_prefixes),
    ):
        entities = _load_json(
            f"custom_components/smartnext/translations/{filename}"
        )["entity"]
        for platform_entities in entities.values():
            for translation in platform_entities.values():
                name = translation["name"]
                assert " · " in name
                assert name.split(" · ", 1)[0] in allowed_prefixes


def test_english_strings_match_translation_catalog() -> None:
    """Keep the source catalog synchronized with the English translation."""
    assert _load_json("custom_components/smartnext/strings.json") == _load_json(
        "custom_components/smartnext/translations/en.json"
    )


def test_ph_initialization_options_are_translated() -> None:
    """Ensure every stable select option has English and French labels."""
    source = Path("custom_components/smartnext/select.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    option_assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "OPTIONS_TO_SECONDS"
            for target in node.targets
        )
    )
    options = set(ast.literal_eval(option_assignment.value))

    for path in (
        "custom_components/smartnext/strings.json",
        "custom_components/smartnext/translations/en.json",
        "custom_components/smartnext/translations/fr.json",
    ):
        states = _load_json(path)["entity"]["select"][
            "ph_initialization_time"
        ]["state"]
        assert states.keys() == options

    french_states = _load_json(
        "custom_components/smartnext/translations/fr.json"
    )["entity"]["select"]["ph_initialization_time"]["state"]
    assert french_states["off"] == "Désactivé"


def test_polarity_reversal_options_are_translated() -> None:
    """Ensure every polarity period has English and French labels."""
    source = Path("custom_components/smartnext/select.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    option_assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id == "POLARITY_OPTIONS_TO_HOURS"
            for target in node.targets
        )
    )
    options = set(ast.literal_eval(option_assignment.value))

    for path in (
        "custom_components/smartnext/strings.json",
        "custom_components/smartnext/translations/en.json",
        "custom_components/smartnext/translations/fr.json",
    ):
        states = _load_json(path)["entity"]["select"][
            "polarity_reversal_period"
        ]["state"]
        assert states.keys() == options
