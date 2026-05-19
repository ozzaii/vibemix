# SPDX-License-Identifier: Apache-2.0
"""Phase 27-03 — corpus diversity gate tests (EVAL-03 / Pitfall P43)."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]
MANIFEST = PROJECT_ROOT / "eval" / "corpus" / "manifest.json"
LICENSES = PROJECT_ROOT / "eval" / "corpus" / "LICENSES.md"
SESSIONS_DIR = PROJECT_ROOT / "eval" / "corpus" / "sessions"
GITATTRIBUTES = PROJECT_ROOT / ".gitattributes"


def test_manifest_exists_and_loads() -> None:
    assert MANIFEST.exists(), f"missing {MANIFEST}"
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert "sessions" in payload
    assert isinstance(payload["sessions"], list)


def test_manifest_has_six_sessions() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert len(payload["sessions"]) == 6


def test_manifest_three_distinct_genres() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    genres = {s["genre"] for s in payload["sessions"]}
    assert len(genres) >= 3, f"corpus must span ≥3 genres; got {genres}"


def test_manifest_hard_tek_pct_under_70() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    hard_tek = sum(1 for s in payload["sessions"] if s["genre"] == "hard_tek")
    pct = hard_tek / len(payload["sessions"])
    assert pct <= 0.70, f"hard_tek share {pct:.1%} exceeds 70% cap"


def test_manifest_validates_via_corpus_manifest_validator() -> None:
    """Plan 27-01's validate_manifest accepts the corpus manifest."""
    from scripts.eval.corpus_manifest import validate_manifest

    result = validate_manifest(MANIFEST)
    assert result["valid"] is True, (
        f"corpus manifest fails diversity gate: {result['errors']}"
    )
    assert len(result["manifest_hash"]) == 12


def test_six_session_directories_exist() -> None:
    for session in [
        "hard_tek_01",
        "hard_tek_02",
        "techno_01",
        "techno_02",
        "house_01",
        "house_02",
    ]:
        assert (SESSIONS_DIR / session).is_dir(), (
            f"missing session dir: {session}"
        )


def test_each_session_has_genre_file_matching_dir_name_prefix() -> None:
    for session_dir in SESSIONS_DIR.iterdir():
        if not session_dir.is_dir() or session_dir.name == ".gitkeep":
            continue
        genre_path = session_dir / "genre.txt"
        assert genre_path.exists(), f"missing genre.txt in {session_dir}"
        genre = genre_path.read_text(encoding="utf-8").strip()
        expected_prefix = session_dir.name.rsplit("_", 1)[0]
        assert genre == expected_prefix, (
            f"{session_dir.name}: genre.txt says {genre!r}, "
            f"directory prefix says {expected_prefix!r}"
        )


def test_each_session_has_source_txt() -> None:
    for session_dir in SESSIONS_DIR.iterdir():
        if not session_dir.is_dir() or session_dir.name == ".gitkeep":
            continue
        assert (session_dir / "source.txt").exists()


def test_each_session_has_events_jsonl_file() -> None:
    """events.jsonl exists per session (may be empty pending labeling)."""
    for session_dir in SESSIONS_DIR.iterdir():
        if not session_dir.is_dir() or session_dir.name == ".gitkeep":
            continue
        events = session_dir / "events.jsonl"
        assert events.exists(), f"missing events.jsonl in {session_dir}"


def test_licenses_md_exists() -> None:
    assert LICENSES.exists()
    text = LICENSES.read_text(encoding="utf-8")
    for session in [
        "hard_tek_01",
        "hard_tek_02",
        "techno_01",
        "techno_02",
        "house_01",
        "house_02",
    ]:
        assert session in text, f"LICENSES.md missing {session}"
    assert "hard_tek" in text or "Hard Tek" in text


def test_gitattributes_lfs_removed() -> None:
    """git-lfs was removed 2026-05-19 — no filter=lfs rules in .gitattributes.

    Reason: GitHub LFS data-pack billing exhausted at 778 unpushed commits;
    working-tree total (~23 MB) fits comfortably under GitHub's 100 MB
    per-file hard limit. Dropping the external git-lfs dependency aligns
    with the one-click install thesis (every external dep removed).
    """
    text = GITATTRIBUTES.read_text(encoding="utf-8")
    assert "filter=lfs" not in text


def test_source_corpus_script_help_works() -> None:
    """scripts/eval/source_corpus.py CLI is importable + --help works."""
    import subprocess
    import sys as _sys

    result = subprocess.run(
        [_sys.executable, "-m", "scripts.eval.source_corpus", "--help"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "DJ corpus" in result.stdout


def test_label_corpus_script_help_works() -> None:
    """scripts/eval/label_corpus.py CLI is importable + --help works."""
    import subprocess
    import sys as _sys

    result = subprocess.run(
        [_sys.executable, "-m", "scripts.eval.label_corpus", "--help"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_diversity_pct_matches_declaration() -> None:
    """The declared hard_tek_pct in manifest matches derived count."""
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    declared = payload["hard_tek_pct"]
    sessions = payload["sessions"]
    derived = sum(1 for s in sessions if s["genre"] == "hard_tek") / len(sessions)
    assert abs(declared - derived) < 0.001
