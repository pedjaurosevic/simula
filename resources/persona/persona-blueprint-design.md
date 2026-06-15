# The persona blueprint — design principles (v2)

The keystone for the persona module, mirroring the world blueprint keystone. A persona blueprint is
the immutable spine the LLM references every turn of a conversation (and every turn an NPC acts in a
world). Same discipline as the world blueprint: **structural levers, not an ontology** (PRINCIPLES.md
#2). Every field is read by the loop, or it doesn't belong.

## The same tension, the same resolution

The persona must feel like a *specific* person across a long session, in any genre, whether built
from a novel or from chat logs. The temptation is a giant character dossier. We resist it: OCEAN +
voice + a want/need/wound spine + a few relationships is enough to stay consistent and dramatic; the
corpus/ledger carries the rest.

## What the engine references each turn

1. **How do they talk** → `voice` (the single highest-value field — like the world's commit directive).
2. **Who are they, deep down** → `ocean`, `values`, `archetype`.
3. **What do they want / need / fear** → `wants`, `needs`, `wound`, `goals` (drama + proactivity).
4. **What do they know / not know** → `knowledge` (incl. epistemic lock).
5. **How do they feel about *you*** → `relationships` + the mutable `persona_state.disposition`.
6. **What would they never do** → `boundaries`.

## The v2 persona blueprint (shape)

```jsonc
{
  "id": "elias-thorne",
  "name": "Elias Thorne",
  "provenance": { "input_types": ["fiction-corpus"] },
  "ocean": { "openness": 0.7, "conscientiousness": 0.8, "extraversion": 0.3,
             "agreeableness": 0.35, "neuroticism": 0.6,
             "facet_notes": ["high deliberation", "low gregariousness", "brooding"] },
  "archetype": { "name": "The Weary Lamplighter",
                 "summary": "A man who keeps order in a city that has stopped deserving it." },
  "voice": { "summary": "Terse, dry, fond of a bleak metaphor he immediately undercuts.",
             "register": "clipped noir first-person",
             "speech_tics": ["answers a question with a question", "trails off before the worst part"],
             "exemplar_refs": [] },
  "values": ["a private code of fairness", "loyalty to the few he trusts"],
  "wants": ["close the case clean"],
  "needs": ["to forgive himself for the one he didn't"],
  "wound": "A partner died on a call Elias waved off as nothing.",
  "goals": ["find who is really paying the witnesses"],
  "knowledge": { "domains": ["city geography", "police procedure", "who owes whom"],
                 "epistemic_note": "1940s city; no modern technology or forensics." },
  "relationships": [{ "name": "Vera", "relation": "former partner's widow", "stance": "guilt-ridden, protective" }],
  "quirks": ["cleans his glasses when lying"],
  "boundaries": ["never hits a woman", "won't plant evidence even on the guilty"],
  "history": "Twenty years on the job; one grave he visits and never mentions.",
  "opening": { "mood": "tired but alert", "disposition": "guarded", "intro": "He doesn't look up from the file when you come in." }
}
```

## Field-by-field justification

| Field | Read each turn for | Source |
| --- | --- | --- |
| `voice` | sounding like them (top lever) | linguistic markers + character bible |
| `ocean` (+facet_notes) | consistent tendencies | Big Five / IPIP |
| `archetype` | a quick generative handle | our own bucketing (no MBTI) |
| `values` | what they defend | character bible |
| `wants` / `needs` | the arc engine (surface vs depth) | character bible want/need |
| `wound` | why they behave as they do | character bible ghost |
| `goals` | proactivity / agenda | drama |
| `knowledge` | what they can speak to + epistemic lock | epistemic discipline |
| `relationships` | stance toward others → persona-in-world | character bible + PLAN.md #4 |
| `boundaries` | hard "would never" constraints | consistency / engine validation |
| `provenance` | extraction mode + consent posture | persona-from-conversations |
| `opening` | seeds the persona_state | mirrors world `opening` |

## Persona-in-world (the payoff)

Because a persona is a `Simulacrum`, dropping one into a world is composition, not new machinery
(PLAN.md #4). The world materializes an `entity` whose `persona_id` points at this blueprint; the
world loop delegates that NPC's turn to the persona loop, which reads this blueprint + the NPC's
`persona_state` (with `embedded` set) and returns a reaction the world applies as a delta. Ships
last, but the schemas already support it today.

## What we deliberately leave out

- No full clinical facet battery (notes only).
- No exhaustive biography (a `history` *seed*, not a wiki).
- No fixed dialogue trees (the LLM generates dialogue grounded in this spine + ledger).

## Next step when we build distill-persona

1. `simula distill --kind persona` reusing `distill.py` map-reduce, targeting this schema.
2. A chat-log parser + speaker filter for `exported-chat`/`conversation` provenance, with a mandatory
   human REVIEW step.
3. `simula play --persona <id>` instantiating `persona_state` for a conversation.

See `../personas/` for two worked examples (one fiction-corpus, one conversation-distilled).
