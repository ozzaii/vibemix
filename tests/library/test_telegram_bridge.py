# SPDX-License-Identifier: Apache-2.0
"""Telegram bridge — pure logic + message routing. No `telegram` import at
module level (the bridge lazy-imports it inside run()), so these tests need no
bot, no network, no token.

Pins: fail-closed allow-list, path-leak scrubbing (privacy), honest reply
formatting, and the handler routing (authorize → curate-in-executor → reply),
including the no-hang timeout + error degrade.
"""

from __future__ import annotations

import asyncio
import tomllib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from vibemix.library.telegram_bridge import (
    CURATE_TIMEOUT_S,
    TelegramBridge,
    TelegramDependencyError,
    build_bridge_from_env,
    format_reply,
    is_authorized,
    parse_allowed_chats,
    strip_leaks,
    telegram_dependency_error,
)

# -- pure logic ------------------------------------------------------------- #


def test_parse_allowed_chats():
    assert parse_allowed_chats("123,456") == {123, 456}
    assert parse_allowed_chats(" 123 ; 456 ") == {123, 456}
    assert parse_allowed_chats("123,oops,456") == {123, 456}  # skips junk
    assert parse_allowed_chats("") == set()
    assert parse_allowed_chats(None) == set()


def test_is_authorized_fail_closed():
    allowed = {42}
    assert is_authorized(42, allowed) is True
    assert is_authorized(99, allowed) is False
    assert is_authorized(None, allowed) is False
    assert is_authorized(42, set()) is False  # empty allow-list = nobody


def test_strip_leaks_scrubs_paths():
    assert "/Users/ozai" not in strip_leaks("saved to /Users/ozai/.cache/vibemix/x.m3u8")
    assert "[path]" in strip_leaks("saved to /Users/ozai/.cache/vibemix/x.m3u8")
    assert strip_leaks("just a vibe, no path") == "just a vibe, no path"


def test_format_reply_success_lists_tracks_no_paths():
    out = format_reply(
        {"ok": True, "name": "Warm-Up", "titles": ["A - One", "B - Two"]}
    )
    assert "Warm-Up (2 tracks)" in out
    assert "1. A - One" in out and "2. B - Two" in out
    # No filesystem path leaks into the chat.
    assert "/Users/" not in out and ".m3u8" not in out


def test_format_reply_failure_is_honest():
    out = format_reply({"ok": False, "error": "no playlist (max_iters)"})
    assert "no playlist" in out
    assert out.startswith("⚠️")


# -- Plan 99-07: tool_starvation branch + regression-pin --------------------- #
#
# Closes the Telegram leg of HARDEN-RETRY-07: Plan 99-06's
# `_normalize_codex_curate_result` helper emits
#   {"ok": False, "stop_reason": "tool_starvation", "hint": "<text>"}
# and `format_reply` renders the hint via `strip_leaks` (privacy preserved).
# Phase 100's `clarification_needed` shape will be a sibling branch — the
# starvation branch sits BEFORE the generic `if not norm.get("ok")` block so
# the generic branch (which matches ok=False) doesn't shadow it.


def test_format_reply_starvation_branch():
    """tool_starvation hint is rendered as a single warning-glyph line."""
    out = format_reply(
        {
            "ok": False,
            "stop_reason": "tool_starvation",
            "hint": "library has 0 tracks — run `library ingest` first",
        }
    )
    assert isinstance(out, str) and out
    assert "library has 0 tracks" in out
    # Mirrors the existing error branch's glyph convention (test_format_reply_failure_is_honest).
    assert out.startswith("⚠️")
    # Single line — NOT numbered choices (that's Phase 100's clarification_needed shape).
    assert "1." not in out


def test_format_reply_starvation_strips_leaks():
    """FS paths in the hint are scrubbed by `strip_leaks` defensively (T-99-05)."""
    out = format_reply(
        {
            "ok": False,
            "stop_reason": "tool_starvation",
            "hint": "library has 0 tracks at /Users/ozai/.cache/vibemix/library.pkl",
        }
    )
    # Mirrors test_strip_leaks_scrubs_paths assertion style.
    assert "/Users/ozai" not in out
    assert "[path]" in out
    # The non-path portion of the hint survives the scrub.
    assert "library has 0 tracks" in out


