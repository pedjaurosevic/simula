"""Workspace bootstrap. Cross-platform via platformdirs + pathlib (PLAN.md #6, #7).

Creates ~/simula-workspace (or platform default) with the standard layout, and never ships
any corpus: the user supplies their own materials (PLAN.md #9).
"""
from __future__ import annotations

from pathlib import Path

LAYOUT = ["materials", "blueprints", "saves", "evals"]

# Embedded so `simula init` works from an installed wheel too. Keep in sync with
# simula.toml.example at the repo root (which exists for documentation).
DEFAULT_CONFIG = """\
# simula.toml — copy created by `simula init`. Edit to taste.

[backend]
# "llamacpp" (default, local) | "openai_compat"
kind = "llamacpp"

[backend.llamacpp]
endpoint = "http://127.0.0.1:18083"
model = "gemma-4-12b-it"          # alias only; the loaded GGUF is what matters
prefer_native_grammar = true

[backend.openai_compat]
base_url = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"    # read from the environment, never stored here
model = "gpt-4o-mini"
structured_output = "json_schema" # "json_schema" | "tools" | "repair"

[embeddings]
# RAG embeddings stay local by default, decoupled from the chat model. Run a small e5 server:
#   llama-server -m multilingual-e5-small-f16.gguf --embeddings --pooling mean -ngl 0 --port 8081
kind = "llamacpp"                 # "llamacpp" (local e5) | "openai_compat" | "none" (lexical-only)
endpoint = "http://127.0.0.1:8081"
model = "multilingual-e5-small"

[generation]
temperature = 0.2
max_tokens = 800

[distill]
window_chars = 80000              # raise for big-context (cloud) backends
"""


def default_workspace() -> Path:
    """Workspace path. Honors $SIMULA_WORKSPACE, else a platform-appropriate location."""
    import os
    override = os.environ.get("SIMULA_WORKSPACE")
    if override:
        return Path(override)
    try:
        import platformdirs
        return Path(platformdirs.user_data_dir("simula")) / "workspace"
    except Exception:
        return Path.home() / "simula-workspace"


def bootstrap_workspace(path: Path | None = None) -> Path:
    """Create the workspace folder tree and a starter config if missing. Returns the path."""
    ws = path or default_workspace()
    ws.mkdir(parents=True, exist_ok=True)
    for sub in LAYOUT:
        (ws / sub).mkdir(exist_ok=True)
    cfg = ws / "simula.toml"
    if not cfg.exists():
        cfg.write_text(DEFAULT_CONFIG, encoding="utf-8")
    # library.sqlite (FTS5 + embeddings) is created lazily by `simula ingest` (see rag.py).
    return ws
