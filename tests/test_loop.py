"""End-to-end Phase 0 turn, exercised with a deterministic fake backend (no server needed)."""
from __future__ import annotations

import json

import pytest

from simula.backends import Contract, Message
from simula.loop import (
    Simulacrum,
    build_prompt,
    delta_is_valid,
    parse_turn_output,
    run_turn,
)


class FakeBackend:
    """A Backend that echoes a canned TurnOutput, recording the messages it was given."""

    def __init__(self, output: dict) -> None:
        self._output = output
        self.seen_messages: list[Message] = []

    def complete(self, messages, *, contract=None, temperature=0.2, max_tokens=800) -> str:
        self.seen_messages = list(messages)
        return json.dumps(self._output)

    def embed(self, texts):  # pragma: no cover - not used in Phase 0
        raise NotImplementedError


def _empty_world() -> Simulacrum:
    return Simulacrum(id="w1", kind="world", blueprint={}, state={})


def test_run_turn_applies_valid_and_rejects_invalid():
    backend = FakeBackend(
        {
            "narration": "Dust settles on the counter.",
            "deltas": [
                {"op": "set", "target": "player.location", "value": "kitchen"},
                {"op": "add", "target": "inventory", "value": "knife"},
                {"op": "bogus", "target": "x"},          # invalid op -> rejected
                {"op": "set", "target": "", "value": "y"},  # empty target -> rejected
            ],
        }
    )
    sim = _empty_world()

    result = run_turn(
        sim,
        "look around",
        backend,
        retrieve=lambda q, k: [],
        ledger=None,
        transcript_window=[],
        contract=Contract(),
    )

    assert result.narration == "Dust settles on the counter."
    assert len(result.applied) == 2
    assert len(result.rejected) == 2
    # State was mutated by the engine, not the model.
    assert sim.state["player"]["location"] == "kitchen"
    assert sim.state["inventory"] == ["knife"]


def test_remove_delta_filters_list():
    backend = FakeBackend(
        {"narration": "You drop the knife.", "deltas": [{"op": "remove", "target": "inventory", "value": "knife"}]}
    )
    sim = Simulacrum(id="w1", kind="world", blueprint={}, state={"inventory": ["knife", "lamp"]})

    result = run_turn(
        sim, "drop knife", backend,
        retrieve=None, ledger=None, transcript_window=[], contract=Contract(),
    )

    assert result.applied and not result.rejected
    assert sim.state["inventory"] == ["lamp"]


def test_fact_delta_goes_to_ledger_not_state():
    appended: list[dict] = []

    class Ledger:
        def append(self, delta):
            appended.append(delta)

    backend = FakeBackend(
        {"narration": "Noted.", "deltas": [{"op": "fact", "target": "world", "value": "the sun is green"}]}
    )
    sim = _empty_world()

    run_turn(
        sim, "remember this", backend,
        retrieve=None, ledger=Ledger(), transcript_window=[], contract=Contract(),
    )

    assert appended == [{"op": "fact", "target": "world", "value": "the sun is green"}]
    assert sim.state == {}  # fact does not touch state


def test_ledger_contradiction_rejects_delta():
    class StrictLedger:
        def contradicts(self, delta):
            return True

    backend = FakeBackend(
        {"narration": "Hmm.", "deltas": [{"op": "set", "target": "player.location", "value": "moon"}]}
    )
    sim = _empty_world()

    result = run_turn(
        sim, "go to the moon", backend,
        retrieve=None, ledger=StrictLedger(), transcript_window=[], contract=Contract(),
    )

    assert not result.applied
    assert len(result.rejected) == 1
    assert sim.state == {}


def test_build_prompt_is_thin_and_ordered():
    sim = Simulacrum(
        id="kipple", kind="world",
        blueprint={"title": "Kipple", "tone": {"summary": "entropic, melancholy"}, "rules": ["reality is unreliable"]},
        state={"player": {"location": "apartment"}},
    )
    messages = build_prompt(sim, "open the door", grounding=["chunk: dust everywhere"], state=sim.state, transcript_window=[])

    assert messages[0].role == "system"
    assert messages[-1].role == "user" and messages[-1].content == "open the door"
    sys = messages[0].content
    assert "Commit to a concrete" in sys      # commit directive leads
    assert "Kipple" in sys and "entropic" in sys
    assert "dust everywhere" in sys           # grounding folded in


def test_parse_turn_output_rejects_bad_shape():
    with pytest.raises(ValueError):
        parse_turn_output("not json")
    with pytest.raises(ValueError):
        parse_turn_output(json.dumps({"narration": "x"}))  # missing deltas


def test_delta_is_valid():
    assert delta_is_valid({"op": "set", "target": "a"})
    assert not delta_is_valid({"op": "set", "target": ""})
    assert not delta_is_valid({"op": "nope", "target": "a"})
    assert not delta_is_valid("not a dict")
