# SPDX-License-Identifier: Apache-2.0
"""Plan 41-07 — Phase 41 latency-stack metric flags on replay_harness.

Pins the three additive observational CLI flags:

  * ``--print-llm-to-tts-delta`` aggregates `llm_to_tts_delta_ms` events
    (LAT-04 verification surface).
  * ``--print-cache-hit-rate``   aggregates `cache_hit` ratio vs LLM
    invokes (LAT-02 verification surface for Open Q3 ≥60% threshold).
  * ``--print-router-resolves``  scans `src/vibemix/` for `resolve(...)`
    call sites (LAT-01 audit surface).

All three flags are additive — default off, do not alter the scorecard
emit path, and never exit non-zero on observational mismatches.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.eval.replay_harness import (
    _emit_cache_hit_rate_report,
    _emit_llm_to_tts_delta_report,
    _emit_router_resolves_report,
    _extract_delta_values,
    _percentile,
    _scan_router_resolves,
    main,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_VIBEMIX = REPO_ROOT / "src" / "vibemix"


# ---------------------------------------------------------------------------
# --print-llm-to-tts-delta unit tests (Pure helpers + emitter)
# ---------------------------------------------------------------------------


def test_extract_delta_values_filters_to_typed_events() -> None:
    """`_extract_delta_values` only picks up `llm_to_tts_delta_ms` rows."""
    events = [
        {"type": "llm_to_tts_delta_ms", "delta_ms": 250},
        {"type": "llm_to_tts_delta_ms", "delta_ms": 410.5},
        {"type": "cache_hit", "delta_ms": 999},  # wrong type — skip
        {"type": "llm_to_tts_delta_ms"},  # missing delta_ms — skip
        {"type": "llm_to_tts_delta_ms", "delta_ms": "garbage"},  # non-numeric — skip
    ]
    out = _extract_delta_values(events)
    assert out == [250.0, 410.5]


def test_percentile_linear_interp_matches_numpy_default() -> None:
    """_percentile uses NumPy-style linear interpolation."""
    # For [1, 2, 3, 4, 5], p50 = 3, p25 = 2, p75 = 4 — clean integer cases.
    vals = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert _percentile(vals, 50.0) == 3.0
    assert _percentile(vals, 0.0) == 1.0
    assert _percentile(vals, 100.0) == 5.0
    # p95 of 10 deltas spanning 200..500 — interpolation between idx 8 & 9.
    deltas = [200.0, 250.0, 280.0, 305.0, 305.0, 320.0, 350.0, 410.0, 450.0, 500.0]
    p95 = _percentile(deltas, 95.0)
    # Index 9 - 0.5 between vals[8]=450 and vals[9]=500 → ~475
    assert 450.0 <= p95 <= 500.0


def test_percentile_returns_zero_on_empty() -> None:
    assert _percentile([], 95.0) == 0.0


def test_print_llm_to_tts_delta_empty_session_emits_marker(capsys) -> None:
    """No `llm_to_tts_delta_ms` events → observational marker line."""
    events: list[dict] = [{"type": "cache_hit", "cached_tokens": 1024}]
    _emit_llm_to_tts_delta_report(events)
    out = capsys.readouterr().out
    assert "no LLMToTTSDeltaMeter events found" in out
    assert "pre-Phase-41 session or no first-sentence emissions" in out


def test_print_llm_to_tts_delta_aggregates_real_distribution(capsys) -> None:
    """10 synthetic deltas mixed 200-500ms → aggregate row prints with
    count, mean, median, p50/p95/p99, min, max."""
    events = [
        {"type": "llm_to_tts_delta_ms", "delta_ms": d}
        for d in (200, 210, 250, 280, 305, 320, 350, 410, 450, 500)
    ]
    _emit_llm_to_tts_delta_report(events)
    out = capsys.readouterr().out
    assert "[llm-to-tts-delta]" in out
    assert "count=10" in out
    # mean of those = 327.5
    assert "mean=327.5ms" in out
    # min/max bounds in output (the integers should round cleanly)
    assert "min=200ms" in out
    assert "max=500ms" in out
    # p95 ≥ p50 ≥ median sanity
    assert "p50=" in out
    assert "p95=" in out
    assert "p99=" in out


# ---------------------------------------------------------------------------
# --print-cache-hit-rate unit tests
# ---------------------------------------------------------------------------


def test_print_cache_hit_rate_30_invokes_18_hits_yields_60pct(capsys) -> None:
    """30 llm_invoke + 18 cache_hit (each tagged with cached_tokens)
    → ratio 18/30 = 60.0%."""
    events: list[dict] = []
    for _ in range(30):
        events.append({"type": "llm_invoke"})
    for _ in range(18):
        events.append({"type": "cache_hit", "cached_tokens": 1024})
    _emit_cache_hit_rate_report(events)
    out = capsys.readouterr().out
    assert "[cache-hit-rate]" in out
    assert "18/30 = 60.0%" in out
    # Mean cached_tokens row land on integer 1024 (all same value).
    assert "mean cached_tokens on hit: 1024" in out


def test_print_cache_hit_rate_no_invokes_falls_back_to_count(capsys) -> None:
    """Events-only fixtures without llm_invoke markers print the hit count
    + a `no llm_invoke-family events` qualifier (still observational)."""
    events: list[dict] = [
        {"type": "cache_hit", "cached_tokens": 800},
        {"type": "cache_hit", "cached_tokens": 1200},
    ]
    _emit_cache_hit_rate_report(events)
    out = capsys.readouterr().out
    assert "cache_hit: 2 events recorded" in out
    assert "no llm_invoke-family events in log" in out
    # mean(800, 1200) = 1000 → integer rounded
    assert "1000" in out


def test_print_cache_hit_rate_event_fired_counts_as_invoke(capsys) -> None:
    """`event_fired` is one of the LLM-invoke-family markers — accepted
    as denominator (events.jsonl shape varies across phases)."""
    events: list[dict] = []
    for _ in range(10):
        events.append({"type": "event_fired"})
    for _ in range(5):
        events.append({"type": "cache_hit", "cached_tokens": 512})
    _emit_cache_hit_rate_report(events)
    out = capsys.readouterr().out
    assert "5/10 = 50.0%" in out


# ---------------------------------------------------------------------------
# --print-router-resolves unit tests
# ---------------------------------------------------------------------------


def test_scan_router_resolves_finds_real_call_sites_in_src_vibemix() -> None:
    """Plan 41-01 migration guarantees ≥9 resolve() call sites under
    src/vibemix/ (one per migrated SDK invocation site)."""
    counts = _scan_router_resolves(SRC_VIBEMIX)
    total = sum(counts.values())
    # Plan 41-01 lock — at least 9 sites across the 8 router paths.
    assert total >= 9, (
        f"expected ≥9 resolve() call sites under src/vibemix/, "
        f"got {total}: {counts!r}"
    )


def test_scan_router_resolves_skips_router_internal_files(tmp_path) -> None:
    """`_router_config.py` and `model_router.py` are skipped (allowlisted
    location for raw literals, self-references would inflate count)."""
    # Build a synthetic source tree with resolve() calls in both
    # allowlisted internals and a regular caller.
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "_router_config.py").write_text("resolve('live_coach')\n")
    (pkg / "model_router.py").write_text("resolve('debrief')\n")
    (pkg / "caller.py").write_text("x = resolve('embedding')\n")
    counts = _scan_router_resolves(pkg)
    # Only caller.py's resolve('embedding') should land.
    assert counts == {"embedding": 1}


def test_emit_router_resolves_report_prints_paths_alphabetically(
    tmp_path, capsys
) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text(
        "resolve('zeta')\nresolve('alpha')\nresolve('alpha')\n"
    )
    _emit_router_resolves_report(pkg)
    out = capsys.readouterr().out
    assert "[router-resolves]" in out
    assert "3 call sites" in out
    # alpha appears before zeta (alphabetical row order)
    alpha_idx = out.index("alpha")
    zeta_idx = out.index("zeta")
    assert alpha_idx < zeta_idx
    # alpha count 2, zeta count 1
    assert "alpha" in out
    assert "  2" in out
    assert "  1" in out


def test_emit_router_resolves_report_empty_source_tree(tmp_path, capsys) -> None:
    """No .py files / no resolve() calls → zero-line marker + header at 0."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    _emit_router_resolves_report(pkg)
    out = capsys.readouterr().out
    assert "0 call sites" in out
    assert "(no resolve() call sites detected)" in out


