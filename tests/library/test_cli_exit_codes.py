# SPDX-License-Identifier: Apache-2.0
"""Phase 99 HARDEN-RETRY — Plan 99-06 CLI exit-code dispatch tests.

These pin Decision 6 (CONTEXT.md) end-to-end on the user-visible CLI surface:

* ``library curate <theme>`` exits with code **10** when ``curate_with_codex``
  returns ``CodexCurateResult(stop_reason="tool_starvation", ...)``.
* ``library build-set <brief>`` exits with code **10** on the same shape from
  ``build_set_with_codex``.
* Both commands exit **1** on any OTHER non-success stop_reason (regression-pin
  on the pre-99-06 behavior — ``timeout`` / ``codex_not_installed`` / etc).
* Both commands exit **0** on a successful curation (``stop_reason="created"`` /
  ``"exported"``) — regression-pin.
* The Telegram ``curate_fn`` adapter normalizes the starvation payload to
  ``{"ok": False, "stop_reason": "tool_starvation", "hint": <error string>}``
  — the contract bridge that Plan 99-07's ``format_reply`` will consume.

Phase 100 forward-compat: the inline ternary
``return 10 if result.stop_reason == "tool_starvation" else 1`` is the surgical
edit shape; Plan 100 can extend it to ``... else 11 if ... == "clarification_needed"
else 1`` without test refactoring.

## Test posture

The CLI handlers ``_cmd_library_curate_codex`` and ``_cmd_library_build_set_codex``
live in ``vibemix.__main__`` and lazy-import their wrapper from
``vibemix.library.codex_curate`` inside the function body. The standard
``unittest.mock.patch`` of the source module (``vibemix.library.codex_curate
.curate_with_codex``) is the cleanest seam — the lazy import resolves the
name at the patched module attribute. No subprocess, no real Codex install,
no real Rekordbox library required: the handler treats the wrapper return
value as opaque after construction, so a sentinel ``lib`` object suffices.

The Telegram ``curate_fn`` adapter is tested via the module-level helper
``_normalize_codex_curate_result(result) -> dict`` introduced by Plan 99-06
Task 2 (refactor: the closure calls the helper). This keeps the test
posture unit-level without invoking the real Telegram bridge.
"""

from __future__ import annotations

import argparse
from unittest.mock import patch

import pytest

import vibemix.__main__ as m
from vibemix.library.codex_curate import CodexCurateResult

# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def curate_args() -> argparse.Namespace:
    """Minimal Namespace shape accepted by _cmd_library_curate_codex."""
    return argparse.Namespace(theme="dark techno", name=None)


@pytest.fixture
def build_set_args() -> argparse.Namespace:
    """Minimal Namespace shape accepted by _cmd_library_build_set_codex."""
    return argparse.Namespace(
        brief="peak-time 60 min",
        curve=None,
        name=None,
        n_slots=None,
        export=None,
    )


@pytest.fixture
def lib_sentinel() -> object:
    """Opaque ``lib`` arg — the CLI handler passes it through but never touches it."""
    return object()


@pytest.fixture(autouse=True)
def _silence_stdout_stderr(capsys):
    """Tests assert on stderr substrings via capsys; this is just documentation
    that we want capsys captured. The fixture itself is a no-op (capsys is
    already a per-test pytest fixture)."""
    yield


# ──────────────────────────────────────────────────────────────────────
# curate exit-code tests
# ──────────────────────────────────────────────────────────────────────


def test_curate_exits_10_on_starvation(
    curate_args: argparse.Namespace, lib_sentinel: object, capsys
) -> None:
    """tool_starvation → exit 10, bracket-tagged stderr hint."""
    starved = CodexCurateResult(
        theme="dark techno",
        stop_reason="tool_starvation",
        error="library has 0 tracks — run `library ingest` first",
    )
    with patch(
        "vibemix.library.codex_curate.curate_with_codex",
        return_value=starved,
    ):
        rc = m._cmd_library_curate_codex(curate_args, lib_sentinel)

    captured = capsys.readouterr()
    assert rc == 10, (
        f"expected exit 10 on tool_starvation, got {rc!r}; "
        f"stderr={captured.err!r}"
    )
    assert "[viber/codex] tool_starvation:" in captured.err, (
        f"expected bracket-tagged stderr; got {captured.err!r}"
    )
    assert "library has 0 tracks" in captured.err, (
        f"expected hint substring in stderr; got {captured.err!r}"
    )


