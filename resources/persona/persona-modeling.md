# Persona modeling — the substrate

A persona is a `Simulacrum` whose state is an *agent* (mood, knowledge, relationship, goals) and
whose loop is conversation (PLAN.md #1). The blueprint is its distilled, immutable spine. Two
traditions feed the design: the **Big Five / OCEAN** trait model (the scientific substrate) and the
fiction-writer's **character bible** (the dramatic substrate). simula uses both — OCEAN for
*consistency*, the character bible for *drama*.

## 1. OCEAN (Big Five) — the trait substrate

Five continuous axes in [0,1] (PLAN.md #11; IPIP public-domain items, never MBTI/NERIS):

- **O**penness — curiosity, imagination, vocabulary range.
- **C**onscientiousness — order, discipline, dutifulness.
- **E**xtraversion — sociability, positive-emotion expression.
- **A**greeableness — warmth, trust, cooperation.
- **N**euroticism — anxiety, volatility, vulnerability.

Each axis has **facets** (e.g., Conscientiousness → competence, order, dutifulness, achievement,
self-discipline, deliberation). We keep facets as *optional notes* (`ocean.facet_notes`), not a full
facet schema — a spine, not a clinical instrument (PRINCIPLES.md #2).

**Why OCEAN and not MBTI:** OCEAN is continuous, empirically robust, and falsifiable; MBTI/NERIS is
trademarked and dichotomous. Continuity lets the engine *derive* tendencies instead of forcing types.

## 2. Linguistic markers — why voice is extractable

Personality leaves fingerprints in text: high Extraversion → more positive-emotion words; high
Openness → richer, more varied vocabulary; high Neuroticism → more negative-affect and
self-reference. This is what makes distilling a persona *from a corpus or chat logs* tractable: the
model reads the linguistic style and infers both the **voice** (register, cadence, tics) and rough
**OCEAN** signals. (See `distilling-from-conversations.md`.)

## 3. Character bible — the dramatic substrate

OCEAN keeps a persona *consistent*; it does not make them *dramatic*. Fiction writers add:

- **Want vs Need** — the conscious surface desire vs the deeper thing they actually need. The gap is
  the engine of an arc. → blueprint `wants` / `needs`.
- **The Wound (ghost)** — a past hurt that soured them and drives behavior. → `wound`.
- **Goals / agenda** — what they actively pursue in a scene (makes them proactive, not reactive). →
  `goals`.
- **Relationships** — stances toward others (the seed of persona-in-world NPC relations). →
  `relationships`.
- **Voice & sample lines** — how they actually talk. → `voice` (paraphrased exemplars, never long
  verbatim).

## 4. Legal & ethical hygiene

- **No MBTI/NERIS** text, type names, or brand (PLAN.md #11).
- **Real people** (personas from chat logs) require **consent**, recorded in `provenance.consent_note`
  — this is an ethics requirement, not just legal. simula ships the engine, never the logs.
- The blueprint extracts *texture and tendency*, not verbatim private content.

## Sources
- [Big Five Personality Traits (OCEAN) — Yu-kai Chou](https://yukaichou.com/behavioral-analysis/big-five-personality-ocean-traits-costa-mccrae/)
- [Personality facets recognition from text (arXiv)](https://arxiv.org/pdf/1810.02980)
- [How to Create and Use a Character Bible — ProWritingAid](https://prowritingaid.com/art/717/how-to-create-and-use-a-character-bible-for-your-novel.aspx)
- [What Is a Character Bible — Writers Write](https://www.writerswrite.co.za/what-is-a-character-bible-why-do-i-need-one/)
