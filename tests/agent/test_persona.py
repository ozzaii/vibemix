# SPDX-License-Identifier: Apache-2.0
"""Persona invariants — PERSONA-01/02/03.

Anti-hallucination invariants are load-bearing IP per CLAUDE.md. PERSONA-02
pins byte-equality against cohost_v4.py:150-213; PERSONA-03 pins the specific
substrings that paraphrasing would lose.
"""

from __future__ import annotations

from tests.agent.conftest import v4_persona_string
from vibemix.agent.persona import SYSTEM_INSTRUCTION


def test_persona_01_resolves_as_str() -> None:
    """PERSONA-01: SYSTEM_INSTRUCTION resolves to a str."""
    assert isinstance(SYSTEM_INSTRUCTION, str)


def test_persona_02_byte_identical_to_v4() -> None:
    """PERSONA-02: byte-equal to cohost_v4.py SYSTEM_INSTRUCTION body."""
    v4_body = v4_persona_string()
    assert SYSTEM_INSTRUCTION == v4_body, (
        f"persona drift: pkg_len={len(SYSTEM_INSTRUCTION)} v4_len={len(v4_body)}"
    )
    # Sanity floor — the body is ~8KB of prose; <2000 chars means paraphrasing.
    assert len(SYSTEM_INSTRUCTION) > 2000


def test_persona_03_anti_hallucination_substrings_present() -> None:
    """PERSONA-03: every anti-hallucination invariant substring is present.

    Catches paraphrase drift in the load-bearing IP. The full byte-equality
    test is PERSONA-02; this is the readable safety net.
    """
    expected = [
        "THERE IS NO CROWD",
        "LATENCY IS BRUTAL",
        "ANTI HALLUCINATION RULES (HARD GATES)",
        "If you have NOTHING grounded to say, say NOTHING",
        "NEVER break the 4th wall",
        "ENGLISH ONLY",
    ]
    for needle in expected:
        assert needle in SYSTEM_INSTRUCTION, f"missing anti-hallucination substring: {needle!r}"