def test_curate_exits_1_on_other_failures(
    curate_args: argparse.Namespace, lib_sentinel: object, capsys
) -> None:
    """Regression-pin: non-starvation failure → exit 1 (pre-99-06 behavior)."""
    timed_out = CodexCurateResult(
        theme="dark techno",
        stop_reason="timeout",
        error="Codex took too long",
    )
    with patch(
        "vibemix.library.codex_curate.curate_with_codex",
        return_value=timed_out,
    ):
        rc = m._cmd_library_curate_codex(curate_args, lib_sentinel)

    captured = capsys.readouterr()
    assert rc == 1, (
        f"expected exit 1 on timeout, got {rc!r}; stderr={captured.err!r}"
    )
    assert "[viber/codex] timeout:" in captured.err


def test_curate_exits_0_on_success(
    curate_args: argparse.Namespace, lib_sentinel: object, capsys
) -> None:
    """Regression-pin: happy path → exit 0."""
    ok = CodexCurateResult(
        theme="dark techno",
        stop_reason="created",
        playlist_name="dark techno",
        track_ids=["t1", "t2"],
        m3u_path="/tmp/dark-techno.m3u",
    )
    with patch(
        "vibemix.library.codex_curate.curate_with_codex",
        return_value=ok,
    ):
        rc = m._cmd_library_curate_codex(curate_args, lib_sentinel)

    assert rc == 0


# ──────────────────────────────────────────────────────────────────────
# build-set exit-code tests
# ──────────────────────────────────────────────────────────────────────


def test_build_set_exits_10_on_starvation(
    build_set_args: argparse.Namespace, lib_sentinel: object, capsys
) -> None:
    """tool_starvation → exit 10, bracket-tagged stderr hint."""
    starved = CodexCurateResult(
        theme="peak-time 60 min",
        stop_reason="tool_starvation",
        error="library has 0 tracks — run `library ingest` first",
    )
    with patch(
        "vibemix.library.codex_curate.build_set_with_codex",
        return_value=starved,
    ):
        rc = m._cmd_library_build_set_codex(build_set_args, lib_sentinel)

    captured = capsys.readouterr()
    assert rc == 10, (
        f"expected exit 10 on tool_starvation, got {rc!r}; "
        f"stderr={captured.err!r}"
    )
    assert "[viber/codex] tool_starvation:" in captured.err
    assert "library has 0 tracks" in captured.err


def test_build_set_exits_1_on_other_failures(
    build_set_args: argparse.Namespace, lib_sentinel: object, capsys
) -> None:
    """Regression-pin: non-starvation failure → exit 1."""
    timed_out = CodexCurateResult(
        theme="peak-time 60 min",
        stop_reason="timeout",
        error="Codex took too long",
    )
    with patch(
        "vibemix.library.codex_curate.build_set_with_codex",
        return_value=timed_out,
    ):
        rc = m._cmd_library_build_set_codex(build_set_args, lib_sentinel)

    assert rc == 1


# ──────────────────────────────────────────────────────────────────────
# Telegram curate_fn normalizer (Decision 8 / Plan 99-07 bridge)
# ──────────────────────────────────────────────────────────────────────


def test_telegram_curate_fn_normalizes_starvation() -> None:
    """The module-level helper that ``curate_fn`` calls before its
    happy-path check returns the normalized starvation payload that
    Plan 99-07's ``format_reply`` consumes.

    Contract (Decision 8):
        starvation result -> {"ok": False,
                              "stop_reason": "tool_starvation",
                              "hint": <error string>}
    Non-starvation result -> None (fall-through to the existing
                                   ``curate_fn`` happy-path / error branches).
    """
    starved = CodexCurateResult(
        theme="dark techno",
        stop_reason="tool_starvation",
        error="library has 0 tracks",
    )
    normalized = m._normalize_codex_curate_result(starved)
    assert normalized == {
        "ok": False,
        "stop_reason": "tool_starvation",
        "hint": "library has 0 tracks",
    }

    # Non-starvation: helper returns None (let curate_fn handle).
    ok = CodexCurateResult(
        theme="dark techno",
        stop_reason="created",
        playlist_name="dark techno",
        track_ids=["t1"],
    )
    assert m._normalize_codex_curate_result(ok) is None

    timed_out = CodexCurateResult(
        theme="dark techno",
        stop_reason="timeout",
        error="Codex took too long",
    )
    assert m._normalize_codex_curate_result(timed_out) is None

    # Defensive: starvation with None error → empty-string hint, not None.
    starved_no_error = CodexCurateResult(
        theme="dark techno",
        stop_reason="tool_starvation",
        error=None,
    )
    normalized2 = m._normalize_codex_curate_result(starved_no_error)
    assert normalized2 == {
        "ok": False,
        "stop_reason": "tool_starvation",
        "hint": "",
    }


