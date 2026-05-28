# SPDX-License-Identifier: Apache-2.0
"""Skill-tree engine invariant pins — static-grep gates (#1, #4, privacy).

Phase 102 Plan 02 (v11.0 "Earned"). Three line-oriented ``re`` static gates,
mirroring the shipped idiom in ``tests/learn/test_runtime_invariants.py``
(resolve the module via ``repo_root``; skip ``#``-comment lines). The skill-tree
engine is pure logic — these pins prove it never crosses the three boundaries it
must not touch:

  * Invariant #1 (single-writer): never imports or WRITES ``MusicState`` /
    ``ControllerState`` — only the live state-refresh loop writes MusicState.
  * Invariant #4 (one socket): opens no new ws listener — the mascot/wizard bus
    binds 127.0.0.1:8765 only, debrief 8766; the engine adds no third port.
  * Privacy (Pitfall P51): no skill data leaks into ``profile.json``. The engine
    never imports the profile surface, AND the ``PROFILE_SCHEMA`` privacy
    contract is still exactly its 5 allowed fields with
    ``additionalProperties: false`` (no ``skills`` / ``live_proof_count`` /
    ``mastered`` keys).

These gates use the SUBSTANTIVE check (an actual ``import`` / actual field
WRITE), not a naive substring count — the engine's docstrings legitimately
mention "MusicState" / "profile.json" to explain what it does NOT do (a
CLAUDE.md "explain why" convention). Comment lines are filtered first; bare
substring ``== 0`` gates on unfiltered source are forbidden per CLAUDE grep-gate
hygiene (and would false-positive on the explanatory prose).

REQ-IDs: SKILL-02 (purity / Invariant #1), plus the no-new-port (#4) and
privacy-contract pins.
"""
from __future__ import annotations

import pathlib
import re


def _repo_root() -> pathlib.Path:
    # tests/learn/test_skill_tree_invariants.py -> ../../
    return pathlib.Path(__file__).resolve().parent.parent.parent


SKILL_TREE_PATH = _repo_root() / "src" / "vibemix" / "learn" / "skill_tree.py"


def _code_lines(path: pathlib.Path) -> list[tuple[int, str]]:
    """Return ``(line_no, line)`` pairs for non-comment source lines.

    Mirrors ``test_runtime_invariants.py``: a line whose first non-whitespace
    character is ``#`` is a comment and is skipped. Docstring bodies are not
    code lines for our import/write/port gates either — but they are not
    line-comments, so we rely on the precise patterns below (an actual
    ``import`` statement / a field-assignment / ``websockets.serve(`` etc.)
    rather than coarse substrings, so explanatory prose inside a docstring can
    never trip the gate.
    """
    source = path.read_text(encoding="utf-8")
    out: list[tuple[int, str]] = []
    for line_no, line in enumerate(source.splitlines(), start=1):
        if line.lstrip().startswith("#"):
            continue
        out.append((line_no, line))
    return out


# ---------------------------------------------------------------------------
# Invariant #1 — skill_tree.py never imports or writes MusicState
# ---------------------------------------------------------------------------
# An actual import of the music-state module, OR an actual field write to a
# music_state / MusicState / controller_state / ControllerState object. Prose
# mentions ("never writes MusicState") match NONE of these.
_FORBIDDEN_IMPORTS = (
    re.compile(r"^\s*import\s+vibemix\.state\.music_state\b"),
    re.compile(r"^\s*from\s+vibemix\.state\.music_state\b"),
    re.compile(r"^\s*from\s+vibemix\.state\b\s+import\b.*\bMusicState\b"),
    re.compile(r"^\s*import\s+.*\bmusic_state\b"),
)
_FORBIDDEN_WRITES = (
    re.compile(r"\b(music_state|MusicState)\.\w+\s*=\s*"),
    re.compile(r"\b(controller_state|ControllerState)\.\w+\s*=\s*"),
)


def test_skill_tree_never_mutates_musicstate() -> None:
    """Invariant #1: the engine neither imports nor writes MusicState /
    ControllerState. It is a pure reader of LearnProgress."""
    offenders: list[str] = []
    for line_no, line in _code_lines(SKILL_TREE_PATH):
        for pat in _FORBIDDEN_IMPORTS:
            if pat.search(line):
                offenders.append(f"{SKILL_TREE_PATH}:{line_no}: IMPORT {line.strip()}")
        for pat in _FORBIDDEN_WRITES:
            if pat.search(line):
                offenders.append(f"{SKILL_TREE_PATH}:{line_no}: WRITE {line.strip()}")
    assert not offenders, (
        "Invariant #1 violation — skill_tree.py imported or wrote MusicState/"
        "ControllerState. The engine is a pure reader.\n" + "\n".join(offenders)
    )


