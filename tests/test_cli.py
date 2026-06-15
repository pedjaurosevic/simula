"""CLI wiring tests. The backend is faked so no server is needed."""
from __future__ import annotations

import json

import simula.config as config
from simula.__main__ import main


class PartialBackend:
    def complete(self, messages, *, contract=None, temperature=0.2, max_tokens=800) -> str:
        return json.dumps({"tone": "bleak", "rules": ["entropy wins"], "lexicon": ["kipple"]})

    def embed(self, texts):  # pragma: no cover
        raise NotImplementedError


def test_init_then_distill(tmp_path, monkeypatch):
    monkeypatch.setenv("SIMULA_WORKSPACE", str(tmp_path / "ws"))
    monkeypatch.setattr(config, "make_backend", lambda *a, **k: PartialBackend())

    assert main(["init"]) == 0
    (tmp_path / "ws" / "materials" / "book.txt").write_text("a world of dust", encoding="utf-8")

    assert main(["distill", "--id", "kipple", "--title", "Kipple"]) == 0

    out = tmp_path / "ws" / "blueprints" / "kipple.world.json"
    assert out.exists()
    bp = json.loads(out.read_text(encoding="utf-8"))
    assert bp["id"] == "kipple"
    assert bp["lexicon"] == ["kipple"]


def test_distill_without_init_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("SIMULA_WORKSPACE", str(tmp_path / "ws"))
    # No init -> no config -> graceful error, non-zero exit.
    assert main(["distill", "--id", "x"]) == 1