# ──────────────────────────────────────────────────────────────────────
# Phase 100 HARDEN-CLARIFY-04 — exit code 11 dispatch + normalizer extension
# ──────────────────────────────────────────────────────────────────────
#
# These 3 tests pin Decision 5 (exit 11 reserved range 10-19) + Decision 6
# (2-block stderr render: header + question + numbered choices + re-run hint)
# + the _normalize_codex_curate_result clarification branch (the cross-module
# dict contract Plan 100-05 telegram_bridge.format_reply consumes).
#
# The 6 Phase 99 Plan 99-06 tests above are REGRESSION-PINS — additive only.


def test_curate_exits_11_on_clarification(
    curate_args: argparse.Namespace, lib_sentinel: object, capsys
) -> None:
    """clarification_needed → exit 11, 2-block stderr render (header + question +
    numbered choices + re-run hint).

    Pinned per CONTEXT.md Decision 5 (exit-11 reserved range 10-19) + Decision 6
    (two-block stderr layout). The re-run hint closes the single-turn loop:
    vibemix retains NO state across the cycle — the user re-invokes manually.
    """
    clarification = CodexCurateResult(
        theme="ambiguous",
        stop_reason="clarification_needed",
        question="What BPM range?",
        choices=["slow (90-110)", "fast (130-140)", "mixed"],
    )
    # ambiguous theme echoed in the re-run hint
    curate_args.theme = "ambiguous"
    with patch(
        "vibemix.library.codex_curate.curate_with_codex",
        return_value=clarification,
    ):
        rc = m._cmd_library_curate_codex(curate_args, lib_sentinel)

    captured = capsys.readouterr()
    assert rc == 11, (
        f"expected exit 11 on clarification_needed, got {rc!r}; "
        f"stderr={captured.err!r}"
    )

    # 2-block stderr render (Decision 6):
    # Block 1: bracket-tagged header consistent with [viber/codex] prefix
    assert "[viber/codex] clarification_needed:" in captured.err, (
        f"expected bracket-tagged header; got {captured.err!r}"
    )
    # The question is rendered verbatim.
    assert "What BPM range?" in captured.err, (
        f"expected question substring in stderr; got {captured.err!r}"
    )
    # Numbered 1-indexed choices — assert substring presence of each
    # number+choice pair. The exact format ("1." vs "1)") is executor-latitude
    # but the load-bearing substring is the number followed by the choice.
    err = captured.err
    for idx, choice in enumerate(
        ["slow (90-110)", "fast (130-140)", "mixed"], start=1
    ):
        # Either "1." or "1)" is acceptable — check both
        marker_dot = f"{idx}. {choice}"
        marker_paren = f"{idx}) {choice}"
        assert marker_dot in err or marker_paren in err, (
            f"expected numbered choice '{marker_dot}' or '{marker_paren}' "
            f"in stderr; got {err!r}"
        )

    # Block 2: re-run hint with literal `library curate` command form +
    # theme echo (the user typed it, no PII leak vs Phase 99 precedent).
    assert "Re-run with:" in err, f"expected re-run hint; got {err!r}"
    assert "library curate" in err, (
        f"expected literal 'library curate' command in re-run hint; got {err!r}"
    )
    assert "ambiguous" in err, (
        f"expected theme echo in re-run hint; got {err!r}"
    )

    # stdout stays clean (Decision 6: non-success path goes to stderr only).
    # The handler emits the result JSON to STDERR (the existing non-success
    # path), so stdout MUST be empty.
    assert captured.out == "", (
        f"expected clean stdout on clarification (Decision 6); got {captured.out!r}"
    )


