"""Load simula.toml from the workspace and construct a backend from it."""
from __future__ import annotations

from pathlib import Path

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

from .backends import Backend, from_config
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
