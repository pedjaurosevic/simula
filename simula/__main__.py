"""Minimal CLI entry point for `simula`.

Phase 0 exposes `init`/`where`/`version` and `distill` (corpus -> world blueprint). The play loop
arrives next; see PLAN.md for the phases.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .workspace import bootstrap_workspace, default_workspace


def _cmd_distill(args) -> int:
    # Imported lazily so `init`/`where` work even before optional deps are present.
    from .config import load_config, make_backend
    from .distill import DEFAULT_WINDOW_CHARS, distill_world

    ws = default_workspace()
    materials = [Path(m) for m in args.materials] if args.materials else [ws / "materials"]
    try:
        cfg = load_config(ws)
        backend = make_backend(cfg)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    window = args.window or cfg.get("distill", {}).get("window_chars", DEFAULT_WINDOW_CHARS)

    def progress(i, total):
        print(f"  distilling window {i}/{total}...", file=sys.stderr)

    try:
        blueprint = distill_world(
            materials, backend,
            world_id=args.id, title=args.title or args.id,
            window_chars=window, source_note=args.source_note or "", progress=progress,
        )
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    out = Path(args.out) if args.out else (ws / "blueprints" / f"{args.id}.world.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(blueprint, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"World blueprint written: {out}")
    return 0


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

    p_distill = sub.add_parser("distill", help="Distill a corpus into a world blueprint.")
    p_distill.add_argument("materials", nargs="*", help="Files/dirs (default: workspace/materials).")
    p_distill.add_argument("--id", required=True, help="World id (also the output filename).")
    p_distill.add_argument("--title", default=None, help="World title (default: the id).")
    p_distill.add_argument("--out", default=None, help="Output path (default: blueprints/<id>.world.json).")
    p_distill.add_argument("--window", type=int, default=None, help="Map window size in chars.")
    p_distill.add_argument("--source-note", default=None, help="Provenance note (no source text shipped).")

    args = parser.parse_args(argv)

    if args.command == "init":
        ws = bootstrap_workspace(args.path)
        print(f"Workspace ready: {ws}")
        return 0
    if args.command == "where":
        print(default_workspace())
        return 0
    if args.command == "distill":
        return _cmd_distill(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