def test_build_set_exits_11_on_clarification(
    build_set_args: argparse.Namespace, lib_sentinel: object, capsys
) -> None:
    """Sibling parity with curate path: clarification → exit 11 + 2-block stderr
    render with 'library build-set' in the re-run hint (build-set takes ``brief``,
    not ``theme``)."""
    clarification = CodexCurateResult(
        theme="peak-time 60 min",
        stop_reason="clarification_needed",
        question="Which energy curve?",
        choices=["slow-build", "peak-time", "wave"],
    )
    build_set_args.brief = "peak-time 60 min"
    with patch(
        "vibemix.library.codex_curate.build_set_with_codex",
        return_value=clarification,
    ):
        rc = m._cmd_library_build_set_codex(build_set_args, lib_sentinel)

    captured = capsys.readouterr()
    assert rc == 11, (
        f"expected exit 11 on clarification_needed, got {rc!r}; "
        f"stderr={captured.err!r}"
    )
    assert "[viber/codex] clarification_needed:" in captured.err
    assert "Which energy curve?" in captured.err

    err = captured.err
    for idx, choice in enumerate(["slow-build", "peak-time", "wave"], start=1):
        marker_dot = f"{idx}. {choice}"
        marker_paren = f"{idx}) {choice}"
        assert marker_dot in err or marker_paren in err, (
            f"expected numbered choice '{marker_dot}' or '{marker_paren}' "
            f"in stderr; got {err!r}"
        )

    assert "Re-run with:" in err
    # build-set's re-run hint uses 'library build-set' (not 'library curate')
    assert "library build-set" in err, (
        f"expected literal 'library build-set' command in re-run hint; got {err!r}"
    )
    assert "peak-time 60 min" in err, (
        f"expected brief echo in re-run hint; got {err!r}"
    )


def test_telegram_curate_fn_normalizes_clarification() -> None:
    """The _normalize_codex_curate_result helper surfaces a clarification dict
    that Plan 100-05's telegram_bridge.format_reply will consume.

    Contract (Plan 100-04 extension):
        clarification result -> {"ok": False,
                                 "stop_reason": "clarification_needed",
                                 "question": <str>,
                                 "choices": list[str]}

    The 4 sub-assertions also pin:
    - cold path: created → None (existing contract, byte-equivalent regression)
    - cold path: tool_starvation → starvation dict (Phase 99 contract preserved)
    - defensive: clarification with None question + None choices → dict with
      question="" + choices=[] (matches the wrapper's defensive isinstance fallback
      from Plan 100-03's library/codex_curate.py:584-587)
    """
    clarification = CodexCurateResult(
        theme="x",
        stop_reason="clarification_needed",
        question="Q?",
        choices=["a", "b"],
    )
    normalized = m._normalize_codex_curate_result(clarification)
    assert normalized == {
        "ok": False,
        "stop_reason": "clarification_needed",
        "question": "Q?",
        "choices": ["a", "b"],
    }

    # Cold-path regression: created → None (Plan 99-06 contract).
    created = CodexCurateResult(
        theme="y",
        stop_reason="created",
        playlist_name="p",
    )
    assert m._normalize_codex_curate_result(created) is None

    # Phase 99 regression: tool_starvation still returns its dict shape
    # byte-equivalent. The Plan 99-06 contract MUST be preserved.
    starved = CodexCurateResult(
        theme="z",
        stop_reason="tool_starvation",
        error="hint",
    )
    assert m._normalize_codex_curate_result(starved) == {
        "ok": False,
        "stop_reason": "tool_starvation",
        "hint": "hint",
    }

    # Defensive: clarification with None fields → empty-string question +
    # empty-list choices (NOT None) so format_reply can iterate without
    # is-None checks. Mirrors the Phase 99 starvation hint=""  defensive shape.
    clarification_empty = CodexCurateResult(
        theme="w",
        stop_reason="clarification_needed",
        question=None,
        choices=None,
    )
    normalized_empty = m._normalize_codex_curate_result(clarification_empty)
    assert normalized_empty == {
        "ok": False,
        "stop_reason": "clarification_needed",
        "question": "",
        "choices": [],
    }
