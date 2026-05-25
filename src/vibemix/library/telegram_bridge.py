# SPDX-License-Identifier: Apache-2.0
"""Telegram bridge — the Viber agent's mobile surface.

Lets the user curate a playlist from their phone: send a theme ("90 min warm-up,
hypnotic, 122-126") to the bot, get back the grounded playlist. It runs the SAME
curation agent (Gemini or Codex) the CLI uses — Telegram is just a transport.

v1 auth = a **chat_id allow-list** (``VIBEMIX_TELEGRAM_ALLOWED_CHATS``): only
those chats are answered, everything else gets a flat "not authorized" and is
ignored. No public URL — LONG-POLL (``run_polling``), so it runs alongside the
desktop app with nothing to expose. Per-user == per-local-install (one user's
own library on their own machine).

Two layers, split for testing:

* **Pure logic** (dep-free, unit-tested): ``parse_allowed_chats`` /
  ``is_authorized`` / ``strip_leaks`` / ``format_reply``. No ``telegram`` import,
  no network.
* **Bot plumbing** (``TelegramBridge.run``): lazily imports ``telegram`` only
  when actually run, so importing this module (and the whole library package)
  never pulls the dep into the live co-host.

Privacy: ``strip_leaks`` scrubs absolute filesystem paths (home dir, /Users/...)
from every outbound message, so a curation result never leaks the user's local
paths into a chat. The agent's grounding (seen-set + library re-validation) still
holds — the bot only ever relays REAL library tracks, never invented ones.

No-hang: each curation runs under a hard wall-clock timeout in an executor so a
slow agent can never wedge the bot's poll loop; a timeout replies an honest
"took too long" rather than hanging.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Hard wall-clock per curation request (the agent is itself bounded; this is the
# belt-and-braces so one request can never park the poll loop).
CURATE_TIMEOUT_S = 90.0

# A curate_fn returns this normalized shape (the CLI adapts ViberAgent /
# CodexCurateResult to it), so format_reply stays backend-agnostic:
#   {"ok": bool, "name": str | None, "titles": list[str], "error": str | None}
CurateFn = Callable[[str], dict[str, Any]]

_ENV_TOKEN = "VIBEMIX_TELEGRAM_TOKEN"
_ENV_ALLOWED = "VIBEMIX_TELEGRAM_ALLOWED_CHATS"

# Matches POSIX home/abs paths and Windows paths so we never leak local FS layout
# into a chat message.
_PATH_RE = re.compile(r"(/[\w.\-]+){2,}|[A-Za-z]:\\[^\s]+|~/[\w./\-]+")


# --------------------------------------------------------------------------- #
# Pure logic (no telegram import; unit-tested)                                #
# --------------------------------------------------------------------------- #


def parse_allowed_chats(raw: str | None) -> set[int]:
    """Parse ``VIBEMIX_TELEGRAM_ALLOWED_CHATS`` ("123,456") → ``{123, 456}``.

    Non-integer tokens are skipped (defensive). Empty/None → empty set (which
    means NOBODY is authorized — fail-closed, never fail-open).
    """
    if not raw:
        return set()
    out: set[int] = set()
    for tok in raw.replace(";", ",").split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            out.add(int(tok))
        except ValueError:
            logger.warning("[telegram] ignoring non-integer chat id %r", tok)
    return out


def is_authorized(chat_id: int | None, allowed: set[int]) -> bool:
    """Fail-closed allow-list check. Unknown/None chat → not authorized."""
    return chat_id is not None and chat_id in allowed


def strip_leaks(text: str) -> str:
    """Scrub absolute filesystem paths from an outbound message (privacy)."""
    return _PATH_RE.sub("[path]", text)


def format_reply(norm: dict[str, Any]) -> str:
    """Render a normalized curation result into a chat message (leak-stripped).

    Honest: a failed/empty curation says so plainly; a success lists the tracks
    by ``artist - title`` (NO filesystem paths — the M3U lives on the user's
    machine, not in the chat).
    """
    if not norm.get("ok"):
        err = norm.get("error") or "no playlist could be built"
        return strip_leaks(f"⚠️ {err}")

    name = norm.get("name") or "playlist"
    titles = norm.get("titles") or []
    lines = [f"🎧 {name} ({len(titles)} tracks)"]
    for i, t in enumerate(titles, 1):
        lines.append(f"{i}. {t}")
    lines.append("\nSaved to your vibemix playlists folder.")
    return strip_leaks("\n".join(lines))


# --------------------------------------------------------------------------- #
# Bot plumbing (lazy telegram import; live-tested with a real token)          #
# --------------------------------------------------------------------------- #


class TelegramBridge:
    """Long-poll Telegram bot that routes authorized themes to ``curate_fn``."""

    def __init__(
        self,
        token: str,
        allowed_chat_ids: set[int],
        curate_fn: CurateFn,
        *,
        timeout_s: float = CURATE_TIMEOUT_S,
    ) -> None:
        self._token = token
        self._allowed = allowed_chat_ids
        self._curate_fn = curate_fn
        self._timeout_s = timeout_s

    async def _handle(self, update: Any, _context: Any) -> None:
        """Per-message handler: authorize → curate (executor + timeout) → reply.

        Returns (never raises) on every path so a bad message can't wedge the
        poll loop — the no-hang contract carried to the bot surface.
        """
        msg = getattr(update, "effective_message", None) or getattr(update, "message", None)
        chat = getattr(update, "effective_chat", None)
        chat_id = getattr(chat, "id", None)
        text = (getattr(msg, "text", None) or "").strip()
        if msg is None:
            return
        if not is_authorized(chat_id, self._allowed):
            logger.warning("[telegram] rejected unauthorized chat %r", chat_id)
            await msg.reply_text("not authorized")
            return
        if not text:
            await msg.reply_text("Send me a vibe or theme and I'll build a set.")
            return
        try:
            loop = asyncio.get_running_loop()
            norm = await asyncio.wait_for(
                loop.run_in_executor(None, self._curate_fn, text),
                timeout=self._timeout_s,
            )
        except asyncio.TimeoutError:
            await msg.reply_text("⚠️ that took too long — try a narrower theme.")
            return
        except Exception as e:  # noqa: BLE001 — never wedge the loop
            logger.warning("[telegram] curate failed: %s", e)
            await msg.reply_text("⚠️ something went wrong building that set.")
            return
        await msg.reply_text(format_reply(norm))

    def run(self) -> None:
        """Start the long-poll loop (blocking). Lazily imports telegram."""
        from telegram.ext import (  # lazy — only when actually running
            ApplicationBuilder,
            MessageHandler,
            filters,
        )

        app = ApplicationBuilder().token(self._token).build()
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle))
        logger.info(
            "[telegram] long-poll started (allow-list: %d chats)", len(self._allowed)
        )
        app.run_polling(drop_pending_updates=True)


def build_bridge_from_env(curate_fn: CurateFn) -> tuple[TelegramBridge | None, str | None]:
    """Build a bridge from env. Returns ``(bridge, error)`` — error is an
    actionable message (mirrors the api-key-missing / codex-not-installed UX)
    when the token or allow-list is missing, so the CLI can surface it."""
    token = os.environ.get(_ENV_TOKEN)
    if not token:
        return None, (
            f"No Telegram token. Set {_ENV_TOKEN} (from @BotFather) in your "
            ".env/environment to enable the mobile surface."
        )
    allowed = parse_allowed_chats(os.environ.get(_ENV_ALLOWED))
    if not allowed:
        return None, (
            f"No authorized chats. Set {_ENV_ALLOWED} to your numeric Telegram "
            "chat id(s) (comma-separated) — the allow-list IS the auth."
        )
    return TelegramBridge(token, allowed, curate_fn), None


__all__ = [
    "CURATE_TIMEOUT_S",
    "TelegramBridge",
    "build_bridge_from_env",
    "format_reply",
    "is_authorized",
    "parse_allowed_chats",
    "strip_leaks",
]
