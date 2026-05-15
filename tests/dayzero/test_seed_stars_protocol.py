"""Tests for `scripts/dayzero/seed_stars.md` — Pitfall P59 enforcement.

Asserts:
1. The anti-pattern phrase appears only inside a Forbidden / NOT context
   (never as a recommended action).
2. All four aligned-community pools are listed by name.
3. The Day-1 log path is gitignored.
"""
from __future__ import annotations

import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[2]
SEED_STARS_MD = ROOT / "scripts" / "dayzero" / "seed_stars.md"
GITIGNORE = ROOT / ".gitignore"
SEED_LOG_PATH = "scripts/dayzero/seed_stars.log"


def test_seed_stars_md_present():
    assert SEED_STARS_MD.is_file()
    assert SEED_STARS_MD.stat().st_size > 500, "Protocol doc must be substantive"


def test_seed_stars_md_no_random_friend_antipattern():
    """The phrase 'random friend-favors' must appear ONLY inside a
    Forbidden / NOT / Anti-pattern context.

    Walk every line that mentions the anti-pattern keyword and verify
    one of the negation markers appears within a 6-line window around it
    (above OR same line). Any unguarded positive mention fails.
    """
    text = SEED_STARS_MD.read_text()
    lines = text.splitlines()
    anti_pat = re.compile(r"random\s+friend-favou?rs?", re.IGNORECASE)
    guard_pat = re.compile(
        r"(forbidden|anti-pattern|antipattern|\bnot\b|never|off-limits|p59)",
        re.IGNORECASE,
    )

    hits = [(i, ln) for i, ln in enumerate(lines) if anti_pat.search(ln)]
    assert hits, "Anti-pattern keyword must appear at least once (P59 reminder)"

    for i, ln in hits:
        window = "\n".join(lines[max(0, i - 6) : i + 1])
        assert guard_pat.search(window), (
            f"Anti-pattern keyword on line {i + 1} is missing a guard "
            f"(Forbidden / NOT / Anti-pattern / P59) within 6 lines above. "
            f"Line: {ln!r}"
        )


def test_seed_stars_md_aligned_pools_listed():
    """All four community pools must be listed by name."""
    text = SEED_STARS_MD.read_text()
    for keyword in ("Bravoh", "DJ network", "ARRAY", "Contributor circle"):
        assert keyword in text, f"Missing pool keyword: {keyword!r}"


def test_seed_stars_md_mentions_p59():
    """P59 callout must be present so future contributors can trace the rule."""
    text = SEED_STARS_MD.read_text()
    assert "P59" in text


def test_seed_stars_log_is_gitignored():
    """Day-1 log path must be in .gitignore — contains personal contact info."""
    text = GITIGNORE.read_text()
    assert SEED_LOG_PATH in text, (
        f"{SEED_LOG_PATH} must be listed in .gitignore "
        "to avoid leaking personal handles."
    )


def test_seed_stars_md_has_reality_check():
    """The doc should include a reality-check section (defence-in-depth
    against creeping friend-favour requests)."""
    text = SEED_STARS_MD.read_text()
    assert "Reality-check" in text or "reality-check" in text.lower()
