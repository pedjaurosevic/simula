"""Gameplay runtime: instantiate a stable world_state from a blueprint and play it.

The engine owns truth (PLAN.md #1, #8): the blueprint is an immutable seed; the world_state is the
mutable, PERSISTENT instance. Each turn runs `run_turn` (model proposes deltas, engine validates and
applies), then the runtime materializes the current place, bumps the turn counter, and fires any
emergent ending whose condition is met. State persists only on save; a new world starts fresh.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .backends import Backend, Contract
from .loop import Simulacrum, run_turn

GRAMMAR_PATH = Path(__file__).resolve().parent.parent / "grammars" / "turn_output.gbnf"


# --------------------------------------------------------------------------------------------------
# Instantiation
# --------------------------------------------------------------------------------------------------

def _init_stats(blueprint: dict) -> dict:
    """Flat stat map: gauges keyed by name, axes keyed by id (matches stakes.endings tokens)."""
    stats: dict[str, float] = {}
    bp_stats = blueprint.get("stats") or {}
    for gauge_key in ("resilience", "progress"):
        g = bp_stats.get(gauge_key)
        if isinstance(g, dict) and g.get("name"):
            stats[g["name"]] = float(g.get("start", 0))
    for axis in bp_stats.get("axes", []) or []:
        if isinstance(axis, dict) and axis.get("id"):
            stats[axis["id"]] = float(axis.get("start", 0))
    return stats


def instantiate_world(blueprint: dict, *, seed: int | None = None) -> dict:
    """Build a fresh world_state from a world blueprint's opening + seeds."""
    opening = blueprint.get("opening") or {}
    location = opening.get("location") or ""
    state: dict[str, Any] = {
        "world_id": f"{blueprint['id']}-{int(time.time())}",
        "blueprint_id": blueprint["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "turn": 0,
        "player": {"location": location, "inventory": list(opening.get("inventory", []))},
        "stats": _init_stats(blueprint),
        "map": {},
        "entities": {},
        "flags": {},
        "facts": [],
        "ending": None,
    }
    if seed is not None:
        state["seed"] = seed
    # Materialize seeded places so the map is stable from turn 0.
    for place in (blueprint.get("seeds") or {}).get("places", []) or []:
        pid = place.get("id") or place.get("name")
        if not pid:
            continue
        entry: dict[str, Any] = {"id": pid, "name": place.get("name", pid)}
        if place.get("note"):
            entry["description"] = place["note"]
        if place.get("exits"):
            entry["exits"] = [{"to": e["to"], **({"direction": e["direction"]} if e.get("direction") else {})}
                              for e in place["exits"] if e.get("to")]
        entry["contents"] = []
        entry["visited"] = pid == location
        state["map"][pid] = entry
    return state


# --------------------------------------------------------------------------------------------------
# Ending conditions (a small, safe evaluator — never eval())
# --------------------------------------------------------------------------------------------------

_CMP = re.compile(r"^([\w.]+)\s*(<=|>=|==|<|>)\s*(-?\d+(?:\.\d+)?)$")


def _num(state: dict, token: str) -> float:
    """Resolve a condition token (e.g. 'resilience.Sanity', 'axes.dread', 'captured') to a number."""
    seg = token.split(".")[-1]
    if seg in state.get("stats", {}):
        return float(state["stats"][seg])
    if seg in state.get("flags", {}):
        return float(bool(state["flags"][seg]))
    return 0.0


def _clause(state: dict, clause: str) -> bool:
    clause = clause.strip()
    neg = clause.startswith("not ")
    if neg:
        clause = clause[4:].strip()
    m = _CMP.match(clause)
    if m:
        left, op, right = _num(state, m.group(1)), m.group(2), float(m.group(3))
        res = {"<=": left <= right, ">=": left >= right, "==": left == right,
               "<": left < right, ">": left > right}[op]
    else:
        res = bool(_num(state, clause))
    return (not res) if neg else res


def eval_condition(state: dict, when: str) -> bool:
    """Evaluate a stakes condition: clauses joined by ' and ' / ' or ' (or-of-ands)."""
    if not when:
        return False
    return any(all(_clause(state, c) for c in part.split(" and "))
               for part in when.split(" or "))


def check_endings(state: dict, blueprint: dict) -> str | None:
    """Return the id of the first emergent ending whose condition holds, and record it."""
    for ending in (blueprint.get("stakes") or {}).get("endings", []) or []:
        if ending.get("id") and eval_condition(state, ending.get("when", "")):
            state["ending"] = ending["id"]
            return ending["id"]
    return None


# --------------------------------------------------------------------------------------------------
# One turn
# --------------------------------------------------------------------------------------------------

class _Ledger:
    """Minimal fact ledger over world_state['facts']."""

    def __init__(self, state: dict) -> None:
        self.state = state

    def append(self, delta: dict) -> None:
        self.state["facts"].append({"text": str(delta.get("value", "")), "turn": self.state["turn"]})

    def contradicts(self, delta: dict) -> bool:  # richer checks arrive later
        return False


def step(state: dict, blueprint: dict, player_input: str, backend: Backend,
         *, temperature: float = 0.2, max_tokens: int = 800):
    """Run one turn: model proposes, engine applies, then materialize place + check endings."""
    contract = Contract(gbnf_path=GRAMMAR_PATH if GRAMMAR_PATH.exists() else None,
                        json_schema=_TURN_SCHEMA)
    sim = Simulacrum(id=state["world_id"], kind="world", blueprint=blueprint, state=state)
    result = run_turn(
        sim, player_input, backend,
        retrieve=None, ledger=_Ledger(state), transcript_window=[],
        contract=contract, temperature=temperature, max_tokens=max_tokens,
    )
    state["turn"] += 1
    _materialize_current_place(state)
    check_endings(state, blueprint)
    return result


def _materialize_current_place(state: dict) -> None:
    """Ensure the player's current location exists in the stable map; mark it visited."""
    loc = state.get("player", {}).get("location")
    if not loc:
        return
    if loc not in state["map"]:
        state["map"][loc] = {"id": loc, "name": loc, "contents": [], "visited": True}
    else:
        state["map"][loc]["visited"] = True


# Minimal TurnOutput json_schema for backends that prefer it over GBNF.
_TURN_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["narration", "deltas"],
    "properties": {
        "narration": {"type": "string"},
        "deltas": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["op", "target"],
                "properties": {
                    "op": {"type": "string", "enum": ["set", "add", "remove", "move", "flag", "fact"]},
                    "target": {"type": "string"},
                    "value": {"type": ["string", "number", "boolean", "null"]},
                    "reason": {"type": "string"},
                },
            },
        },
    },
}


