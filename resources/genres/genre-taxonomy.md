# Genre taxonomy — making the blueprint genre-agnostic

The blueprint must express *any* genre with the same fields. Genre is not a special case in the
schema; it is **data**: a label plus a bundle of conventions (texture, stat vocabulary, typical
dramatic situations, failure flavor). The engine reads that bundle and adapts. This is how one
universal blueprint covers Fantasy, Cyberpunk, Gothic Horror, Western, etc.

## Genre pool (from the example + common IF practice)

Fantasy (High Magic / Dark) · Urban Fantasy · Cyberpunk · Steampunk · Sci-Fi (Space Opera / Hard) ·
Time Travel · Post-Apocalyptic · Dystopian · Alternate History · Historical Drama · Historical War ·
Samurai Japan · Mythic (Greek / Norse) · Arthurian Legend · Fairy Tale (Reversed) · Gothic Horror ·
Folk Horror · Haunted House · Paranormal Romance · Espionage Thriller · Political Thriller ·
Military Noir · Detective Noir · Psychological Thriller · Western · Contemporary Crime ·
Magical Realism · Surrealist Absurd · Coming-of-Age · Prison Escape · Underworld Crime ·
Biopunk Genetics · AI Consciousness / Transhumanism.

The pool is open — it lives in data, not code, so new genres need no engine change.

## Per-genre conventions the blueprint encodes

Each world's blueprint instantiates these from its genre (and from the distilled corpus, which
refines them with the author's specific texture):

### 1. Stat vocabulary (renamable HP/XP + axes)
The two core gauges (resilience / progress) get genre-styled names; extra axes are added as needed.

| Genre | Resilience (HP) | Progress (XP) | Common extra axes |
| --- | --- | --- | --- |
| Fantasy | Vitality | Lore | Mana, Renown |
| Cyberpunk | Neural Integrity | Ghost Signal | Cred, Heat |
| Detective Noir | Stamina | Notoriety | Leads, Trust |
| Gothic Horror | Sanity | Influence | Dread, Faith |
| Sci-Fi | Hull Integrity | Reputation | Fuel, Oxygen |
| Western | Grit | Legend | Bounty, Honor |
| Historical Drama | Resolve | Legacy | Standing, Coin |
| Dystopian | Compliance | Awareness | Suspicion, Network |
| Post-Apocalyptic | Health | Survival | Supplies, Radiation |

### 2. Tone / prose register
Sensory palette, cadence, and figurative density (the example's "prose guidelines"). E.g., Noir =
terse, rain-slick, first-person fatalism; Mythic = elevated, formulaic epithets; Surrealist = dream
logic, unstable causality.

### 3. Typical Polti situations
A genre leans on certain conflicts: Western → *Crime Pursued by Vengeance*, *Ambition*; Gothic
Horror → *Madness*, *Discovery of Dishonor*, *Remorse*; Espionage → *The Enigma*, *Pursuit*,
*Mistaken Jealousy*. See `dramatic-situations-polti.md`.

### 4. Failure flavor (soft / hard / fatal)
Same three-tier consequence model, re-skinned: Cyberpunk hard-failure = cyberware glitch + Heat
spike; Gothic hard-failure = a Sanity break; Western fatal = a duel lost.

### 5. Epistemic lock
Characters know only what their epoch/genre allows (the example's "epistemic lock"). This is a hard
`rules` constraint the engine enforces against anachronism drift.

## Design consequence

None of the above is a new schema branch. It is all values inside the universal blueprint's
`genre`, `voice`, `stats`, `dramatic_engine`, `stakes`, and `rules` fields — see
`../worldbuilding/blueprint-design-principles.md`.
