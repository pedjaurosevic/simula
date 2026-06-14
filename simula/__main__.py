"""Minimalni CLI ulaz za `simula`.

Trenutno (Phase 0) izlaže samo `version` i `init` (bootstrap workspace-a). Engine je još uvek
skelet; vidi PLAN.md za faze implementacije.
"""
from __future__ import annotations

import argparse

from . import __version__
from .workspace import bootstrap_workspace, default_workspace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="simula",
        description="Lokalno-prvi pogon za sazdavanje i naseljavanje svetova i persona.",
    )
    parser.add_argument("--version", action="version", version=f"simula {__version__}")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="Napravi workspace folder tree.")
    p_init.add_argument("path", nargs="?", default=None, help="Putanja (podrazumevano: platform default).")

    sub.add_parser("where", help="Ispiši podrazumevanu putanju workspace-a.")

    args = parser.parse_args(argv)

    if args.command == "init":
        ws = bootstrap_workspace(args.path)
        print(f"Workspace spreman: {ws}")
        return 0
    if args.command == "where":
        print(default_workspace())
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
