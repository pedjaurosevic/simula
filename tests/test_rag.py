"""Tests for the RAG index (ingest + hybrid retrieval), no live server needed."""
from __future__ import annotations

from simula import rag


class FakeEmbedBackend:
    """Deterministic 'embeddings': a tiny bag-of-keywords vector so cosine is meaningful in tests."""

    VOCAB = ["kipple", "entropy", "dust", "garden", "river", "sunlight"]

    def embed(self, texts):
        vectors = []
        for text in texts:
            low = text.lower()
            vectors.append([float(low.count(word)) for word in self.VOCAB])
        return vectors


class DeadBackend:
    def embed(self, texts):
        raise RuntimeError("no embedding server")


def _write_materials(ws):
    mats = ws / "materials"
    mats.mkdir(parents=True, exist_ok=True)
    (mats / "a.txt").write_text(
        "The conapt fills with kipple and dust, entropy everywhere.", encoding="utf-8"
    )
    (mats / "b.md").write_text(
        "Beyond the wall lies a garden by the river, full of sunlight.", encoding="utf-8"
    )
    return mats


def test_ingest_counts_and_embeds(tmp_path):
    _write_materials(tmp_path)
    stats = rag.ingest(tmp_path, FakeEmbedBackend())
    assert stats["files"] == 2
    assert stats["chunks"] == 2
    assert stats["embedded"] is True
    assert rag.library_path(tmp_path).exists()


def test_vector_retrieval_ranks_semantic_match_first(tmp_path):
    _write_materials(tmp_path)
    rag.ingest(tmp_path, FakeEmbedBackend())

    hits = rag.retrieve(tmp_path, "sunlight in the garden", top_k=2, backend=FakeEmbedBackend())
    assert hits, "expected at least one grounding chunk"
    assert "garden" in hits[0].lower()


def test_lexical_only_fallback_when_no_embeddings(tmp_path):
    _write_materials(tmp_path)
    stats = rag.ingest(tmp_path, DeadBackend())
    assert stats["embedded"] is False

    # No backend at retrieval time either: FTS5 keyword search must still ground.
    hits = rag.retrieve(tmp_path, "kipple", top_k=2)
    assert any("kipple" in h.lower() for h in hits)


def test_reingest_is_idempotent(tmp_path):
    _write_materials(tmp_path)
    rag.ingest(tmp_path, FakeEmbedBackend())
    stats = rag.ingest(tmp_path, FakeEmbedBackend())
    assert stats["chunks"] == 2  # not doubled


def test_empty_query_and_empty_index_are_safe(tmp_path):
    (tmp_path / "materials").mkdir()
    assert rag.retrieve(tmp_path, "anything") == []   # empty index
    _write_materials(tmp_path)
    rag.ingest(tmp_path, FakeEmbedBackend())
    assert rag.retrieve(tmp_path, "   ") == []         # empty query


def test_make_retriever_matches_run_turn_shape(tmp_path):
    _write_materials(tmp_path)
    rag.ingest(tmp_path, FakeEmbedBackend())
    retrieve = rag.make_retriever(tmp_path, FakeEmbedBackend())
    out = retrieve("entropy and dust", 3)
    assert isinstance(out, list)
    assert all(isinstance(x, str) for x in out)
