"""Workspace bootstrap. Cross-platform via platformdirs + pathlib (PLAN.md #6, #7).

Creates ~/simula-workspace (or platform default) with the standard layout, and never ships
any corpus: the user supplies their own materials (PLAN.md #9).

SKELETON.
"""
from __future__ import annotations

from pathlib import Path

LAYOUT = ["materials", "blueprints", "saves", "evals"]


def default_workspace() -> Path:
    """Platform-appropriate workspace path. Falls back to ~/simula-workspace."""
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
        # Phase 0: copy simula.toml.example into place.
        pass
    # Phase 1: initialize library.sqlite (sqlite-vec + FTS5 tables).
    return ws
