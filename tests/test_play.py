"""Tests for the gameplay runtime (instantiation, endings, a turn, a scripted session)."""
from __future__ import annotations

import json

import pytest

from simula.__main__ import main
from simula.play import (
    check_endings,
    eval_condition,
    instantiate_world,
    run_session,
    step,
)

BLUEPRINT = {
    "id": "testworld",
    "title": "Test World",
    "genre": {"primary": "Dystopian", "conventions": ["entropy"]},
    "voice": {"summary": "bleak", "person": "second", "sensory_palette": ["dust"]},
    "rules": ["entropy wins"],
    "lexicon": ["kipple"],
    "stats": {
        "resilience": {"name": "Vitality", "start": 100, "min": 0, "max": 100},
        "progress": {"name": "Awareness", "start": 0, "max": 100},
        "axes": [{"id": "kipple_level", "name": "Kipple", "start": 10, "max": 100}],
    },
    "stakes": {"endings": [
        {"id": "dead", "when": "resilience.Vitality <= 0"},
        {"id": "consumed", "when": "axes.kipple_level >= 100"},
        {"id": "escape", "when": "progress.Awareness >= 80 and not captured"},
    ]},
    "space": {"topology": "interconnected-rooms"},
    "seeds": {"places": [
        {"id": "conapt", "name": "The Conapt", "note": "dusty", "exits": [{"to": "hall"}]},
    ]},
    "opening": {"location": "conapt", "inventory": ["dial"], "intro": "The dust has reached the sill."},
}


class ScriptedBackend:
    """Returns a queued TurnOutput per call."""

    def __init__(self, outputs):
        self._outputs = list(outputs)
        self.calls = 0

    def complete(self, messages, *, contract=None, temperature=0.2, max_tokens=800) -> str:
        out = self._outputs[min(self.calls, len(self._outputs) - 1)]
        self.calls += 1
        return json.dumps(out)

    def embed(self, texts):  # pragma: no cover
        raise NotImplementedError


def _scripted_input(lines):
    it = iter(lines)

    def _input(_prompt=""):
        try:
            return next(it)
        except StopIteration:
            raise EOFError
    return _input


def test_instantiate_world_builds_stable_state():
    state = instantiate_world(BLUEPRINT, seed=42)
    assert state["blueprint_id"] == "testworld"
    assert state["player"]["location"] == "conapt"
    assert state["player"]["inventory"] == ["dial"]
    assert state["stats"] == {"Vitality": 100.0, "Awareness": 0.0, "kipple_level": 10.0}
    assert state["map"]["conapt"]["visited"] is True
    assert state["map"]["conapt"]["description"] == "dusty"
    assert state["seed"] == 42


def test_eval_condition_and_or_not():
    state = {"stats": {"Awareness": 85.0, "Vitality": 100.0}, "flags": {}}
    assert eval_condition(state, "progress.Awareness >= 80 and not captured")
    assert not eval_condition(state, "resilience.Vitality <= 0")
    assert eval_condition(state, "resilience.Vitality <= 0 or progress.Awareness >= 80")
    state["flags"]["captured"] = True
    assert not eval_condition(state, "progress.Awareness >= 80 and not captured")


def test_check_endings_fires_on_condition():
    state = instantiate_world(BLUEPRINT)
    state["stats"]["Vitality"] = 0.0
    assert check_endings(state, BLUEPRINT) == "dead"
    assert state["ending"] == "dead"


def test_step_applies_deltas_and_fires_ending():
    state = instantiate_world(BLUEPRINT)
    backend = ScriptedBackend([
        {"narration": "The dust takes you.", "deltas": [
            {"op": "set", "target": "stats.Vitality", "value": 0},
            {"op": "fact", "target": "world", "value": "The lift is broken."},
        ]},
    ])
    result = step(state, BLUEPRINT, "wait", backend)

    assert "dust" in result.narration.lower()
    assert state["turn"] == 1
    assert state["stats"]["Vitality"] == 0
    assert state["facts"] == [{"text": "The lift is broken.", "turn": 0}]
    assert state["ending"] == "dead"


def test_run_session_plays_saves_and_ends(tmp_path):
    save = tmp_path / "testworld.save.json"
    backend = ScriptedBackend([
        {"narration": "You look around. Dust everywhere.", "deltas": [
            {"op": "set", "target": "player.location", "value": "hall"}]},
        {"narration": "Entropy wins.", "deltas": [
            {"op": "set", "target": "stats.Vitality", "value": 0}]},
    ])
    outputs: list[str] = []
    state = run_session(
        BLUEPRINT, backend, save_path=save, state=instantiate_world(BLUEPRINT),
        input_fn=_scripted_input(["/look", "look around", "wait"]),
        output_fn=outputs.append,
    )

    joined = "\n".join(outputs)
    assert "The dust has reached the sill." in joined   # intro shown
    assert "Dust everywhere" in joined                  # first turn narration
    assert state["ending"] == "dead"
    assert state["player"]["location"] == "hall"        # movement persisted
    assert "hall" in state["map"]                        # materialized on entry
    assert save.exists()                                 # autosaved at end


def test_play_cli_errors_without_blueprint(tmp_path, monkeypatch):
    monkeypatch.setenv("SIMULA_WORKSPACE", str(tmp_path / "ws"))
    assert main(["play", "--world", "missing"]) == 1
    assert main(["play"]) == 1  # neither --world nor --blueprint
