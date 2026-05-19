# SPDX-License-Identifier: Apache-2.0
"""Phase 19 Plan 19-01 — Repo hygiene CI gate (GH-18).

These tests are the contract that locks the post-scrub state of the repo:
- Five scratch files removed from root (``_test_*.py`` + ``sprite-*.png``).
- ``cohost.streaming.py.bak`` is the only tracked ``*.bak`` file (POC exempt).
- No tracked ``.env`` files.
- All tracked files >1 MB are LFS-tracked, except the POC reference set.
- ``.gitattributes`` declares the ``*.glb filter=lfs`` rule.
- POC reference files (``cohost*.py``, ``mascot.html``, ``run_v*.sh``,
  ``generate_bat.py``, ``fillers/``, ``mocks/``) survive untouched —
  per CLAUDE.md "POC = reference, devour it".
- ``.gitignore`` carries the Phase 19 hygiene block.

Style follows ``tests/test_license.py`` (the repo-level test template).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SCRATCH_NAMES = {"_test_multimodal.py", "_test_tts.py"}
SPRITE_NAMES = {"sprite-1.png", "sprite-2.png", "sprite-3.png"}

# POC reference files survive the scrub per CLAUDE.md "POC = reference,
# devour it". These are *trusted intuition to port wholesale*, not legacy
# to preserve verbatim — but they stay in the repo until Phase 2-13 finish
# lifting their logic into the new package shape.
POC_EXEMPT: set[str] = {
    "cohost.py",
    "cohost_v2.py",
    "cohost_lk.py",
    "cohost_v3.py",
    "cohost_v4.py",
    "cohost.streaming.py.bak",
    "mascot.html",
    "run.sh",
    "run_lk.sh",
    "run_v2.sh",
    "run_v3.sh",
    "run_v4.sh",
    "generate_bat.py",
}

POC_EXEMPT_DIRS: set[str] = {"fillers", "mocks", "archive"}

# Globs in ``.gitattributes`` that route files through git-lfs. Tracked
# files matching any of these patterns are EXEMPT from the >1 MB cap.
# NOTE: matched against ``Path(path).name`` — filename-only patterns.
LFS_TRACKED_GLOBS: set[str] = {
    "*.glb",
    # Phase 28 Plan 02 — synthetic parity fixture (see .gitattributes).
    "synthetic_embeddings.npy",
    "synthetic_queries.json",
}

ONE_MB = 1024 * 1024


def _git_ls_files() -> list[str]:
    """Return the list of tracked file paths (POSIX, repo-root-relative)."""
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in out.stdout.splitlines() if line]


def _matches_any_glob(path: str, globs: set[str]) -> bool:
    """True if the path matches any of the given filename-only globs."""
    name = Path(path).name
    return any(Path(name).match(g) for g in globs)


def _is_poc_exempt(path: str) -> bool:
    """True if the path is a POC reference file or under a POC dir."""
    p = Path(path)
    if p.name in POC_EXEMPT:
        return True
    return bool(p.parts) and p.parts[0] in POC_EXEMPT_DIRS


# -----------------------------------------------------------------------
# Behavior tests (8 invariants)
# -----------------------------------------------------------------------


def test_no_scratch_test_files_at_root() -> None:
    """``_test_multimodal.py`` and ``_test_tts.py`` are gone."""
    for name in SCRATCH_NAMES:
        path = REPO_ROOT / name
        assert not path.exists(), (
            f"Scratch file {name} is still at repo root — should be deleted "
            "per CONTEXT Area 5."
        )


def test_no_sprite_files_at_root() -> None:
    """The three 2.3 MB mascot sprite scratches are gone."""
    for name in SPRITE_NAMES:
        path = REPO_ROOT / name
        assert not path.exists(), (
            f"Sprite scratch {name} is still at repo root — should be "
            "deleted per CONTEXT Area 5."
        )


def test_only_poc_bak_file_is_tracked() -> None:
    """``cohost.streaming.py.bak`` is the only tracked .bak file (POC)."""
    bak_files = [p for p in _git_ls_files() if p.endswith(".bak")]
    unexpected = [p for p in bak_files if Path(p).name not in POC_EXEMPT]
    assert not unexpected, (
        f"Unexpected tracked .bak files: {unexpected}. Only "
        "cohost.streaming.py.bak (POC reference) is exempt."
    )


def test_no_env_files_are_tracked() -> None:
    """No ``.env`` / ``.env.local`` style files are tracked.

    ``.env.example`` is allowed (it's a template, not a secret).
    """
    tracked = _git_ls_files()
    bad = [
        p
        for p in tracked
        if Path(p).name in {".env", ".env.local"}
        or (
            Path(p).name.startswith(".env.")
            and Path(p).name != ".env.example"
        )
    ]
    assert not bad, (
        f"Tracked env files leak secrets: {bad}. Move to .env.example "
        "(template only) and add to .gitignore."
    )


def test_no_tracked_file_above_one_mb_outside_lfs() -> None:
    """All tracked files >1 MB are LFS-tracked or POC-exempt."""
    offenders: list[tuple[str, int]] = []
    for path in _git_ls_files():
        if _is_poc_exempt(path):
            continue
        if _matches_any_glob(path, LFS_TRACKED_GLOBS):
            continue
        full = REPO_ROOT / path
        if not full.is_file():
            continue
        size = full.stat().st_size
        if size > ONE_MB:
            offenders.append((path, size))
    assert not offenders, (
        f"Tracked files >1 MB outside LFS: {offenders}. Track via "
        "git-lfs (add a pattern to .gitattributes) or move out of repo."
    )


def test_gitattributes_no_lfs_rules() -> None:
    """git-lfs removed 2026-05-19 — `.gitattributes` carries no LFS routing.

    History demoted via `git lfs migrate export --everything`. Working-tree
    total (~23 MB) fits comfortably under GitHub's 100 MB per-file hard
    limit, so the external git-lfs dependency is no longer required (and
    its data-pack billing model was exhausting at 778 unpushed commits).
    """
    path = REPO_ROOT / ".gitattributes"
    assert path.exists(), ".gitattributes missing at repo root"
    text = path.read_text()
    pattern = re.compile(r"^\s*[^#].*filter=lfs", re.MULTILINE)
    assert not pattern.search(text), (
        ".gitattributes carries an LFS routing rule; expected none after the "
        "2026-05-19 demotion."
    )


def test_poc_reference_files_still_present() -> None:
    """The POC reference set survives the scrub — sentinel against over-delete."""
    sentinels = [
        "cohost.py",
        "cohost_v2.py",
        "cohost_lk.py",
        "mascot.html",
        "run_v2.sh",
        "generate_bat.py",
    ]
    for name in sentinels:
        path = REPO_ROOT / name
        assert path.exists(), (
            f"POC reference file {name} is missing — Plan 19-01 must not "
            "delete POC reference material (CLAUDE.md 'POC = reference, "
            "devour it')."
        )
    assert (REPO_ROOT / "mocks").is_dir(), "mocks/ POC reference dir missing"


def test_gitignore_carries_phase19_hygiene_block() -> None:
    """``.gitignore`` extends with Phase 19 hygiene patterns."""
    path = REPO_ROOT / ".gitignore"
    assert path.exists(), ".gitignore missing"
    text = path.read_text()
    required_patterns = [
        "*.bak",
        "v5-*.png",
        ".claude/worktrees/",
        ".playwright-mcp/",
        "recordings/",
    ]
    missing = [pat for pat in required_patterns if pat not in text]
    assert not missing, (
        f".gitignore missing Phase 19 hygiene patterns: {missing}"
    )
    # docs/assets whitelist comment + the un-ignore rule
    assert "!docs/assets/" in text or "!docs/assets/**" in text, (
        ".gitignore should explicitly whitelist docs/assets/ so the "
        "Phase 19 hero.png + architecture.svg survive future ignores."
    )
