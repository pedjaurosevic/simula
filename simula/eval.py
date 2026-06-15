"""Eval rig (PLAN.md #10): the instrument, not an afterthought.

Runs a fixed transcript against a blueprint+backend and measures whether the output stays true to
the materials. Three metrics:

  - commit-rate    — fraction of turns whose narration commits to a concrete, blueprint-anchored
                     detail (lexicon, sensory palette, place/entity names) instead of generic mush.
                     The direct test of the COMMIT_DIRECTIVE (PRINCIPLES.md #1).
  - style-fidelity — mean cosine of each narration to the nearest corpus chunk (does it *sound* like
                     the world/persona). Needs an embedder + a built RAG index; None otherwise.
  - drift          — bookkeeping drift = rate of deltas the engine had to reject. Narrative/factual
                     drift (PLAN.md #8) needs a real fact ledger (Ledger.contradicts is still a
                     stub) and is reported as None until that lands: we measure, we don't fake.

The headline use is ABLATION: run the same transcript with grounding on vs off and compare, so we
only keep a component when it shows a delta (PLAN.md #12).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import rag


@dataclass
class TurnRecord:
    player_input: str
    narration: str
    applied: list
    rejected: list
    committed: bool = False


@dataclass
class EvalReport:
    kind: str
    grounded: bool
    turns: int
    commit_rate: float | None        # None when the blueprint has no anchorable terms
    style_fidelity: float | None     # None when no embedder / no built index
    bookkeeping_drift: float
    narrative_drift: float | None    # None until a real fact ledger exists (PLAN.md #8)
    records: list = field(default_factory=list)


# --------------------------------------------------------------------------------------------------
# Anchors (for commit-rate)
# --------------------------------------------------------------------------------------------------

def anchor_terms(blueprint: dict) -> set[str]:
    """Concrete, blueprint-specific terms a committed narration is expected to touch.

    Drawn from the spine, NOT from per-turn grounding, so the metric is comparable across the
    grounded/ungrounded ablation arms.
    """
    bp = blueprint or {}
    terms: set[str] = set()

    def add(items):
        for x in items or []:
            if isinstance(x, str) and len(x.strip()) > 2:
                terms.add(x.strip().lower())

    add(bp.get("lexicon"))
    add((bp.get("voice") or {}).get("sensory_palette"))
    seeds = bp.get("seeds") or {}
    add([p.get("name") for p in (seeds.get("places") or []) if isinstance(p, dict)])
    add((bp.get("opening") or {}).get("inventory"))
    # Persona spine.
    for key in ("values", "wants", "needs", "goals", "quirks"):
        add(bp.get(key))
    return terms


def _committed(narration: str, anchors: set[str]) -> bool:
    low = narration.lower()
    return any(term in low for term in anchors)


# --------------------------------------------------------------------------------------------------
# Run a transcript
# --------------------------------------------------------------------------------------------------

def run_transcript(blueprint: dict, backend, inputs, *, kind: str = "world", retrieve=None):
    """Play a fixed list of player inputs; return (records, final_state). Pure-ish, no persistence."""
    from .play import instantiate_persona, instantiate_world, step, step_persona

    if kind == "persona":
        state = instantiate_persona(blueprint)
        stepper = step_persona
    else:
        state = instantiate_world(blueprint)
        stepper = step

    records: list[TurnRecord] = []
    for player_input in inputs:
        result = stepper(state, blueprint, player_input, backend, retrieve=retrieve)
        records.append(TurnRecord(player_input, result.narration, result.applied, result.rejected))
    return records, state


# --------------------------------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------------------------------

def commit_rate(records: list[TurnRecord], anchors: set[str]) -> float | None:
    if not anchors or not records:
        return None
    committed = 0
    for r in records:
        r.committed = _committed(r.narration, anchors)
        committed += r.committed
    return committed / len(records)


def style_fidelity(records: list[TurnRecord], workspace: Path | None, embedder) -> float | None:
    if embedder is None or workspace is None:
        return None
    corpus = rag.corpus_embeddings(workspace)
    narrations = [r.narration for r in records if r.narration.strip()]
    if not corpus or not narrations:
        return None
    try:
        vectors = embedder.embed(narrations)
    except Exception:
        return None
    if not vectors or len(vectors) != len(narrations):
        return None
    sims = [max(rag.cosine(v, c) for c in corpus) for v in vectors]
    return sum(sims) / len(sims)


def bookkeeping_drift(records: list[TurnRecord]) -> float:
    """Rate of deltas the engine rejected as invalid against state. 0.0 when no deltas were proposed."""
    total = sum(len(r.applied) + len(r.rejected) for r in records)
    rejected = sum(len(r.rejected) for r in records)
    return (rejected / total) if total else 0.0


# --------------------------------------------------------------------------------------------------
# Evaluate + ablate
# --------------------------------------------------------------------------------------------------

def evaluate(blueprint: dict, backend, inputs, *, kind: str = "world", retrieve=None,
             workspace: Path | None = None, embedder=None) -> EvalReport:
    records, _ = run_transcript(blueprint, backend, inputs, kind=kind, retrieve=retrieve)
    anchors = anchor_terms(blueprint)
    return EvalReport(
        kind=kind,
        grounded=retrieve is not None,
        turns=len(records),
        commit_rate=commit_rate(records, anchors),
        style_fidelity=style_fidelity(records, workspace, embedder),
        bookkeeping_drift=bookkeeping_drift(records),
        narrative_drift=None,
        records=records,
    )


def ablate_grounding(blueprint: dict, backend, inputs, *, kind: str = "world", retrieve,
                     workspace: Path | None = None, embedder=None) -> dict:
    """Run the same transcript grounded vs ungrounded; return both reports + the metric deltas."""
    grounded = evaluate(blueprint, backend, inputs, kind=kind, retrieve=retrieve,
                        workspace=workspace, embedder=embedder)
    ungrounded = evaluate(blueprint, backend, inputs, kind=kind, retrieve=None,
                          workspace=workspace, embedder=embedder)

    def diff(field_name):
        g, u = getattr(grounded, field_name), getattr(ungrounded, field_name)
        return (g - u) if (g is not None and u is not None) else None

    return {
        "grounded": grounded,
        "ungrounded": ungrounded,
        "delta": {
            "commit_rate": diff("commit_rate"),
            "style_fidelity": diff("style_fidelity"),
            "bookkeeping_drift": diff("bookkeeping_drift"),
        },
    }


def report_to_dict(report: EvalReport) -> dict:
    d = asdict(report)
    d["records"] = [asdict(r) for r in report.records]
    return d
