"""The turn loop and the unified entity model.

Everything is a Simulacrum = (blueprint, state, memory, contract). A World is a simulacrum of
place; a Persona is a simulacrum of agent; an NPC is a Persona embedded in a World. The loop is
the same for both; only blueprint and applied-delta semantics differ. (PLAN.md #1, #3)

SKELETON: contracts + docstrings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .backends import Backend, Contract, Message


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
    "Obavezi se na konkretan, opipljiv detalj ukorenjen u teksturi ovog sveta/persone. "
    "Nikad ne uzmичi u genericku fantastiku ili neodredjenost. Ako radnja nije izvodljiva, "
    "reci zasto, konkretno."
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
    raise NotImplementedError


def build_prompt(sim: Simulacrum, player_input: str, grounding: list, state: dict,
                 transcript_window: list[Message]) -> list[Message]:
    """Assemble the minimal prompt. Keep it thin: spine + pointers-grounding, not a big ontology
    (PRINCIPLES.md #2)."""
    raise NotImplementedError
