# SPDX-License-Identifier: Apache-2.0
"""Phase 35 Plan 35-04 — Anti-slop grep gate for scripts/demo_film/.

Pitfall P58: no AI voiceover. This test ensures no source file under
scripts/demo_film/ references a known AI-TTS service.

We grep .sh / .py / .json / .ts / .js — NOT .md. The .md docs (vo_policy.md
in particular) intentionally enumerate the forbidden tokens to make the
policy unambiguous.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_FILM_DIR = REPO_ROOT / "scripts" / "demo_film"

FORBIDDEN_TOKENS = (
    "elevenlabs",
    "openai",
    "gemini-tts",
    "tts.googleapis",
    "synth.voice",
    "ai-voiceover",
    "synthesize_speech",
)

# Files that ARE allowed to mention the tokens because they exist solely
# to deny them. The vo_policy.md is .md so it's already excluded by the
# extension filter; cut.sh is .sh and DOES carry the deny-list. We allow
# cut.sh to mention the tokens since they appear in a CASE expression
# that REJECTS them (belt-and-braces local check).
ALLOWED_PATHS = {
    DEMO_FILM_DIR / "cut.sh",  # tokens appear in deny CASE
}

SOURCE_EXTS = {".sh", ".py", ".json", ".ts", ".js"}


def _iter_source_files() -> list[Path]:
    if not DEMO_FILM_DIR.is_dir():
        return []
    out: list[Path] = []
    for path in DEMO_FILM_DIR.rglob("*"):
        if path.is_file() and path.suffix in SOURCE_EXTS:
            out.append(path)
    return sorted(out)


def test_no_ai_vo_in_scripts() -> None:
    """No forbidden TTS token appears in scripts/demo_film/ source.

    cut.sh is allowlisted because its tokens appear inside a CASE that
    REJECTS them (deny-list, not a call site).
    """
    pattern = re.compile(
        "|".join(re.escape(tok) for tok in FORBIDDEN_TOKENS),
        re.IGNORECASE,
    )
    violations: list[tuple[Path, str, str]] = []
    for path in _iter_source_files():
        if path in ALLOWED_PATHS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_num, line in enumerate(text.splitlines(), start=1):
            m = pattern.search(line)
            if m:
                violations.append((path.relative_to(REPO_ROOT), str(line_num), line.strip()))
    assert not violations, (
        f"Pitfall P58 violation — AI-VO tokens found in demo_film/:\n"
        + "\n".join(f"  - {p}:{n}: {l}" for p, n, l in violations)
    )


def test_vo_policy_doc_exists() -> None:
    """The policy doc must exist + state the no-AI-VO rule."""
    policy = DEMO_FILM_DIR / "vo_policy.md"
    assert policy.is_file(), f"missing {policy}"
    text = policy.read_text(encoding="utf-8").lower()
    # Either "no ai" or "no voiceover" or "no vo" — the canonical phrasings.
    assert any(
        marker in text for marker in ("no ai", "no voiceover", "no vo")
    ), "vo_policy.md must state 'no AI / no VO' rule explicitly"


def test_three_beat_doc_exists() -> None:
    """The 3-beat structure doctrine doc must exist."""
    doc = DEMO_FILM_DIR / "3beat_structure.md"
    assert doc.is_file(), f"missing {doc}"
    text = doc.read_text(encoding="utf-8").lower()
    for beat in ("beat a", "beat b", "beat c"):
        assert beat in text, f"3beat_structure.md must label {beat!r}"


def test_recording_protocol_doc_exists() -> None:
    doc = DEMO_FILM_DIR / "recording_protocol.md"
    assert doc.is_file(), f"missing {doc}"


def test_asset_pipeline_doc_exists() -> None:
    doc = REPO_ROOT / "docs" / "asset_pipeline.md"
    assert doc.is_file(), f"missing {doc}"
    text = doc.read_text(encoding="utf-8").lower()
    # Must mention the pipeline pieces.
    for piece in ("meshy", "mixamo", "draco", "ktx2", "rokoko"):
        assert piece in text, f"asset_pipeline.md must mention {piece!r}"
