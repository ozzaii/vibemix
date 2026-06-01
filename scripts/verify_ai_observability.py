#!/usr/bin/env python3
"""Verify persisted ai_message rows and artifacts after a live run.

This is the release-proof companion for the AI-message observability work. It
does not trigger the co-host; it inspects what a rebuilt/relaunched app already
wrote to disk.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        with path.open(encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    row = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    errors.append(f"{path}:{lineno}: invalid JSON: {exc}")
                    continue
                if isinstance(row, dict):
                    rows.append(row)
                else:
                    errors.append(f"{path}:{lineno}: JSON line is not an object")
    except OSError as exc:
        errors.append(f"{path}: read failed: {exc}")
    return rows, errors


def _resolve_artifact_path(base: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    return path if path.is_absolute() else base / path


def _artifact_path_items(row: dict[str, Any], *, base: Path) -> list[tuple[str, Path]]:
    artifacts = row.get("artifacts")
    if not isinstance(artifacts, dict):
        return []
    out: list[tuple[str, Path]] = []
    for key, value in artifacts.items():
        if "path" not in str(key) and not str(key).endswith("_dir"):
            continue
        path = _resolve_artifact_path(base, value)
        if path is not None:
            out.append((str(key), path))
    return out


def _has_prompt_response_artifacts(row: dict[str, Any]) -> bool:
    artifacts = row.get("artifacts")
    if not isinstance(artifacts, dict):
        return False
    keys = set(artifacts)
    return (
        {"session_prompt_path", "session_response_path"} <= keys
        or {"prompt_path", "response_path"} <= keys
    )


def _has_move_context(row: dict[str, Any]) -> bool:
    moves = row.get("moves")
    if not isinstance(moves, dict):
        return False
    for key in ("recent_moves", "event_moves", "live_context_recent_moves"):
        value = moves.get(key)
        if isinstance(value, list) and value:
            return True
    return False


def _has_deck_mixer(row: dict[str, Any]) -> bool:
    moves = row.get("moves")
    return isinstance(moves, dict) and isinstance(moves.get("deck_mixer"), dict)


def _verify_ai_rows(
    rows: list[dict[str, Any]],
    *,
    base: Path,
    require_artifacts: bool,
    require_move_context: bool,
    require_deck_mixer: bool,
) -> tuple[dict[str, int], list[str]]:
    errors: list[str] = []
    artifact_pairs = 0
    move_rows = 0
    deck_mixer_rows = 0
    checked_paths = 0
    engines: set[str] = set()
    surfaces: set[str] = set()

    for idx, row in enumerate(rows):
        engine = row.get("engine")
        if isinstance(engine, str) and engine.strip():
            engines.add(engine.strip())
        surface = row.get("surface")
        if isinstance(surface, str) and surface.strip():
            surfaces.add(surface.strip())
        if _has_prompt_response_artifacts(row):
            artifact_pairs += 1
        if _has_move_context(row):
            move_rows += 1
        if _has_deck_mixer(row):
            deck_mixer_rows += 1
        for key, path in _artifact_path_items(row, base=base):
            checked_paths += 1
            if not path.exists():
                errors.append(
                    f"ai_message[{idx}] artifact {key} does not exist: {path}"
                )

    if require_artifacts and artifact_pairs == 0:
        errors.append("no ai_message row has prompt+response artifacts")
    if require_move_context and move_rows == 0:
        errors.append("no ai_message row has recent/event/live move context")
    if require_deck_mixer and deck_mixer_rows == 0:
        errors.append("no ai_message row has moves.deck_mixer")

    return (
        {
            "rows": len(rows),
            "artifact_pairs": artifact_pairs,
            "move_rows": move_rows,
            "deck_mixer_rows": deck_mixer_rows,
            "checked_artifact_paths": checked_paths,
            "engines": sorted(engines),
            "surfaces": sorted(surfaces),
        },
        errors,
    )


def _latest_session(recordings_root: Path) -> Path | None:
    try:
        dirs = [p for p in recordings_root.iterdir() if p.is_dir()]
    except OSError:
        return None
    if not dirs:
        return None
    return max(dirs, key=lambda p: p.stat().st_mtime)


def _latest_ai_message_session(recordings_root: Path) -> Path | None:
    try:
        dirs = sorted(
            (p for p in recordings_root.iterdir() if p.is_dir()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return None
    for session_dir in dirs:
        rows, _errors = _read_jsonl(session_dir / "events.jsonl")
        if any(row.get("kind") == "ai_message" for row in rows):
            return session_dir
    return None


def verify_session(
    session_dir: Path,
    *,
    require_artifacts: bool = False,
    require_move_context: bool = False,
    require_deck_mixer: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    events_path = session_dir / "events.jsonl"
    rows, errors = _read_jsonl(events_path)
    ai_rows = [row for row in rows if row.get("kind") == "ai_message"]
    if not ai_rows:
        errors.append(f"{events_path}: no kind='ai_message' rows")
    stats, row_errors = _verify_ai_rows(
        ai_rows,
        base=session_dir,
        require_artifacts=require_artifacts,
        require_move_context=require_move_context,
        require_deck_mixer=require_deck_mixer,
    )
    errors.extend(row_errors)
    return (
        {
            "session_dir": str(session_dir),
            "events_path": str(events_path),
            "total_events": len(rows),
            **stats,
        },
        errors,
    )


def verify_global(
    root: Path,
    *,
    require_artifacts: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    log_path = root / "ai_messages" / "ai_messages.jsonl"
    rows, errors = _read_jsonl(log_path)
    if not rows:
        errors.append(f"{log_path}: no global ai_message rows")
    stats, row_errors = _verify_ai_rows(
        rows,
        base=root,
        require_artifacts=require_artifacts,
        require_move_context=False,
        require_deck_mixer=False,
    )
    errors.extend(row_errors)
    return (
        {
            "root": str(root),
            "log_path": str(log_path),
            **stats,
        },
        errors,
    )


def _default_recordings_root() -> Path:
    from vibemix.runtime.config_store import app_data_dir

    return app_data_dir() / "recordings"


def _default_global_root() -> Path:
    from vibemix.runtime.config_store import app_data_dir

    return app_data_dir()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", type=Path, help="Session directory to verify.")
    parser.add_argument(
        "--recordings-root",
        type=Path,
        help="Recordings root; newest child session is used when --session-dir is omitted.",
    )
    parser.add_argument(
        "--latest-with-ai-message",
        action="store_true",
        help="When --session-dir is omitted, choose the newest session containing ai_message.",
    )
    parser.add_argument(
        "--global-root",
        type=Path,
        help="Root containing ai_messages/ai_messages.jsonl.",
    )
    parser.add_argument("--skip-session", action="store_true")
    parser.add_argument("--require-global", action="store_true")
    parser.add_argument("--require-artifacts", action="store_true")
    parser.add_argument("--require-move-context", action="store_true")
    parser.add_argument("--require-deck-mixer", action="store_true")
    parser.add_argument(
        "--require-engine",
        action="append",
        default=[],
        help="Require at least one inspected ai_message row with this engine; repeatable.",
    )
    parser.add_argument(
        "--require-surface",
        action="append",
        default=[],
        help="Require at least one inspected ai_message row with this surface; repeatable.",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    errors: list[str] = []
    report: dict[str, Any] = {}

    if not args.skip_session:
        session_dir = args.session_dir
        if session_dir is None:
            recordings_root = args.recordings_root or _default_recordings_root()
            session_dir = (
                _latest_ai_message_session(recordings_root)
                if args.latest_with_ai_message
                else _latest_session(recordings_root)
            )
            if session_dir is None:
                if args.latest_with_ai_message:
                    errors.append(f"{recordings_root}: no sessions containing ai_message found")
                else:
                    errors.append(f"{recordings_root}: no session directories found")
        if session_dir is not None:
            session_report, session_errors = verify_session(
                Path(session_dir),
                require_artifacts=args.require_artifacts,
                require_move_context=args.require_move_context,
                require_deck_mixer=args.require_deck_mixer,
            )
            report["session"] = session_report
            errors.extend(session_errors)

    if args.global_root is not None or args.require_global:
        global_root = args.global_root or _default_global_root()
        global_report, global_errors = verify_global(
            global_root,
            require_artifacts=args.require_artifacts,
        )
        report["global"] = global_report
        errors.extend(global_errors)

    observed_engines: set[str] = set()
    observed_surfaces: set[str] = set()
    for section in ("session", "global"):
        section_report = report.get(section)
        if not isinstance(section_report, dict):
            continue
        observed_engines.update(
            str(engine).strip()
            for engine in section_report.get("engines", [])
            if str(engine).strip()
        )
        observed_surfaces.update(
            str(surface).strip()
            for surface in section_report.get("surfaces", [])
            if str(surface).strip()
        )
    if args.require_engine:
        missing = sorted(set(args.require_engine) - observed_engines)
        if missing:
            observed = ", ".join(sorted(observed_engines)) or "none"
            errors.append(
                "missing required ai_message engine(s): "
                + ", ".join(missing)
                + f" (observed: {observed})"
            )
    if args.require_surface:
        missing = sorted(set(args.require_surface) - observed_surfaces)
        if missing:
            observed = ", ".join(sorted(observed_surfaces)) or "none"
            errors.append(
                "missing required ai_message surface(s): "
                + ", ".join(missing)
                + f" (observed: {observed})"
            )

    report["ok"] = not errors
    report["errors"] = errors
    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    elif errors:
        print("AI observability verification failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
    else:
        parts = []
        if "session" in report:
            parts.append(f"session rows={report['session']['rows']}")
        if "global" in report:
            parts.append(f"global rows={report['global']['rows']}")
        print("OK: ai_message observability verified (" + ", ".join(parts) + ")")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
