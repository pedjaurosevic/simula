"""Guard the persona schemas and example personas against drift."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
PERSONAS = ROOT / "resources" / "personas"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_example_personas_validate_against_v2():
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load(SCHEMAS / "persona_blueprint.schema.json")
    examples = list(PERSONAS.glob("*.persona.json"))
    assert examples, "no example personas found"
    for f in examples:
        jsonschema.validate(_load(f), schema)


def test_v1_persona_still_validates_under_v2():
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load(SCHEMAS / "persona_blueprint.schema.json")
    v1 = {
        "id": "p1", "name": "Old Persona",
        "ocean": {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
                  "agreeableness": 0.5, "neuroticism": 0.5},
        "voice": {"summary": "dry", "exemplar_refs": []},
        "values": ["honesty"],
    }
    jsonschema.validate(v1, schema)


def test_persona_state_save_validates():
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load(SCHEMAS / "persona_state.schema.json")
    save = {
        "persona_id": "elias-run1", "blueprint_id": "elias-thorne",
        "created_at": "2026-06-15T00:00:00Z", "turn": 5, "seed": 7,
        "mood": {"valence": -0.2, "arousal": 0.1, "label": "wary"},
        "disposition": {"player": {"trust": 0.1, "affection": -0.1, "note": "testing you"}},
        "knowledge": [{"text": "The witness was paid.", "turn": 4}],
        "goals": [{"text": "find the paymaster", "status": "advanced"}],
    }
    jsonschema.validate(save, schema)


def test_persona_in_world_embedded_block():
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load(SCHEMAS / "persona_state.schema.json")
    npc = {
        "persona_id": "mira-npc", "blueprint_id": "mira-the-archivist",
        "created_at": "2026-06-15T00:00:00Z", "turn": 0,
        "embedded": {"world_id": "kipple-run1", "entity_id": "npc_mira", "location": "conapt"},
    }
    jsonschema.validate(npc, schema)
