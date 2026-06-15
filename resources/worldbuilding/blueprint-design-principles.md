# The universal world blueprint — design principles

This is the keystone document. It synthesizes Zork's world model, IF narrative theory (QBN/salience),
Polti's dramatic engine, genre taxonomy, and the user's L.I.F.E.AI example into **one genre-agnostic
blueprint** — the artifact the LLM references every turn.

## The central tension (and its resolution)

Two forces pull in opposite directions:

- The user's goal: the blueprint is **key** and must **cover the most diverse genres**.
- `PRINCIPLES.md #2`: the blueprint is **pointers + a tiny spine, NOT a big ontology** — empirically,
  ontology is decoration; grounding and de-hedging carry the effect.

**Resolution:** the blueprint grows in **structural levers**, not in **content volume**. We add a few
*genre-agnostic fields* (stats, dramatic engine, stakes, voice) that are each **a handful of lines**,
not a knowledge base. The corpus + fact ledger + RAG (later) carry the *content*; the blueprint
carries the *spine and the dials*. Every field below earns its place by being a lever the engine
*acts on each turn*, not lore for its own sake. If a field is never read by the loop, it does not
belong in the blueprint.

## What the engine references each turn (so the blueprint must provide)

From the loop (PLAN.md #3) and the sources, each turn the LLM needs:
1. **Who/where am I** → identity + state (location, inventory, NPCs).  → `seeds`, `opening`, state
2. **What is this world like** → tone, rules, lexicon.  → `voice`, `rules`, `lexicon`
3. **What is at stake / how do I fail** → consequence model + end conditions.  → `stats`, `stakes`
4. **What is the conflict** → a concrete dramatic situation to commit to.  → `dramatic_engine`
5. **What must stay true** → epistemic lock + established facts.  → `rules`, fact ledger
6. **How should this read** → prose register.  → `voice`

## The universal blueprint (proposed v2)

> v1 (shipped `schemas/world_blueprint.schema.json`) has: `id, title, tone, rules, lexicon, seeds,
> opening`. v2 adds `genre, voice, stats, dramatic_engine, stakes` and enriches `seeds`. It stays a
> spine: every block is short.

```jsonc
{
  "id": "kipple",
  "title": "Kipple",
  "genre": {
    "primary": "Dystopian Sci-Fi",            // free label; data, not an enum
    "conventions": ["entropy as antagonist", "unreliable reality", "bureaucratic dread"]
  },
  "source_note": "Distilled from the user's own materials. No source text shipped.",

  "voice": {                                   // prose register (example's "prose guidelines")
    "summary": "Melancholy, deadpan, entropic. Concrete decay over abstraction.",
    "person": "second",                        // narration person: first|second|third
    "sensory_palette": ["dust", "static", "fluorescent hum", "synthetic smells"],
    "exemplar_refs": []                        // RAG chunk ids later; short paraphrase notes for now
  },

  "rules": [                                   // world physics + HARD constraints (epistemic lock)
    "Objects decay into kipple if untended; entropy always wins locally.",
    "Reality may be simulated; some objects are simulacra.",
    "Epistemic lock: no knowledge beyond a 1990s-imagined near future."
  ],

  "lexicon": ["kipple", "kibble", "empathy box", "conapt", "mood organ"],

  "stats": {                                   // QBN qualities the engine tracks; genre-styled
    "resilience": { "name": "Vitality", "start": 100, "min": 0, "max": 100 },
    "progress":   { "name": "Awareness", "start": 0 },
    "axes": [                                  // extra named qualities (optional)
      { "id": "suspicion", "name": "Suspicion", "start": 0, "max": 100 },
      { "id": "kipple_level", "name": "Kipple", "start": 10, "max": 100 }
    ]
  },

  "dramatic_engine": {                         // hidden Polti levers (genre-independent)
    "situations": ["Revolt", "The Enigma", "Erroneous Judgment", "Pursuit"],
    "note": "Bureaucratic systems persecute; truth is unstable; the player resists or unravels it."
  },

  "stakes": {                                  // consequence model + emergent end conditions
    "soft": "lose a contact / gain Suspicion; emotional cost",
    "hard": "injury or a reality-break; major state shift",
    "fatal": "Vitality reaches 0, or absorbed fully into the system",
    "endings": [                              // emergent, condition-based — NOT a branch tree
      { "id": "escape",  "when": "progress.Awareness >= 80 and not captured" },
      { "id": "consumed", "when": "stats.kipple_level >= 100" }
    ]
  },

  "seeds": {                                   // light Zork-style substrate, NOT enumerated
    "places":    [{ "name": "The Conapt", "note": "decaying apartment; dust as a slow tide" }],
    "factions":  [{ "name": "The Bureau", "note": "issues unreliable directives" }],
    "archetypes":[{ "name": "The Bounty Clerk", "note": "weary functionary who suspects the truth" }]
  },

  "opening": {                                 // initial state for a new save
    "location": "The Conapt",
    "inventory": ["mood organ dial", "a single eroding photograph"],
    "intro": "The dust has reached the windowsill again. The mood organ waits for a setting."
  }
}
```

## Field-by-field: why each earns its place

| Field | Read each turn for | Source it comes from |
| --- | --- | --- |
| `genre` | adapting register, stat names, typical conflicts | genre-taxonomy + example genre pool |
| `voice` | prose register / sensory palette | example "prose guidelines" |
| `rules` | world physics + **epistemic lock** validation | Zork object rules + example epistemic lock |
| `lexicon` | signature vocabulary so output sounds in-world | v1 schema |
| `stats` | the QBN qualities the engine mutates via deltas | IF QBN theory |
| `dramatic_engine` | a concrete conflict to commit to (anti-mush) | Polti's 36 |
| `stakes` | soft/hard/fatal consequences + emergent endings | example failure system + IF emergent endings |
| `space` | the spatial model — how the map is organized and traversed | Zork room graph |
| `seeds` | light place/faction/archetype substrate (places carry `exits`) | Zork substrate (un-enumerated) |
| `opening` | initial save state | Zork starting room |

## Spatial model (maps) — first-class for many genres

Many genres live or die on space: a dungeon, a manor, a megacity, a star sector. The blueprint
therefore carries a `space` block (topology / scale / traversal / regions) and lets `seeds.places`
declare `exits` — a seeded **map graph**, exactly Zork's room graph but *not enumerated*. A few key
places and their connections are seeded; the rest **materializes at play** and is written into the
persistent world-state.

- `space.topology`: `interconnected-rooms`, `hub-and-spoke`, `open-wilderness`, `city-districts`,
  `star-systems`, `dungeon-levels`, … (free text; data, not an enum).
- `seeds.places[].exits`: `{to, direction, locked}` edges. The engine uses these to keep movement
  consistent — you cannot walk through a wall the map doesn't have.

## Stability & persistence — a started world stays put

The user's key requirement: **once a world is started in a session, it is stable** — the same map,
objects, NPCs, and facts persist unchanged until the user saves or starts a new world. This is an
architecture split, not a blueprint field:

- **Blueprint = immutable seed** (`world_blueprint.schema.json`). Read-only at play. It never changes
  during a session.
- **World-state = the persistent, authoritative instance** (`world_state.schema.json`). The engine
  owns it; the LLM only proposes `deltas` (turn_output) which the engine validates and applies.

How stability is guaranteed:
1. **Materialize once, reuse verbatim.** When a place is first entered, its description + exits are
   written into `world_state.map[id]`. On return, the engine feeds that stored place back into the
   prompt, so the room is the *same room*, not a fresh re-description.
2. **The engine adjudicates every change.** Nothing mutates except through a validated delta
   (PRINCIPLES.md #4); the model cannot silently rewrite the world.
3. **A fixed `seed`** in the world-state makes any randomness reproducible.
4. **The fact ledger** (`world_state.facts`) blocks contradictions of established facts (drift
   control, PRINCIPLES.md #5).
5. **Save / new world = explicit.** State is persisted to `saves/` only on the user's command; a new
   experience instantiates a fresh world-state from the blueprint. Sessions don't bleed into each
   other.

## What we deliberately do NOT put in the blueprint

- **No enumerated map / object database** (Zork drop): the world materializes at play time into state.
- **No pre-authored storylets / branch tree** (CYOA drop): endings are emergent from `stakes`.
- **No big lore ontology** (PRINCIPLES.md #2): the corpus + ledger carry content, not the blueprint.
- **No rigid multi-step reasoning templates** (PRINCIPLES.md #3): the dramatic engine offers levers,
  not a fixed procedure.

## Next step when we build distill v2 + play

1. Extend `schemas/world_blueprint.schema.json` with `genre/voice/stats/dramatic_engine/stakes`
   (keep them optional so v1 blueprints still validate).
2. Teach `distill.py` MAP/REDUCE to fill them (the model already extracts tone/rules/lexicon; add
   stat-axis and dramatic-situation extraction).
3. `simula play` reads `stats`/`stakes` to track qualities and fire emergent endings, and folds
   `voice`/`dramatic_engine` into the per-turn prompt.

See `../worlds/` for two worked examples (one Sci-Fi/dystopian, one Gothic Horror) proving the same
schema covers very different genres.
