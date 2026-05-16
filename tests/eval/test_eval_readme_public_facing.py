# SPDX-License-Identifier: Apache-2.0
"""Plan 42-06 Task 2 — eval/README.md public-facing contract tests (GATE-09).

Pins the section-coverage and threshold-mirror invariants for the public-
facing eval doc shipped by Plan 42-06. README is the only OSS-contributor
surface for the v3.0 hybrid hallucination gate, so drift between the doc
and ``eval/THRESHOLD-LOCK.md`` is a release blocker.

These tests are paired with ``test_eval_readme_redacts_ear_test_content.py``
(privacy contract). Together they pin:
    - public contract: every required section is present
    - threshold mirror: every locked numeric value appears verbatim
    - rubric-leak guard: no inline prompt or rubric body content
    - privacy contract: no ear-test log textual content leaks to public doc
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "eval" / "README.md"
LOCK = REPO_ROOT / "eval" / "THRESHOLD-LOCK.md"
RUBRIC_PRO = REPO_ROOT / "eval" / "rubrics" / "judge_pro.md"
RUBRIC_FLASH = REPO_ROOT / "eval" / "rubrics" / "judge_flash.md"


@pytest.fixture(scope="module")
def readme_text() -> str:
    return README.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def locked_thresholds() -> dict[str, float]:
    """Load the locked threshold dict from THRESHOLD-LOCK.md frontmatter."""
    from scripts.eval.threshold_lock import parse_threshold_lock_frontmatter

    parsed = parse_threshold_lock_frontmatter(LOCK)
    return parsed["thresholds"]


# ---------------------------------------------------------------------------
# Existence + size
# ---------------------------------------------------------------------------


def test_readme_exists():
    assert README.is_file(), f"public README missing: {README}"


def test_readme_under_350_lines(readme_text: str):
    """Public docs stay scannable — single-page mental load."""
    line_count = len(readme_text.splitlines())
    assert line_count <= 350, (
        f"eval/README.md is {line_count} lines; budget is ≤ 350 (single-page contributor doc)."
    )


# ---------------------------------------------------------------------------
# Section coverage — hybrid regime
# ---------------------------------------------------------------------------


def test_readme_documents_hybrid_regime(readme_text: str):
    """Body must name both lanes + the autonomous-proxy + ear-test handles."""
    text = readme_text.lower()
    assert "fast" in text, "missing Fast-lane reference"
    assert "slow" in text, "missing Slow-lane reference"
    assert "autonomous proxy" in text, "missing 'autonomous proxy' phrase"
    assert "ear-test" in text, "missing 'ear-test' phrase"


def test_readme_documents_2_judge_architecture(readme_text: str):
    """Both judge names appear so contributors can locate the rubrics."""
    pro_present = ("Gemini 3 Pro" in readme_text) or ("gemini-3-pro" in readme_text)
    flash_present = ("Gemini 3 Flash" in readme_text) or ("gemini-3-flash" in readme_text)
    assert pro_present, "missing Gemini 3 Pro reference"
    assert flash_present, "missing Gemini 3 Flash reference"


# ---------------------------------------------------------------------------
# Threshold mirroring
# ---------------------------------------------------------------------------


def test_readme_mirrors_f1_threshold(readme_text: str):
    """The 5 locked threshold numerals must appear literally in README."""
    for token in ("0.80", "0.65", "0.40", "0.15", "0.70"):
        assert token in readme_text, f"missing threshold value: {token}"


@pytest.mark.parametrize(
    "key",
    [
        "f1_min",
        "substance_min",
        "cited_cosine_min",
        "bypass_max",
        "per_genre_f1_min",
    ],
)
def test_readme_threshold_values_match_lock_file(
    readme_text: str, locked_thresholds: dict[str, float], key: str
):
    """Per-key drift detection between THRESHOLD-LOCK.md and README."""
    value = locked_thresholds[key]
    # Normalize to 2-decimal-place string (matches README's table formatting).
    formatted = f"{value:.2f}"
    assert formatted in readme_text, (
        f"locked threshold {key}={formatted} not mirrored in eval/README.md "
        f"(drift between THRESHOLD-LOCK.md and the public doc)."
    )


# ---------------------------------------------------------------------------
# Reproducibility invocation
# ---------------------------------------------------------------------------


def test_readme_documents_reproducibility_invocation(readme_text: str):
    """OSS contributors must be able to copy-paste the proxy-gate runner."""
    assert "replay_harness.py" in readme_text or "replay_harness" in readme_text, (
        "missing replay_harness reference"
    )
    assert "--threshold-lock" in readme_text, "missing --threshold-lock CLI flag"
    assert "--corpus" in readme_text, "missing --corpus CLI flag"


# ---------------------------------------------------------------------------
# Cross-links
# ---------------------------------------------------------------------------


def test_readme_cross_links_protocol_doc(readme_text: str):
    assert "EAR-TEST-PROTOCOL.md" in readme_text


def test_readme_cross_links_decision_log(readme_text: str):
    assert "P85-OVERRIDE-RETIRED.md" in readme_text


# ---------------------------------------------------------------------------
# Anti-feature carveouts + redaction principle
# ---------------------------------------------------------------------------


def test_readme_documents_anti_feature_carveouts(readme_text: str):
    """Anti-feature section must announce itself + name at least one carveout."""
    lowered = readme_text.lower()
    has_anti = ("anti-feature" in lowered) or ("not building" in lowered) or ("NOT building" in readme_text)
    assert has_anti, "missing 'anti-feature' / 'NOT building' section signal"
    carveouts = ("cross-dj" in lowered) or ("single-dj" in lowered) or ("gamif" in lowered)
    assert carveouts, "missing at least one carveout (cross-DJ / single-DJ / gamification)"


def test_readme_documents_redaction_principle(readme_text: str):
    """README must self-describe the privacy-redaction contract (positive assertion)."""
    lowered = readme_text.lower()
    has_redact = ("redacted" in lowered) or ("redact" in lowered) or ("redacts" in lowered)
    assert has_redact, "missing 'redact' / 'REDACTED' principle statement"
    assert "ear-test" in lowered, "missing 'ear-test' phrase paired with redaction principle"


# ---------------------------------------------------------------------------
# Rubric / prompt leak guard
# ---------------------------------------------------------------------------


def _first_meaningful_chunk(rubric_path: Path, *, n_chars: int = 40) -> str:
    """Return first ~n_chars of meaningful body content past any YAML frontmatter.

    Used as a sentinel for verbatim leakage detection — if the README slurped in
    the rubric body, this prefix would appear verbatim.
    """
    text = rubric_path.read_text(encoding="utf-8")
    # Strip YAML frontmatter if present (delimited by --- ... ---).
    fm_match = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.DOTALL)
    if fm_match:
        text = text[fm_match.end():]
    # Skip blank and HTML-comment-only lines; collect first meaningful chunk.
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("<!--"):
            continue
        # Skip pure markdown headers if they're short — we want substantive body.
        lines.append(stripped)
        if sum(len(line_text) for line_text in lines) >= n_chars:
            break
    body = " ".join(lines)
    return body[:n_chars]


def test_readme_no_inline_rubric_or_prompt_bodies(readme_text: str):
    """Smoke check: rubric body content does not leak into README verbatim.

    Sentinels are derived from the actual rubric files (judge_pro.md +
    judge_flash.md) so the test self-updates when the rubrics evolve. Avoids
    a hardcoded prompt-string maintenance burden.
    """
    LEAK_TOKENS = [
        _first_meaningful_chunk(RUBRIC_PRO),
        _first_meaningful_chunk(RUBRIC_FLASH),
    ]
    for token in LEAK_TOKENS:
        # Sanity: derived token must be non-trivial.
        assert len(token) >= 20, (
            f"derived leak-sentinel too short ({len(token)} chars); "
            f"rubric file may be malformed: {token!r}"
        )
        assert token not in readme_text, (
            f"rubric body content leaked into public README: {token!r}"
        )
