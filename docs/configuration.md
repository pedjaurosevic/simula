---
title: Configuration
layout: default
nav_order: 5
---

# Configuration

simula is configured through a `simula.toml` file in your workspace. Copy
[`simula.toml.example`](https://github.com/pedjaurosevic/simula/blob/main/simula.toml.example) into
your workspace as `simula.toml` and edit it.

```toml
[backend]
# "llamacpp" (default, local) | "openai_compat"
kind = "llamacpp"

[backend.llamacpp]
endpoint = "http://127.0.0.1:18083"
# Native /completion is preferred because it accepts a GBNF `grammar` for hard-constrained output.
model = "gemma-4-12b-it"          # alias only; the loaded GGUF is what matters
prefer_native_grammar = true

[backend.openai_compat]
# Used when backend.kind = "openai_compat". Works with OpenAI or any compatible server.
base_url = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"    # read from the environment, never stored here
model = "gpt-4o-mini"
structured_output = "json_schema" # "json_schema" | "tools" | "repair"

[embeddings]
# Embeddings stay local by default to avoid coupling, even in openai_compat mode.
kind = "local_e5"                 # intfloat/multilingual-e5-small

[generation]
temperature = 0.2                 # low for consistency; tune via the eval rig
max_tokens = 800

[experience]
mode = "world"                    # "world" | "persona"
blueprint = "blueprints/kipple.world.json"

[rag]
top_k = 6
hybrid = true                     # sqlite-vec (dense) + FTS5 (lexical)

[workspace]
# Leave empty to use the platform default (~/simula-workspace via platformdirs).
path = ""
```

## Notes

- **API keys are never stored in config.** The `openai_compat` backend reads the key from the
  environment variable named in `api_key_env`.
- **Embeddings stay local by default** so you are not coupled to a remote embedding provider, even
  when generation runs against a remote endpoint.
- **`temperature` is low by default** (0.2) for consistency; tune it through the eval rig rather than
  by intuition.
