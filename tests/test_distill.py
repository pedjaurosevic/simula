"""Tests for the distill (map-reduce) pipeline. Model calls use a deterministic fake backend."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from simula.backends import Message
from simula.distill import (
    chunk_text,
    distill_world,
    read_materials,
    reduce_partials,
)

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "world_blueprint.schema.json"


class PartialBackend:
    """Returns a fixed partial-notes JSON for every window (simulates the MAP step)."""

    def __init__(self, partial: dict) -> None:
        self._partial = partial
        self.calls = 0

    def complete(self, messages, *, contract=None, temperature=0.2, max_tokens=800) -> str:
        self.calls += 1
        return json.dumps(self._partial)

    def embed(self, texts):  # pragma: no cover
        raise NotImplementedError


def test_chunk_text_respects_max_and_splits_oversized():
    text = "\n\n".join(["para one", "para two", "x" * 50])
    windows = chunk_text(text, max_chars=20)
    assert all(len(w) <= 20 for w in windows)
    assert "".join(windows).count("x") == 50  # nothing lost on hard-split


def test_read_materials_reads_txt_and_md(tmp_path):
    (tmp_path / "a.txt").write_text("alpha", encoding="utf-8")
    (tmp_path / "b.md").write_text("beta", encoding="utf-8")
    (tmp_path / "c.pdf").write_text("ignored", encoding="utf-8")
    text = read_materials([tmp_path])
    assert "alpha" in text and "beta" in text and "ignored" not in text


def test_reduce_dedups_and_shapes():
    partials = [
        {"tone": "bleak", "rules": ["entropy wins"], "lexicon": ["kipple", "Kipple"],
         "places": [{"name": "Apartment", "note": "dusty"}]},
        {"tone": "bleak", "rules": ["entropy wins", "objects decay"], "lexicon": ["kibble"],
         "places": [{"name": "apartment"}]},
    ]
    bp = reduce_partials(partials, world_id="kipple", title="Kipple")

    assert bp["id"] == "kipple" and bp["title"] == "Kipple"
    assert bp["tone"]["summary"] == "bleak"               # deduped tone
    assert bp["rules"] == ["entropy wins", "objects decay"]
    assert bp["lexicon"] == ["kipple", "kibble"]          # case-insensitive dedup
    assert len(bp["seeds"]["places"]) == 1                # deduped by name


def test_distill_world_produces_valid_blueprint(tmp_path):
    (tmp_path / "book.txt").write_text("\n\n".join(f"chapter {i} text" for i in range(5)), encoding="utf-8")
    backend = PartialBackend(
        {"tone": "entropic, melancholy", "rules": ["reality is unreliable"],
         "lexicon": ["kipple"], "places": [{"name": "Conapt"}]}
    )

    bp = distill_world([tmp_path], backend, world_id="kipple", title="Kipple", window_chars=20)

    assert backend.calls >= 1
    for key in ("id", "title", "tone", "rules", "lexicon", "seeds"):
        assert key in bp

    # Validate against the real shipped schema.
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(bp, schema)


def test_distill_world_errors_on_empty_corpus(tmp_path):
    with pytest.raises(ValueError):
        distill_world([tmp_path], PartialBackend({}), world_id="x", title="X")
