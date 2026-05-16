# SPDX-License-Identifier: Apache-2.0
"""Plan 41-05 LAT-06 — Embedding 2 cache audit + migration script.

Power-user tool. The DEFAULT migration UX is lazy-on-first-launch: the
LibraryEmbedder GA-rename probe (Plan 41-05 Task 1) naturally bumps
``EXCERPT_STRATEGY_VERSION`` when it lands on ``gemini-embedding-002``,
and the next read of any track triggers a re-embed via the existing
content-hash cache miss path. Users do NOT need to run this script.

This module exists for two cases:
    1. Power-users who want to pre-warm the cache before a session
       (saves the lazy-re-embed first-call latency).
    2. Engineers who want to verify cache state — confirm which model
       id the production probe lands on, count cached entries, surface
       drift before it ships.

Modes:
    --audit-only (default)
        Probe the live API for the canonical model id; report current
        cache contents + cache-key version. No mutation.

    --dry-run
        Audit + report what ``--re-embed-all`` would do (track count,
        estimated cost, estimated time). No mutation.

    --re-embed-all
        Actually invoke the lazy re-embed path on every cached track.
        Useful before a known offline session window.

Run:
    python -m scripts.library.migrate_embeddings_2 --help
    python -m scripts.library.migrate_embeddings_2 --audit-only
    python -m scripts.library.migrate_embeddings_2 --dry-run
    python -m scripts.library.migrate_embeddings_2 --re-embed-all
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from google import genai


# ─── Cost model (Plan 41-05 SUMMARY assumption) ───────────────────────────────


# ~150 tokens/track avg × $0.025 per 1K tokens at Flex pricing = $0.00375/track.
# This is a conservative estimate; the actual cost depends on track
# duration (3-excerpt path triples it) and Flex/Standard tier routing.
EMBED_USD_PER_TRACK_AVG = 0.00375
USD_TO_EUR_DEFAULT = 0.92


# ─── Result types ─────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class CacheAudit:
    """What the audit found in ~/.cache/vibemix/embeddings.db."""

    cache_path: Path
    cache_exists: bool
    entry_count: int
    probe_model_id: str | None
    probe_version: str | None
    probe_error: str | None


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """What --re-embed-all would cost."""

    track_count: int
    est_cost_usd: float
    est_cost_eur: float
    est_duration_minutes: float


# ─── Audit ────────────────────────────────────────────────────────────────────


def _count_cache_entries(cache_path: Path) -> int:
    if not cache_path.exists():
        return 0
    try:
        conn = sqlite3.connect(str(cache_path))
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM embed_cache"
            ).fetchone()
            return int(row[0]) if row else 0
        finally:
            conn.close()
    except sqlite3.Error:
        # Schema not initialized yet — counts as zero.
        return 0


def audit_cache(
    client: "genai.Client | None" = None,
    cache_path: Path | None = None,
) -> CacheAudit:
    """Run the GA probe + count cached entries; no mutation.

    Args:
        client: pre-built proxy-wired ``genai.Client``. If ``None``, the
            probe is skipped and ``probe_*`` fields reflect that.
        cache_path: override for the cache db location (test path).
    """
    from vibemix.library.embed import (
        EMBED_CACHE_DB_PATH,
        _probe_ga_model_id,
    )

    path = cache_path or EMBED_CACHE_DB_PATH
    entry_count = _count_cache_entries(path)

    probe_model_id: str | None = None
    probe_version: str | None = None
    probe_error: str | None = None
    if client is not None:
        try:
            probe_model_id, probe_version = _probe_ga_model_id(client)
        except RuntimeError as exc:
            probe_error = str(exc)

    return CacheAudit(
        cache_path=path,
        cache_exists=path.exists(),
        entry_count=entry_count,
        probe_model_id=probe_model_id,
        probe_version=probe_version,
        probe_error=probe_error,
    )


# ─── Cost estimate ────────────────────────────────────────────────────────────


def estimate_reembed_cost(
    track_count: int,
    *,
    usd_per_track: float = EMBED_USD_PER_TRACK_AVG,
    usd_to_eur: float = USD_TO_EUR_DEFAULT,
    embed_seconds_per_track: float = 1.5,
) -> CostEstimate:
    """Rough cost + time estimate for a full re-embed.

    Assumptions documented in CostProjection / Phase 28-08:
        - ~150 tokens/track avg × Flex pricing ≈ $0.00375/track.
        - ~1.5s wall-clock per track at typical proxy latency.
    """
    usd = track_count * usd_per_track
    eur = usd * usd_to_eur
    minutes = (track_count * embed_seconds_per_track) / 60.0
    return CostEstimate(
        track_count=track_count,
        est_cost_usd=usd,
        est_cost_eur=eur,
        est_duration_minutes=minutes,
    )


# ─── Rendering ────────────────────────────────────────────────────────────────


def _render_audit(audit: CacheAudit, *, stream=None) -> None:
    # Resolve sys.stdout lazily so capsys redirection in tests works.
    if stream is None:
        stream = sys.stdout
    print("Embedding 2 cache audit", file=stream)
    print("=======================", file=stream)
    print(f"  Cache path:      {audit.cache_path}", file=stream)
    print(f"  Cache exists:    {audit.cache_exists}", file=stream)
    print(f"  Entry count:     {audit.entry_count}", file=stream)
    if audit.probe_error is not None:
        print(f"  Probe error:     {audit.probe_error}", file=stream)
    elif audit.probe_model_id is not None:
        print(f"  GA probe model:  {audit.probe_model_id}", file=stream)
        print(f"  Cache version:   {audit.probe_version}", file=stream)
    else:
        print(
            "  GA probe:        SKIPPED (no client supplied; pass a "
            "proxy-wired genai.Client to enable)",
            file=stream,
        )
    print("", file=stream)


def _render_cost(est: CostEstimate, *, stream=None) -> None:
    # Resolve sys.stdout lazily so capsys redirection in tests works.
    if stream is None:
        stream = sys.stdout
    print("Re-embed-all cost estimate", file=stream)
    print("==========================", file=stream)
    print(f"  Tracks to re-embed:  {est.track_count}", file=stream)
    print(f"  Estimated cost:      ${est.est_cost_usd:.2f} USD "
          f"(€{est.est_cost_eur:.2f})", file=stream)
    print(f"  Estimated duration:  {est.est_duration_minutes:.1f} min",
          file=stream)
    print(
        "  Assumption:          $0.025/1K tokens × ~150 tokens/track "
        "avg at Flex pricing",
        file=stream,
    )
    print("", file=stream)


# ─── Re-embed loop ────────────────────────────────────────────────────────────


def reembed_all(
    embedder: object,
    cache_path: Path | None = None,
) -> int:
    """Iterate the cache table + drop every row so the next read re-embeds.

    Note: we deliberately do NOT eagerly call ``embedder.embed_track()``
    for each track here — that would require iterating the Rekordbox
    library, and the cache rows don't hold enough info to reconstruct
    the TrackEntry. The simplest "force re-embed" primitive is to
    invalidate the cache; the next ``LibraryImporter.import_all()`` or
    runtime ``embed_track()`` call naturally re-fills it with the new
    model id.

    Returns: number of rows deleted.
    """
    from vibemix.library.embed import EMBED_CACHE_DB_PATH

    path = cache_path or EMBED_CACHE_DB_PATH
    if not path.exists():
        return 0
    conn = sqlite3.connect(str(path))
    try:
        rows = conn.execute(
            "SELECT COUNT(*) FROM embed_cache"
        ).fetchone()
        deleted = int(rows[0]) if rows else 0
        conn.execute("DELETE FROM embed_cache")
        conn.commit()
        return deleted
    finally:
        conn.close()


# ─── CLI ──────────────────────────────────────────────────────────────────────


HELP_EPILOG = """\
Migration UX note:
    The default vibemix UX is LAZY ON FIRST LAUNCH. After the
    LibraryEmbedder GA-rename probe ships (Plan 41-05), the next time
    a user reads any track, the cache key miss triggers a transparent
    re-embed. You only need this script if you want to pre-warm or
    audit the cache explicitly.

