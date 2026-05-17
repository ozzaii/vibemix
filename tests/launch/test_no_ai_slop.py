# SPDX-License-Identifier: Apache-2.0
"""tests/launch/test_no_ai_slop.py — SHIP-TWEET 5-channel copy lock gate.

LAUNCH-07 (Phase 44, Plan 44-05): asserts the 5 launch-copy files under
``scripts/dayzero/launch_copy/`` carry the Kaan + Francesco sign-off
footer, hit every CONTEXT §specifics anchor phrase across the combined
corpus, and stay free of the 16-token AI-slop blocklist (plus the
``\\bdeeply\\s+\\w+`` adverb-construction regex).

Pattern mirrors ``tests/launch/test_readme_hero_lock.py``:
- Module-level shape tests pin the public surface
- Happy path against the live ``scripts/dayzero/launch_copy/`` corpus
- Negative cases — synthetic tmp_path corpora each violating one gate

Memory ``feedback_no_scope_creep_clean_utility``: the AI-slop gate is
the core enforcement mechanism for the launch — it's the wire that
blocks "harness the power of AI to revolutionize your DJing" from
silently landing in a copy edit.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.launch.check_no_ai_slop import (
    AI_SLOP_BLOCKLIST,
    ANCHOR_PHRASES,
    LAUNCH_COPY_FILES,
    check_launch_copy,
    main,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
LIVE_LAUNCH_DIR = REPO_ROOT / "scripts" / "dayzero" / "launch_copy"


# ---------------------------------------------------------------------------
# Module-level shape tests — pin the public surface of the checker.
# ---------------------------------------------------------------------------


def test_module_imports_cleanly() -> None:
    """Importing the checker exposes the symbols used by CI + sibling scripts."""
    assert callable(main)
    assert callable(check_launch_copy)
    assert isinstance(AI_SLOP_BLOCKLIST, tuple)
    assert isinstance(ANCHOR_PHRASES, tuple)
    assert isinstance(LAUNCH_COPY_FILES, tuple)


def test_blocklist_has_sixteen_canonical_tokens() -> None:
    """CONTEXT §specifics negative list pins exactly 16 tokens, verbatim."""
    assert len(AI_SLOP_BLOCKLIST) == 16, (
        f"blocklist drift: expected 16 tokens, got {len(AI_SLOP_BLOCKLIST)}"
    )
    canon = {
        "leverage",
        "synergize",
        "revolutionize",
        "game-changer",
        "next-generation",
        "cutting-edge",
        "seamless",
        "robust",
        "powerful",
        "intuitive",
        "delightful experience",
        "AI-powered",
        "harness the power",
        "unlock",
        "transformative",
        "paradigm",
    }
    assert canon == set(AI_SLOP_BLOCKLIST), (
        f"blocklist drift: symmetric_diff "
        f"{canon.symmetric_difference(set(AI_SLOP_BLOCKLIST))}"
    )


def test_anchor_phrases_pinned() -> None:
    """The 5 CONTEXT §specifics positive anchors are present in order."""
    assert len(ANCHOR_PHRASES) == 5
    # Flatten for easy presence-check
    flat = {variant for variants in ANCHOR_PHRASES for variant in variants}
    assert "real DJ friend in your ear" in flat
    assert "built by DJs" in flat
    assert "your audio doesn't leave" in flat
    assert ("open source" in flat) or ("open-source" in flat)
    assert "Mac + Windows" in flat


def test_launch_copy_files_pin_five_channels() -> None:
    """The 5 launch-copy channels are pinned in deterministic order."""
    assert LAUNCH_COPY_FILES == (
        "twitter.txt",
        "instagram.txt",
        "linkedin.txt",
        "reddit.txt",
        "discord.txt",
    )


# ---------------------------------------------------------------------------
# Happy path — the live 5-file corpus must pass after Task 2 lands.
# ---------------------------------------------------------------------------


def test_real_launch_copy_passes_lock() -> None:
    """Live launch_copy/ passes all 4 gates after discord.txt + footers land.

    During Task 1 (TDD RED) this test fails because discord.txt is not
    yet drafted and the signature footers are not yet appended. Task 2
    drafts the file + appends footers, flipping this test GREEN.
    """
    rc = check_launch_copy(LIVE_LAUNCH_DIR, quiet=True)
    assert rc == 0, (
        "launch-copy lock check failed — re-run "
        "`uv run python scripts/launch/check_no_ai_slop.py` "
        "for the failing-gate diagnostic"
    )


# ---------------------------------------------------------------------------
# Synthetic corpus helpers — build a known-good 5-file tmp corpus, then
# mutate one axis per negative test.
# ---------------------------------------------------------------------------


def _build_valid_corpus(target: Path) -> None:
    """Write a known-good 5-file corpus into ``target`` (must be empty dir).

    The corpus collectively hits every anchor phrase and carries the
    signature footer in every file. Used as the baseline for negative
    tests — each test mutates ONE axis to assert the gate catches it.
    """
    target.mkdir(parents=True, exist_ok=True)
    footer = (
        "\n---\n"
        "Kaan signature:     ____  (date: ____)\n"
        "Francesco signature: ____  (date: ____)\n"
        "Locked for: v3.0.0-rc1 launch\n"
    )
    (target / "twitter.txt").write_text(
        "vibemix is live — free, open-source AI DJ co-host.\n"
        "Real DJ friend in your ear, not voice-assistant slop.\n"
        "Mac + Windows. Your audio doesn't leave the machine.\n"
        + footer,
        encoding="utf-8",
    )
    (target / "instagram.txt").write_text(
        "vibemix — built by DJs, runs on your machine.\n"
        "Real reactions, never scripted.\n"
        + footer,
        encoding="utf-8",
    )
    (target / "linkedin.txt").write_text(
        "Open-sourcing vibemix today — Bravoh's first OSS release.\n"
        "Local-first, grounded in real audio + screen + MIDI events.\n"
        + footer,
        encoding="utf-8",
    )
    (target / "reddit.txt").write_text(
        "Hey r/DJs — we open-sourced vibemix, a local-first AI co-host.\n"
        "Audio/MIDI/screen never leaves your box. Free, MIT-licensed.\n"
        + footer,
        encoding="utf-8",
    )
    (target / "discord.txt").write_text(
        "vibemix is live — drop it in your rig.\n"
        "Open source, Mac + Windows, github.com/bravoh-ai/vibemix\n"
        + footer,
        encoding="utf-8",
    )


def test_valid_synthetic_corpus_passes(tmp_path: Path) -> None:
    """Sanity check — the synthetic baseline corpus itself passes the gate."""
    _build_valid_corpus(tmp_path)
    rc = check_launch_copy(tmp_path, quiet=True)
    assert rc == 0, (
        "synthetic baseline corpus failed — check _build_valid_corpus helper"
    )


# ---------------------------------------------------------------------------
# Negative cases — each mutates exactly one axis to assert gate isolation.
# ---------------------------------------------------------------------------


def test_negative_slop_token(tmp_path: Path) -> None:
    """A corpus with an AI-slop token (e.g. 'leverage') must fail."""
    _build_valid_corpus(tmp_path)
    twitter = tmp_path / "twitter.txt"
    twitter.write_text(
        twitter.read_text(encoding="utf-8")
        + "\nLeverage vibemix to elevate your set.\n",
        encoding="utf-8",
    )
    rc = check_launch_copy(tmp_path, quiet=True)
    assert rc != 0, "checker missed: 'leverage' slop token present"


def test_negative_missing_anchor(tmp_path: Path) -> None:
    """A corpus missing one anchor phrase across all 5 files must fail.

    Strips the ``real DJ friend in your ear`` anchor from instagram.txt —
    the only file in the synthetic baseline that carries that exact
    spelling ("real DJ friend in your ear" appears in twitter.txt as
    "Real DJ friend in your ear" — case-insensitive match still hits, so
    we strip THAT one instead to actually break the combined-corpus
    anchor check). Defensive: also strip any other occurrence of the
    canonical lowercase spelling across all 5 files.
    """
    _build_valid_corpus(tmp_path)
    for fname in LAUNCH_COPY_FILES:
        fpath = tmp_path / fname
        # Case-insensitive replace by walking the text and substituting
        # any case-variant of the anchor with a benign placeholder.
        text = fpath.read_text(encoding="utf-8")
        import re as _re
        text = _re.sub(
            r"real DJ friend in your ear",
            "real coach in your ear",
            text,
            flags=_re.IGNORECASE,
        )
        fpath.write_text(text, encoding="utf-8")
    rc = check_launch_copy(tmp_path, quiet=True)
    assert rc != 0, (
        "checker missed: 'real DJ friend in your ear' anchor absent from corpus"
    )


def test_negative_missing_signature_footer(tmp_path: Path) -> None:
    """A corpus where one file lacks the signature footer must fail."""
    _build_valid_corpus(tmp_path)
    discord = tmp_path / "discord.txt"
    # Strip the Francesco signature line specifically — Kaan-only is
    # still a half-discharge and engineering's gate must block it.
    discord.write_text(
        discord.read_text(encoding="utf-8").replace(
            "Francesco signature: ____  (date: ____)\n", ""
        ),
        encoding="utf-8",
    )
    rc = check_launch_copy(tmp_path, quiet=True)
    assert rc != 0, "checker missed: discord.txt missing Francesco signature"


def test_negative_missing_channel_file(tmp_path: Path) -> None:
    """A corpus missing one of the 5 channel files must fail."""
    _build_valid_corpus(tmp_path)
    (tmp_path / "discord.txt").unlink()
    rc = check_launch_copy(tmp_path, quiet=True)
    assert rc != 0, "checker missed: discord.txt absent from corpus"


def test_negative_deeply_adverb_construction(tmp_path: Path) -> None:
    """A corpus containing 'deeply <word>' construction must fail."""
    _build_valid_corpus(tmp_path)
    linkedin = tmp_path / "linkedin.txt"
    linkedin.write_text(
        linkedin.read_text(encoding="utf-8")
        + "\nvibemix is deeply integrated with your DJ workflow.\n",
        encoding="utf-8",
    )
    rc = check_launch_copy(tmp_path, quiet=True)
    assert rc != 0, "checker missed: 'deeply integrated' adverb construction"


# ---------------------------------------------------------------------------
# CLI entrypoint — subprocess smoke test.
# ---------------------------------------------------------------------------


def test_cli_entrypoint_runs_on_synthetic_corpus(tmp_path: Path) -> None:
    """Invoking the script via subprocess against a valid corpus returns 0."""
    _build_valid_corpus(tmp_path)
    script = REPO_ROOT / "scripts" / "launch" / "check_no_ai_slop.py"
    result = subprocess.run(
        [sys.executable, str(script), "--dir", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"CLI exit {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )


def test_cli_missing_dir_fails(tmp_path: Path) -> None:
    """CLI returns non-zero when --dir points at an empty/absent directory."""
    script = REPO_ROOT / "scripts" / "launch" / "check_no_ai_slop.py"
    missing = tmp_path / "does-not-exist"
    result = subprocess.run(
        [sys.executable, str(script), "--dir", str(missing), "--quiet"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode != 0
