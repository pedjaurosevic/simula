---
title: Design
layout: default
nav_order: 3
---

# Design
{: .no_toc }

1. TOC
{:toc}

---

The full design plan lives in [`PLAN.md`](https://github.com/pedjaurosevic/simula/blob/main/PLAN.md)
in the repository. This page summarizes the architecture.

## The unified entity model

Everything in simula is a **simulacrum**:

```
Simulacrum = (Blueprint, State, Memory, Contract)
```

- **Blueprint** — the distilled spine: *what* the entity is. Mostly pointers into the materials plus
  a short summary. Not a large ontology.
- **State** — the deterministic source of truth, held by the *engine*, not the model.
- **Memory** — short-term (transcript window) + long-term (fact ledger, history) + search (RAG) over
  both.
- **Contract** — the grammar/schema the LLM must emit to propose a delta. Structure at the boundary,
  free reasoning inside.

From this, everything follows:

- **World** = a simulacrum whose state is the *environment* (places, objects, NPCs, time); the loop
  is exploration.
- **Persona** = a simulacrum whose state is the *agent* (mood, knowledge, relationship, goals); the
  loop is conversation.
- **NPC** = a persona-simulacrum *embedded* in a world-simulacrum. Persona-in-world is a
  composition of simulacra, not new machinery.

## The turn loop (ORORO-minimal)

One turn, identical for world and persona:

1. **Observe** — take the user's input.
2. **Retrieve** — RAG fetches relevant passages + relevant facts from the ledger.
3. **React** — assemble a minimal prompt: commit directive + blueprint spine + exemplars + current
   state + transcript window + input.
4. **Constrain** — call the backend with a contract (GBNF locally / `json_schema` on OpenAI-compat).
   Output `{ narration, deltas[] }`, guaranteed parsable.
5. **Validate & apply** — the engine checks deltas against state and the ledger, applies valid ones,
   writes to the ledger.
6. **Persist & render** — save state, render the narration.

The **commit directive** is the most valuable part of the prompt: the model's failure mode is
hedging into generic mush, and the directive pushes it toward a concrete, anchored detail.

## Backend abstraction

One interface, two adapters:

```
complete(messages, *, contract=None, temperature, max_tokens) -> str
```

- **LlamaCppBackend** (primary, local): constrained output via a GBNF grammar — valid JSON
  guaranteed at decode time.
- **OpenAICompatBackend**: constrained output via `response_format: json_schema` or tool-calling,
  with a parse-and-repair fallback.

The "Contract" is the structured-output abstraction, implemented differently per backend. It is the
reliability backbone.

## Against drift

Two levels of drift, two cures:

- **Bookkeeping** (inventory, location): state outside the model + constrained deltas + engine
  validation. The model proposes, the engine adjudicates.
- **Narrative/tonal/factual**: RAG grounding on the materials every turn + a **fact ledger** that is
  both retrieved and used to validate contradictions.

The second level is the real hard problem — simula's engineering value lives there.

## Eval rig

The eval rig is the product; the prompt is a consumable. It measures:

- **style-fidelity** — embedding distance of output to the corpus.
- **drift** — contradictions against the fact ledger across N turns.
- **commit-rate** — fraction of turns with a concrete, anchored detail vs generic mush.

Every prompt/RAG/backend change passes a fast ablation before adoption.

## Build phases

Each phase has an eval gate; a component is added only when ablation shows a delta or prevents a
regression.

| Phase | What |
| --- | --- |
| 0 | Skeleton: workspace, config, backend adapter, contract, hello-world loop on empty content |
| 1 | Ingest + RAG: books → chunk → embed → retrieve |
| 2 | Worldbuilding: world distill + play loop + state + fact ledger + TUI (first world: **Kipple**) |
| 3 | Eval rig: style-fidelity, drift, commit-rate |
| 4 | Persona: OCEAN/IPIP substrate × material → persona blueprint + conversation loop |
| 5 | Web UI: thin client over the core (FastAPI) |
| 6 | Persona-in-world: a persona as a rich NPC |

## Non-goals

- No large world ontology in the prompt.
- No rigid multi-step reasoning templates in the system prompt.
- No self-modifying layer in v1.
- No LangChain or heavy abstractions — direct calls.
- No Z-machine/Zork fork.
