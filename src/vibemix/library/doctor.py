# SPDX-License-Identifier: Apache-2.0
"""``library doctor`` — a live capability self-check for the Viber/library agent.

Why this exists: the recurring "every module is failing" confusion is almost
always a STALE build or a missing optional piece — no ``onnxruntime``, no CLAP
model on disk, an orphaned knowledge store, no Tavily key, no Codex CLI. Each
capability already fails with an honest error at call time, but there was no
single command to see the whole board at once. ``doctor`` probes each capability
against the REAL environment and reports ``ok`` / not-ok with a concrete fix, so
a user (or a maintainer staring at a screenshot) can tell a stale build from a
real breakage in one shot.

Contract: every check is best-effort and MUST NOT raise — a probe that cannot
run reports its own failure (``ok=False`` + the exception) rather than crashing
the whole report. Pure environment inspection: no network except the explicitly
key-gated web-search probe, which only checks for the key's PRESENCE (it does
not call out).
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from typing import Any


def _check(name: str, ok: bool, detail: str, fix: str = "") -> dict[str, Any]:
    return {"name": name, "ok": ok, "detail": detail, "fix": fix}


def check_clap_runtime() -> dict[str, Any]:
    """The embedding engine's runtime — the exact piece whose absence shows up
    as ``search_vibe failed: ModuleNotFoundError`` in the field."""
    missing = []
    for mod in ("onnxruntime", "tokenizers"):
        try:
            __import__(mod)
        except Exception:
            missing.append(mod)
    if missing:
        return _check(
            "clap_runtime",
            False,
            f"missing: {', '.join(missing)}",
            "uv sync --extra ai-local  (the packaged app bundles these)",
        )
    return _check("clap_runtime", True, "onnxruntime + tokenizers importable")


def check_clap_model() -> dict[str, Any]:
    """The CLAP ONNX snapshot must be on disk for any embed to run. The Xenova
    snapshot keeps the two graphs under an ``onnx/`` subdir (mirrors the engine's
    ``onnx/audio_model.onnx`` + ``onnx/text_model.onnx`` load paths) — checking
    the dir alone would false-positive on a half-download."""
    from pathlib import Path

    override = os.environ.get("VIBEMIX_CLAP_ONNX_DIR")
    base = Path(override) if override else Path.home() / ".cache" / "vibemix" / "clap-onnx"
    needed = (base / "onnx" / "audio_model.onnx", base / "onnx" / "text_model.onnx")
    missing = [str(p.relative_to(base)) for p in needed if not p.exists()]
    if not missing:
        return _check("clap_model", True, f"present at {base}")
    return _check(
        "clap_model",
        False,
        f"missing under {base}: {', '.join(missing)}",
        "uv run python -m vibemix library models --install clap",
    )


def check_library_cache() -> dict[str, Any]:
    """The track-title/library cache the grounded tools read from."""
    try:
        from vibemix.library.rekordbox import RekordboxLibrary

        lib = RekordboxLibrary()
        if lib.try_load_cache():
            return _check("library_cache", True, f"{len(lib.tracks)} tracks loaded")
        return _check(
            "library_cache",
            False,
            "no library cache",
            "uv run python -m vibemix library ingest   (or embed-folder)",
        )
    except Exception as e:
        return _check("library_cache", False, f"{type(e).__name__}: {e}")


def check_library_setup_candidates() -> dict[str, Any]:
    """Concrete sources a first-run DJ can explicitly index.

    This is not a replacement for ``library_cache``: Viber still cannot search
    until the user imports something. It turns "no cache" into an actionable
    setup board with local, bounded candidates.
    """
    try:
        from vibemix.library.rekordbox import RekordboxLibrary
        from vibemix.library.setup_discovery import discover_library_setup_candidate_dicts

        lib = RekordboxLibrary()
        if lib.try_load_cache():
            return _check(
                "library_setup",
                True,
                f"library already indexed ({len(lib.tracks)} tracks)",
            )
        candidates = discover_library_setup_candidate_dicts(max_candidates=3)
        if candidates:
            summary = "; ".join(
                f"{c.get('kind')}:{c.get('path')} ({c.get('audio_files_seen', 0)} files)"
                for c in candidates
            )
            return {
                **_check("library_setup", True, f"setup candidates: {summary}"),
                "candidates": candidates,
            }
        return _check(
            "library_setup",
            False,
            "no Rekordbox XML or music-folder candidates found",
            "Drop a Rekordbox collection.xml or music folder in Settings -> Library.",
        )
    except Exception as e:
        return _check("library_setup", False, f"{type(e).__name__}: {e}")


def check_embeddings_store() -> dict[str, Any]:
    """The sqlite-vec / numpy vector store the search rides on."""
    try:
        from vibemix.library.store import open_store

        store = open_store()
        backend = "sqlite-vec" if store.backend_name == "SqliteVecStore" else "numpy"
        count = store.row_count()
        n = int(count) if count is not None else 0
        if n > 0:
            return _check("embeddings_store", True, f"{n} vectors ({backend})")
        return _check(
            "embeddings_store",
            False,
            f"0 vectors ({backend})",
            "embed tracks: library ingest / embed-folder",
        )
    except Exception as e:
        return _check("embeddings_store", False, f"{type(e).__name__}: {e}")


def check_dj_knowledge() -> dict[str, Any]:
    """Report whether the DJ-knowledge text store can be queried."""
    try:
        from vibemix.library.dj_knowledge import DEFAULT_KNOWLEDGE_DIR, KnowledgeStore

        store = KnowledgeStore.load(DEFAULT_KNOWLEDGE_DIR / "dj_knowledge")
        if len(store) == 0:
            return _check(
                "dj_knowledge", False, "knowledge base empty", "no corpus ingested yet"
            )
        store_dim = store.dim
        if store_dim is None or int(store_dim) <= 0:
            return _check(
                "dj_knowledge",
                False,
                f"invalid knowledge matrix dim {store_dim}",
                "rebuild the KB from the DJ-knowledge corpus",
            )
        if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("VIBEMIX_PROXY_JWT")):
            return _check(
                "dj_knowledge",
                False,
                f"{len(store)} chunks, dim {store_dim}; no text embedder credential",
                "set GEMINI_API_KEY or VIBEMIX_PROXY_JWT for DJ-knowledge retrieval",
            )
        return _check(
            "dj_knowledge",
            True,
            f"{len(store)} chunks, dim {store_dim}; text embedder credential present",
        )
    except Exception as e:
        return _check("dj_knowledge", False, f"{type(e).__name__}: {e}")


def check_web_search() -> dict[str, Any]:
    """web_search degrades honestly without a key; report which state we're in."""
    if os.environ.get("TAVILY_API_KEY"):
        return _check("web_search", True, "TAVILY_API_KEY set")
    return _check(
        "web_search",
        False,
        "no TAVILY_API_KEY (web_search returns an honest error)",
        "set TAVILY_API_KEY in .env (free tier at tavily.com)",
    )


