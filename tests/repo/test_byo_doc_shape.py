# SPDX-License-Identifier: Apache-2.0
"""Phase 69 Plan 69-02 — anti-rot shape test for docs/byo-key.md.

OSS-03 invariant: the BYO-Gemini-key path is a first-class contributor
surface, not a hidden escape hatch. This gate ensures docs/byo-key.md
keeps the 6 required sections + the 2 env var names + the Google
AI Studio key URL — deletion or rename of any of those signals
contributor-doc rot and fails CI red.

Pairs with tests/repo/test_oss_presence.py (Plan 69-01 OSS-01 gate);
together they pin the v7.0 OSS contributor surface end-to-end.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BYO_DOC = REPO_ROOT / "docs" / "byo-key.md"

REQUIRED_SECTIONS: list[str] = [
    "## Why BYO",
    "## Get a Gemini API key",
    "## Set the env vars",
    "## Verify",
    "## Switch back to Bravoh proxy",
    "## Privacy & Limits",
]

REQUIRED_ENV_VARS: list[str] = ["VIBEMIX_LLM_MODE", "GEMINI_API_KEY"]
REQUIRED_URL: str = "https://aistudio.google.com/apikey"
_MIN_BYTES: int = 200


def test_byo_doc_exists() -> None:
    """docs/byo-key.md exists at the canonical path and is non-trivial."""
    assert BYO_DOC.exists(), (
        f"Missing required BYO doc at {BYO_DOC.relative_to(REPO_ROOT)}. "
        "v7.0 OSS-03 requires this file at docs/byo-key.md. "
        "See Plan 69-02 Task 1."
    )
    size = BYO_DOC.stat().st_size
    assert size >= _MIN_BYTES, (
        f"docs/byo-key.md is suspiciously small ({size} bytes < {_MIN_BYTES}); "
        "placeholder? See Plan 69-02 Task 1."
    )


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_byo_doc_has_required_sections(section: str) -> None:
    """Each required H2 section appears exactly once in docs/byo-key.md.

    Exact-count == 1 (not >= 1) is deliberate: a duplicated header signals
    a copy-paste accident or a stale draft that survived a refactor, and
    we want the gate to catch both deletion and duplication.
    """
    text = BYO_DOC.read_text(encoding="utf-8")
    count = text.count(section)
    assert count == 1, (
        f"docs/byo-key.md missing or duplicate required section header: "
        f"{section!r} (found {count}, expected 1). "
        "v7.0 OSS-03 requires all 6 sections in order. "
        "See Plan 69-02 Task 1."
    )


@pytest.mark.parametrize("env_var", REQUIRED_ENV_VARS)
def test_byo_doc_names_env_vars(env_var: str) -> None:
    """Both env vars the BYO path depends on are named in docs/byo-key.md."""
    text = BYO_DOC.read_text(encoding="utf-8")
    assert env_var in text, (
        f"docs/byo-key.md must document the {env_var} env var. "
        "See src/vibemix/runtime/session_loop.py:842 and Plan 69-02 Task 1."
    )


def test_byo_doc_names_aistudio_url() -> None:
    """The Google AI Studio key URL is named verbatim in docs/byo-key.md."""
    text = BYO_DOC.read_text(encoding="utf-8")
    assert REQUIRED_URL in text, (
        f"docs/byo-key.md must reference {REQUIRED_URL} so contributors "
        "know where to mint a Gemini API key. See Plan 69-02 Task 1."
    )
