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
    from .distill import DEFAULT_WINDOW_CHARS, distill_persona, distill_world

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
        if args.kind == "persona":
            input_types = [t.strip() for t in (args.input_types or "").split(",") if t.strip()] or None
            blueprint = distill_persona(
                materials, backend,
                persona_id=args.id, name=args.name or args.id, speaker=args.speaker,
                input_types=input_types, window_chars=window,
                source_note=args.source_note or "", progress=progress,
            )
            suffix = "persona"
        else:
            blueprint = distill_world(
                materials, backend,
                world_id=args.id, title=args.title or args.id,
                window_chars=window, source_note=args.source_note or "", progress=progress,
            )
            suffix = "world"
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    out = Path(args.out) if args.out else (ws / "blueprints" / f"{args.id}.{suffix}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(blueprint, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{suffix.capitalize()} blueprint written: {out}")
    if args.kind == "persona" and args.speaker:
        print("note: persona built from a specific speaker — review the draft before use (consent/accuracy).",
              file=sys.stderr)
    return 0


def _cmd_play(args) -> int:
    from .config import load_config, make_backend
    from .play import (
        instantiate_persona, instantiate_world, load_state,
        run_persona_session, run_session,
    )

    ws = default_workspace()
    is_persona = bool(args.persona)
    if args.blueprint:
        bp_path = Path(args.blueprint)
    elif is_persona:
        bp_path = ws / "blueprints" / f"{args.persona}.persona.json"
    else:
        bp_path = ws / "blueprints" / f"{args.world}.world.json"
    if not bp_path.exists():
        print(f"error: no blueprint at {bp_path} — run `simula distill` first", file=sys.stderr)
        return 1
    blueprint = json.loads(bp_path.read_text(encoding="utf-8"))

    try:
        backend = make_backend(load_config(ws))
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    kind = "persona" if is_persona else "world"
    save_path = Path(args.save) if args.save else (ws / "saves" / f"{blueprint['id']}.{kind}.save.json")
    instantiate = instantiate_persona if is_persona else instantiate_world
    if save_path.exists() and not args.new:
        state = load_state(save_path)
        print(f"[resuming {save_path} at turn {state.get('turn', 0)}]", file=sys.stderr)
    else:
        state = instantiate(blueprint)

    # Ground every turn on the materials, if an index exists (run `simula ingest` first).
    from .rag import library_path, make_retriever
    retrieve = make_retriever(ws, backend) if library_path(ws).exists() else None
    if retrieve is None:
        print("[no RAG index — run `simula ingest` to ground on your materials]", file=sys.stderr)

    if is_persona:
        print("Talk to the persona. Commands: /mood /save /quit", file=sys.stderr)
        run_persona_session(blueprint, backend, save_path=save_path, state=state, retrieve=retrieve)
    else:
        print("Type your actions. Commands: /look /stats /save /quit", file=sys.stderr)
        run_session(blueprint, backend, save_path=save_path, state=state, retrieve=retrieve)
    return 0


def _cmd_ingest(args) -> int:
    from .config import load_config, make_backend
    from .rag import ingest

    ws = default_workspace()
    materials = Path(args.materials) if args.materials else None
    try:
        backend = make_backend(load_config(ws))
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    def progress(done, total):
        print(f"  indexing {done}/{total} chunks...", file=sys.stderr)

    stats = ingest(ws, backend, materials_dir=materials, progress=progress)
    note = "with embeddings" if stats["embedded"] else "lexical-only (no embedding server reachable)"
    print(f"Indexed {stats['chunks']} chunks from {stats['files']} file(s), {note}.")
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

    p_distill = sub.add_parser("distill", help="Distill a corpus into a world or persona blueprint.")
    p_distill.add_argument("materials", nargs="*", help="Files/dirs (default: workspace/materials).")
    p_distill.add_argument("--kind", choices=["world", "persona"], default="world", help="What to distill.")
    p_distill.add_argument("--id", required=True, help="Blueprint id (also the output filename).")
    p_distill.add_argument("--title", default=None, help="World title (world kind; default: the id).")
    p_distill.add_argument("--name", default=None, help="Persona name (persona kind; default: the id).")
    p_distill.add_argument("--speaker", default=None, help="Persona kind: keep only this speaker's chat lines.")
    p_distill.add_argument("--input-types", default=None, help="Persona kind: comma list, e.g. 'exported-chat,manual'.")
    p_distill.add_argument("--out", default=None, help="Output path (default: blueprints/<id>.<kind>.json).")
    p_distill.add_argument("--window", type=int, default=None, help="Map window size in chars.")
    p_distill.add_argument("--source-note", default=None, help="Provenance note (no source text shipped).")

    p_ingest = sub.add_parser("ingest", help="Index the workspace materials for RAG grounding.")
    p_ingest.add_argument("materials", nargs="?", default=None, help="Dir to index (default: workspace/materials).")

    p_play = sub.add_parser("play", help="Play a world, or talk to a persona (gameplay runtime).")
    p_play.add_argument("--world", help="World id (loads blueprints/<id>.world.json).")
    p_play.add_argument("--persona", help="Persona id (loads blueprints/<id>.persona.json).")
    p_play.add_argument("--blueprint", default=None, help="Explicit blueprint path (overrides --world/--persona).")
    p_play.add_argument("--save", default=None, help="Save path (default: saves/<id>.<kind>.save.json).")
    p_play.add_argument("--new", action="store_true", help="Start fresh, ignoring any existing save.")

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
    if args.command == "ingest":
        return _cmd_ingest(args)
    if args.command == "play":
        if not args.world and not args.persona and not args.blueprint:
            print("error: provide --world <id>, --persona <id>, or --blueprint <path>", file=sys.stderr)
            return 1
        return _cmd_play(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