# --------------------------------------------------------------------------------------------------
# Persistence + interactive session
# --------------------------------------------------------------------------------------------------

def save_state(state: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_session(
    blueprint: dict,
    backend: Backend,
    *,
    save_path: Path,
    state: dict | None = None,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> dict:
    """Interactive loop. Commands: /save, /look, /stats, /quit. Returns the final state.

    Testable: pass input_fn/output_fn to drive it without a TTY. Stops on /quit, EOF, or an ending.
    """
    state = state if state is not None else instantiate_world(blueprint)
    opening = blueprint.get("opening") or {}
    if state["turn"] == 0 and opening.get("intro"):
        output_fn(opening["intro"])

    while state.get("ending") is None:
        try:
            raw = input_fn("> ")
        except EOFError:
            break
        cmd = raw.strip()
        if cmd in ("/quit", "/q"):
            break
        if cmd in ("/save", "/s"):
            save_state(state, save_path)
            output_fn(f"[saved to {save_path}]")
            continue
        if cmd == "/look":
            place = state["map"].get(state["player"]["location"], {})
            output_fn(place.get("description") or place.get("name") or "Nowhere in particular.")
            continue
        if cmd == "/stats":
            output_fn(", ".join(f"{k}: {v:g}" for k, v in state["stats"].items()) or "(no stats)")
            continue
        if not cmd:
            continue

        result = step(state, blueprint, cmd, backend)
        output_fn(result.narration)

    if state.get("ending"):
        output_fn(f"[ The story reaches an ending: {state['ending']} ]")
    save_state(state, save_path)
    return state


# --------------------------------------------------------------------------------------------------
# Persona runtime (conversation). A persona is a Simulacrum too, so the loop is the same; only the
# state shape (mood/disposition/knowledge/goals) and the lack of a map/endings differ.
# --------------------------------------------------------------------------------------------------

class _PersonaLedger:
    def __init__(self, state: dict) -> None:
        self.state = state

    def append(self, delta: dict) -> None:
        self.state["knowledge"].append({"text": str(delta.get("value", "")), "turn": self.state["turn"]})

    def contradicts(self, delta: dict) -> bool:
        return False


def instantiate_persona(blueprint: dict, *, seed: int | None = None) -> dict:
    """Build a fresh persona_state from a persona blueprint's opening + goals."""
    opening = blueprint.get("opening") or {}
    state: dict[str, Any] = {
        "persona_id": f"{blueprint['id']}-{int(time.time())}",
        "blueprint_id": blueprint["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "turn": 0,
        "mood": {"label": opening["mood"]} if opening.get("mood") else {},
        "disposition": {},
        "knowledge": [],
        "goals": [{"text": str(g), "status": "open"} for g in blueprint.get("goals", []) or []],
    }
    if seed is not None:
        state["seed"] = seed
    return state


def step_persona(state: dict, blueprint: dict, player_input: str, backend: Backend,
                 *, temperature: float = 0.4, max_tokens: int = 800):
    """One conversational turn: the persona replies (narration) and the engine applies deltas."""
    contract = Contract(gbnf_path=GRAMMAR_PATH if GRAMMAR_PATH.exists() else None,
                        json_schema=_TURN_SCHEMA)
    sim = Simulacrum(id=state["persona_id"], kind="persona", blueprint=blueprint, state=state)
    result = run_turn(
        sim, player_input, backend,
        retrieve=None, ledger=_PersonaLedger(state), transcript_window=[],
        contract=contract, temperature=temperature, max_tokens=max_tokens,
    )
    state["turn"] += 1
    return result


def run_persona_session(
    blueprint: dict,
    backend: Backend,
    *,
    save_path: Path,
    state: dict | None = None,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> dict:
    """Interactive conversation. Commands: /save, /mood, /quit. Returns the final persona_state."""
    state = state if state is not None else instantiate_persona(blueprint)
    opening = blueprint.get("opening") or {}
    if state["turn"] == 0 and opening.get("intro"):
        output_fn(opening["intro"])

    while True:
        try:
            raw = input_fn("> ")
        except EOFError:
            break
        cmd = raw.strip()
        if cmd in ("/quit", "/q"):
            break
        if cmd in ("/save", "/s"):
            save_state(state, save_path)
            output_fn(f"[saved to {save_path}]")
            continue
        if cmd == "/mood":
            output_fn(state.get("mood", {}).get("label") or "(neutral)")
            continue
        if not cmd:
            continue
        result = step_persona(state, blueprint, cmd, backend)
        output_fn(result.narration)

    save_state(state, save_path)
    return state
