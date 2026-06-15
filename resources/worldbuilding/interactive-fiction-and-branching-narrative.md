# Interactive fiction & multiple-ending narrative structures

Stories with "more than one ending" are not one technique but a family. Choosing the right structure
decides what **state** the engine must track. This is the bridge between literature/IF theory and our
`state` + `blueprint` design. (Reference: Emily Short, "Beyond Branching".)

## The structures, and what each forces the engine to store

| Structure | How it works | What the engine must track | Cost |
| --- | --- | --- | --- |
| **Branching / CYOA (time cave)** | Every choice forks into distinct content; a tree of endings | Current node + choice history | Combinatorial explosion — content grows exponentially |
| **Gauntlet** | One main spine; branches are short detours that die or merge back | Position on spine + a few flags | Cheap, but low replay variety |
| **Quality-Based Narrative (QBN)** | Content = **storylets** unlocked by numeric **qualities** (skills, items, relationships, progress) | A bag of numeric/boolean qualities; storylet availability conditions | Modular, recombinant; needs bookkeeping discipline |
| **Salience-based** | A pool of tagged content; the best match for current world state plays | World-state flags + per-content match conditions + scoring | Great for ambient variety; weak for plot-critical beats |
| **Waypoint** | Story advances through topics; content lives on transitions between them | Topic graph + current topic + used transitions | Powerful for conversation; complex to implement |

## What this means for simula

We are **not** authoring a tree. Our model is closest to **QBN + salience over an authoritative
state**, with the LLM (not a quality table) deciding what is salient:

1. **State is the bag of qualities.** Inventory, location, flags, NPC moods, relationship scores,
   plot progress — exactly the QBN "qualities." The engine owns them (turn_output deltas mutate them).
2. **The blueprint supplies the salience pool.** `seeds` (places/factions/archetypes) +
   `dramatic_engine` (Polti situations) + `lexicon` are the tagged content the LLM draws on when it
   judges what fits the moment. No pre-authored storylets — the LLM generates them, grounded in the
   blueprint and the fact ledger.
3. **Endings are emergent, not enumerated.** There is no fixed ending list. An ending occurs when
   state crosses a condition the blueprint defines in `stakes`/`win_loss` (e.g., HP→0 = fatal,
   goal achieved = resolution). This gives "infinite endings" without combinatorial authoring.
4. **Multiple-ending discipline = the fact ledger.** What keeps branching coherent (no contradicting
   an established fact across a long, forking session) is the ledger + RAG, not a branch tree
   (PRINCIPLES.md #5: drift is the real front).

### Practical takeaways for the blueprint
- The blueprint must declare the **qualities/stats** the world cares about (genre-styled HP/XP, plus
  named relationship/progress axes) so the engine knows what to track.
- The blueprint must declare **end conditions** (`stakes`) so emergent endings can fire.
- The blueprint must declare a **dramatic engine** (which Polti situations are in play) so the LLM
  has conflict to be salient *toward*, instead of drifting into generic mush (PRINCIPLES.md #1).

## Sources
- [Beyond Branching: Quality-Based, Salience-Based, and Waypoint Structures — Emily Short](https://emshort.blog/2016/04/12/beyond-branching-quality-based-and-salience-based-narrative-structures/)
- [Storylets: You Want Them — Emily Short](https://emshort.blog/2019/11/29/storylets-you-want-them/)
- [Sketching a Map of the Storylets Design Space (Springer)](https://link.springer.com/chapter/10.1007/978-3-030-04028-4_14)
