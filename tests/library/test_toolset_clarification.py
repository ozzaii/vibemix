# SPDX-License-Identifier: Apache-2.0
"""Phase 100 HARDEN-CLARIFY — Plan 100-01 tests.

Sibling-extension of Phase 99's ``test_toolset_starvation.py`` posture. Pins
the wave-1 foundation surface for the Factor-7 RequestClarification tool:

* Module-level constants ``MIN_CHOICES = 2`` and ``MAX_CHOICES = 5`` exist
  in ``vibemix.library.toolset`` (CONTEXT.md Decision 2 lock; tunable for
  KAAN-ACTION §HARDEN-PHASE-B-CLARIFICATION-TONE on funded-key ear-pass).
* ``LibraryToolset._build_clarification_payload(question, choices)`` returns
  the discriminated-union shape ``{reason: "clarification_needed", question,
  choices, tool: "request_clarification"}`` (CONTEXT.md Decision 3).
* ``LibraryToolset.request_clarification(args)`` validates the args (REJECTS
  invalid choices length / non-string entries / empty question WITHOUT
  writing ``self.stop_reason``) and on valid args writes the payload to
  ``self.stop_reason`` + calls ``self._write_side_channel`` (REUSED from
  Phase 99 unchanged) + returns the payload to the caller.
* Phase 99's terminal short-circuit at ``dispatch()`` top is REUSED by
  construction — once ``request_clarification`` writes ``self.stop_reason``,
  subsequent ``dispatch()`` calls return the terminal echo without invoking
  the handler.
* Cardinal Invariant #2 (citation grounding): ``request_clarification`` has
  NO ``track_id`` surface — body reads only ``args.get("question")`` and
  ``args.get("choices")``. Behavioral pin here; Plan 100-06 ships the AST
  gate.

Fixture posture mirrors ``tests/library/test_toolset_starvation.py`` (fake
``library`` / ``embedder`` / ``store`` via ``MagicMock``). Locally declared
so this file owns single-source for its fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vibemix.library import toolset as tool_mod
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry
from vibemix.library.toolset import LibraryToolset


def _make_track(tid: str, bpm: float = 124.0, key: str = "8A") -> TrackEntry:
    """Minimal track entry — mirrors the canonical helper in test_toolset.py."""
    return TrackEntry(
        track_id=tid,
        title=f"Title {tid}",
        artist=f"Artist {tid}",
        album="A",
        bpm=bpm,
        key=key,
        duration_s=300.0,
        cues=(),
        filepath=f"/tmp/{tid}.mp3",
    )


@pytest.fixture
def library() -> RekordboxLibrary:
    lib = RekordboxLibrary()
    lib.tracks = {f"t{i:03d}": _make_track(f"t{i:03d}") for i in range(5)}
    return lib


@pytest.fixture
def toolset(library) -> LibraryToolset:
    return LibraryToolset(MagicMock(), MagicMock(), library)


# ---------------------------------------------------------------------------
# Module-constant pins — CONTEXT.md Decision 2.
# ---------------------------------------------------------------------------


def test_min_choices_constant_present() -> None:
    """Decision 2 — module-level ``MIN_CHOICES = 2`` (int)."""
    assert hasattr(tool_mod, "MIN_CHOICES"), (
        "MIN_CHOICES must be defined at module scope in "
        "vibemix.library.toolset (Phase 100 Decision 2 lock)."
    )
    value = tool_mod.MIN_CHOICES
    assert isinstance(value, int), (
        f"MIN_CHOICES must be an int; got {type(value).__name__}"
    )
    assert value == 2, (
        f"MIN_CHOICES must equal 2 (Decision 2 locked); got {value}"
    )


def test_max_choices_constant_present() -> None:
    """Decision 2 — module-level ``MAX_CHOICES = 5`` (int)."""
    assert hasattr(tool_mod, "MAX_CHOICES"), (
        "MAX_CHOICES must be defined at module scope in "
        "vibemix.library.toolset (Phase 100 Decision 2 lock)."
    )
    value = tool_mod.MAX_CHOICES
    assert isinstance(value, int), (
        f"MAX_CHOICES must be an int; got {type(value).__name__}"
    )
    assert value == 5, (
        f"MAX_CHOICES must equal 5 (Decision 2 locked); got {value}"
    )


def test_choices_constants_re_exported() -> None:
    """``__all__`` re-exports both module constants for downstream imports."""
    assert "MIN_CHOICES" in tool_mod.__all__, (
        "MIN_CHOICES must be in vibemix.library.toolset.__all__"
    )
    assert "MAX_CHOICES" in tool_mod.__all__, (
        "MAX_CHOICES must be in vibemix.library.toolset.__all__"
    )


# ---------------------------------------------------------------------------
# Validation matrix — REJECTED (no state mutation).
#
# The handler rejects invalid args WITHOUT writing self.stop_reason. The run
# CONTINUES (Codex can retry with corrected args).
# ---------------------------------------------------------------------------


def _assert_rejected_no_state_mutation(
    toolset: LibraryToolset, result: dict
) -> None:
    """Common asserts for every rejected-args test."""
    assert isinstance(result, dict)
    assert result.get("rejected") is True, (
        f"rejected calls must return rejected=True; got {result!r}"
    )
    assert "error" in result, (
        f"rejected calls must return an 'error' string; got {result!r}"
    )
    assert toolset.stop_reason is None, (
        "rejected calls MUST NOT write self.stop_reason — the run continues "
        f"so Codex can retry with corrected args; got {toolset.stop_reason!r}"
    )
    assert toolset._consecutive_empties == 0, (
        "rejected request_clarification calls MUST NOT touch the starvation "
        "counter (clarification path is independent of _consecutive_empties)."
    )


def test_reject_empty_choices(toolset: LibraryToolset) -> None:
    """choices=[] (0 elements) → rejected (below MIN_CHOICES)."""
    result = toolset.request_clarification({"question": "Q?", "choices": []})
    _assert_rejected_no_state_mutation(toolset, result)
    # Error message should mention 'choices' and the length contract.
    assert "choices" in result["error"]


def test_reject_one_choice(toolset: LibraryToolset) -> None:
    """choices=['only'] (1 element) → rejected (below MIN_CHOICES)."""
    result = toolset.request_clarification({"question": "Q?", "choices": ["only"]})
    _assert_rejected_no_state_mutation(toolset, result)
    assert "choices" in result["error"]


def test_reject_six_choices(toolset: LibraryToolset) -> None:
    """choices length 6 → rejected (above MAX_CHOICES)."""
    result = toolset.request_clarification(
        {"question": "Q?", "choices": ["a", "b", "c", "d", "e", "f"]}
    )
    _assert_rejected_no_state_mutation(toolset, result)
    assert "choices" in result["error"]


def test_reject_ten_choices(toolset: LibraryToolset) -> None:
    """choices length 10 → rejected (well above MAX_CHOICES)."""
    result = toolset.request_clarification(
        {
            "question": "Q?",
            "choices": [f"c{i}" for i in range(10)],
        }
    )
    _assert_rejected_no_state_mutation(toolset, result)


@pytest.mark.parametrize(
    "bad_choices",
    [
        "not a list",
        {"a": "b"},
        None,
        42,
        ("a", "b"),  # tuple — must be a list, not a tuple
    ],
)
def test_reject_non_list_choices(toolset: LibraryToolset, bad_choices) -> None:
    """choices not a list → rejected."""
    result = toolset.request_clarification(
        {"question": "Q?", "choices": bad_choices}
    )
    _assert_rejected_no_state_mutation(toolset, result)


def test_reject_choices_with_non_string_element(toolset: LibraryToolset) -> None:
    """choices contains a non-string element → rejected."""
    result = toolset.request_clarification(
        {"question": "Q?", "choices": ["a", 123, "c"]}
    )
    _assert_rejected_no_state_mutation(toolset, result)


def test_reject_choices_with_empty_string(toolset: LibraryToolset) -> None:
    """choices contains an empty/whitespace-only string → rejected."""
    result = toolset.request_clarification(
        {"question": "Q?", "choices": ["a", "", "c"]}
    )
    _assert_rejected_no_state_mutation(toolset, result)


def test_reject_choices_with_whitespace_string(toolset: LibraryToolset) -> None:
    """choices contains a whitespace-only string → rejected."""
    result = toolset.request_clarification(
        {"question": "Q?", "choices": ["a", "   ", "c"]}
    )
    _assert_rejected_no_state_mutation(toolset, result)


def test_reject_empty_question(toolset: LibraryToolset) -> None:
    """question is empty string → rejected."""
    result = toolset.request_clarification(
        {"question": "", "choices": ["a", "b"]}
    )
    _assert_rejected_no_state_mutation(toolset, result)
    assert "question" in result["error"]


def test_reject_whitespace_question(toolset: LibraryToolset) -> None:
    """question is whitespace-only → rejected."""
    result = toolset.request_clarification(
        {"question": "   \t\n  ", "choices": ["a", "b"]}
    )
    _assert_rejected_no_state_mutation(toolset, result)


@pytest.mark.parametrize("bad_question", [None, 42, ["a"], {"q": "v"}])
def test_reject_non_string_question(toolset: LibraryToolset, bad_question) -> None:
    """question is not a string → rejected."""
    result = toolset.request_clarification(
        {"question": bad_question, "choices": ["a", "b"]}
    )
    _assert_rejected_no_state_mutation(toolset, result)


# ---------------------------------------------------------------------------
# Validation matrix — ACCEPTED.
#
# Valid args write self.stop_reason and call self._write_side_channel
# (REUSED from Phase 99 unchanged) and return the payload to the caller.
# ---------------------------------------------------------------------------


def test_accept_two_choices(toolset: LibraryToolset) -> None:
    """choices length 2 (MIN_CHOICES boundary) → accepted."""
    result = toolset.request_clarification(
        {"question": "BPM range?", "choices": ["slow", "fast"]}
    )
    assert toolset.stop_reason is not None
    assert isinstance(result, dict)
    assert result.get("clarification_needed") is True


def test_accept_three_choices(toolset: LibraryToolset) -> None:
    """choices length 3 → accepted."""
    result = toolset.request_clarification(
        {
            "question": "context?",
            "choices": ["bedroom", "club", "festival"],
        }
    )
    assert toolset.stop_reason is not None
    assert result.get("clarification_needed") is True


def test_accept_five_choices(toolset: LibraryToolset) -> None:
    """choices length 5 (MAX_CHOICES boundary) → accepted."""
    result = toolset.request_clarification(
        {
            "question": "mood register?",
            "choices": ["chill", "energetic", "dark", "euphoric", "mixed"],
        }
    )
    assert toolset.stop_reason is not None
    assert result.get("clarification_needed") is True


# ---------------------------------------------------------------------------
# Payload shape — CONTEXT.md Decision 3 discriminated-union.
# ---------------------------------------------------------------------------


def test_payload_shape_on_accept(toolset: LibraryToolset) -> None:
    """self.stop_reason matches the Decision-3 discriminated-union shape."""
    question = "What BPM range fits?"
    choices = ["slow (80-100)", "mid (100-120)", "fast (120-140)"]
    toolset.request_clarification({"question": question, "choices": choices})

    payload = toolset.stop_reason
    assert isinstance(payload, dict)
    assert payload["reason"] == "clarification_needed", (
        "Decision 3 — discriminator is 'clarification_needed' (sibling of "
        "Phase 99's 'tool_starvation')."
    )
    assert payload["question"] == question
    assert payload["choices"] == choices  # list equality preserves order
    assert payload["tool"] == "request_clarification"


def test_payload_choices_defensive_copy(toolset: LibraryToolset) -> None:
    """Payload uses list(choices) — caller-side mutation must not corrupt payload."""
    question = "Q?"
    choices = ["a", "b", "c"]
    toolset.request_clarification({"question": question, "choices": choices})

    # Caller mutates their own list AFTER the handler returned.
    choices.append("tampered")
    assert toolset.stop_reason is not None
    assert toolset.stop_reason["choices"] == ["a", "b", "c"], (
        "_build_clarification_payload must defensively copy choices via "
        "list(...) — otherwise caller-side mutation corrupts the in-process "
        "stop_reason."
    )


def test_handler_return_payload_matches_clarification_contract(
    toolset: LibraryToolset,
) -> None:
    """Handler returns clarification_needed=True + question + choices to Codex."""
    question = "Q?"
    choices = ["a", "b", "c"]
    result = toolset.request_clarification(
        {"question": question, "choices": choices}
    )
    assert result["clarification_needed"] is True
    assert result["question"] == question
    assert result["choices"] == choices


# ---------------------------------------------------------------------------
# Side-channel write reuse — Phase 99 ``_write_side_channel`` unchanged.
# ---------------------------------------------------------------------------


def test_side_channel_write_on_valid_call(
    toolset: LibraryToolset, monkeypatch, tmp_path: Path
) -> None:
    """With VIBEMIX_STOP_REASON_FILE set, valid call writes JSON to that path."""
    sr_path = tmp_path / "sr.json"
    monkeypatch.setenv("VIBEMIX_STOP_REASON_FILE", str(sr_path))

    question = "Q?"
    choices = ["a", "b"]
    toolset.request_clarification({"question": question, "choices": choices})

    assert sr_path.exists(), (
        "_write_side_channel must write to the env-var path on valid call "
        "(reused unchanged from Phase 99 Plan 99-04)."
    )
    parsed = json.loads(sr_path.read_text())
    assert parsed == toolset.stop_reason, (
        "Side-channel JSON must equal in-process stop_reason payload."
    )
    assert parsed["reason"] == "clarification_needed"


def test_side_channel_noop_without_env(
    toolset: LibraryToolset, monkeypatch, tmp_path: Path
) -> None:
    """Without VIBEMIX_STOP_REASON_FILE, valid call still writes in-process."""
    monkeypatch.delenv("VIBEMIX_STOP_REASON_FILE", raising=False)

    result = toolset.request_clarification(
        {"question": "Q?", "choices": ["a", "b"]}
    )
    assert toolset.stop_reason is not None
    assert result.get("clarification_needed") is True
    # No file was written (env absent → silent no-op per Phase 99 contract).
    assert not any(tmp_path.iterdir()), (
        "tmp_path must stay empty — _write_side_channel is a silent no-op "
        "when VIBEMIX_STOP_REASON_FILE is unset."
    )


# ---------------------------------------------------------------------------
# Terminal short-circuit reuse — Phase 99's dispatch-top short-circuit fires
# for clarification too, BY CONSTRUCTION. No new code; this test pins the
# reuse.
# ---------------------------------------------------------------------------


def test_dispatch_short_circuit_after_clarification(
    toolset: LibraryToolset, monkeypatch
) -> None:
    """After valid request_clarification, dispatch() returns terminal echo
    on subsequent calls and NEVER invokes the named handler.
    """
    # Trip clarification.
    toolset.request_clarification(
        {"question": "Q?", "choices": ["a", "b"]}
    )
    assert toolset.stop_reason is not None
    captured_reason = dict(toolset.stop_reason)

    # If the short-circuit fails, this patched search_vibe would crash.
    def _boom(args: dict):
        raise RuntimeError(
            "search_vibe was invoked AFTER clarification trip — short-circuit broken"
        )

    monkeypatch.setattr(toolset, "search_vibe", _boom)

    # Subsequent dispatch must NOT invoke the handler; returns the terminal echo.
    echo = toolset.dispatch("search_vibe", {"query": "x"})
    assert isinstance(echo, dict)
    assert "stop_reason" in echo, (
        f"dispatch after clarification must return terminal echo dict; got {echo!r}"
    )
    assert echo["stop_reason"]["reason"] == "clarification_needed", (
        "Terminal echo must carry clarification_needed reason — proves Phase "
        "99's short-circuit handles BOTH terminal stop_reasons (sibling-"
        "extension by construction)."
    )
    assert echo["stop_reason"] == captured_reason, (
        "Terminal echo must equal the original clarification payload."
    )


def test_dispatch_short_circuit_via_request_clarification_dispatch_entry(
    toolset: LibraryToolset,
) -> None:
    """Calling request_clarification through dispatch() also works + trips
    the short-circuit on the next call.
    """
    # First call: dispatched as a regular tool, fires the handler, writes payload.
    first = toolset.dispatch(
        "request_clarification",
        {"question": "Q?", "choices": ["a", "b"]},
    )
    assert isinstance(first, dict)
    # The handler return surfaces clarification_needed=True; the short-circuit
    # has NOT fired yet (stop_reason was None at top-of-dispatch).
    assert first.get("clarification_needed") is True
    assert toolset.stop_reason is not None

    # Second call: any tool returns the terminal echo (short-circuit fires).
    echo = toolset.dispatch("get_track_features", {"track_id": "t000"})
    assert "stop_reason" in echo
    assert echo["stop_reason"]["reason"] == "clarification_needed"


# ---------------------------------------------------------------------------
# Cardinal Invariant #2 — no track_id surface.
#
# Behavioral pin: a valid request_clarification call does NOT touch
# self.seen / self.seen_sections / self._library / self._store / self._embedder.
# Plan 100-06 ships the AST gate; this test pins the behavior structurally.
# ---------------------------------------------------------------------------


def test_no_track_id_surface_on_accept(toolset: LibraryToolset) -> None:
    """Valid call must NOT touch self.seen / self.seen_sections / issued_* dicts.

    Behavioral pin for Cardinal Invariant #2 (no track_id surface). The
    grounding spine (``self.seen``) is the per-run anti-hallucination gate;
    a clarification handler that wrote to it would let the LLM smuggle
    invented track ids through the discriminated-union payload. Snapshot
    state before the call, run the handler with valid args, snapshot after
    — every grounding container must be UNCHANGED.

    Plan 100-06 will install the AST gate; this test is the runtime pin
    that complements it.
    """
    # Snapshot grounding state pre-call.
    seen_before = set(toolset.seen)
    seen_sections_before = dict(toolset.seen_sections)
    issued_transitions_before = dict(toolset.issued_transition_candidates)
    issued_context_before = dict(toolset.issued_context_packets)
    issued_cues_before = dict(toolset.issued_cue_proposals)
    seen_urls_before = set(getattr(toolset, "seen_urls", set()))

    result = toolset.request_clarification(
        {"question": "Q?", "choices": ["a", "b", "c"]}
    )
    assert result.get("clarification_needed") is True

    # Every grounding container UNCHANGED — no track_id / section / context /
    # cue / url was introduced via the clarification path.
    assert toolset.seen == seen_before, (
        "Cardinal Invariant #2 — request_clarification must NOT write to "
        f"self.seen. Diff: {toolset.seen - seen_before!r}"
    )
    assert toolset.seen_sections == seen_sections_before
    assert toolset.issued_transition_candidates == issued_transitions_before
    assert toolset.issued_context_packets == issued_context_before
    assert toolset.issued_cue_proposals == issued_cues_before
    assert getattr(toolset, "seen_urls", set()) == seen_urls_before


def test_no_consecutive_empties_drift_on_accept(toolset: LibraryToolset) -> None:
    """Valid call must NOT increment self._consecutive_empties.

    Clarification is independent of the counter — it's a single-trip LLM-
    driven path (CONTEXT.md Decision 4 rationale), not threshold-driven.
    """
    assert toolset._consecutive_empties == 0
    toolset.request_clarification(
        {"question": "Q?", "choices": ["a", "b"]}
    )
    assert toolset._consecutive_empties == 0, (
        "request_clarification must NOT increment _consecutive_empties — "
        "it's a counter-independent terminal path."
    )


def test_handler_does_not_read_track_id_from_args(toolset: LibraryToolset) -> None:
    """Even if the args carry a track_id key, the handler must ignore it.

    Behavioral pin for the no-track-id-surface contract (Cardinal Invariant
    #2). Plan 100-06's AST gate enforces this structurally; this test pins
    the runtime equivalent.
    """
    seen_before = set(toolset.seen)
    # Adversarial args — the LLM tries to slip a track_id into the clarification.
    result = toolset.request_clarification(
        {
            "question": "Q?",
            "choices": ["a", "b"],
            "track_id": "t999-INVENTED-ID",  # MUST be ignored
        }
    )
    # Valid args ⇒ accepted (the trailing track_id key is ignored, not rejected).
    assert result.get("clarification_needed") is True
    # The invented track_id MUST NOT enter self.seen via the handler.
    assert toolset.seen == seen_before
    assert "t999-INVENTED-ID" not in toolset.seen
    # The payload MUST NOT carry the track_id either.
    assert "track_id" not in toolset.stop_reason
