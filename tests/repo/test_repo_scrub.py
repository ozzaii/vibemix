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

import io
import re
import subprocess
import sys
import tokenize
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


# -----------------------------------------------------------------------
# DECK-05 — strictly-read-only deck path (Phase 59 Plan 59-03)
# -----------------------------------------------------------------------
#
# The deck-state grounding ladder (DeckState model now; deck poller in Plan
# 59-04) reads the user's Rekordbox collection ONLY via the unencrypted XML
# export. It must NEVER open any DJ-software DB in write mode — a single write
# to a live ``master.db`` corrupts the user's collection (Risk 4, the
# ``master.db`` landmine). This regression pin asserts that hard guarantee
# statically over tracked source so a future commit (the 59-04 poller, or any
# later contributor) cannot silently introduce a write path.
#
# It is the static sibling of the proven runtime dormancy idiom in
# ``tests/library/test_rekordbox.py::test_no_sqlcipher_module_imported_after_load``
# (which asserts the SQLCipher module stays out of ``sys.modules`` after a load)
# — extended below as ``_deck_path_sqlcipher_dormant`` to cover the deck import
# path specifically.

# Patterns banned EVERYWHERE in src/vibemix/ — they can only mean the
# SQLCipher live DJ-DB path was activated (it has no legitimate use anywhere
# in vibemix; the XML export is the only sanctioned Rekordbox read). These
# mirror the existing repo-wide grep gate documented in library/rekordbox.py.
_DJ_DB_FORBIDDEN_GLOBAL: tuple[str, ...] = (
    "Rekordbox6Database",  # the SQLCipher live-DB class — banned wholesale
    "pyrekordbox.db6",     # the SQLCipher db6 subpackage — banned wholesale
)

# Write-mode patterns banned in the DECK PATH only. ``.commit()`` /
# write-mode sqlite URIs are LEGITIMATE for vibemix's OWN internal stores
# (the sqlite-vec embedding cache in library/embed.py / index_sqlite_vec.py /
# search.py writes its own DB — that is not a DJ-software DB). DECK-05 is
# specifically the guarantee that the path which touches the USER's DJ
# collection never opens it in write mode (the master.db landmine, Risk 4).
# So these are scanned only inside the deck path, where any DB touch is, by
# construction, the user's read-only DJ collection.
_DECK_WRITE_FORBIDDEN: tuple[str, ...] = (
    ".commit(",        # a write committed to a DJ-DB connection in the deck path
    "executescript(",  # bulk-write entrypoint against a DJ DB
    'mode=rwc',        # sqlite URI write-create mode
    'mode=rw"',        # sqlite URI write mode (quote-anchored to skip mode=rwc dupes)
    "mode=rw'",        # sqlite URI write mode (single-quote variant)
)

# The deck path: the deck-state grounding modules + the Rekordbox library
# reader they consume. This is exactly the source that may resolve a track
# against the user's DJ collection — the DECK-05 boundary. The 59-04 poller
# (state/deck_poller.py) lands inside this set.
_DECK_PATH_PREFIXES: tuple[str, ...] = (
    "src/vibemix/state/deck",       # deck_state.py, deck_poller.py (59-04), deck_*.py
    "src/vibemix/state/harmonics",  # to_camelot — the key-normalization leg
    "src/vibemix/library/rekordbox.py",  # the XML reader the deck path consumes
)


