# Zork as a world-model case study

Zork (MIT, 1977–79; Infocom) is the canonical "the engine holds the truth" interactive-fiction
system, and it is the cleanest historical proof of simula's core thesis (PLAN.md #1, #8): a small,
authoritative **state engine** plus a thin language layer beats trying to keep the whole world in
one head.

## How Zork actually worked

- **Everything is an object.** ~400 objects total — rooms (White House, forest), things (mailbox,
  lamp, sword), and the player. Each object has properties: names, synonyms, adjectives, a
  description, contents, flags (open/closed, lit, takeable), and actions.
- **Rooms form a graph.** Locations are nodes; exits (N/S/E/W/up/down) are edges. Movement is just
  traversing the graph; the engine, not prose, knows where you are.
- **The parser is thin and pattern-based.** ~900 words, ~70 verbs. Patterns like
  `STAB <obj> WITH <obj>` match input against verb tables + object synonym lists. The parser
  *proposes* an action; the engine validates it against world state (is the knife here? is the door
  open?) and either applies it or refuses with a reason.
- **State is the source of truth.** Inventory, room contents, flags, and a turn counter live in the
  engine. The narration is a *view* of that state, never the state itself.
- **Portability via a VM.** ZIL (a LISP-like DSL) compiled to the Z-machine bytecode, so one game
  ran everywhere. (Relevant to us only as a principle: separate the *world definition* from the
  *runtime*.)

## What we take, and what we deliberately drop

| Zork | simula |
| --- | --- |
| Engine owns state; language layer only proposes | **Keep exactly.** The LLM emits constrained `deltas`; the engine validates/applies (turn_output.schema.json). |
| Objects with properties, flags, contents | **Keep** as the `state` shape (places, items, NPCs, flags). |
| Room graph for movement | **Keep** as `seeds.places` + state location; but soft — the LLM can narrate transitions the graph implies. |
| Hand-authored 400 objects | **Drop.** We *distill* the spine from the user's corpus; the world grows at play time, it is not pre-enumerated. |
| Rigid verb table parser | **Drop.** Natural language in; the LLM maps intent to deltas. This is the whole point of using an LLM instead of a parser. |
| Fixed authored map | **Drop.** A corpus-derived world is generative, not a fixed maze (PLAN.md #0: "not a Zork fork"). |

**The lesson for our blueprint:** the blueprint must seed a *Zork-like object/room substrate*
(places, items, factions as light seeds) **without** pre-enumerating it. The engine then materializes
new objects/rooms on demand and records them in state, exactly as Zork recorded its fixed ones.

## Sources
- [Zork: The Great Inner Workings (Medium)](https://medium.com/swlh/zork-the-great-inner-workings-b68012952bdc)
- [Zork and the Z-Machine (Hackaday)](https://hackaday.com/2019/05/22/zork-and-the-z-machine-bringing-the-mainframe-to-8-bit-home-computers/)
- [Zork (Britannica)](https://www.britannica.com/topic/Zork-1688286)
- [The Z-Machine Standards Document](https://inform-fiction.org/zmachine/standards/z1point1/appe.html)
