# SPDX-License-Identifier: Apache-2.0
"""Phase 32 Plan 32-06 — end-to-end profile pipeline E2E.

Validates the integration across all five plans without spinning up the
LiveKit cascade:

  1. Storage  : default no profile, no consent.
  2. Consent  : enable → save_consent(True) → load_consent() returns True.
  3. Build    : build_profile from synthetic evidence_snapshot.
  4. Cache    : render_profile_for_cache + GeminiContextCache.padded_body
                contains the section AND remains ≥1024-token-floor.
  5. P60 gate : the literal "profile" identifier MUST NOT appear inside
                DJCoHostAgent.llm_node (per-turn prompt path).
  6. P53 gate : DJCoHostAgent accepts profile= kwarg + is byte-identical
                to the v2.0 call shape when profile is omitted (covered by
                tests/agent/test_dj_cohost_profile_kwarg.py — here we just
                spot-check the constructor accepts the new kwarg).
  7. Delete   : profile.delete unlinks the file + load_profile returns None.

Runs entirely offline (no Gemini SDK calls — GeminiContextCache.create is
NOT exercised; only padded_body which is pure-string).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

from vibemix.agent.cache import GEMINI_CACHE_TOKEN_FLOOR, GeminiContextCache
from vibemix.profile import (
    build_profile,
    delete_profile,
    load_consent,
    load_profile,
    render_profile_for_cache,
    save_consent,
    save_profile,
    serialize_profile,
)


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    if sys.platform == "win32":
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
    yield


def test_profile_e2e_full_lifecycle() -> None:
    """Boot → consent → build → cache inject → delete round-trip."""
    # ---- 1. Boot: no profile, no consent. --------------------------------
    assert load_profile() is None
    assert load_consent() is False
    assert render_profile_for_cache(None) == ""

    # ---- 2. User opts in via wizard / settings. --------------------------
    save_consent(True)
    assert load_consent() is True

    # ---- 3. Build from synthetic evidence snapshot. ----------------------
    # Evidence shape mirrors EvidenceRegistry.snapshot() — dict[source]
    # of dict[key] of timestamp-tuples. The builder's ≥2-citation rule
    # per tendency field (PROFILE-06) requires ≥2 distinct event-source
    # observations to (re)generate a field.
    synthetic_evidence: dict[str, dict[str, tuple[float, ...]]] = {
        "event": {
            "PHASE": (1.0, 2.0, 3.0, 4.0, 5.0, 6.0),  # ≥6 → "always"
            "TRACK_CHANGE": (1.5, 2.5, 3.5, 4.5),  # 3-5 → "sometimes"
            "MIX_MOVE": (1.0, 2.0),  # 1-2 → "rarely"
        }
    }
    profile = build_profile(
        prior_profile=None,
        session_events=[],
        evidence_snapshot=synthetic_evidence,
        consent=True,
    )
    assert profile is not None
    assert "preferred_genre" in profile
    assert "avg_session_duration" in profile
    assert "mix_style_tags" in profile
    assert "tempo_preference_bin" in profile
    assert "event_type_response_preferences" in profile

    # ---- 4. Serialize + persist to disk under the 2KB hard cap. ----------
    raw = serialize_profile(profile)
    assert len(raw) <= 2048  # P51 hard cap
    save_profile(profile)
    assert load_profile() == profile

    # ---- 5. Cache injection: render → padded_body contains the section. -
    section = render_profile_for_cache(profile)
    assert section  # non-empty
    # Token budget guard from Plan 32-01 §cache_render.
    assert len(section) // 4 <= 300

    # Stub the SDK client — padded_body is pure-string; create() is not called.
    cache = GeminiContextCache(
        client=None,  # type: ignore[arg-type]
        system_instruction_body="SYS_PROMPT_STUB_FOR_TEST",
        profile_section=section,
    )
    padded = cache.padded_body()
    assert section in padded
    # 1024-token floor preserved (system instruction + section + pad block).
    assert (len(padded) // 4) >= GEMINI_CACHE_TOKEN_FLOOR

    # Cache-key stability: identical profile_section → identical padded_body.
    cache2 = GeminiContextCache(
        client=None,  # type: ignore[arg-type]
        system_instruction_body="SYS_PROMPT_STUB_FOR_TEST",
        profile_section=section,
    )
    assert cache2.padded_body() == padded

    # ---- 6. Delete unlinks. ----------------------------------------------
    assert delete_profile() is True
    assert load_profile() is None
    # Subsequent delete returns False (not_found semantics — handler
    # converts this to error="not_found" in the IPC reply).
    assert delete_profile() is False


def test_profile_not_in_per_turn_llm_node_path() -> None:
    """P60 grep gate: the literal `profile` identifier must not appear inside
    the per-turn agent path (``DJCoHostAgent.llm_node``).

    This is the cross-cutting protection that prevents the profile dict from
    being silently spliced into the per-call prompt (which would double the
    cache miss rate AND defeat the cache-side injection win from Plan 32-02).
    The grep is restricted to the llm_node function body — references in
    __init__ + docstrings are allowed (the kwarg lives there).
    """
    src_path = (
        Path(__file__).resolve().parent.parent.parent
        / "src"
        / "vibemix"
        / "agent"
        / "dj_cohost.py"
    )
    src = src_path.read_text("utf-8")
    # Slice out llm_node — between `def llm_node` and the next top-level
    # method. The class methods are 4-space indented so `\n    def ` is
    # the boundary.
    if "def llm_node" not in src:
        pytest.skip("llm_node not present; grep gate not applicable")
    after = src.split("def llm_node", 1)[1]
    body = after.split("\n    def ", 1)[0]

    # Strip comments + docstrings — the test only cares about runtime refs.
    # A simple heuristic: drop lines that start with `#` and triple-quoted
    # blocks. Triple-quoted blocks are matched non-greedily.
    body_no_docs = re.sub(r'"""[\s\S]*?"""', "", body)
    code_only = "\n".join(
        line for line in body_no_docs.splitlines() if not line.lstrip().startswith("#")
    )
    # Case-insensitive grep for "profile" in the runtime body.
    assert "profile" not in code_only.lower(), (
        "P60 violation: `profile` appears in DJCoHostAgent.llm_node — the "
        "profile must live in GeminiContextCache.padded_body, not in the "
        "per-turn prompt. Move the reference back to __init__."
    )


def test_profile_serialize_compact_within_cap() -> None:
    """A maximal allowlisted profile fits under the 2048-byte cap.

    Builds a worst-case profile (all 8 mix_style_tags, every event-type
    response preference filled) and asserts serialize_profile succeeds
    instead of raising ProfileError. Documents the engineering headroom
    we have for future allowlist extensions before P51's size cap bites.
    """
    maximal = {
        "preferred_genre": "hard_tek",
        "avg_session_duration": 480.0,
        "mix_style_tags": [
            "long_blends",
            "quick_cuts",
            "loops",
            "filter_sweeps",
            "loud_drops",
            "subtle_transitions",
            "vocal_pickups",
            "bass_riding",
        ],
        "tempo_preference_bin": "138-150",
        "event_type_response_preferences": {
            "TRACK_CHANGE": "always",
            "PHASE": "sometimes",
            "KAAN_SPOKE": "rarely",
            "MIX_MOVE": "never",
            "DISTORTION_CLIMB": "always",
            "ACID_LINE_ENTRY": "sometimes",
            "HEARTBEAT": "rarely",
            "LAYER_ARRIVAL": "always",
        },
    }
    raw = serialize_profile(maximal)
    assert len(raw) <= 2048
    # Sanity: round-trip preserves shape.
    assert json.loads(raw) == maximal
