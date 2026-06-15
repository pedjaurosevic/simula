"""Distill a corpus into a compact world blueprint (map-reduce). No RAG — a one-time batch.

The corpus is far larger than any context window, so we (1) split it into context-sized windows,
(2) MAP each window to partial world notes via the model, and (3) REDUCE the partials into one
blueprint with deterministic merging. This is NOT RAG: no embeddings, no vector store. The model
extracts *texture* (tone, rules, lexicon, seeds) and is told to paraphrase, never quote at length
(PLAN.md #9, copyright hygiene).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .backends import Backend, Contract, Message

DEFAULT_WINDOW_CHARS = 80_000  # ~20k tokens; raise it for big-context (cloud) backends.
MAX_LEXICON = 40
MAX_RULES = 20
MAX_SEEDS = 12
MAX_SITUATIONS = 6
MAX_PALETTE = 12

# Default genre-styled stat names; falls back to generic if the genre is unknown.
GENRE_STATS = {
    "fantasy": ("Vitality", "Lore"),
    "cyberpunk": ("Neural Integrity", "Ghost Signal"),
    "noir": ("Stamina", "Notoriety"),
    "detective noir": ("Stamina", "Notoriety"),
    "gothic horror": ("Sanity", "Influence"),
    "horror": ("Sanity", "Resolve"),
    "sci-fi": ("Hull Integrity", "Reputation"),
    "dystopian sci-fi": ("Vitality", "Awareness"),
    "western": ("Grit", "Legend"),
    "historical drama": ("Resolve", "Legacy"),
    "dystopian": ("Compliance", "Awareness"),
    "post-apocalyptic": ("Health", "Survival"),
}

# Constrained shape for each MAP step. Backends honor it via json_schema (OpenAI / llama.cpp chat).
MAP_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["voice", "rules", "lexicon"],
    "properties": {
        "genre_primary": {"type": "string"},
        "genre_conventions": {"type": "array", "items": {"type": "string"}},
        "voice": {"type": "string"},
        "person": {"type": "string", "enum": ["first", "second", "third", ""]},
        "sensory_palette": {"type": "array", "items": {"type": "string"}},
        "rules": {"type": "array", "items": {"type": "string"}},
        "lexicon": {"type": "array", "items": {"type": "string"}},
        "dramatic_situations": {"type": "array", "items": {"type": "string"}},
        "topology": {"type": "string"},
        "places": {"type": "array", "items": {"$ref": "#/$defs/place"}},
        "factions": {"type": "array", "items": {"$ref": "#/$defs/seed"}},
        "archetypes": {"type": "array", "items": {"$ref": "#/$defs/seed"}},
    },
    "$defs": {
        "seed": {
            "type": "object",
            "additionalProperties": False,
            "required": ["name"],
            "properties": {"name": {"type": "string"}, "note": {"type": "string"}},
        },
        "place": {
            "type": "object",
            "additionalProperties": False,
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "note": {"type": "string"},
                "exits": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
}

MAP_INSTRUCTION = (
    "You are distilling a world from an excerpt of the user's own materials. Extract only the "
    "TEXTURE of the world, never the plot or long quotations. Paraphrase in your own words. Return: "
    "genre_primary (a short genre label) and genre_conventions; voice (1-2 sentences on register/"
    "mood) plus person (narration person) and a sensory_palette; rules (the world's conventions/"
    "'physics' and any epistemic limits); lexicon (signature coinages); dramatic_situations (which "
    "of Polti's 36 classic conflicts fit, by name); topology (how space is organized, e.g. "
    "'interconnected-rooms', 'city-districts', 'star-systems'); and light seeds: places (with a few "
    "exits to other place names), factions, archetypes. Be terse and concrete; short lists if the "
    "excerpt reveals little."
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


def map_window(
    window: str,
    backend: Backend,
    *,
    instruction: str = MAP_INSTRUCTION,
    schema: dict = MAP_SCHEMA,
    temperature: float = 0.2,
    max_tokens: int = 800,
) -> dict:
    """MAP one window to partial notes (world or persona). Defensive: a bad window yields {}."""
    messages = [Message(role="system", content=instruction), Message(role="user", content=window)]
    raw = backend.complete(
        messages, contract=Contract(json_schema=schema), temperature=temperature, max_tokens=max_tokens
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


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name.strip().lower()).strip("_")


def _most_common(items: list[str]) -> str:
    counts: dict[str, int] = {}
    first: dict[str, str] = {}
    for it in items:
        key = it.strip().lower()
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
        first.setdefault(key, it.strip())
    if not counts:
        return ""
    best = max(counts, key=lambda k: counts[k])
    return first[best]


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


def _dedup_places(places: list[dict], cap: int) -> list[dict]:
    """Dedup places by name, assign stable ids, and normalize exits into {to} edges."""
    seen: dict[str, dict] = {}
    for p in places:
        if not isinstance(p, dict) or not p.get("name"):
            continue
        name = str(p["name"]).strip()
        key = name.lower()
        if key in seen:
            continue
        entry: dict[str, Any] = {"id": _slug(name) or key, "name": name}
        if p.get("note"):
            entry["note"] = str(p["note"]).strip()
        exits = [str(e).strip() for e in p.get("exits", []) if str(e).strip()]
        if exits:
            entry["exits"] = [{"to": _slug(e) or e} for e in exits]
        seen[key] = entry
    return list(seen.values())[:cap]


def _stats_for_genre(genre: str, axes: list[dict]) -> dict:
    res, prog = GENRE_STATS.get(genre.strip().lower(), ("Vitality", "Progress"))
    stats: dict[str, Any] = {
        "resilience": {"name": res, "start": 100, "min": 0, "max": 100},
        "progress": {"name": prog, "start": 0, "max": 100},
    }
    if axes:
        stats["axes"] = axes
    return stats


def reduce_partials(partials: list[dict], *, world_id: str, title: str, source_note: str = "") -> dict:
    """REDUCE partials into a single v2 WorldBlueprint via deterministic merging."""
    genre = _most_common([p.get("genre_primary", "") for p in partials])
    conventions: list[str] = []
    voices: list[str] = []
    palette: list[str] = []
    persons: list[str] = []
    rules: list[str] = []
    lexicon: list[str] = []
    situations: list[str] = []
    topologies: list[str] = []
    places: list[dict] = []
    factions: list[dict] = []
    archetypes: list[dict] = []
    for p in partials:
        conventions += [str(c) for c in p.get("genre_conventions", []) if c]
        if p.get("voice"):
            voices.append(str(p["voice"]))
        palette += [str(s) for s in p.get("sensory_palette", []) if s]
        if p.get("person"):
            persons.append(str(p["person"]))
        rules += [str(r) for r in p.get("rules", []) if r]
        lexicon += [str(w) for w in p.get("lexicon", []) if w]
        situations += [str(s) for s in p.get("dramatic_situations", []) if s]
        if p.get("topology"):
            topologies.append(str(p["topology"]))
        places += list(p.get("places", []) or [])
        factions += list(p.get("factions", []) or [])
        archetypes += list(p.get("archetypes", []) or [])

    person = _most_common(persons)
    voice: dict[str, Any] = {
        "summary": " ".join(_dedup(voices, cap=3)) or f"The world of {title}.",
        "sensory_palette": _dedup(palette, MAX_PALETTE),
        "exemplar_refs": [],
    }
    if person in ("first", "second", "third"):
        voice["person"] = person

    blueprint: dict[str, Any] = {
        "id": world_id,
        "title": title,
        "genre": {"primary": genre or "Unspecified", "conventions": _dedup(conventions, 8)},
        "voice": voice,
        "rules": _dedup(rules, MAX_RULES),
        "lexicon": _dedup(lexicon, MAX_LEXICON),
        "stats": _stats_for_genre(genre, []),
        "dramatic_engine": {"situations": _dedup(situations, MAX_SITUATIONS)},
        "space": {"topology": _most_common(topologies) or "interconnected-rooms"},
        "seeds": {
            "places": _dedup_places(places, MAX_SEEDS),
            "factions": _dedup_seeds(factions, MAX_SEEDS),
            "archetypes": _dedup_seeds(archetypes, MAX_SEEDS),
        },
    }
    first_place = blueprint["seeds"]["places"][0] if blueprint["seeds"]["places"] else None
    if first_place:
        blueprint["opening"] = {"location": first_place["id"], "inventory": [], "intro": ""}
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


# --------------------------------------------------------------------------------------------------
# Persona distillation (books, materials, or conversations / exported chats). See
# resources/persona/ for the design. Same map-reduce; a chat-log parser + speaker filter front it.
# --------------------------------------------------------------------------------------------------

OCEAN_KEYS = ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")

PERSONA_MAP_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["voice"],
    "properties": {
        "voice": {"type": "string"},
        "register": {"type": "string"},
        "speech_tics": {"type": "array", "items": {"type": "string"}},
        "values": {"type": "array", "items": {"type": "string"}},
        "wants": {"type": "array", "items": {"type": "string"}},
        "needs": {"type": "array", "items": {"type": "string"}},
        "wound": {"type": "string"},
        "goals": {"type": "array", "items": {"type": "string"}},
        "quirks": {"type": "array", "items": {"type": "string"}},
        "boundaries": {"type": "array", "items": {"type": "string"}},
        "knowledge_domains": {"type": "array", "items": {"type": "string"}},
        "ocean": {
            "type": "object",
            "additionalProperties": False,
            "properties": {k: {"type": "number", "minimum": 0, "maximum": 1} for k in OCEAN_KEYS},
        },
    },
}

PERSONA_MAP_INSTRUCTION = (
    "You are distilling a PERSONA from an excerpt of the user's own materials (a character's lines, "
    "essays, or one person's chat messages). Extract only TEXTURE and TENDENCY, never long verbatim "
    "quotes or private secrets. Paraphrase. Return: voice (1-2 sentences on register/cadence/attitude) "
    "plus register and speech_tics; values; wants (surface desires) and needs (deeper, often unseen); "
    "wound (a formative hurt, if implied); goals; quirks; boundaries (things they would never say/do); "
    "knowledge_domains; and an ocean estimate (Big Five, each 0..1) from linguistic cues. Short fields "
    "if the excerpt reveals little."
)

# Matches "Name: message", optionally preceded by a timestamp like "[2024-01-01 12:00]" or
# "1/1/24, 12:00 -". Tolerant of common exported-chat formats.
_CHAT_LINE = re.compile(
    r"^\s*(?:\[[^\]]+\]\s*|[\d/.,:\s-]+-\s*)?(?P<speaker>[^:\n]{1,40}?):\s(?P<text>.*\S.*)$"
)


def parse_chat(text: str) -> list[tuple[str, str]]:
    """Parse exported-chat / conversation text into (speaker, message) turns.

    Returns [] if the text does not look like a speaker-tagged chat. Continuation lines (no speaker
    prefix) are appended to the previous turn.
    """
    turns: list[list[str]] = []
    for line in text.splitlines():
        m = _CHAT_LINE.match(line)
        if m:
            turns.append([m.group("speaker").strip(), m.group("text").strip()])
        elif turns and line.strip():
            turns[-1][1] += "\n" + line.strip()
    return [(s, t) for s, t in turns]


def speakers_in(turns: list[tuple[str, str]]) -> dict[str, int]:
    """Count messages per speaker (to help pick or validate a target)."""
    counts: dict[str, int] = {}
    for speaker, _ in turns:
        counts[speaker] = counts.get(speaker, 0) + 1
    return counts


def extract_speaker_text(text: str, speaker: str | None) -> str:
    """If `text` is a chat and `speaker` is given, return only that speaker's messages; else `text`.

    Speaker matching is case-insensitive and substring-tolerant (so 'mira' matches 'Mira K.').
    """
    turns = parse_chat(text)
    if not turns:
        return text
    if speaker is None:
        return text
    needle = speaker.strip().lower()
    picked = [t for s, t in turns if needle in s.lower()]
    return "\n\n".join(picked)


def _avg_ocean(partials: list[dict]) -> dict:
    out: dict[str, float] = {}
    for k in OCEAN_KEYS:
        vals = [float(p["ocean"][k]) for p in partials
                if isinstance(p.get("ocean"), dict) and isinstance(p["ocean"].get(k), (int, float))]
        out[k] = round(sum(vals) / len(vals), 3) if vals else 0.5
    return out


def reduce_persona_partials(
    partials: list[dict], *, persona_id: str, name: str,
    input_types: list[str] | None = None, source_note: str = "",
) -> dict:
    """REDUCE persona partials into a single v2 PersonaBlueprint via deterministic merging."""
    def gather(key: str) -> list[str]:
        out: list[str] = []
        for p in partials:
            out += [str(x) for x in p.get(key, []) if x]
        return out

    voices = [str(p["voice"]) for p in partials if p.get("voice")]
    registers = [str(p["register"]) for p in partials if p.get("register")]
    wounds = [str(p["wound"]) for p in partials if p.get("wound")]

    blueprint: dict[str, Any] = {
        "id": persona_id,
        "name": name,
        "ocean": _avg_ocean(partials),
        "voice": {
            "summary": " ".join(_dedup(voices, cap=3)) or f"The voice of {name}.",
            "exemplar_refs": [],
        },
        "values": _dedup(gather("values"), 12),
        "wants": _dedup(gather("wants"), 8),
        "needs": _dedup(gather("needs"), 8),
        "goals": _dedup(gather("goals"), 8),
        "quirks": _dedup(gather("quirks"), 12),
        "boundaries": _dedup(gather("boundaries"), 12),
        "knowledge": {"domains": _dedup(gather("knowledge_domains"), 12)},
    }
    register = _most_common(registers)
    if register:
        blueprint["voice"]["register"] = register
    tics = _dedup(gather("speech_tics"), 8)
    if tics:
        blueprint["voice"]["speech_tics"] = tics
    wound = _most_common(wounds)
    if wound:
        blueprint["wound"] = wound
    if input_types:
        blueprint["provenance"] = {"input_types": input_types}
    if source_note:
        blueprint["source_note"] = source_note
    return blueprint


def distill_persona(
    materials: list[str | Path],
    backend: Backend,
    *,
    persona_id: str,
    name: str,
    speaker: str | None = None,
    input_types: list[str] | None = None,
    window_chars: int = DEFAULT_WINDOW_CHARS,
    source_note: str = "",
    progress=None,
) -> dict:
    """Full pipeline: materials -> (optional speaker filter) -> windows -> MAP -> REDUCE -> PersonaBlueprint."""
    text = extract_speaker_text(read_materials(materials), speaker)
    if not text.strip():
        raise ValueError("no readable persona text found (check the file or --speaker name)")
    windows = chunk_text(text, window_chars)
    partials: list[dict] = []
    for i, window in enumerate(windows):
        if progress:
            progress(i + 1, len(windows))
        partials.append(map_window(
            window, backend, instruction=PERSONA_MAP_INSTRUCTION, schema=PERSONA_MAP_SCHEMA
        ))
    return reduce_persona_partials(
        partials, persona_id=persona_id, name=name, input_types=input_types, source_note=source_note
    )
