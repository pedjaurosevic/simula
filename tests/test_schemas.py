"""Guard the shipped schemas and the example worlds against drift."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
WORLDS = ROOT / "resources" / "worlds"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_all_schemas_are_valid_json():
    for f in SCHEMAS.glob("*.json"):
        _load(f)  # raises on malformed JSON


def test_example_worlds_validate_against_v2_blueprint():
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load(SCHEMAS / "world_blueprint.schema.json")
    examples = list(WORLDS.glob("*.world.json"))
    assert examples, "no example worlds found"
    for f in examples:
        jsonschema.validate(_load(f), schema)


def test_v1_blueprint_still_validates_under_v2():
    """distill.py emits a v1-shaped blueprint; v2 must stay backward compatible."""
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load(SCHEMAS / "world_blueprint.schema.json")
    v1 = {
        "id": "x", "title": "X",
        "tone": {"summary": "bleak", "exemplar_refs": []},
        "rules": ["entropy wins"], "lexicon": ["kipple"],
        "seeds": {"places": [{"name": "Conapt"}], "factions": [], "archetypes": []},
    }
    jsonschema.validate(v1, schema)


def test_world_state_save_validates():
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load(SCHEMAS / "world_state.schema.json")
    save = {
        "world_id": "kipple-run1", "blueprint_id": "kipple",
        "created_at": "2026-06-15T00:00:00Z", "turn": 3, "seed": 42,
        "player": {"location": "conapt", "inventory": ["mood organ dial"]},
        "stats": {"Vitality": 92.0, "Awareness": 15.0},
        "map": {"conapt": {"id": "conapt", "name": "The Conapt", "description": "Dust on the sill.",
                            "exits": [{"to": "hallway"}], "contents": [], "visited": True}},
        "entities": {}, "flags": {"lift_broken": True},
        "facts": [{"text": "The lift is broken.", "turn": 2}], "ending": None,
    }
    jsonschema.validate(save, schema)
