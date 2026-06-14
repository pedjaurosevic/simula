# simula — PLAN

> A local-first engine for generating and inhabiting fashioned worlds and personas from the
> user's own materials. One engine, two blueprint types, one unified entity model.
> The name carries a question, not a claim: is a fashioned mind/world real? (PKD)

This document is the design plan. Code, schemas, and config are all in English (portability, GitHub).

---

## 0. What simula is (and is NOT)

**It is:** a thin harness that (1) takes the user's materials (books, texts), (2) distills a
*blueprint* from them (the spine of a world or a persona — mostly pointers into the material plus a
tiny summary), and (3) runs an interactive, stateful, memory-bearing experience in which the LLM
**proposes** structured changes while the engine **holds the truth**.

**It is NOT:** a world generator "out of thin air," an elaborate cognitive architecture, or a Zork
fork. Zork is a fixed authored world; we build a world *from a corpus*. (See `PRINCIPLES.md` for
why — these are lessons from our experiment series, not style.)

Two implementations over the same core:
- **simula worldbuilding** — a TUI/web game; the user walks through a world generated from their
  books. The founding idea; we build it first.
- **simula persona** — the same concept applied to creating a persona (Big Five / OCEAN substrate
  via IPIP, public domain × the user's material). Second phase.

A key idea: a persona created in *persona* mode can live inside a world from *worldbuilding* mode.
This is NOT an add-on — it is exactly what the unified entity model exists for (section 4).

---

## 1. The unified entity model — the heart of the design

Everything in simula is a **simulacrum**:

```
Simulacrum = (Blueprint, State, Memory, Contract)
```

- **Blueprint** — the distilled spine: WHAT the entity is. Mostly pointers into materials plus a
  short summary. NOT a large ontology (the B'=B lesson: ontology is decoration; grounding on the
  text carries the consequence).
- **State** — the deterministic source of truth held by the *engine*, not the model.
- **Memory** — short-term (transcript window) + long-term (fact ledger, history) + search (RAG)
  over both. This is the "remember."
- **Contract** — the grammar/schema the LLM MUST emit to propose a delta (narration + state change).
  Structure at the boundary, free reasoning inside.

Everything follows from this:
- **World** = a simulacrum whose state is the *environment* (places, objects, NPCs, time), and the
  loop is exploration.
- **Persona** = a simulacrum whose state is the *agent* (mood, knowledge, relationship, goals), and
  the loop is conversation.
- **NPC** = a persona-simulacrum *embedded* in a world-simulacrum. When the player talks to it, the
  world loop delegates that entity's turn to the persona loop, then returns the result as a world
  delta.

That is why persona-in-world is a **composition of simulacra**, not new machinery. You build one
entity abstraction and two blueprint schemas; the crossover is free (but *ships* last — section 4).

---

## 2. Layers

```
┌─────────────────────────────────────────────────────────┐
│  Clients (thin):  TUI (Textual)   |   Web UI (FastAPI)   │
├─────────────────────────────────────────────────────────┤
│  simula-core (library)                                   │
│   • Backend abstraction (llama.cpp local | OpenAI-compat)│
│   • Constrained output (GBNF local | json_schema/tools)  │
│   • RAG (sqlite-vec + FTS5, e5-small embeddings)         │
│   • State engine (sqlite, source of truth) + Fact ledger │
│   • Memory (short/long-term + search)                    │
│   • Turn loop (ORORO-minimal)                            │
│   • Eval rig (style-fidelity, drift, commit-rate)        │
├─────────────────────────────────────────────────────────┤
│  Blueprint layer:  World blueprint  |  Persona blueprint │
├─────────────────────────────────────────────────────────┤
│  Workspace:  ~/simula-workspace/  (sqlite, materials)    │
└─────────────────────────────────────────────────────────┘
```

Clients are thin — all logic is in `simula-core`. TUI and web are two skins over the same core.

---

## 3. Turn loop (ORORO-minimal)

One turn, identical for world and persona (the difference is only the blueprint and the delta
schema):

1. **Observe** — take the user's input.
2. **Retrieve** — RAG fetches relevant passages from the materials + relevant facts from the ledger
   (grounding against *narrative* drift, not just bookkeeping drift).
3. **React** — assemble a MINIMAL prompt: commit directive + blueprint spine + retrieved exemplars
   + current state + transcript window + user input.
4. **Constrain** — call the backend with a contract (GBNF locally / json_schema on OpenAI-compat).
   Output = `{ narration, deltas[] }`, guaranteed parsable.
5. **Validate & apply** — the engine checks deltas against state and the ledger (reject invalid ones
   — e.g., taking an object that isn't there), applies the valid ones, writes to the ledger.
6. **Persist & render** — save state, render the narration.

The commit directive is the most valuable part of the prompt (lesson from the tests: the model's
failure mode is hedging → generic mush). Roughly: *"Commit to a concrete, tangible detail rooted in
the texture of this world/persona. Never retreat into generic fantasy or vagueness."*

---

## 4. Persona-in-world — my view

The idea is good and not peripheral: it is the *reason* the entity model is unified. If both world
and persona are "simulacrum = (blueprint, state, memory, contract)," then a persona in a world is
just a rich NPC — the world loop delegates its turn to the persona loop. The abstraction allows it
from day one, so we should design it *in* immediately (uniform entities), even before we use it.

But honestly about the cost, so we don't build it too early:
- Two LLM-driven entities, each with their own state, mean *two* calls per turn (latency) and
  *multiplied* drift risk — the persona must stay true to itself AND fit the world's tone.
- That is the hardest coherence case. The "measure where it fails" lesson: don't build the hardest
  thing first.

So: **the architecture allows it from the start, but it ships last** (Phase 6), only once the eval
rig shows that the drift of a *single* entity is under control. Love the idea, defer the execution.

---

## 5. Backend abstraction (local-first, but always OpenAI-compat)

One interface, two adapters (see `simula/backends.py`):

```
complete(messages, *, contract=None, temperature, max_tokens) -> str
```

- **LlamaCppBackend** (primary): HTTP to a local server (:18083). Constrained output via a
  **GBNF grammar** (the `grammar` field) — a guarantee of valid JSON at decode time. Embeddings
  local (e5-small). This is the default.
- **OpenAICompatBackend**: any OpenAI-compatible endpoint + key + model. Constrained output via
  `response_format: json_schema` or tool-calling; a parse-and-repair fallback loop if the model
  doesn't support it. Embeddings: either their endpoint or still local e5 (recommended: local e5,
  to avoid coupling).

The backend choice lives in `simula.toml` in the workspace. The "Contract" is the structured-output
abstraction implemented differently per backend — it is the reliability backbone.

---

## 6. Workspace (installed on the user's machine)

Location via `platformdirs` (cross-platform), default `~/simula-workspace/`:

```
simula-workspace/
  simula.toml             # config: backend, endpoint, model, key, experience mode
  materials/              # the user's books/texts (theirs, local)
  library.sqlite          # RAG (sqlite-vec + FTS5) + state + memory + ledger
  blueprints/             # distilled world/persona blueprints (JSON)
  saves/                  # experience snapshots / transcripts
  evals/                  # eval rig results
```

The user adds books through the TUI or web (which copies them into `materials/` and runs the
ingest). Everything is inspectable and portable. **We do not ship a corpus** — the user brings
their own (section 9).

---

## 7. Cross-platform

The core is Python (Linux/Mac/Windows). Rules:
- No Linux-only dependencies; `pathlib` everywhere, no bash assumptions in the core.
- TUI: **Textual** (modern, cross-platform). Web: **FastAPI** + a thin frontend.
- sqlite-vec works cross-platform; e5-small via `sentence-transformers`/`llama.cpp` embeddings.
- The llama.cpp backend is just HTTP to a server the user runs (or uses OpenAI-compat), so the core
  doesn't depend on the server's platform.
- Workspace locations via `platformdirs`.

You develop on Linux Mint; CI tests Win/Mac too (a matrix) before every release.

---

## 8. Reliability: against drift

Two levels of drift, two cures:
- **Bookkeeping** (inventory, location): state outside the model + constrained deltas + validation
  in the engine. The model proposes, the engine adjudicates.
- **Narrative/tonal/factual** (forgets an established fact, betrays the tone, contradicts itself):
  RAG grounding on the materials every turn + a **fact ledger** (a running record of established
  facts) that is both retrieved and used to validate contradictions.

The second level is the real hard problem (the "measure where it fails" lesson). simula's
engineering value lives there, not in the beauty of a single turn.

---

## 9. Copyright / IP (important for a public GitHub)

- We ship the **engine, never the corpus**. The user brings their own books into `materials/`.
- The blueprint extracts *texture* (tone, motifs, structure, lexicon as pointers), it does not
  reproduce text. Add a guard against long verbatim passages in the narration.
- Result: a world *in the texture* of some author, not a transcript. Legal hygiene and better art.

---

## 10. Eval rig — the backbone, not an afterthought

Repurposes our apparatus from the test series (conditions, ablation, pre-registration). It measures:
- **style-fidelity** — embedding distance of the output to the corpus (does it sound like the
  world/persona).
- **drift** — the number of contradictions of the output against the fact ledger across N turns.
- **commit-rate** — the fraction of turns with a concrete, anchored detail vs generic mush
  (anti-mush; measures whether the commit directive works).

Every prompt/RAG/backend change passes a fast ablation before adoption. Every phase has an eval gate.

---

## 11. Persona blueprint — Big Five / OCEAN via IPIP (and NOT MBTI/16Personalities)

The persona substrate is **Big Five / OCEAN**, instantiated via **IPIP** items — which are in the
**public domain** (https://ipip.ori.org), free to copy, modify, translate, and use commercially,
without permission or fee. This is a deliberate choice, both legal and scientific:

- **Legally (important for a public GitHub release):** MBTI is a trademark of the Myers-Briggs
  company and a licensed instrument; 16Personalities is NOT MBTI but the NERIS framework with its
  own brand, descriptions, archetype names ("Advocate," etc.), and graphics — all their property.
  We do not reproduce their text, type names, or brand. The typology itself (the idea of axes,
  four-letter labels) is not copyrightable, but because we ship a public, commercially usable
  engine, we do not rely on a "hobby/personal" exception — we choose a clean public-domain
  substrate. (This is not legal advice; specifics vary for Serbia/EU vs US users of the repo.)
- **Scientifically:** OCEAN is empirically robust and falsifiable, unlike MBTI dichotomies. That
  matches the ethos of the test series (PRINCIPLES.md): measurable and honest, not a clinical claim.

Mapping: five **continuous** axes (O, C, E, A, N in [0,1]) → behavioral tendencies, register/voice
(from the materials if the persona is "after" a corpus), values, mannerisms, an own "history" in
memory. If a discrete seed is needed for generative convenience, we **bucket the continuous scores
into our own archetypes with our own names and descriptions** (the `archetype` field, optional) —
never anyone else's names or text. See `schemas/persona_blueprint.schema.json` (`ocean` instead of
the old `lattice`).

---

## 12. Build phases (each with an eval gate)

- **Phase 0 — skeleton.** Workspace bootstrap, config, backend adapter (llama.cpp + openai),
  contract abstraction, a "hello world" turn loop end-to-end on *empty* content. (First make it work
  end-to-end on empty, then add pieces.)
- **Phase 1 — ingest + RAG.** Add books → chunk → embed → retrieve. Gate: retrieval relevance on
  manual queries.
- **Phase 2 — worldbuilding (the founding idea).** World DISTILL (corpus → world blueprint) +
  worldbuilding PLAY loop + STATE + fact ledger. TUI client. First playable world: **Kipple** (PKD).
- **Phase 3 — eval rig.** style-fidelity, drift, commit-rate; ablate prompt/RAG choices. Gate:
  drift under control across a long session.
- **Phase 4 — persona.** Persona DISTILL (OCEAN/IPIP substrate × material → persona blueprint) +
  persona PLAY loop (conversation, consistency).
- **Phase 5 — web UI.** A thin client over the core (FastAPI). Adding books through the web.
- **Phase 6 — persona-in-world.** The uniform entity model pays off: a persona as a rich NPC. Only
  once Phase 3 shows controlled drift for a single entity.

The rule across all phases: add a component only when ablation shows a delta or prevents a
regression. The thinnest harness that works, then growth by proof — the inverse of "970/1000 of
machinery richness."

---

## 13. Explicit non-goals (anti-inflation)

- No large world ontology in the prompt (pointers + spine instead).
- No rigid multi-step reasoning templates in the system prompt (rigidity hurts — see dim_masina in
  `PRINCIPLES.md`).
- No self-modifying "super-exo" layer in v1 (defeasible heuristics later, if ablation asks).
- No LangChain or heavy abstractions — direct calls.
- No Z-machine/Zork fork — the wrong foundation for corpus→world.
