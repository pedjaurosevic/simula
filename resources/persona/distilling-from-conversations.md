# Distilling a persona from conversations / exported chats

A persona can be built from four kinds of input (`provenance.input_types`):

1. **fiction-corpus** — a character drawn from a novel/story (same map-reduce as world distill).
2. **personal-materials** — someone's essays, letters, posts.
3. **conversation** — a live or pasted dialogue.
4. **exported-chat** — chat logs exported from a messenger / assistant (WhatsApp, Telegram, Signal,
   ChatGPT export, etc.).
5. **manual** — the user fills the blueprint in by hand, to any depth.

The conversation/exported-chat path is what makes simula personal — you can build a persona of a
specific voice — and it carries the heaviest **consent** duty.

## Why chat logs are different from books

| | Book corpus | Chat logs |
| --- | --- | --- |
| Structure | continuous prose | turn-by-turn, speaker-tagged, timestamped |
| Signal | narrator + character | the person's *own* words, directly |
| Noise | low | high (typos, emoji, links, group chatter) |
| Privacy | usually published | private; **needs consent** |

So the pipeline differs in pre-processing, not in spirit:

```
1. PARSE    export format -> normalized turns [{speaker, text, ts}]
2. FILTER   keep only the TARGET speaker's turns; drop links/system msgs/other people
3. SAMPLE   if huge, sample across time (early/mid/recent) to capture range, not just recent style
4. MAP      windows of the target's turns -> partial persona notes
            (voice/register/tics, OCEAN signals, recurring values, wants, relationships)
5. REDUCE   merge -> one persona blueprint (dedup; synthesize OCEAN from accumulated signals)
6. REVIEW   show the draft to the user to confirm/edit (personas of real people are sensitive)
```

## What to extract (and what NOT to)

**Extract (texture & tendency):**
- Voice: register, cadence, signature tics/fillers/emoji habits — *paraphrased*, plus a few short
  exemplar lines.
- OCEAN signals from linguistic markers (see `persona-modeling.md`).
- Recurring values, wants, characteristic relationships/roles.

**Do NOT extract / ship:**
- Verbatim private messages at length, secrets, credentials, addresses, third parties' content.
- Anything the consenting person didn't agree to. Record the agreement in
  `provenance.consent_note`.

## Stability & the same engine

Once built, a conversation-distilled persona instantiates a `persona_state` exactly like any other
persona: mood, disposition, learned knowledge, goals — persistent and stable until save/new
(see `persona_state.schema.json`). The play loop is identical; only the blueprint differs. And
because it is a `Simulacrum`, this persona can be dropped into a world as an NPC (persona-in-world).

## Engineering note

Phase-wise this is `simula distill --kind persona`: reuse `distill.py`'s map-reduce, add a chat-log
parser + speaker filter, and target the persona schema instead of the world schema. The REVIEW step
(human confirmation) is mandatory for `exported-chat`/`conversation` provenance.
