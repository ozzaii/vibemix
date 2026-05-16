# SPDX-License-Identifier: Apache-2.0
"""Plan 41-05 Task 3 — Tests for scripts/library/migrate_embeddings_2.py.

The migration script is the power-user surface for the Embedding 2
LAT-06 audit + re-embed flow. Default UX is lazy on first launch (Task 1
ships the probe that handles it); this script only matters for users
who want to verify or pre-warm explicitly.

Tests:
    - test_audit_only_no_mutation
    - test_dry_run_reports_count
    - test_help_text_documents_lazy_default
    - test_re_embed_all_invalidates_cache
    - test_main_runs_default_mode
    - test_estimate_reembed_cost_math

All Gemini probe calls are mocked. Cache lives in a tmp path.
"""

from __future__ import annotations

import io
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from scripts.library.migrate_embeddings_2 import (
    CacheAudit,
    CostEstimate,
    _build_parser,
    audit_cache,
    estimate_reembed_cost,
    main,
    reembed_all,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_cache(tmp_path: Path) -> Path:
    """Seed a tmp embed_cache.db with 3 rows."""
    path = tmp_path / "embeddings.db"
    conn = sqlite3.connect(str(path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS embed_cache (
            key TEXT PRIMARY KEY,
            vector BLOB NOT NULL,
            ts REAL NOT NULL
        )
        """
    )
    for i in range(3):
        conn.execute(
            "INSERT INTO embed_cache (key, vector, ts) VALUES (?, ?, ?)",
            (f"key-{i}", b"\x00" * 16, float(i)),
        )
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def empty_tmp_cache(tmp_path: Path) -> Path:
    """Path to a cache that does not exist yet."""
    return tmp_path / "missing.db"


# ─── Audit tests ─────────────────────────────────────────────────────────────


def test_audit_only_no_mutation(tmp_cache: Path) -> None:
    """audit_cache reads the row count but never writes."""
    mtime_before = tmp_cache.stat().st_mtime

    audit = audit_cache(client=None, cache_path=tmp_cache)

    assert isinstance(audit, CacheAudit)
    assert audit.cache_path == tmp_cache
    assert audit.cache_exists is True
    assert audit.entry_count == 3
    # No client → no probe → no probe fields populated.
    assert audit.probe_model_id is None
    assert audit.probe_version is None
    assert audit.probe_error is None

    # File mtime did not change → no writes.
    assert tmp_cache.stat().st_mtime == mtime_before


def test_audit_handles_missing_cache(empty_tmp_cache: Path) -> None:
    """audit_cache on a missing path returns entry_count=0 + cache_exists=False."""
    audit = audit_cache(client=None, cache_path=empty_tmp_cache)
    assert audit.cache_exists is False
    assert audit.entry_count == 0


def test_audit_with_client_runs_probe(tmp_cache: Path) -> None:
    """When a client is supplied, audit_cache invokes the GA probe."""
    client = MagicMock()
    client.models.embed_content.return_value = SimpleNamespace(
        embeddings=[SimpleNamespace(values=[0.1] * 768)]
    )

    audit = audit_cache(client=client, cache_path=tmp_cache)

    assert audit.probe_model_id == "gemini-embedding-002"
    assert audit.probe_version == "v2-3excerpt-mean-emb2-ga"
    assert audit.probe_error is None
    # Probe sent exactly one canary call.
    assert client.models.embed_content.call_count == 1


def test_audit_with_failing_probe_records_error(tmp_cache: Path) -> None:
    """When all candidates fail, audit captures the RuntimeError message."""
    client = MagicMock()
    client.models.embed_content.side_effect = Exception("503 UNAVAILABLE")

    audit = audit_cache(client=client, cache_path=tmp_cache)

    assert audit.probe_model_id is None
    assert audit.probe_version is None
    assert audit.probe_error is not None
    assert "GEMINI_EMBEDDING_MODEL_GA_CANDIDATES" in audit.probe_error


# ─── Cost estimate tests ─────────────────────────────────────────────────────


def test_estimate_reembed_cost_math() -> None:
    """estimate_reembed_cost produces deterministic dollar + euro values."""
    est = estimate_reembed_cost(track_count=1000)
    assert isinstance(est, CostEstimate)
    assert est.track_count == 1000
    # 1000 × $0.00375 = $3.75
    assert abs(est.est_cost_usd - 3.75) < 1e-6
    # × 0.92 = €3.45
    assert abs(est.est_cost_eur - 3.45) < 1e-6
    # 1000 × 1.5s = 1500s = 25 min
    assert abs(est.est_duration_minutes - 25.0) < 1e-6


def test_estimate_zero_tracks() -> None:
    """Zero-track corpus yields zero cost + zero duration."""
    est = estimate_reembed_cost(track_count=0)
    assert est.est_cost_usd == 0.0
    assert est.est_cost_eur == 0.0
    assert est.est_duration_minutes == 0.0


# ─── Re-embed-all tests ──────────────────────────────────────────────────────


def test_re_embed_all_invalidates_cache(tmp_cache: Path) -> None:
    """reembed_all wipes every row so next read forces a re-embed."""
    deleted = reembed_all(embedder=None, cache_path=tmp_cache)

    assert deleted == 3

    conn = sqlite3.connect(str(tmp_cache))
    try:
        remaining = conn.execute(
            "SELECT COUNT(*) FROM embed_cache"
        ).fetchone()[0]
    finally:
        conn.close()
    assert remaining == 0


def test_re_embed_all_missing_cache_returns_zero(
    empty_tmp_cache: Path,
) -> None:
    """reembed_all on a missing cache silently returns 0."""
    deleted = reembed_all(embedder=None, cache_path=empty_tmp_cache)
    assert deleted == 0


# ─── CLI integration ─────────────────────────────────────────────────────────


def _patch_paths(monkeypatch: pytest.MonkeyPatch, cache_path: Path) -> None:
    """Patch EMBED_CACHE_DB_PATH to point at the test cache."""
    monkeypatch.setattr(
        "vibemix.library.embed.EMBED_CACHE_DB_PATH", cache_path
    )


def test_main_default_mode_renders_audit(
    tmp_cache: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``python -m scripts.library.migrate_embeddings_2`` → audit-only output."""
    _patch_paths(monkeypatch, tmp_cache)
    # No proxy env → _build_client_or_none returns None → probe skipped.
    monkeypatch.delenv("VIBEMIX_PROXY_JWT", raising=False)
    monkeypatch.delenv("VIBEMIX_PROXY_URL", raising=False)

    rc = main(argv=[])
    out = capsys.readouterr().out

    assert rc == 0
    assert "Embedding 2 cache audit" in out
    assert "Entry count:     3" in out
    assert "lazy on first launch" in out.lower()


def test_main_dry_run_includes_cost_estimate(
    tmp_cache: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--dry-run mode appends the cost estimate."""
    _patch_paths(monkeypatch, tmp_cache)
    monkeypatch.delenv("VIBEMIX_PROXY_JWT", raising=False)
    monkeypatch.delenv("VIBEMIX_PROXY_URL", raising=False)

    rc = main(argv=["--dry-run"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "Re-embed-all cost estimate" in out
    assert "Tracks to re-embed:  3" in out
    # Cost line mentions USD + EUR.
    assert "USD" in out and "€" in out
    assert "dry-run" in out
    # The dry-run mode MUST mention the lazy default in the audit chunk.
    assert "lazy on first launch" not in out  # only printed in default mode


def test_main_re_embed_all_invalidates(
    tmp_cache: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--re-embed-all wipes the cache + reports count."""
    _patch_paths(monkeypatch, tmp_cache)
    monkeypatch.delenv("VIBEMIX_PROXY_JWT", raising=False)
    monkeypatch.delenv("VIBEMIX_PROXY_URL", raising=False)

    rc = main(argv=["--re-embed-all"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "Invalidated 3 cache rows" in out
    # Confirm cache actually emptied.
    conn = sqlite3.connect(str(tmp_cache))
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM embed_cache"
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 0


def test_help_text_documents_lazy_default(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--help output mentions the lazy-on-first-launch default UX."""
    parser = _build_parser()
    # Capture full --help by formatting the parser directly.
    help_text = parser.format_help()

    assert "lazy on first launch" in help_text.lower()
    assert "power-user" in help_text.lower()
    # Three mutually exclusive modes documented.
    assert "--audit-only" in help_text
    assert "--dry-run" in help_text
    assert "--re-embed-all" in help_text


def test_help_via_main_argparse_exits_clean(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`python -m scripts.library.migrate_embeddings_2 --help` exits 0."""
    with pytest.raises(SystemExit) as excinfo:
        main(argv=["--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "lazy on first launch" in out.lower()


def test_mutually_exclusive_modes() -> None:
    """argparse rejects passing both --dry-run and --re-embed-all."""
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--dry-run", "--re-embed-all"])
