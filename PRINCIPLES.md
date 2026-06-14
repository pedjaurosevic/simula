# PRINCIPLES — lessons the test series earned

This file exists so that a future builder (human or agent) does not push the project back into
over-design. Everything below is *empirically derived* from a series of experiments on sign-type
discrimination on Gemma 12B (local, llama.cpp), not a stylistic preference. The details are in the
project history; here are the engineering consequences.

## 1. The 12B model's failure mode is OVER-HEDGING, not false affirmation.
Without a frame, the model rejects even valid conclusions. Replicated across three versions
(license-acc bare: 0.00 → 0.14 → 0.44; always the lowest). Consequence: the most valuable part of
the prompt is the *commit directive* ("commit to the concrete, don't hedge without reason"). In
narration this translates to: a concrete, anchored detail instead of generic mush.

## 2. The content of the frame is often irrelevant; the effect is "attention/de-hedging," not ontology.
B' = B = 1.00: empty hermeneutic jargon licenses just as well as naming the exact concepts. Two
full conditions maxed out every item. Consequence: **ontology/persona is decoration until ablation
proves otherwise.** Blueprint = pointers into the material + a tiny spine, not a large ontology.

## 3. An elaborate procedure does not beat plain framing — and can trip you up.
Operational procedure C did not outperform priming, and in one case (dim_masina) its own rigid step
led it into an error that a freer model avoided. Consequence: no rigid reasoning templates in the
system prompt. Structure goes on the I/O boundary, not into the model's head.

## 4. State and facts live OUTSIDE the model; the model proposes constrained deltas.
The only structure that worked everywhere and never hurt was forced, parsable output. Consequence:
GBNF (local) / json_schema (OpenAI-compat) for deltas; the engine is the source of truth.

## 5. Drift is the real front. Measure where the model actually fails.
Ceiling-saturated metrics teach nothing (block-acc was 1.00 everywhere → a dead signal).
Consequence: don't spend measurement on what the model already passes; target long-horizon
coherence (narrative/factual drift), not the beauty of a single turn.

## 6. The eval rig is the product; the skeleton/prompt is a consumable.
Every "richer is better" intuition fell as soon as a real control was added — three times.
Consequence: on 12B you don't trust prompt intuition; every change passes a differential eval
(condition A/B + ablation + a pre-registered threshold). It is a permanent part of the system, not a
one-off experiment.

## 7. The lessons are scale-dependent.
On 4B, empty verbosity HURTS, and naming the types helps (the opposite of 12B). Consequence: if
simula falls back to a smaller model (fallback machines), the prompt strategy is NOT the same — more
skeleton for the smaller, less for the larger. Don't assume the 12B recipe works on 4B.

## 8. Build the thinnest, grow by proof.
The strongest move of the whole series would be: start from the thinnest harness, add piece by piece
only when ablation shows a delta. This is the inverse of plans that score high on *machinery
richness* they cannot show actually works. Tokens and rigidity are paid for; the benefit must be
proven.
