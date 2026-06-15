"""Tests for the RAG index (ingest + hybrid retrieval), no live server needed."""
from __future__ import annotations

from simula import rag
from simula.backends import LlamaCppBackend, OpenAICompatBackend
from simula.config import make_embedder


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


def test_fts_query_drops_stopwords_and_short_tokens():
    # Only content terms survive; stopwords ("a", "the") and single chars are dropped.
    assert rag._fts_query("a machine fixing timepieces") == '"machine" OR "fixing" OR "timepieces"'
    # An all-stopword query yields nothing -> lexical leg is skipped, vector handles it.
    assert rag._fts_query("is it the") == ""


def test_stopword_does_not_pollute_lexical_ranking(tmp_path):
    # Regression (lexical-only to isolate the FTS fix): the distractor shares only the stopword "a"
    # with the query; the target shares the content word "android". Stopwords must not flip ranking.
    mats = tmp_path / "materials"
    mats.mkdir(parents=True)
    (mats / "android.txt").write_text("An android repairs broken clocks.", encoding="utf-8")
    (mats / "garden.txt").write_text("A green garden, a slow river, a high wall.", encoding="utf-8")
    rag.ingest(tmp_path, DeadBackend())  # no embeddings -> pure lexical

    hits = rag.retrieve(tmp_path, "a android", top_k=1)
    assert hits and "android" in hits[0].lower()


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


def test_make_embedder_decoupled_from_chat_backend():
    # Default/local e5 -> a llamacpp backend pointed at the embeddings endpoint, not the chat one.
    emb = make_embedder({"embeddings": {"kind": "llamacpp", "endpoint": "http://127.0.0.1:8081",
                                        "model": "e5"}})
    assert isinstance(emb, LlamaCppBackend)
    assert emb.endpoint == "http://127.0.0.1:8081"
    # "local_e5" is accepted as an alias with a sane default endpoint.
    assert isinstance(make_embedder({"embeddings": {"kind": "local_e5"}}), LlamaCppBackend)
    # Explicitly disabled -> None (RAG runs lexical-only).
    assert make_embedder({"embeddings": {"kind": "none"}}) is None
    # Missing section -> defaults to a local e5 backend (never silently chat-coupled).
    assert isinstance(make_embedder({}), LlamaCppBackend)


def test_make_retriever_matches_run_turn_shape(tmp_path):
    _write_materials(tmp_path)
    rag.ingest(tmp_path, FakeEmbedBackend())
    retrieve = rag.make_retriever(tmp_path, FakeEmbedBackend())
    out = retrieve("entropy and dust", 3)
    assert isinstance(out, list)
    assert all(isinstance(x, str) for x in out)
