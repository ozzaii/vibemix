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
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from vibemix.library.telegram_bridge import (
    TelegramBridge,
    build_bridge_from_env,
    format_reply,
    is_authorized,
    parse_allowed_chats,
    strip_leaks,
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
