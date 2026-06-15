"""RAG over the user's materials (PLAN.md #1, #2, #8): the grounding that fights narrative drift.

The index lives in the workspace's `library.sqlite`. Two retrieval paths, merged by RRF:
  - lexical: SQLite FTS5 (always available in the stdlib sqlite3 build) — robust, exact terms.
  - vector:  e5-small-style embeddings (via the backend) + cosine — semantic, paraphrase-tolerant.

Embeddings are stored as float32 blobs and compared in Python (numpy). This keeps us off the
`sqlite-vec` loadable extension (fragile across platforms); the same `retrieve` interface can swap
in a vector store later. If embeddings are unavailable (no embedding server), retrieval degrades
gracefully to lexical-only — an un-embedded corpus still grounds.
"""
from __future__ import annotations

import re
import sqlite3
import struct
from pathlib import Path
from typing import Callable, Sequence

from .distill import chunk_text

# Retrieval chunks are far smaller than distill windows: we want pointed exemplars, not pages.
RETRIEVAL_CHUNK_CHARS = 1000
DEFAULT_TOP_K = 6
_RRF_K = 60  # reciprocal-rank-fusion constant; 60 is the common default.

_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)

# Common EN + SR function words. They carry no grounding signal but, left in the FTS query, let a
# chunk rank on a stopword match (e.g. "a", "the") and pollute the lexical leg of the hybrid.
_STOPWORDS = frozenset("""
a an the and or of to in on at is are am was were be been being it its this that these those for
with as by from has have had do does did not no nor so but if then than there here
i u o na se je su da li ne ni ali pa te za od do iz sa ka po kao sto što koji koja koje a ja ti on
ona ono mi vi oni su bi bih ce će
""".split())


def library_path(workspace: Path) -> Path:
    return Path(workspace) / "library.sqlite"


def connect(workspace: Path) -> sqlite3.Connection:
    """Open (and lazily create) the workspace RAG index."""
    conn = sqlite3.connect(library_path(workspace))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS chunks (
               id        INTEGER PRIMARY KEY,
               source    TEXT NOT NULL,
               ord       INTEGER NOT NULL,
               text      TEXT NOT NULL,
               embedding BLOB
           )"""
    )
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(text)")
    return conn


# --------------------------------------------------------------------------------------------------
# Embedding storage (float32 blobs, no extra deps to read/write)
# --------------------------------------------------------------------------------------------------

def _pack(vec: Sequence[float]) -> bytes:
    return struct.pack(f"<{len(vec)}f", *vec)


def _unpack(blob: bytes) -> list[float]:
    return list(struct.unpack(f"<{len(blob) // 4}f", blob))


def _embed_safe(backend, texts: list[str]):
    """Embed a batch, or return None if the backend can't (then we fall back to lexical-only)."""
    if backend is None or not texts:
        return None
    try:
        vectors = backend.embed(texts)
    except Exception:
        return None
    if not vectors or len(vectors) != len(texts):
        return None
    return vectors


# --------------------------------------------------------------------------------------------------
# Ingest
# --------------------------------------------------------------------------------------------------

def _iter_files(materials_dir: Path):
    for f in sorted(materials_dir.rglob("*")):
        if f.is_file() and f.suffix.lower() in (".txt", ".md"):
            yield f


def ingest(
    workspace: Path,
    backend=None,
    *,
    materials_dir: Path | None = None,
    chunk_chars: int = RETRIEVAL_CHUNK_CHARS,
    progress: Callable[[int, int], None] | None = None,
) -> dict:
    """(Re)build the RAG index from the workspace materials. Idempotent: replaces any prior index.

    Returns stats: {files, chunks, embedded}. Embedding is best-effort; lexical search always works.
    """
    ws = Path(workspace)
    materials_dir = materials_dir or (ws / "materials")
    rows: list[tuple[str, int, str]] = []
    files = list(_iter_files(materials_dir))
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for ord_, chunk in enumerate(chunk_text(text, chunk_chars)):
            rows.append((f.name, ord_, chunk))

    conn = connect(ws)
    try:
        conn.execute("DELETE FROM chunks")
        conn.execute("DELETE FROM chunks_fts")

        embedded = False
        for i in range(0, len(rows), 64):
            batch = rows[i : i + 64]
            vectors = _embed_safe(backend, [text for _, _, text in batch])
            embedded = embedded or vectors is not None
            for j, (source, ord_, text) in enumerate(batch):
                blob = _pack(vectors[j]) if vectors is not None else None
                cur = conn.execute(
                    "INSERT INTO chunks (source, ord, text, embedding) VALUES (?, ?, ?, ?)",
                    (source, ord_, text, blob),
                )
                conn.execute(
                    "INSERT INTO chunks_fts (rowid, text) VALUES (?, ?)", (cur.lastrowid, text)
                )
            if progress is not None:
                progress(min(i + 64, len(rows)), len(rows))
        conn.commit()
    finally:
        conn.close()

    return {"files": len(files), "chunks": len(rows), "embedded": embedded}


