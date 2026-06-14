---
title: Getting started
layout: default
nav_order: 2
---

# Getting started
{: .no_toc }

1. TOC
{:toc}

---

## Install

```bash
pip install simula
```

simula targets Python 3.10+ and runs on Linux, macOS, and Windows.

## The CLI

Phase 0 exposes three commands:

```bash
simula --version     # print the version
simula init          # create the workspace folder tree
simula where         # print the default workspace path
```

`simula init` accepts an optional path; without it, the workspace is created at a
platform-appropriate location (via `platformdirs`), falling back to `~/simula-workspace`.

## The workspace

```
simula-workspace/
  simula.toml             # config: backend, endpoint, model, key, experience mode
  materials/              # your books/texts (yours, local)
  library.sqlite          # RAG (sqlite-vec + FTS5) + state + memory + ledger
  blueprints/             # distilled world/persona blueprints (JSON)
  saves/                  # experience snapshots / transcripts
  evals/                  # eval rig results
```

Everything is inspectable and portable. **No corpus is shipped** — you bring your own materials.

## Configuration

Copy `simula.toml.example` into your workspace as `simula.toml` and edit it. The key choices:

- **Backend:** `llamacpp` (default, local) or `openai_compat` (any OpenAI-compatible endpoint).
- **Embeddings:** local `e5-small` by default, to avoid coupling — even in `openai_compat` mode.
- **Experience mode:** `world` or `persona`, plus the blueprint to load.
- **RAG:** `top_k` and hybrid (sqlite-vec dense + FTS5 lexical).

API keys are read from the environment, never stored in config.

See [Configuration](configuration) for the full annotated example.

## Running a local backend

By default simula talks to a local `llama.cpp` server over HTTP (e.g. `http://127.0.0.1:18083`).
The native `/completion` endpoint is preferred because it accepts a GBNF `grammar` for
hard-constrained output. Point `simula.toml` at your server and you're set.
