---
title: Home
layout: default
nav_order: 1
---

# simula
{: .fs-9 }

A local-first engine for generating and inhabiting worlds and personas from your own materials.
{: .fs-6 .fw-300 }

[Get started](getting-started){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[View on GitHub](https://github.com/pedjaurosevic/simula){: .btn .fs-5 .mb-4 .mb-md-0 }

---

## What is simula?

**simula** is a thin harness that turns *your own* texts into something you can walk through and
talk to. It:

1. takes your materials (books, texts),
2. distills a **blueprint** from them — the spine of a world or a persona (mostly pointers into the
   material plus a tiny summary), and
3. runs an interactive, stateful, memory-bearing experience in which the LLM **proposes** structured
   changes while the engine **holds the truth**.

One engine, two blueprint types (`world` | `persona`), one unified entity model — the
`Simulacrum`. The name carries a question, not a claim: *is a fashioned mind or world real?* (PKD)

## Why it's different

- **Local-first.** Runs against a local `llama.cpp` server by default, with hard-constrained output
  via GBNF grammars. Your materials and your generation can stay on your machine.
- **Always portable.** The same engine runs against any OpenAI-compatible endpoint with
  `json_schema` constrained output.
- **The engine holds the truth.** The model only *proposes* deltas; the engine validates and applies
  them against authoritative state. This is what keeps long sessions coherent.
- **No corpus shipped, ever.** You bring your own books; simula extracts *texture*, not text.

## Status

Early alpha (Phase 0). The core is a skeleton; the packaging, CLI, and design are in place. See the
[Design](design) and [Build phases](design#build-phases) pages for the road ahead, and
[Principles](principles) for the empirically derived lessons that drive every decision.

## Install

```bash
pip install simula
```

```bash
simula --version
simula init     # create a workspace
simula where    # print the workspace path
```
