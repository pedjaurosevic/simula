"""Load simula.toml from the workspace and construct a backend from it."""
from __future__ import annotations

from pathlib import Path

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

from .backends import Backend, LlamaCppBackend, OpenAICompatBackend, from_config
from .workspace import default_workspace


def load_config(workspace: Path | None = None) -> dict:
    """Parse simula.toml from the workspace. Raises FileNotFoundError if it is missing."""
    ws = workspace or default_workspace()
    cfg_path = ws / "simula.toml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"no config at {cfg_path} — run `simula init` first")
    return tomllib.loads(cfg_path.read_text(encoding="utf-8"))


def make_backend(cfg: dict | None = None, *, workspace: Path | None = None) -> Backend:
    """Construct the configured backend. Loads config from the workspace if not given."""
    return from_config(cfg if cfg is not None else load_config(workspace))


def make_embedder(cfg: dict | None = None, *, workspace: Path | None = None) -> Backend | None:
    """Construct the embedding backend from [embeddings] (decoupled from chat; PLAN.md #5).

    Returns None when embeddings are disabled — RAG then runs lexical-only. Keeping embeddings on
    their own small e5 server avoids coupling the RAG index to the chat model's endpoint.
    """
    cfg = cfg if cfg is not None else load_config(workspace)
    emb = cfg.get("embeddings") or {}
    kind = emb.get("kind", "llamacpp")
    if kind in ("none", "off"):
        return None
    if kind in ("llamacpp", "local_e5"):
        endpoint = emb.get("endpoint", "http://127.0.0.1:8081")
        return LlamaCppBackend(endpoint, emb.get("model", "multilingual-e5-small"))
    if kind == "openai_compat":
        import os
        return OpenAICompatBackend(emb["base_url"], os.environ[emb["api_key_env"]], emb["model"])
    return None
