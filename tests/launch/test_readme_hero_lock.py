# SPDX-License-Identifier: Apache-2.0
"""tests/launch/test_readme_hero_lock.py — README hero lock gate.

LAUNCH-01 (Phase 44, Plan 44-01): asserts the live ``README.md`` keeps
the locked hero one-liner verbatim, hits all 5 CONTEXT §specifics anchor
phrases, and contains zero AI-slop blocklist tokens. Catches drift like
a future "harness the power of AI to revolutionize your DJing" PR before
it merges.

Three gates, one test file:
- ``test_real_readme_passes_lock`` — happy path against repo's README.md
- negative cases — synthetic README copies in ``tmp_path`` that violate
  one rule each, asserting non-zero exit code.

Pattern mirrors ``tests/launch/test_storyboard_palette.py``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.launch.check_readme_hero_lock import (
    _AI_SLOP_BLOCKLIST,
    LOCKED_ONE_LINER,
    check_readme,
    main,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "README.md"


# ---------------------------------------------------------------------------
# Module-level shape tests — pin the public surface of the checker.
# ---------------------------------------------------------------------------


def test_module_imports_cleanly() -> None:
    """Importing the checker exposes the four public symbols used by CI."""
    assert callable(main)
    assert callable(check_readme)
    assert isinstance(LOCKED_ONE_LINER, str)
    assert isinstance(_AI_SLOP_BLOCKLIST, tuple)


def test_locked_one_liner_value() -> None:
    """The locked one-liner is the CONTEXT §specifics canonical text."""
    assert LOCKED_ONE_LINER == "the only AI co-host that actually listens to your set"


def test_blocklist_pins_canonical_tokens() -> None:
    """A handful of the CONTEXT §specifics blocklist tokens are present.

    Pinning a subset rather than the whole tuple keeps the test resilient
    to deliberate planner-approved adds/removes while still catching
    accidental removals of the load-bearing slop tokens.
    """
    canon = {
        "leverage",
        "synergize",
        "revolutionize",
        "game-changer",
        "seamless",
        "robust",
        "harness the power",
    }
    assert canon.issubset(set(_AI_SLOP_BLOCKLIST)), (
        f"blocklist drift: missing canonical tokens {canon - set(_AI_SLOP_BLOCKLIST)}"
    )


# ---------------------------------------------------------------------------
# Happy path — the live README must pass.
# ---------------------------------------------------------------------------


def test_real_readme_passes_lock() -> None:
    """Live README.md passes all three gates (locked one-liner + anchors + no slop)."""
    rc = check_readme(README, quiet=True)
    assert rc == 0, (
        "README hero lock check failed — re-run "
        "`uv run python scripts/launch/check_readme_hero_lock.py` "
        "for the failing-gate diagnostic"
    )


# ---------------------------------------------------------------------------
# Negative cases — each synthetic README violates one rule.
# ---------------------------------------------------------------------------


_VALID_README_BODY = (
    "# vibemix\n\n"
    "the only AI co-host that actually listens to your set\n\n"
    "## No AI slop\n\n"
    "vibemix is a real DJ friend in your ear. Built by DJs. Your audio "
    "doesn't leave your machine without you knowing. Open source. "
    "Mac + Windows.\n"
)


def test_negative_missing_locked_one_liner(tmp_path: Path) -> None:
    """A README missing the locked one-liner must fail with non-zero rc."""
    bad = tmp_path / "README.md"
    # Strip the locked one-liner from the otherwise-valid body
    bad.write_text(
        _VALID_README_BODY.replace(LOCKED_ONE_LINER, "Something else entirely"),
        encoding="utf-8",
    )
    rc = check_readme(bad, quiet=True)
    assert rc != 0, "checker missed: locked one-liner absent"


def test_negative_slop_token_present(tmp_path: Path) -> None:
    """A README with an AI-slop token (e.g. 'leverage') must fail."""
    bad = tmp_path / "README.md"
    body_with_slop = (
        _VALID_README_BODY
        + "\nvibemix lets you leverage AI to elevate your set.\n"
    )
    bad.write_text(body_with_slop, encoding="utf-8")
    rc = check_readme(bad, quiet=True)
    assert rc != 0, "checker missed: 'leverage' slop token present"


def test_negative_missing_anchor_phrase(tmp_path: Path) -> None:
    """A README missing one anchor phrase must fail."""
    bad = tmp_path / "README.md"
    # Strip 'built by DJs' specifically
    bad.write_text(
        _VALID_README_BODY.replace("Built by DJs. ", ""),
        encoding="utf-8",
    )
    rc = check_readme(bad, quiet=True)
    assert rc != 0, "checker missed: 'built by DJs' anchor phrase absent"


def test_negative_deeply_adverb_construction(tmp_path: Path) -> None:
    """A README containing 'deeply <word>' construction must fail."""
    bad = tmp_path / "README.md"
    body_deeply = (
        _VALID_README_BODY
        + "\nvibemix is deeply integrated with your workflow.\n"
    )
    bad.write_text(body_deeply, encoding="utf-8")
    rc = check_readme(bad, quiet=True)
    assert rc != 0, "checker missed: 'deeply integrated' adverb construction"


def test_negative_locked_one_liner_appears_twice(tmp_path: Path) -> None:
    """A README with the locked one-liner appearing twice must also fail.

    Duplicate one-liners suggest a copy-paste error during a hero rewrite
    (e.g. someone left the old phrasing AND added the new one). The gate
    pins exactly-one to keep the hero clean.
    """
    bad = tmp_path / "README.md"
    body_double = (
        _VALID_README_BODY
        + "\n\n"
        + LOCKED_ONE_LINER
        + "\n"
    )
    bad.write_text(body_double, encoding="utf-8")
    rc = check_readme(bad, quiet=True)
    assert rc != 0, "checker missed: locked one-liner duplicated"


# ---------------------------------------------------------------------------
# CLI entrypoint — subprocess smoke test against the live README.
# ---------------------------------------------------------------------------


def test_cli_entrypoint_runs() -> None:
    """Invoking the script via subprocess against README.md returns 0."""
    script = REPO_ROOT / "scripts" / "launch" / "check_readme_hero_lock.py"
    result = subprocess.run(
        [sys.executable, str(script), "--readme", str(README)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"CLI exit {result.returncode}\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )


def test_cli_missing_readme_fails(tmp_path: Path) -> None:
    """CLI returns non-zero when --readme points at a missing path."""
    script = REPO_ROOT / "scripts" / "launch" / "check_readme_hero_lock.py"
    missing = tmp_path / "does-not-exist.md"
    result = subprocess.run(
        [sys.executable, str(script), "--readme", str(missing), "--quiet"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode != 0