# ---------------------------------------------------------------------------
# Invariant #4 — skill_tree.py opens no new ws port
# ---------------------------------------------------------------------------
# An actual ws-server bind, a WS_PORT symbol use, or a bind to the known
# vibemix ports. The engine is pure logic with no socket surface.
_FORBIDDEN_PORT = (
    re.compile(r"websockets\.serve\b"),
    re.compile(r"\bWS_PORT\b"),
    re.compile(r"\b8765\b"),
    re.compile(r"\b8766\b"),
)


def test_no_new_ws_port() -> None:
    """Invariant #4: the engine opens no ws listener and references no ws
    port literal/symbol — there is exactly one bus (8765) + debrief (8766),
    and this module adds no third."""
    offenders: list[str] = []
    for line_no, line in _code_lines(SKILL_TREE_PATH):
        for pat in _FORBIDDEN_PORT:
            if pat.search(line):
                offenders.append(f"{SKILL_TREE_PATH}:{line_no}: {line.strip()}")
    assert not offenders, (
        "Invariant #4 violation — skill_tree.py referenced a ws port / "
        "listener. The engine has no socket surface.\n" + "\n".join(offenders)
    )


# ---------------------------------------------------------------------------
# Privacy (Pitfall P51) — no skill data ever reaches profile.json
# ---------------------------------------------------------------------------
# An actual import/reference to the profile surface. Prose mentions of
# "profile.json" in the module docstring (explaining it does NOT touch it)
# match none of these.
_FORBIDDEN_PROFILE = (
    re.compile(r"^\s*import\s+.*\bvibemix\.profile\b"),
    re.compile(r"^\s*from\s+vibemix\.profile\b"),
    re.compile(r"\bserialize_profile\b"),
    re.compile(r"\bvalidate_profile\b"),
    re.compile(r"\bPROFILE_SCHEMA\b"),
)

_PROFILE_REQUIRED = {
    "preferred_genre",
    "avg_session_duration",
    "mix_style_tags",
    "tempo_preference_bin",
    "event_type_response_preferences",
}
_SKILL_KEYS_THAT_MUST_NOT_LEAK = ("skills", "live_proof_count", "mastered")


def test_skills_never_in_profile_json() -> None:
    """Privacy: (a) the engine never imports/references the profile surface,
    and (b) the PROFILE_SCHEMA contract is still exactly its 5 allowed fields
    with ``additionalProperties: false`` and no skill keys in ``properties``."""
    # (a) The engine never touches the profile surface.
    offenders: list[str] = []
    for line_no, line in _code_lines(SKILL_TREE_PATH):
        for pat in _FORBIDDEN_PROFILE:
            if pat.search(line):
                offenders.append(f"{SKILL_TREE_PATH}:{line_no}: {line.strip()}")
    assert not offenders, (
        "Privacy violation — skill_tree.py referenced the profile surface. "
        "Skill data lives ONLY in learn-progress.json, never profile.json.\n"
        + "\n".join(offenders)
    )

    # (b) The privacy contract is still exactly 5 fields, locked closed.
    from vibemix.profile.schema import PROFILE_SCHEMA

    assert set(PROFILE_SCHEMA["required"]) == _PROFILE_REQUIRED, (
        "PROFILE_SCHEMA.required drifted from the 5-field privacy contract: "
        f"{sorted(PROFILE_SCHEMA['required'])}"
    )
    assert PROFILE_SCHEMA["additionalProperties"] is False, (
        "PROFILE_SCHEMA must stay additionalProperties:false — any open field "
        "is a privacy leak."
    )
    properties = PROFILE_SCHEMA["properties"]
    assert set(properties) == _PROFILE_REQUIRED, (
        "PROFILE_SCHEMA.properties drifted — a non-allowlisted field appeared: "
        f"{sorted(properties)}"
    )
    for leak_key in _SKILL_KEYS_THAT_MUST_NOT_LEAK:
        assert leak_key not in properties, (
            f"Privacy violation — skill key {leak_key!r} appeared in "
            "PROFILE_SCHEMA.properties. Skill state must never reach profile.json."
        )
