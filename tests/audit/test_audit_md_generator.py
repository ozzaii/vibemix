"""DEPS-04 — assert generator output shape + idempotence + no slop +
no model literals in the generated AUDIT.md."""

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AUDIT_MD = REPO / "docs" / "AUDIT.md"
GENERATOR = REPO / "scripts" / "audit" / "gen_audit_md.py"

# Mirror of AI_SLOP_BLOCKLIST from scripts/launch/check_no_ai_slop.py.
SLOP_TOKENS = (
    "leverage", "synergize", "revolutionize", "game-changer",
    "next-generation", "cutting-edge", "seamless", "robust", "powerful",
    "intuitive", "delightful experience", "AI-powered", "harness the power",
    "unlock", "transformative", "paradigm",
)

BANNED_MODEL_PATTERNS = (
    "gemini-3-flash",
    "gemini-3-pro",
    "gemini-embedding-",
    "gemini-3.1-flash",
    "gemini-2.5-flash",
    "gemini-3.1-flash-live",
)


def test_audit_md_exists():
    assert AUDIT_MD.is_file(), f"missing {AUDIT_MD}"


def test_audit_md_has_required_sections():
    text = AUDIT_MD.read_text()
    for h in ("## Python", "## Rust", "## JavaScript", "## Decisions", "## GitHub Actions"):
        assert h in text, f"missing section: {h}"


def test_audit_md_has_rubric_preamble():
    text = AUDIT_MD.read_text()
    assert "## Install-Impact rating rubric" in text
    assert "🟢" in text and "🟡" in text and "🔴" in text


def test_audit_md_no_slop_tokens():
    text = AUDIT_MD.read_text().lower()
    hits = [t for t in SLOP_TOKENS if t.lower() in text]
    assert not hits, f"AI-slop tokens found in AUDIT.md: {hits}"


def test_audit_md_no_deeply_adverb():
    text = AUDIT_MD.read_text()
    m = re.search(r"\bdeeply\s+\w+", text)
    assert m is None, f"`deeply <word>` slop in AUDIT.md: {m.group(0) if m else ''}"


def test_audit_md_no_gemini_model_literals():
    text = AUDIT_MD.read_text()
    hits = [p for p in BANNED_MODEL_PATTERNS if p in text]
    assert not hits, f"Gemini model literals found in AUDIT.md: {hits}"


def test_generator_is_idempotent():
    # Run the generator in --check mode; if AUDIT.md drifts, fail.
    result = subprocess.run(
        [sys.executable, str(GENERATOR), "--check"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert result.returncode == 0, f"generator --check failed: {result.stderr}"