Examples:
    python -m scripts.library.migrate_embeddings_2 --audit-only
    python -m scripts.library.migrate_embeddings_2 --dry-run
    python -m scripts.library.migrate_embeddings_2 --re-embed-all
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="migrate_embeddings_2",
        description=(
            "Plan 41-05 LAT-06 — Embedding 2 cache audit + migration. "
            "Default UX is lazy on first launch; this is a power-user tool."
        ),
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--audit-only",
        action="store_true",
        help="Default. Report current cache + probe state; no mutation.",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Audit + show what --re-embed-all would do. No mutation.",
    )
    mode.add_argument(
        "--re-embed-all",
        action="store_true",
        help=(
            "Invalidate every cached embedding so subsequent imports "
            "re-fill with the current probe-derived model id."
        ),
    )
    return parser


def _build_client_or_none() -> "genai.Client | None":
    """Build a proxy-wired client if env is configured; else None.

    Tests + power-users without a configured proxy run audit-only mode
    without a live probe (probe fields stay None in the audit output).
    """
    try:
        from vibemix.agent.proxy_client import build_proxy_genai_client
        import os

        proxy_jwt = os.environ.get("VIBEMIX_PROXY_JWT")
        proxy_url = os.environ.get("VIBEMIX_PROXY_URL")
        if not proxy_jwt or not proxy_url:
            return None
        return build_proxy_genai_client(proxy_jwt, proxy_url)
    except Exception:  # pragma: no cover - boot-time defensive
        return None


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    client = _build_client_or_none()
    audit = audit_cache(client=client)
    _render_audit(audit)

    if args.re_embed_all:
        deleted = reembed_all(embedder=None)
        print(
            f"Invalidated {deleted} cache rows. Next import/read will "
            f"re-embed with model "
            f"{audit.probe_model_id or '<not probed>'}.",
        )
        return 0

    if args.dry_run:
        est = estimate_reembed_cost(track_count=audit.entry_count)
        _render_cost(est)
        print(
            "(dry-run — no mutation performed. Run with --re-embed-all "
            "to invalidate and trigger re-embed.)",
        )
        return 0

    # Default --audit-only — already rendered above.
    print(
        "Migration UX: lazy on first launch. The next track read will "
        "trigger a re-embed automatically if the probe lands on a new "
        "model id.",
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
