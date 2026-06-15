"""Tests for persona distillation (chat parsing, speaker filter, map-reduce)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from simula.distill import (
    distill_persona,
    extract_speaker_text,
    parse_chat,
    reduce_persona_partials,
    speakers_in,
)

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "persona_blueprint.schema.json"

CHAT = """\
[2024-01-01 12:00] Mira: okay, so what are you actually trying to build?
[2024-01-01 12:01] Me: not sure yet
Mira: that's fine. name one piece you DO know.
and don't overthink it
Me: a parser maybe
"""


class PersonaBackend:
    def __init__(self, partial: dict) -> None:
        self._partial = partial
        self.windows: list[str] = []

    def complete(self, messages, *, contract=None, temperature=0.2, max_tokens=800) -> str:
        self.windows.append(messages[-1].content)
        return json.dumps(self._partial)

    def embed(self, texts):  # pragma: no cover
        raise NotImplementedError


def test_parse_chat_handles_timestamps_and_continuations():
    turns = parse_chat(CHAT)
    assert ("Mira", "okay, so what are you actually trying to build?") in turns
    # continuation line folded into the previous Mira turn
    mira_second = [t for s, t in turns if s == "Mira" and "name one piece" in t][0]
    assert "don't overthink it" in mira_second
    assert speakers_in(turns)["Mira"] == 2


def test_extract_speaker_text_filters_to_target():
    only_mira = extract_speaker_text(CHAT, "mira")
    assert "name one piece" in only_mira
    assert "not sure yet" not in only_mira  # the other speaker is dropped


def test_extract_speaker_text_passthrough_for_non_chat():
    prose = "Just an essay with no speaker tags.\n\nSecond paragraph."
    assert extract_speaker_text(prose, "mira") == prose


def test_reduce_persona_averages_ocean_and_shapes():
    partials = [
        {"voice": "warm, digressive", "register": "conversational", "speech_tics": ["okay, so—"],
         "values": ["honesty"], "wants": ["see you build it"], "needs": ["to matter"],
         "wound": "the helper no one checked on", "knowledge_domains": ["writing"],
         "ocean": {"openness": 0.8, "conscientiousness": 0.6, "extraversion": 0.5,
                   "agreeableness": 0.9, "neuroticism": 0.3}},
        {"voice": "warm, digressive", "values": ["honesty", "clarity"],
         "ocean": {"openness": 0.9, "conscientiousness": 0.6, "extraversion": 0.6,
                   "agreeableness": 0.7, "neuroticism": 0.3}},
    ]
    bp = reduce_persona_partials(partials, persona_id="mira", name="Mira",
                                 input_types=["exported-chat"])

    assert bp["id"] == "mira" and bp["name"] == "Mira"
    assert bp["ocean"]["openness"] == 0.85          # averaged
    assert bp["voice"]["summary"] == "warm, digressive"
    assert bp["voice"]["register"] == "conversational"
    assert bp["values"] == ["honesty", "clarity"]   # deduped union
    assert bp["wound"] == "the helper no one checked on"
    assert bp["provenance"]["input_types"] == ["exported-chat"]


def test_distill_persona_from_chat_produces_valid_blueprint(tmp_path):
    (tmp_path / "log.txt").write_text(CHAT, encoding="utf-8")
    backend = PersonaBackend(
        {"voice": "warm, exacting", "register": "conversational", "speech_tics": ["okay, so—"],
         "values": ["honesty"], "wants": ["see you build it"],
         "ocean": {"openness": 0.85, "conscientiousness": 0.6, "extraversion": 0.55,
                   "agreeableness": 0.8, "neuroticism": 0.3}}
    )

    bp = distill_persona([tmp_path], backend, persona_id="mira", name="Mira",
                         speaker="mira", input_types=["exported-chat"], window_chars=200)

    # The speaker filter must have removed the other speaker before mapping.
    assert all("not sure yet" not in w for w in backend.windows)
    for key in ("id", "name", "ocean", "voice", "values"):
        assert key in bp

    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(bp, schema)
