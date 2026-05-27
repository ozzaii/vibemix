# SPDX-License-Identifier: Apache-2.0
"""Legacy Gemini Embedding 2 cache audit script.

Power-user compatibility tool. The current product embedding path is local
CLAP ONNX via ``embed_factory.build_embedder()``; normal library search,
similarity, curation, and ingest do not use this Gemini cache. This module only
helps inspect or invalidate historical ``~/.cache/vibemix/embeddings.db`` rows
left by the retired Gemini embedder.

This module exists for two cases:
    1. Power-users who want to audit or clear old Gemini cache rows before
       rebuilding their library with CLAP.
    2. Engineers who want to verify legacy cache/probe behavior without
       touching the product CLAP path.

Modes:
    --audit-only (default)
        Probe the live API for the canonical model id; report current
        cache contents + cache-key version. No mutation.

    --dry-run
        Audit + report what invalidating the old cache would affect. No
        mutation.

    --re-embed-all
        Delete legacy Gemini cache rows. It does not call Gemini and it does
        not prewarm CLAP; the next product import/search uses the CLAP path.

Run:
    python -m scripts.library.migrate_embeddings_2 --help
    python -m scripts.library.migrate_embeddings_2 --audit-only
    python -m scripts.library.migrate_embeddings_2 --dry-run
    python -m scripts.library.migrate_embeddings_2 --re-embed-all
"""

from __future__ import annotations

import argparse
import os
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
    """Legacy Gemini re-embed what-if estimate."""

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
    client: genai.Client | None = None,
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
    """Rough legacy Gemini cost + time estimate for a historical full re-embed.

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
    print("Legacy Gemini Embedding cache audit", file=stream)
    print("===================================", file=stream)
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
    print("Legacy re-embed cost estimate", file=stream)
    print("=============================", file=stream)
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
    """Drop legacy Gemini cache rows.

    Note: we deliberately do NOT call ``embedder.embed_track()`` here. The
    product path is CLAP, and old cache rows do not hold enough information to
    reconstruct a ``TrackEntry``. This helper only clears the legacy Gemini
    cache; normal imports/searches refill through the CLAP embedder.

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
Product UX note:
    Current vibemix library embeddings are local CLAP ONNX/512. This script is
    not part of the product re-embed path; it only audits or clears historical
    Gemini Embedding cache rows.

Examples:
    python -m scripts.library.migrate_embeddings_2 --audit-only
    python -m scripts.library.migrate_embeddings_2 --dry-run
    python -m scripts.library.migrate_embeddings_2 --re-embed-all
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="migrate_embeddings_2",
        description=(
            "Legacy Gemini Embedding cache audit. Product library embeddings "
            "now use local CLAP ONNX/512."
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
        help="Audit + show what clearing the old cache would affect. No mutation.",
    )
    mode.add_argument(
        "--re-embed-all",
        action="store_true",
        help=(
            "Invalidate legacy Gemini cache rows. Product imports/searches "
            "refill via CLAP, not Gemini."
        ),
    )
    return parser


def _build_client_or_none() -> genai.Client | None:
    """Build a proxy-wired client if env is configured; else None.

    Tests + power-users without a configured proxy run audit-only mode
    without a live probe (probe fields stay None in the audit output).
    """
    try:
        from vibemix.agent.proxy_client import build_proxy_genai_client

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
            f"Invalidated {deleted} legacy Gemini cache rows. Product "
            "imports/searches now refill via CLAP, not Gemini.",
        )
        return 0

    if args.dry_run:
        est = estimate_reembed_cost(track_count=audit.entry_count)
        _render_cost(est)
        print(
            "(dry-run — no mutation performed. Run with --re-embed-all "
            "to clear legacy Gemini cache rows.)",
        )
        return 0

    # Default --audit-only — already rendered above.
    print(
        "Product UX: current library embeddings are local CLAP ONNX/512. "
        "This tool only audits the legacy Gemini cache.",
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
