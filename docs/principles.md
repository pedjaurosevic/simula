---
title: Principles
layout: default
nav_order: 4
---

# Principles
{: .no_toc }

These are lessons the test series earned — empirically derived from experiments on sign-type
discrimination on Gemma 12B (local, llama.cpp), not stylistic preference. They exist so that a
future builder (human or agent) does not push the project back into over-design. The full text is in
[`PRINCIPLES.md`](https://github.com/pedjaurosevic/simula/blob/main/PRINCIPLES.md).
{: .fs-5 .fw-300 }

1. **The 12B model's failure mode is over-hedging, not false affirmation.** Without a frame, the
   model rejects even valid conclusions. The most valuable part of the prompt is the *commit
   directive*.

2. **The content of the frame is often irrelevant; the effect is attention/de-hedging, not
   ontology.** The blueprint is pointers into the material + a tiny spine, not a large ontology.

3. **An elaborate procedure does not beat plain framing — and can trip you up.** No rigid reasoning
   templates in the system prompt. Structure goes on the I/O boundary, not into the model's head.

4. **State and facts live outside the model; the model proposes constrained deltas.** GBNF (local) /
   json_schema (OpenAI-compat) for deltas; the engine is the source of truth.

5. **Drift is the real front. Measure where the model actually fails.** Don't spend measurement on
   what the model already passes; target long-horizon coherence.

6. **The eval rig is the product; the skeleton/prompt is a consumable.** Every change passes a
   differential eval with a pre-registered threshold.

7. **The lessons are scale-dependent.** The 12B recipe does not necessarily work on 4B — more
   skeleton for smaller models, less for larger.

8. **Build the thinnest, grow by proof.** Start from the thinnest harness; add a piece only when
   ablation shows a delta. Tokens and rigidity are paid for; the benefit must be proven.
