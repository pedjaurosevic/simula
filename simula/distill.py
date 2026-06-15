"""Distill a corpus into a compact world blueprint (map-reduce). No RAG — a one-time batch.

The corpus is far larger than any context window, so we (1) split it into context-sized windows,
(2) MAP each window to partial world notes via the model, and (3) REDUCE the partials into one
blueprint with deterministic merging. This is NOT RAG: no embeddings, no vector store. The model
extracts *texture* (tone, rules, lexicon, seeds) and is told to paraphrase, never quote at length
(PLAN.md #9, copyright hygiene).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .backends import Backend, Contract, Message

DEFAULT_WINDOW_CHARS = 80_000  # ~20k tokens; raise it for big-context (cloud) backends.
MAX_LEXICON = 40
MAX_RULES = 20
MAX_SEEDS = 12

# Constrained shape for each MAP step. Backends honor it via json_schema (OpenAI / llama.cpp chat).
MAP_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["tone", "rules", "lexicon"],
    "properties": {
        "tone": {"type": "string"},
        "rules": {"type": "array", "items": {"type": "string"}},
        "lexicon": {"type": "array", "items": {"type": "string"}},
        "places": {"type": "array", "items": {"$ref": "#/$defs/seed"}},
        "factions": {"type": "array", "items": {"$ref": "#/$defs/seed"}},
        "archetypes": {"type": "array", "items": {"$ref": "#/$defs/seed"}},
    },
    "$defs": {
        "seed": {
            "type": "object",
            "additionalProperties": False,
            "required": ["name"],
            "properties": {"name": {"type": "string"}, "note": {"type": "string"}},
        }
    },
}

MAP_INSTRUCTION = (
    "You are distilling a world from an excerpt of the user's own materials. Extract only the "
    "TEXTURE of the world, never the plot or long quotations. Paraphrase in your own words. "
    "Return: tone (1-2 sentences on register/mood), rules (the world's conventions/'physics'), "
    "lexicon (signature coinages or vocabulary), and light seeds (places, factions, archetypes). "
    "Be terse and concrete. If the excerpt reveals little, return short lists."
)


def read_materials(paths: list[str | Path]) -> str:
    """Read and concatenate text materials. Phase 0: plain-text files only (.txt/.md)."""
    texts: list[str] = []
    for p in paths:
        path = Path(p)
        files = sorted(path.rglob("*")) if path.is_dir() else [path]
        for f in files:
            if f.is_file() and f.suffix.lower() in (".txt", ".md"):
                texts.append(f.read_text(encoding="utf-8", errors="replace"))
    return "\n\n".join(texts)


def chunk_text(text: str, max_chars: int = DEFAULT_WINDOW_CHARS) -> list[str]:
    """Split text into windows of at most max_chars, preferring paragraph boundaries."""
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    paragraphs = text.split("\n\n")
    windows: list[str] = []
    buf = ""
    for para in paragraphs:
        candidate = f"{buf}\n\n{para}" if buf else para
        if len(candidate) <= max_chars:
            buf = candidate
            continue
        if buf:
            windows.append(buf)
        # A single oversized paragraph is hard-split.
        while len(para) > max_chars:
            windows.append(para[:max_chars])
            para = para[max_chars:]
        buf = para
    if buf:
        windows.append(buf)
    return windows


def _build_map_messages(window: str) -> list[Message]:
    return [
        Message(role="system", content=MAP_INSTRUCTION),
        Message(role="user", content=window),
    ]


def map_window(window: str, backend: Backend, *, temperature: float = 0.2, max_tokens: int = 800) -> dict:
    """MAP one window to partial world notes. Defensive parsing; a bad window yields empty notes."""
    raw = backend.complete(
        _build_map_messages(window),
        contract=Contract(json_schema=MAP_SCHEMA),
        temperature=temperature,
        max_tokens=max_tokens,
    )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _dedup(items: list[str], cap: int) -> list[str]:
    seen: dict[str, str] = {}
    for it in items:
        key = it.strip().lower()
        if key and key not in seen:
            seen[key] = it.strip()
    return list(seen.values())[:cap]


def _dedup_seeds(seeds: list[dict], cap: int) -> list[dict]:
    seen: dict[str, dict] = {}
    for s in seeds:
        if not isinstance(s, dict) or not s.get("name"):
            continue
        key = str(s["name"]).strip().lower()
        if key and key not in seen:
            entry = {"name": str(s["name"]).strip()}
            if s.get("note"):
                entry["note"] = str(s["note"]).strip()
            seen[key] = entry
    return list(seen.values())[:cap]


def reduce_partials(partials: list[dict], *, world_id: str, title: str, source_note: str = "") -> dict:
    """REDUCE partials into a single WorldBlueprint via deterministic merging.

    Tone is synthesized by joining unique partial tones (a model-based reduce can refine this later).
    """
    tones = _dedup([p.get("tone", "") for p in partials if p.get("tone")], cap=3)
    rules: list[str] = []
    lexicon: list[str] = []
    places: list[dict] = []
    factions: list[dict] = []
    archetypes: list[dict] = []
    for p in partials:
        rules += [str(r) for r in p.get("rules", []) if r]
        lexicon += [str(w) for w in p.get("lexicon", []) if w]
        places += list(p.get("places", []) or [])
        factions += list(p.get("factions", []) or [])
        archetypes += list(p.get("archetypes", []) or [])

    blueprint: dict[str, Any] = {
        "id": world_id,
        "title": title,
        "tone": {"summary": " ".join(tones) or f"The world of {title}.", "exemplar_refs": []},
        "rules": _dedup(rules, MAX_RULES),
        "lexicon": _dedup(lexicon, MAX_LEXICON),
        "seeds": {
            "places": _dedup_seeds(places, MAX_SEEDS),
            "factions": _dedup_seeds(factions, MAX_SEEDS),
            "archetypes": _dedup_seeds(archetypes, MAX_SEEDS),
        },
    }
    if source_note:
        blueprint["source_note"] = source_note
    return blueprint


def distill_world(
    materials: list[str | Path],
    backend: Backend,
    *,
    world_id: str,
    title: str,
    window_chars: int = DEFAULT_WINDOW_CHARS,
    source_note: str = "",
    progress=None,
) -> dict:
    """Full pipeline: materials -> windows -> MAP -> REDUCE -> WorldBlueprint dict.

    `progress` is an optional callable(index, total) for CLI feedback.
    """
    text = read_materials(materials)
    if not text.strip():
        raise ValueError("no readable text materials found (.txt/.md)")
    windows = chunk_text(text, window_chars)
    partials: list[dict] = []
    for i, window in enumerate(windows):
        if progress:
            progress(i + 1, len(windows))
        partials.append(map_window(window, backend))
    return reduce_partials(partials, world_id=world_id, title=title, source_note=source_note)
