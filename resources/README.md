# resources/ — worldbuilding research & blueprint design

This folder is the **design reference** behind simula's most important artifact: the world
blueprint. It is not shipped in the package; it is the reasoning and the examples we build from.

The goal that drove this research: the blueprint is the key the LLM references every turn, and it
must express **the most diverse genres** with a single, genre-agnostic structure — while staying a
*spine*, not an ontology (PRINCIPLES.md #2).

## Layout

```
resources/
├── examples/
│   └── life-ai-crossroads-engine.md      # user-supplied reference engine + what each part teaches us
├── worldbuilding/
│   ├── zork-world-model.md               # "engine holds the truth": what to keep / drop from Zork
│   ├── interactive-fiction-and-branching-narrative.md  # CYOA vs QBN vs salience; what state each needs
│   └── blueprint-design-principles.md    # ★ KEYSTONE: the universal world blueprint (v2) spec
├── genres/
│   ├── dramatic-situations-polti.md      # Polti's 36 conflicts = the hidden dramatic engine
│   └── genre-taxonomy.md                 # genre pool + per-genre stat/tone/conflict conventions
├── worlds/
│   ├── kipple.world.json                 # worked example — Dystopian Sci-Fi
│   └── ashgrove-manor.world.json         # worked example — Gothic Horror (same schema, different genre)
├── persona/
│   ├── persona-modeling.md               # OCEAN + linguistic markers + character bible
│   ├── distilling-from-conversations.md  # building a persona from books / chat logs (+ consent)
│   └── persona-blueprint-design.md       # ★ KEYSTONE: the persona blueprint (v2) spec
└── personas/
    ├── elias-thorne.persona.json         # worked example — from a fiction corpus
    └── mira-the-archivist.persona.json   # worked example — from exported chat logs (consented)
```

## The three modules

simula has three modules over one engine, each eventually with a TUI and a web UI:

1. **Worldbuilding** — distill a world blueprint from materials (`worldbuilding/`, `worlds/`).
2. **Persona** — distill a persona blueprint from materials *or conversations* (`persona/`,
   `personas/`).
3. **Gameplay** — the runtime that instantiates a stable world/persona state and plays it.

Worldbuilding and persona are *builders* (they produce immutable blueprints). Gameplay is the
*runtime* (it owns the mutable, persistent `*_state`). Because a world and a persona are both a
`Simulacrum`, a persona can be dropped into a world as an NPC (persona-in-world, PLAN.md #4).

## The logic, in one paragraph

Zork proved the architecture (engine owns state; language only proposes). IF narrative theory
(quality-based + salience) tells us *what state* to track and how multiple endings emerge from
conditions instead of a branch tree. Polti's 36 give the LLM a concrete, genre-independent conflict
to commit to (the antidote to hedged, generic mush). The genre taxonomy shows that "genre" is just
data — a bundle of stat names, tone, and typical conflicts — so one schema covers everything. The
keystone doc folds all of this into a **universal blueprint** whose every field is a lever the turn
loop actually reads. The two example worlds prove the same fields express a PKD dystopia and a Gothic
manor equally well.

## Status

Design + examples. The shipped `schemas/world_blueprint.schema.json` is still v1; the v2 fields
(`genre/voice/stats/dramatic_engine/stakes`) described here get folded into the schema, into
`distill.py`, and into `simula play` when we build that phase.