def _strip_comments_and_docstrings(src_text: str) -> str:
    """Return executable source with ALL comments and string literals removed.

    The plan calls for ``grep -v '^#'`` comment-stripping "so header prose
    cannot self-invalidate the gate" — but the existing grep-gate
    documentation lives in *docstrings* (``library/rekordbox.py:14-18`` and
    ``library/__init__.py:4`` both mention ``Rekordbox6Database`` /
    ``pyrekordbox.db6`` *to document the ban*). A bare line grep would only
    strip ``#`` lines, leaving those docstring mentions to falsely trip the
    gate. Tokenize-based stripping is the robust generalization: it removes
    both COMMENT and STRING tokens, so prose that *documents* the ban (in a
    comment or a docstring) is invisible to the scan, while a real
    ``from pyrekordbox.db6 import Rekordbox6Database`` statement (a NAME/OP
    token sequence) is not.

    Falls back to the line-based ``grep -v '^#'`` discipline if a file fails
    to tokenize (never silently passes a file).
    """
    try:
        kept: list[tokenize.TokenInfo] = []
        for tok in tokenize.generate_tokens(io.StringIO(src_text).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                # Replace a stripped STRING with an empty-string literal so a
                # docstring/string mention vanishes, but token POSITIONS
                # (untokenize uses them) keep surrounding code adjacency —
                # e.g. ``db.commit()`` stays ``db.commit()``, never
                # ``db . commit ( )``, so substring patterns like ``.commit(``
                # still match a real write call.
                if tok.type == tokenize.STRING:
                    kept.append(tok._replace(string='""'))
                continue
            kept.append(tok)
        return tokenize.untokenize(kept)
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        # Conservative fallback: strip only full-line ``#`` comments
        # (the plan's literal ``grep -v '^#'`` discipline).
        return "\n".join(
            ln for ln in src_text.splitlines() if not ln.lstrip().startswith("#")
        )


def _src_python_files() -> list[str]:
    """Tracked .py files under src/vibemix/ (the deck path lives here)."""
    return [
        p
        for p in _git_ls_files()
        if p.startswith("src/vibemix/") and p.endswith(".py")
    ]


def _is_deck_path(path: str) -> bool:
    """True if a tracked path is part of the DECK-05 deck path."""
    return path.startswith(_DECK_PATH_PREFIXES)


def test_deck_readonly_detector_catches_a_write_pattern() -> None:
    """Positive control — the stripper+scan WOULD catch a write-mode open.

    Without this, a stripper bug that accidentally blanks everything would
    make the gate vacuously pass. A synthetic source string carrying a real
    ``from pyrekordbox.db6 import Rekordbox6Database`` + ``.commit()`` must be
    flagged AFTER comment/docstring stripping; the same strings inside a
    docstring must NOT be flagged (header prose can't self-invalidate the
    gate).
    """
    offending = (
        '"""Docstring mentioning Rekordbox6Database to document the ban."""\n'
        "from pyrekordbox.db6 import Rekordbox6Database\n"
        "db = Rekordbox6Database()\n"
        "db.commit()\n"
    )
    stripped = _strip_comments_and_docstrings(offending)
    global_hits = [pat for pat in _DJ_DB_FORBIDDEN_GLOBAL if pat in stripped]
    write_hits = [pat for pat in _DECK_WRITE_FORBIDDEN if pat in stripped]
    assert "Rekordbox6Database" in global_hits, (
        f"detector failed to flag the SQLCipher live-DB class; "
        f"hits={global_hits}"
    )
    assert ".commit(" in write_hits, (
        "detector failed to flag a committed write — tokenize stripping must "
        f"preserve ``db.commit()`` adjacency; hits={write_hits}"
    )

    # The docstring-only mention must be invisible after stripping.
    doc_only = '"""We never use Rekordbox6Database here — XML only."""\n' "x = 1\n"
    doc_stripped = _strip_comments_and_docstrings(doc_only)
    assert "Rekordbox6Database" not in doc_stripped, (
        "stripper left a docstring mention in place — header prose would "
        "self-invalidate the gate"
    )


def test_deck_readonly() -> None:
    """DECK-05 — no DJ-software DB is ever opened in write mode.

    Two-tier scan over EXECUTABLE source (comments + docstrings stripped):

    1. The SQLCipher live-DB class/subpackage (``Rekordbox6Database`` /
       ``pyrekordbox.db6``) is banned EVERYWHERE in src/vibemix/ — it has no
       legitimate use anywhere; the XML export is the only sanctioned read.
       This mirrors the existing repo-wide grep gate.
    2. Write-mode patterns (``.commit()`` / ``executescript()`` / sqlite
       write-mode URI) are banned in the DECK PATH only — vibemix's OWN
       internal sqlite-vec embedding cache legitimately commits to its own
       DB; DECK-05 is the narrower guarantee that the path touching the
       USER's DJ collection never writes it (the master.db landmine, Risk 4).

    Comment/docstring stripping is essential: the grep-gate documentation in
    ``library/rekordbox.py`` / ``library/__init__.py`` mentions the banned
    strings *to document the ban*. Those prose mentions must not trip the
    gate; a real write statement must. This pin will fail if the 59-04
    poller — or any future commit — introduces a DJ-DB write path.
    """
    offenders: dict[str, list[str]] = {}
    for path in _src_python_files():
        full = REPO_ROOT / path
        if not full.is_file():
            continue
        stripped = _strip_comments_and_docstrings(
            full.read_text(encoding="utf-8", errors="replace")
        )
        hits = [pat for pat in _DJ_DB_FORBIDDEN_GLOBAL if pat in stripped]
        if _is_deck_path(path):
            hits += [pat for pat in _DECK_WRITE_FORBIDDEN if pat in stripped]
        if hits:
            offenders[path] = hits
    assert not offenders, (
        "DECK-05 read-only guarantee VIOLATED — DJ-DB write-mode / SQLCipher "
        f"live-DB pattern found in executable source: {offenders}. The deck "
        "path is strictly read-only (XML export only); never open a DJ-software "
        "DB in write mode (master.db corruption landmine, Risk 4)."
    )


def test_deck_path_sqlcipher_dormant() -> None:
    """DECK-05 runtime sibling — importing the deck path loads no SQLCipher.

    Extends the proven subprocess-dormancy idiom from
    ``test_no_sqlcipher_module_imported_after_load``: a fresh interpreter
    imports the deck-state module surface and asserts no ``*sqlcipher*``
    module landed in ``sys.modules``. As the deck path grows (the 59-04
    poller imports added here), this stays the runtime guarantee that the
    read-only XML path never activates the SQLCipher binary.
    """
    script = (
        "import sys\n"
        "import vibemix.state.deck_state  # noqa: F401\n"
        "import vibemix.state.harmonics  # noqa: F401\n"
        "import vibemix.library  # the sanctioned XML library surface\n"
        "leaks = sorted(m for m in sys.modules if 'sqlcipher' in m.lower())\n"
        "print('LEAKED:' + ','.join(leaks) if leaks else 'DORMANT')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO_ROOT,
        env={**__import__("os").environ, "PYTHONPATH": str(REPO_ROOT / "src")},
    )
    assert result.stdout.strip() == "DORMANT", (
        f"SQLCipher path leaked during deck-path import — stdout: "
        f"{result.stdout!r}; stderr: {result.stderr!r}"
    )


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
