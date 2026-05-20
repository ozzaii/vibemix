# SPDX-License-Identifier: Apache-2.0
"""Phase 19 Plan 19-01 — Repo hygiene CI gate (GH-18).

These tests are the contract that locks the post-scrub state of the repo:
- Five scratch files removed from root (``_test_*.py`` + ``sprite-*.png``).
- No tracked ``*.bak`` files (the lone POC ``.bak`` was retired 2026-05-20).
- No tracked ``.env`` files.
- All tracked files >1 MB are LFS-tracked, except ``mascot.html``.
- ``.gitattributes`` declares the ``*.glb filter=lfs`` rule.
- The root POC variant zoo (``cohost*.py``, ``run_v*.sh``, ``generate_bat.py``,
  ``test_voice.py``) is RETIRED — logic lifted into the ``vibemix`` package
  (Phases 2-13), variants pruned to end the canonical-file confusion.
  ``mascot.html`` (live overlay) and ``mocks/`` (UI contracts) survive.
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

# POC reference files have been RETIRED (2026-05-20). Their logic was
# lifted wholesale into the ``vibemix`` package (Phases 2-13) and the
# variant zoo (cohost.py / _v2 / _lk / _v3 / _v4 + run scripts) was pruned
# to end the "which file is canonical?" confusion. ``mascot.html`` is the
# one survivor — it is still the live overlay wired into the package
# runtime (vibemix.runtime.ws_bus) and CI (mascot-audit), not a POC.
POC_EXEMPT: set[str] = {
    "mascot.html",
}

# Retired root-level variant files — the sentinel test below asserts these
# stay gone so a stray ``git add`` can't resurrect the confusion.
RETIRED_POC_FILES: set[str] = {
    "cohost.py",
    "cohost_v2.py",
    "cohost_lk.py",
    "cohost_v3.py",
    "cohost_v4.py",
    "cohost.streaming.py.bak",
    "run.sh",
    "run_lk.sh",
    "run_v2.sh",
    "run_v3.sh",
    "run_v4.sh",
    "generate_bat.py",
    "test_voice.py",
}

POC_EXEMPT_DIRS: set[str] = {"mocks"}

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


def test_no_bak_files_are_tracked() -> None:
    """No ``.bak`` files are tracked — the lone POC ``.bak`` was retired
    2026-05-20 and ``.gitignore`` carries the ``*.bak`` rule."""
    bak_files = [p for p in _git_ls_files() if p.endswith(".bak")]
    unexpected = [p for p in bak_files if Path(p).name not in POC_EXEMPT]
    assert not unexpected, (
        f"Unexpected tracked .bak files: {unexpected}. POC variants were "
        "retired; no .bak should be tracked."
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


def test_retired_poc_files_stay_gone() -> None:
    """The root-level POC variant zoo is retired — sentinel against a stray
    ``git add`` resurrecting the "which file is canonical?" confusion.

    Logic was lifted into the ``vibemix`` package (Phases 2-13); the variants
    were pruned 2026-05-20. ``mascot.html`` and ``mocks/`` are NOT POC variants
    (live overlay + UI design contracts) and must survive."""
    for name in RETIRED_POC_FILES:
        path = REPO_ROOT / name
        assert not path.exists(), (
            f"Retired POC variant {name} is back at repo root — it was pruned "
            "2026-05-20 once its logic landed in the vibemix package. Do not "
            "resurrect the variant zoo."
        )
    assert (REPO_ROOT / "mascot.html").exists(), (
        "mascot.html missing — it is the live overlay (vibemix.runtime.ws_bus "
        "+ CI mascot-audit), not a retired POC, and must survive."
    )
    assert (REPO_ROOT / "mocks").is_dir(), "mocks/ UI design-contract dir missing"


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
