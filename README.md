# simula

**A local-first engine for generating and inhabiting worlds and personas from your own materials.**

One engine, two blueprint types (`world` | `persona`), one unified entity model (`Simulacrum`).
Local-first (llama.cpp + GBNF for hard-constrained output), but always able to run against any
OpenAI-compatible endpoint.

> **Status:** early alpha (Phase 0). The core is still a skeleton — see [`PLAN.md`](PLAN.md) for the
> implementation phases and [`PRINCIPLES.md`](PRINCIPLES.md) for the empirically derived lessons
> that drive the design.

## Install

```bash
pip install simula
```

## Quick start

```bash
simula --version
simula init          # create a workspace (materials/ blueprints/ saves/ evals/)
simula where         # print the workspace path
```

The workspace lives at a platform-appropriate path (via `platformdirs`), falling back to
`~/simula-workspace`. **No corpus is ever shipped** — you bring your own materials.

## Configuration

Copy `simula.toml.example` into your workspace as `simula.toml` and edit the backend (llama.cpp or
OpenAI-compatible), embeddings, RAG, and experience mode (`world` | `persona`).

## Design in brief

- **Constrained output is the reliability backbone:** GBNF on llama.cpp's `/completion`,
  `json_schema` on OpenAI-compatible backends, with a parse-and-repair fallback.
- **Minimal prompt:** a commit directive + the blueprint spine + pointers into your materials (RAG),
  not a large ontology.
- **Local-first and private:** embeddings and generation can stay on your own machine.
- **The engine holds the truth:** the LLM only *proposes* structured changes; the engine validates
  and applies them against authoritative state.

## Documentation

Full docs: **https://pedjaurosevic.github.io/simula/**

## License

MIT — see [LICENSE](LICENSE).