# ---------------------------------------------------------------------------
# CLI integration — flag activation through main(argv).
# ---------------------------------------------------------------------------


def _make_events_fixture(
    tmp_path: Path,
    rows: list[dict],
    session_name: str = "phase_41_synth",
) -> Path:
    """Build a synthetic events-only session under `tmp_path/<session>/`.

    Returns the parent `tmp_path` so the harness `--corpus` flag can point
    at it (the rglob path on empty-sessions falls through to the audit).
    """
    sess = tmp_path / session_name
    sess.mkdir()
    (sess / "events.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows),
        encoding="utf-8",
    )
    return tmp_path


def test_cli_print_llm_to_tts_delta_against_events_only_fixture(
    tmp_path, capsys
) -> None:
    """`--print-llm-to-tts-delta` reads events.jsonl from an events-only
    fixture (no input.wav) and prints the aggregate stats."""
    rows = [
        {"type": "llm_to_tts_delta_ms", "delta_ms": 220},
        {"type": "llm_to_tts_delta_ms", "delta_ms": 305},
        {"type": "llm_to_tts_delta_ms", "delta_ms": 410},
    ]
    corpus = _make_events_fixture(tmp_path, rows)
    out_dir = tmp_path / "out"
    rc = main(
        [
            "--corpus",
            str(corpus),
            "--judges",
            "noop",
            "--output",
            str(out_dir),
            "--print-llm-to-tts-delta",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "[llm-to-tts-delta]" in out
    assert "count=3" in out


def test_cli_print_cache_hit_rate_against_events_only_fixture(
    tmp_path, capsys
) -> None:
    """`--print-cache-hit-rate` reads cache_hit + invoke counts from
    events.jsonl in an events-only fixture and prints the ratio."""
    rows: list[dict] = []
    for _ in range(20):
        rows.append({"type": "llm_invoke"})
    for _ in range(12):
        rows.append({"type": "cache_hit", "cached_tokens": 1500})
    corpus = _make_events_fixture(tmp_path, rows)
    out_dir = tmp_path / "out"
    rc = main(
        [
            "--corpus",
            str(corpus),
            "--judges",
            "noop",
            "--output",
            str(out_dir),
            "--print-cache-hit-rate",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "12/20 = 60.0%" in out
    assert "mean cached_tokens on hit: 1500" in out


def test_cli_print_router_resolves_against_real_src_tree(tmp_path, capsys) -> None:
    """`--print-router-resolves` is source-tree-scoped — runs without
    needing a corpus. Hits real src/vibemix/ and reports ≥9 call sites."""
    out_dir = tmp_path / "out"
    rc = main(
        [
            "--corpus",
            str(tmp_path),  # empty corpus — flag still runs
            "--judges",
            "noop",
            "--output",
            str(out_dir),
            "--print-router-resolves",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "[router-resolves]" in out
    # Real src/vibemix/ — must have ≥9 call sites (Plan 41-01 migration).
    # Extract the count from the header for a precise assertion.
    import re

    m = re.search(r"(\d+) call sites", out)
    assert m is not None, f"could not parse call-site count from: {out!r}"
    count = int(m.group(1))
    assert count >= 9, (
        f"expected ≥9 resolve() call sites in src/vibemix/, got {count}"
    )


def test_cli_help_lists_all_three_phase_41_flags(capsys) -> None:
    """--help must list the three new Phase 41 flags — discoverability."""
    with pytest.raises(SystemExit):
        main(["--help"])
    captured = capsys.readouterr()
    assert "--print-llm-to-tts-delta" in captured.out
    assert "--print-cache-hit-rate" in captured.out
    assert "--print-router-resolves" in captured.out


def test_cli_phase_41_flags_are_additive_to_print_cooldowns(
    tmp_path, capsys
) -> None:
    """All four observational flags coexist — combining them does not
    raise + each emits its own report block."""
    rows = [
        {"type": "PHASE", "t_session": 0.0},
        {"type": "PHASE", "t_session": 12.0},
        {"type": "llm_to_tts_delta_ms", "delta_ms": 305},
    ]
    corpus = _make_events_fixture(tmp_path, rows)
    out_dir = tmp_path / "out"
    rc = main(
        [
            "--corpus",
            str(corpus),
            "--judges",
            "noop",
            "--output",
            str(out_dir),
            "--print-cooldowns",
            "--print-llm-to-tts-delta",
            "--print-cache-hit-rate",
            "--print-router-resolves",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    # Each flag emits a distinct prefix
    assert "[llm-to-tts-delta]" in captured.out
    assert "[cache-hit-rate]" in captured.out
    assert "[router-resolves]" in captured.out