def check_cue_export() -> dict[str, Any]:
    """Rekordbox hot-cue write needs pyrekordbox at runtime (lazy import)."""
    try:
        import pyrekordbox  # noqa: F401

        return _check("cue_export", True, "pyrekordbox importable")
    except Exception as e:
        return _check(
            "cue_export",
            False,
            f"pyrekordbox unavailable ({type(e).__name__})",
            "install the rekordbox extra",
        )


def check_codex() -> dict[str, Any]:
    """The Viber agent's reasoning backend — the Codex CLI must be findable."""
    found = os.environ.get("VIBEMIX_CODEX_BIN") or shutil.which("codex")
    if found:
        return _check("codex_agent", True, f"codex at {found}")
    return _check(
        "codex_agent",
        False,
        "codex CLI not found on PATH",
        "install Codex CLI + `codex login`, or set VIBEMIX_CODEX_BIN",
    )


def check_search_live() -> dict[str, Any]:
    """The definitive "is it actually working" probe: embed a real query and
    run search_vibe end-to-end (CLAP query-embed → sqlite-vec top-k). Presence
    checks above can all pass while this still fails (e.g. the orphaned-store
    class of bug), so this is the one that truly answers "every module is
    failing?". Heavier (loads the embedder) → only runs under ``--deep``."""
    try:
        from vibemix.library.embed_factory import build_embedder
        from vibemix.library.rekordbox import RekordboxLibrary
        from vibemix.library.store import open_store
        from vibemix.library.toolset import LibraryToolset

        lib = RekordboxLibrary()
        lib.try_load_cache()
        toolset = LibraryToolset(build_embedder(), open_store(), lib)
        res = toolset.search_vibe({"query": "dark rolling techno", "k": 3})
        if res.get("error"):
            return _check(
                "search_live",
                False,
                f"search_vibe error: {str(res['error'])[:80]}",
                "run `library doctor` (no --deep) to see which piece is missing",
            )
        n = len(res.get("results", []))
        if n > 0:
            return _check("search_live", True, f"search_vibe returned {n} grounded results")
        return _check(
            "search_live",
            False,
            "search_vibe ran but returned 0 results",
            "embed tracks: library ingest / embed-folder",
        )
    except Exception as e:
        return _check("search_live", False, f"{type(e).__name__}: {e}")


# Ordered so the foundational pieces (runtime → model → store) come first; a
# failure high in the list usually explains failures below it.
CHECKS: tuple[Callable[[], dict[str, Any]], ...] = (
    check_clap_runtime,
    check_clap_model,
    check_library_cache,
    check_library_setup_candidates,
    check_embeddings_store,
    check_dj_knowledge,
    check_web_search,
    check_cue_export,
    check_codex,
)

# Functional (heavier) probes — only run under ``--deep`` because they load the
# embedder and exercise a real end-to-end path, not just inspect for presence.
DEEP_CHECKS: tuple[Callable[[], dict[str, Any]], ...] = (check_search_live,)


def run_doctor(*, deep: bool = False) -> dict[str, Any]:
    """Run every capability probe and aggregate. Never raises: a probe that
    blows up is captured as its own failed check, not propagated. ``deep`` adds
    the functional probes (a real end-to-end search) on top of the presence
    checks."""
    checks = CHECKS + (DEEP_CHECKS if deep else ())
    results: list[dict[str, Any]] = []
    for fn in checks:
        try:
            results.append(fn())
        except Exception as e:
            results.append(
                _check(fn.__name__, False, f"probe crashed: {type(e).__name__}: {e}")
            )
    ok_count = sum(1 for r in results if r["ok"])
    total = len(results)
    return {
        "checks": results,
        "ok_count": ok_count,
        "total": total,
        "all_ok": ok_count == total,
        "deep": deep,
    }


def format_report(report: dict[str, Any]) -> str:
    """Human-readable table: one ``[ok]``/``[!!]`` line per check, with the fix
    for anything not ok."""
    lines = [f"vibemix capability doctor — {report['ok_count']}/{report['total']} ok"]
    for r in report["checks"]:
        mark = "ok" if r["ok"] else "!!"
        lines.append(f"  [{mark}] {r['name']:<16} {r['detail']}")
        if not r["ok"] and r.get("fix"):
            lines.append(f"        fix: {r['fix']}")
    return "\n".join(lines)