# Regression-pin: byte-equivalent rendering of the canonical playlist
# happy-path. Captured from current source (pre-Task-2) — Task 2's insertion
# must NOT change this output.
EXPECTED_PLAYLIST_OUTPUT = (
    "🎧 Warm-Up (2 tracks)\n"
    "1. A - One\n"
    "2. B - Two\n"
    "\n"
    "Saved to your vibemix playlists folder."
)

# Plan 100-05 regression-pin: byte-equivalent rendering of the canonical
# starvation render. Captured from current source (pre-Plan-100-05). Plan
# 100-05's clarification_needed branch insertion must NOT change this output —
# `test_format_reply_existing_branches_unchanged` enforces byte-equivalence.
EXPECTED_STARVATION_OUTPUT = "⚠️ library has 0 tracks — run `library ingest` first"


def test_format_reply_existing_branches_unchanged():
    """Playlist + generic-error + starvation branches stay byte-equivalent."""
    out = format_reply(
        {"ok": True, "name": "Warm-Up", "titles": ["A - One", "B - Two"]}
    )
    assert out == EXPECTED_PLAYLIST_OUTPUT
    # Generic error branch also stays byte-equivalent (no stop_reason key).
    err_out = format_reply({"ok": False, "error": "no playlist (max_iters)"})
    assert err_out == "⚠️ no playlist (max_iters)"
    # Plan 100-05 extension: Phase 99 tool_starvation branch stays byte-equivalent
    # after Plan 100-05's clarification_needed branch lands above the generic
    # `if not norm.get("ok")` block. Drift here = a Plan 100-05 edit accidentally
    # nudged the Phase 99 contract.
    starv_out = format_reply(
        {
            "ok": False,
            "stop_reason": "tool_starvation",
            "hint": "library has 0 tracks — run `library ingest` first",
        }
    )
    assert starv_out == EXPECTED_STARVATION_OUTPUT


# -- Phase 100 HARDEN-CLARIFY-05 — clarification format_reply branch --------- #
#
# Closes the Telegram leg of HARDEN-CLARIFY-05. After Plan 100-04's
# `_normalize_codex_curate_result` extension emits
#   {"ok": False, "stop_reason": "clarification_needed",
#    "question": "<str>", "choices": list[str]}
# `format_reply` renders the question + numbered choices as a multi-line
# message, leak-stripped through `strip_leaks`. Single-turn semantic
# (CONTEXT.md Decision 7): no inline-keyboard buttons — the user re-composes
# the next theme manually. The branch sits BETWEEN the existing tool_starvation
# branch (Phase 99) and the existing generic `if not norm.get("ok")` block —
# same insertion-order discipline as Plan 99-07 (BEFORE the generic, because
# the clarification payload also carries ok=False).


def test_format_reply_clarification_branch():
    """clarification_needed renders question header + numbered choices."""
    out = format_reply(
        {
            "ok": False,
            "stop_reason": "clarification_needed",
            "question": "What BPM range?",
            "choices": ["slow (90-110)", "fast (130-140)", "mixed"],
        }
    )
    assert isinstance(out, str) and out
    # Question header survives.
    assert "What BPM range?" in out
    # Numbered choices — 1-indexed, consistent with the CLI surface (Plan 100-04).
    # Load-bearing: the integer + the choice text on the same line, in order.
    assert "1." in out and "slow (90-110)" in out
    assert "2." in out and "fast (130-140)" in out
    assert "3." in out and "mixed" in out
    # Discriminating leading glyph distinct from ⚠️ (the tool_starvation +
    # generic error branches' glyph). Visually signals "needs user input" vs
    # "error" — CONTEXT.md doesn't lock the glyph; executor picks one consistent
    # with anti-slop tone (❓ is the chosen one in the Plan 100-05 SUMMARY).
    assert not out.startswith("⚠️")


def test_format_reply_clarification_strips_leaks():
    """FS paths in the question or choices are scrubbed by `strip_leaks` (T-100-05-01)."""
    out = format_reply(
        {
            "ok": False,
            "stop_reason": "clarification_needed",
            "question": "Library at /Users/ozai/.cache/vibemix — context?",
            "choices": ["bedroom", "club"],
        }
    )
    # Mirrors test_strip_leaks_scrubs_paths assertion style.
    assert "/Users/ozai" not in out
    assert "[path]" in out
    # The non-path portions of the question + choices survive the scrub.
    assert "context?" in out
    assert "bedroom" in out and "club" in out


