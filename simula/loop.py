"""The turn loop and the unified entity model.

Everything is a Simulacrum = (blueprint, state, memory, contract). A World is a simulacrum of
place; a Persona is a simulacrum of agent; an NPC is a Persona embedded in a World. The loop is
the same for both; only blueprint and applied-delta semantics differ. (PLAN.md #1, #3)

Phase 0: a minimal but real end-to-end turn. The engine still owns truth; the model only proposes
deltas, which are validated and applied here. Persistence (sqlite) is the caller's job.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .backends import Backend, Contract, Message

# The delta ops the engine understands. Mirrors schemas/turn_output.schema.json + the GBNF.
OPS = frozenset({"set", "add", "remove", "move", "flag", "fact"})
DEFAULT_TOP_K = 6


@dataclass
class Simulacrum:
    """A world or a persona (or an NPC = persona-in-world)."""
    id: str
    kind: str                      # "world" | "persona"
    blueprint: dict                # validated against schemas/*.schema.json
    state: dict = field(default_factory=dict)   # engine-owned source of truth
    # memory + ledger live in sqlite (library.sqlite); referenced by id, not held in RAM.


@dataclass
class TurnResult:
    narration: str
    applied: list[dict]            # deltas the engine actually applied (after validation)
    rejected: list[dict]           # deltas rejected (invalid against state/ledger), for audit


COMMIT_DIRECTIVE = (
    "Commit to a concrete, tangible detail rooted in the texture of this world/persona. "
    "Never retreat into generic fantasy or vagueness. If an action is not feasible, say why, "
    "concretely."
)  # The single highest-value prompt content (PRINCIPLES.md #1).


def run_turn(
    sim: Simulacrum,
    player_input: str,
    backend: Backend,
    *,
    retrieve,                       # callable(query, top_k) -> list[chunk]
    ledger,                         # fact ledger interface (read/append/contradicts)
    transcript_window: list[Message],
    contract: Contract,
    temperature: float = 0.2,
    max_tokens: int = 800,
) -> TurnResult:
    """One ORORO-minimal turn (PLAN.md #3):

    1. Observe   - player_input is given.
    2. Retrieve  - grounding from materials + relevant ledger facts.
    3. React     - assemble a MINIMAL prompt (commit-directive + blueprint spine +
                   exemplars + current state + transcript window + input).
    4. Constrain - backend.complete(..., contract=contract) -> guaranteed-parsable TurnOutput.
    5. Validate  - check each delta against state + ledger; apply valid, reject invalid.
    6. Persist   - caller persists state + appends to ledger/transcript.

    Returns narration + applied/rejected deltas. Does NOT mutate sqlite directly; the caller
    persists (keeps this function pure-ish and testable for the eval rig).
    """
    # 2. Retrieve — grounding from materials + ledger. Defensive: an empty world still plays.
    grounding: list = []
    if retrieve is not None:
        try:
            grounding = list(retrieve(player_input, DEFAULT_TOP_K)) or []
        except Exception:
            grounding = []

    # 3. React — assemble the minimal prompt.
    messages = build_prompt(sim, player_input, grounding, sim.state, transcript_window)

    # 4. Constrain — the contract guarantees a parsable TurnOutput.
    raw = backend.complete(
        messages, contract=contract, temperature=temperature, max_tokens=max_tokens
    )
    parsed = parse_turn_output(raw)

    # 5. Validate & apply — engine adjudicates; model only proposes.
    applied: list[dict] = []
    rejected: list[dict] = []
    for delta in parsed["deltas"]:
        if delta_is_valid(delta) and not _contradicts(ledger, delta):
            _apply_delta(sim.state, delta, ledger)
            applied.append(delta)
        else:
            rejected.append(delta)

    return TurnResult(narration=parsed["narration"], applied=applied, rejected=rejected)


def build_prompt(sim: Simulacrum, player_input: str, grounding: list, state: dict,
                 transcript_window: list[Message]) -> list[Message]:
    """Assemble the minimal prompt. Keep it thin: spine + pointers-grounding, not a big ontology
    (PRINCIPLES.md #2)."""
    parts = [COMMIT_DIRECTIVE, "", _render_spine(sim)]
    if state:
        parts += ["", "Current state:", json.dumps(state, ensure_ascii=False)]
    if grounding:
        parts += ["", "Grounding (from the user's materials):"]
        parts += [f"- {chunk}" for chunk in grounding]
    system = Message(role="system", content="\n".join(p for p in parts if p is not None))

    messages = [system, *transcript_window, Message(role="user", content=player_input)]
    return messages


def _render_spine(sim: Simulacrum) -> str:
    """Render the blueprint spine compactly. Tolerates an empty blueprint (hello-world)."""
    bp = sim.blueprint or {}
    lines = [f"You are running a {sim.kind} simulacrum."]
    for key in ("title", "name"):
        if bp.get(key):
            lines.append(f"{key.capitalize()}: {bp[key]}")
    tone = bp.get("tone") or {}
    if isinstance(tone, dict) and tone.get("summary"):
        lines.append(f"Tone: {tone['summary']}")
    if bp.get("rules"):
        lines.append("Rules: " + "; ".join(map(str, bp["rules"])))
    if bp.get("lexicon"):
        lines.append("Lexicon: " + ", ".join(map(str, bp["lexicon"])))
    return "\n".join(lines)


def parse_turn_output(raw: str) -> dict:
    """Parse + shape-check a TurnOutput. The contract should guarantee this; we stay defensive."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"backend returned non-JSON output: {exc}") from exc
    if not isinstance(data, dict) or "narration" not in data or "deltas" not in data:
        raise ValueError("TurnOutput must be an object with 'narration' and 'deltas'")
    if not isinstance(data["narration"], str) or not isinstance(data["deltas"], list):
        raise ValueError("'narration' must be a string and 'deltas' a list")
    return data


def delta_is_valid(delta: Any) -> bool:
    """Structural validity (Phase 0). Richer state/ledger checks arrive with the state engine."""
    return (
        isinstance(delta, dict)
        and delta.get("op") in OPS
        and isinstance(delta.get("target"), str)
        and bool(delta.get("target"))
    )


def _contradicts(ledger: Any, delta: dict) -> bool:
    """Ask the ledger if this delta contradicts an established fact, if it can answer."""
    check = getattr(ledger, "contradicts", None)
    if callable(check):
        try:
            return bool(check(delta))
        except Exception:
            return False
    return False


def _apply_delta(state: dict, delta: dict, ledger: Any) -> None:
    """Apply a validated delta to in-memory state (the caller persists). Minimal Phase 0 semantics."""
    op, target, value = delta["op"], delta["target"], delta.get("value")
    if op == "fact":
        append = getattr(ledger, "append", None)
        if callable(append):
            append(delta)
        return
    if op in ("set", "move", "flag"):
        _set_path(state, target, value)
    elif op == "add":
        _set_path(state, target, _as_list(_get_path(state, target)) + [value])
    elif op == "remove":
        current = _as_list(_get_path(state, target))
        _set_path(state, target, [v for v in current if v != value])


def _as_list(value: Any) -> list:
    return list(value) if isinstance(value, list) else ([] if value is None else [value])


def _get_path(state: dict, dotted: str) -> Any:
    node: Any = state
    for key in dotted.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _set_path(state: dict, dotted: str, value: Any) -> None:
    keys = dotted.split(".")
    node = state
    for key in keys[:-1]:
        nxt = node.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            node[key] = nxt
        node = nxt
    node[keys[-1]] = value
