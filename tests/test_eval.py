"""Tests for the eval rig (metrics + ablation), no live server needed."""
from __future__ import annotations

import json

from simula import eval as evalmod
from simula.eval import anchor_terms, bookkeeping_drift, commit_rate, evaluate

BLUEPRINT = {
    "id": "testworld",
    "title": "Test World",
    "voice": {"summary": "bleak", "person": "second", "sensory_palette": ["dust", "static"]},
    "lexicon": ["kipple", "conapt"],
    "seeds": {"places": [{"id": "conapt", "name": "The Conapt"}]},
    "opening": {"location": "conapt", "inventory": [], "intro": "dust"},
}


class ScriptedBackend:
    """Returns a queued TurnOutput (parsed by the loop) per call."""

    def __init__(self, outputs):
        self._outputs = list(outputs)
        self.calls = 0

    def complete(self, messages, *, contract=None, temperature=0.2, max_tokens=800) -> str:
        out = self._outputs[min(self.calls, len(self._outputs) - 1)]
        self.calls += 1
        return json.dumps(out)

    def embed(self, texts):  # pragma: no cover
        raise NotImplementedError


# A narration that commits (uses "kipple") and one that is generic mush.
_COMMIT = {"narration": "The kipple drifts across the floor.", "deltas": []}
_MUSH = {"narration": "Something happens, somewhere, somehow.", "deltas": []}


def test_anchor_terms_pulls_from_spine():
    anchors = anchor_terms(BLUEPRINT)
    assert "kipple" in anchors and "dust" in anchors and "the conapt" in anchors


def test_commit_rate_counts_anchored_turns():
    records = [evalmod.TurnRecord("look", _COMMIT["narration"], [], []),
               evalmod.TurnRecord("wait", _MUSH["narration"], [], [])]
    assert commit_rate(records, anchor_terms(BLUEPRINT)) == 0.5


def test_commit_rate_none_without_anchors():
    records = [evalmod.TurnRecord("x", "anything", [], [])]
    assert commit_rate(records, set()) is None


def test_bookkeeping_drift_is_rejected_fraction():
    records = [evalmod.TurnRecord("a", "n", applied=[{"op": "set"}], rejected=[{"op": "move"}]),
               evalmod.TurnRecord("b", "n", applied=[{"op": "flag"}], rejected=[])]
    assert bookkeeping_drift(records) == 1 / 3   # 1 rejected of 3 total deltas


def test_evaluate_end_to_end_without_embedder():
    backend = ScriptedBackend([_COMMIT, _MUSH, _COMMIT])
    report = evaluate(BLUEPRINT, backend, ["look", "wait", "touch"], kind="world")
    assert report.turns == 3
    assert report.commit_rate == 2 / 3
    assert report.style_fidelity is None      # no embedder
    assert report.narrative_drift is None     # no real ledger yet
    assert report.bookkeeping_drift == 0.0


def test_ablation_returns_both_arms_and_delta():
    # A stub retriever; the scripted backend ignores grounding, so metrics match and delta is 0.
    backend = ScriptedBackend([_COMMIT])
    result = evalmod.ablate_grounding(
        BLUEPRINT, backend, ["look", "look"], kind="world",
        retrieve=lambda q, k: ["the kipple piles up"],
    )
    assert result["grounded"].grounded is True
    assert result["ungrounded"].grounded is False
    assert result["delta"]["commit_rate"] == 0.0


def test_report_to_dict_is_json_serializable():
    backend = ScriptedBackend([_COMMIT])
    report = evaluate(BLUEPRINT, backend, ["look"], kind="world")
    json.dumps(evalmod.report_to_dict(report))  # must not raise