# -- env wiring ------------------------------------------------------------- #


def test_build_bridge_requires_token(monkeypatch):
    monkeypatch.delenv("VIBEMIX_TELEGRAM_TOKEN", raising=False)
    bridge, err = build_bridge_from_env(lambda t: {"ok": True})
    assert bridge is None and err is not None
    assert "VIBEMIX_TELEGRAM_TOKEN" in err


def test_build_bridge_requires_allowlist(monkeypatch):
    monkeypatch.setenv("VIBEMIX_TELEGRAM_TOKEN", "fake-token")
    monkeypatch.delenv("VIBEMIX_TELEGRAM_ALLOWED_CHATS", raising=False)
    bridge, err = build_bridge_from_env(lambda t: {"ok": True})
    assert bridge is None and "ALLOWED_CHATS" in (err or "")


def test_build_bridge_ok(monkeypatch):
    monkeypatch.setenv("VIBEMIX_TELEGRAM_TOKEN", "fake-token")
    monkeypatch.setenv("VIBEMIX_TELEGRAM_ALLOWED_CHATS", "7,8")
    bridge, err = build_bridge_from_env(lambda t: {"ok": True})
    assert err is None and bridge is not None


def test_telegram_transport_dependency_is_optional() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    deps = data["project"]["dependencies"]
    extras = data["project"]["optional-dependencies"]

    assert not any("python-telegram-bot" in dep for dep in deps)
    assert extras["telegram"] == ["python-telegram-bot>=21"]


def test_telegram_default_timeout_matches_viber_set_prep_budget() -> None:
    assert CURATE_TIMEOUT_S >= 180.0
    bridge = TelegramBridge("t", {42}, lambda theme: {"ok": True})
    assert bridge._timeout_s == CURATE_TIMEOUT_S


def test_telegram_dependency_error_is_actionable(monkeypatch):
    import vibemix.library.telegram_bridge as bridge_mod

    def missing():
        raise TelegramDependencyError("install the telegram extra")

    monkeypatch.setattr(bridge_mod, "_load_telegram_ext", missing)
    assert telegram_dependency_error() == "install the telegram extra"


# -- handler routing (mock update; no telegram needed) ---------------------- #


def _update(chat_id, text):
    msg = SimpleNamespace(text=text, reply_text=AsyncMock())
    return SimpleNamespace(
        effective_message=msg,
        message=msg,
        effective_chat=SimpleNamespace(id=chat_id),
    )


def test_handler_rejects_unauthorized():
    bridge = TelegramBridge("t", {42}, lambda theme: {"ok": True, "name": "X", "titles": []})
    upd = _update(999, "hard techno")
    asyncio.run(bridge._handle(upd, None))
    upd.effective_message.reply_text.assert_awaited_once_with("not authorized")


def test_handler_authorized_curates_and_replies():
    called = {}

    def curate(theme):
        called["theme"] = theme
        return {"ok": True, "name": "Set", "titles": ["A - One"]}

    bridge = TelegramBridge("t", {42}, curate)
    upd = _update(42, "rolling hypnotic")
    asyncio.run(bridge._handle(upd, None))
    assert called["theme"] == "rolling hypnotic"
    reply = upd.effective_message.reply_text.await_args.args[0]
    assert "Set (1 tracks)" in reply and "A - One" in reply


def test_handler_empty_text_prompts():
    bridge = TelegramBridge("t", {42}, lambda theme: {"ok": True})
    upd = _update(42, "   ")
    asyncio.run(bridge._handle(upd, None))
    reply = upd.effective_message.reply_text.await_args.args[0]
    assert "theme" in reply.lower() or "vibe" in reply.lower()


def test_handler_timeout_degrades_not_hangs():
    def slow(theme):
        import time

        time.sleep(5)
        return {"ok": True}

    bridge = TelegramBridge("t", {42}, slow, timeout_s=0.05)
    upd = _update(42, "x")
    asyncio.run(bridge._handle(upd, None))
    reply = upd.effective_message.reply_text.await_args.args[0]
    assert "too long" in reply


def test_handler_curate_exception_degrades():
    def boom(theme):
        raise RuntimeError("kaboom")

    bridge = TelegramBridge("t", {42}, boom)
    upd = _update(42, "x")
    asyncio.run(bridge._handle(upd, None))
    reply = upd.effective_message.reply_text.await_args.args[0]
    assert "went wrong" in reply
