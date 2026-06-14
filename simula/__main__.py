"""Minimal CLI entry point for `simula`.

Currently (Phase 0) it only exposes `version`, `init` (workspace bootstrap), and `where`. The
engine is still a skeleton; see PLAN.md for the implementation phases.
"""
from __future__ import annotations

import argparse

from . import __version__
from .workspace import bootstrap_workspace, default_workspace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="simula",
        description="A local-first engine for generating and inhabiting worlds and personas.",
    )
    parser.add_argument("--version", action="version", version=f"simula {__version__}")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="Create the workspace folder tree.")
    p_init.add_argument("path", nargs="?", default=None, help="Path (default: platform default).")

    sub.add_parser("where", help="Print the default workspace path.")

    args = parser.parse_args(argv)

    if args.command == "init":
        ws = bootstrap_workspace(args.path)
        print(f"Workspace ready: {ws}")
        return 0
    if args.command == "where":
        print(default_workspace())
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