# --------------------------------------------------------------------------------------------------
# Retrieve
# --------------------------------------------------------------------------------------------------

def _fts_query(query: str) -> str:
    """Turn free text into a safe FTS5 OR-query of quoted content terms.

    Drops single characters and stopwords (they carry no grounding signal and otherwise let chunks
    rank on noise), and quotes each term to avoid FTS5 syntax/operator errors. May return "" — then
    the lexical leg is skipped and retrieval falls back to the vector leg.
    """
    terms = [t for t in _WORD_RE.findall(query.lower()) if len(t) > 1 and t not in _STOPWORDS]
    return " OR ".join(f'"{t}"' for t in terms)


def _lexical(conn: sqlite3.Connection, query: str, limit: int) -> list[tuple[int, str]]:
    match = _fts_query(query)
    if not match:
        return []
    try:
        cur = conn.execute(
            """SELECT c.id, c.text
                 FROM chunks_fts f JOIN chunks c ON c.id = f.rowid
                WHERE chunks_fts MATCH ?
                ORDER BY bm25(chunks_fts)
                LIMIT ?""",
            (match, limit),
        )
        return list(cur.fetchall())
    except sqlite3.OperationalError:
        return []


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    import math

    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _vector(conn: sqlite3.Connection, query_vec: Sequence[float], limit: int) -> list[tuple[int, str]]:
    rows = conn.execute(
        "SELECT id, text, embedding FROM chunks WHERE embedding IS NOT NULL"
    ).fetchall()
    scored = [
        (_cosine(query_vec, _unpack(blob)), cid, text) for cid, text, blob in rows
    ]
    scored.sort(key=lambda t: t[0], reverse=True)
    return [(cid, text) for _, cid, text in scored[:limit]]


def _rrf_merge(*ranked_lists: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Reciprocal Rank Fusion: combine ranked id-lists into one order. Stable, score-scale-free."""
    scores: dict[int, float] = {}
    texts: dict[int, str] = {}
    for ranked in ranked_lists:
        for rank, (cid, text) in enumerate(ranked):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (_RRF_K + rank)
            texts[cid] = text
    ordered = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    return [(cid, texts[cid]) for cid in ordered]


def retrieve(
    workspace: Path,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    *,
    backend=None,
) -> list[str]:
    """Return up to top_k chunk texts most relevant to the query (hybrid lexical + vector, RRF).

    Defensive: an empty index, an empty query, or a missing embedding path all yield a partial or
    empty result rather than raising — the turn loop must keep playing (PLAN.md #3).
    """
    if not query or not query.strip():
        return []
    conn = connect(workspace)
    try:
        pool = max(top_k * 4, top_k)
        lexical = _lexical(conn, query, pool)
        vector: list[tuple[int, str]] = []
        qvec = _embed_safe(backend, [query])
        if qvec is not None:
            vector = _vector(conn, qvec[0], pool)
        merged = _rrf_merge(lexical, vector) if (lexical and vector) else (lexical or vector)
        return [text for _, text in merged[:top_k]]
    finally:
        conn.close()


def corpus_embeddings(workspace: Path) -> list[list[float]]:
    """All stored chunk embeddings (for the eval rig's style-fidelity). Empty if none were stored."""
    conn = connect(workspace)
    try:
        rows = conn.execute("SELECT embedding FROM chunks WHERE embedding IS NOT NULL").fetchall()
        return [_unpack(blob) for (blob,) in rows]
    finally:
        conn.close()


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity, exposed for the eval rig."""
    return _cosine(a, b)


def make_retriever(workspace: Path, backend=None) -> Callable[[str, int], list[str]]:
    """Bind a `retrieve(query, top_k)` callable in the shape `run_turn` expects."""

    def _retrieve(query: str, top_k: int = DEFAULT_TOP_K) -> list[str]:
        return retrieve(workspace, query, top_k, backend=backend)

    return _retrieve
