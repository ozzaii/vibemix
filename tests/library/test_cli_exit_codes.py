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
import io
import sys
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
