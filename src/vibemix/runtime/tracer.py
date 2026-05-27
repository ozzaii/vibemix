# SPDX-License-Identifier: Apache-2.0
"""SessionTracer — a comprehensive, fail-soft, thread-safe per-session trace log.

Motivation
----------
The owner wanted to do a real DJ set (push controller buttons, mix tracks) and
afterward read, *in full entirety*, "what did what" — every event, state change,
MIDI action, AI call, TTS, suggestion — from a structured FILE, not copy-pasted
console output.

This is built ON the existing ``events.jsonl`` spine (``audio.recorder``
``VoiceRecorder.log_event``) rather than as a parallel writer. The tracer wraps a
``VoiceRecorder`` and writes richer, categorized records to ``trace.jsonl`` *next
to* ``events.jsonl`` in the same session dir, reusing the recorder's lock + the
session ``start_time`` so the two files share a single time origin and never race.

Record schema (one JSON object per line in ``trace.jsonl``)::

    {
      "ts_iso":  "2026-05-25T23:14:07.812+02:00",  # wall clock, ms precision
      "t_rel_s": 12.481,                            # seconds since session start
      "category": "EVENT",                          # see CATEGORIES below
      "event":    "emit",                           # short verb within category
      "detail":   { ... }                           # category-specific payload
    }

Categories (the "everywhere you can see" surface)::

    AUDIO       level / mic-gating transitions (debounced — never per-frame)
    STATE       MusicState refresh deltas (phase/bpm/deck/key/track change)
    EVENT       every EventDetector emit + which cooldown gated a candidate
    MIDI        every decoded controller action (button / fader / knob move)
    AI_CALL     model, prompt size, in_flight gate decision (incl. skips)
    AI_RESP     latency_ms, token usage, citation strip/bypass outcome, line
    TTS         text-to-speech start / chunk / done
    SUGGESTION  pill seed + chosen next-track + why / None
    WS          outbound frames (debounced)
    ERROR       any caught error worth a forensic line

Hard guarantees
---------------
- **Fail-soft, always.** Every public method swallows its own exceptions. A
  tracer error must NEVER crash a loop, wedge the ``in_flight`` gate, or perturb
  the single-writer / citation-grounding invariants. It is pure observation.
- **Thread-safe.** It writes through the recorder's own lock (audio thread, MIDI
  daemon thread, and the asyncio loop all share it), so trace lines interleave
  safely with ``events.jsonl`` writes.
- **Cheap.** Debounce helpers (``trace_audio_transition`` only logs on a *state
  change*; ``note_change`` only logs on a *value change*) keep the hot paths
  (10Hz refresh, OS audio callbacks, 30Hz WS) from spamming the file.
- **Privacy.** ``_scrub`` recursively redacts anything that looks like an API
  key / bearer token / JWT before it can reach disk. The trace file lives inside
  the (chmod 700) session dir — never under ~/.hermes, ~/.lmstudio, etc.

Enable knob
-----------
- ``VIBEMIX_TRACE`` env var. Default **ON** (the owner wants the full file).
  Set ``VIBEMIX_TRACE=0`` to disable file writes (a no-op disabled tracer is
  still safe to call everywhere — the instrumentation never branches).
- ``VIBEMIX_TRACE_STDERR=1`` additionally mirrors each line to stderr (verbose;
  default OFF so the console stays concise during a live set).

A ``None`` recorder (or a recorder without a usable session dir) yields a
``disabled`` tracer whose methods are all safe no-ops — so callers never have to
null-check.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from vibemix.audio import VoiceRecorder

CATEGORIES = (
    "AUDIO",
    "STATE",
    "EVENT",
    "MIDI",
    "AI_CALL",
    "AI_RESP",
    "TTS",
    "SUGGESTION",
    "WS",
    "ERROR",
)

# Patterns that mark a value as a secret to redact before it touches disk. Keys
# (by name) OR values (by shape) matching these are replaced with "***". This is
# defense-in-depth — instrumentation should not pass secrets in the first place,
# but the trace file must never leak one if a caller is careless.
_SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|secret|token|authorization|bearer|jwt|password|passwd)",
    re.IGNORECASE,
)
# A long opaque token: JWTs (xxx.yyy.zzz), Google AI keys (AIza...), generic
# 32+ char base64-ish blobs. Conservative — only redacts clearly-secret shapes.
_SECRET_VALUE_RE = re.compile(
    r"(eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{10,}"  # JWT
    r"|AIza[\w-]{20,}"  # Google API key
    r"|sk-[\w-]{20,}"  # OpenAI-style
    r")"
)


def _env_truthy(name: str, *, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off", "")


class SessionTracer:
    """Categorized, fail-soft trace writer layered on a ``VoiceRecorder``.

    Construct with ``SessionTracer.attach(recorder)`` — it derives the trace
    path from ``recorder.session_dir`` and reuses the recorder's lock +
    ``start_time``. If anything is missing or tracing is disabled by env, the
    returned tracer is a safe no-op.
    """

    def __init__(
        self,
        recorder: VoiceRecorder | None,
        *,
        enabled: bool,
        mirror_stderr: bool = False,
    ) -> None:
        self._recorder = recorder
        self._mirror_stderr = mirror_stderr
        self._f = None
        self._lock = None
        self._start_time: float = time.time()
        self.enabled = False  # flipped True only once the file is open

        if not enabled or recorder is None:
            return
        session_dir = getattr(recorder, "session_dir", None)
        if session_dir is None:
            return
        try:
            self._start_time = float(getattr(recorder, "start_time", time.time()))
            # Reuse the recorder's lock so trace.jsonl + events.jsonl writes
            # from the audio thread / MIDI thread / event loop never interleave
            # mid-line. Fall back to a private lock if the recorder has none.
            self._lock = getattr(recorder, "_lock", None)
            if self._lock is None:
                import threading

                self._lock = threading.Lock()
            self._f = open(session_dir / "trace.jsonl", "a", encoding="utf-8")
            self.enabled = True
        except Exception as e:
            print(f"[tracer init err] {e}", file=sys.stderr)
            self._f = None
            self.enabled = False

    # -- construction helper ------------------------------------------------

    @classmethod
    def attach(cls, recorder: VoiceRecorder | None) -> SessionTracer:
        """Build a tracer bound to ``recorder``, honoring the env knobs.

        ``VIBEMIX_TRACE`` (default ON) gates the file; ``VIBEMIX_TRACE_STDERR``
        (default OFF) mirrors lines to stderr. Never raises.
        """
        try:
            enabled = _env_truthy("VIBEMIX_TRACE", default=True)
            mirror = _env_truthy("VIBEMIX_TRACE_STDERR", default=False)
            return cls(recorder, enabled=enabled, mirror_stderr=mirror)
        except Exception as e:
            print(f"[tracer attach err] {e}", file=sys.stderr)
            return cls(None, enabled=False)

    # -- privacy scrub ------------------------------------------------------

    @classmethod
    def _scrub(cls, value: Any) -> Any:
        """Recursively redact secret-looking keys/values. Bounded depth so a
        cyclic / pathological payload can't blow the stack."""
        return cls._scrub_inner(value, _depth=0)

    @classmethod
    def _scrub_inner(cls, value: Any, *, _depth: int) -> Any:
        if _depth > 6:
            return "<...>"
        if isinstance(value, dict):
            out: dict[str, Any] = {}
            for k, v in value.items():
                if isinstance(k, str) and _SECRET_KEY_RE.search(k):
                    out[k] = "***"
                else:
                    out[k] = cls._scrub_inner(v, _depth=_depth + 1)
            return out
        if isinstance(value, (list, tuple)):
            return [cls._scrub_inner(v, _depth=_depth + 1) for v in value]
        if isinstance(value, str):
            return _SECRET_VALUE_RE.sub("***", value)
        return value

    # -- core write ---------------------------------------------------------

    def trace(self, category: str, event: str, **detail: Any) -> None:
        """Append one categorized record. The single low-level entry point that
        every convenience method routes through. Fully fail-soft."""
        if not self.enabled or self._f is None:
            return
        try:
            now = time.time()
            wall = datetime.now().astimezone()
            rec = {
                "ts_iso": wall.isoformat(timespec="milliseconds"),
                "t_rel_s": round(now - self._start_time, 3),
                "category": category,
                "event": event,
                "detail": self._scrub(detail),
            }
            line = json.dumps(rec, ensure_ascii=False)
            assert self._lock is not None
            with self._lock:
                self._f.write(line)
                self._f.write("\n")
                self._f.flush()
            if self._mirror_stderr:
                print(f"[trace {category}/{event}] {rec['detail']}", file=sys.stderr)
        except Exception:
            # A trace write failure is never allowed to surface. Swallow.
            pass

    # -- category convenience wrappers -------------------------------------
    # Thin verbs so call-sites read self-documenting; all route through trace().

    def audio(self, event: str, **detail: Any) -> None:
        self.trace("AUDIO", event, **detail)

    def state(self, event: str, **detail: Any) -> None:
        self.trace("STATE", event, **detail)

    def event(self, event: str, **detail: Any) -> None:
        self.trace("EVENT", event, **detail)

    def midi(self, event: str, **detail: Any) -> None:
        self.trace("MIDI", event, **detail)

    def ai_call(self, event: str, **detail: Any) -> None:
        self.trace("AI_CALL", event, **detail)

    def ai_resp(self, event: str, **detail: Any) -> None:
        self.trace("AI_RESP", event, **detail)

    def tts(self, event: str, **detail: Any) -> None:
        self.trace("TTS", event, **detail)

    def suggestion(self, event: str, **detail: Any) -> None:
        self.trace("SUGGESTION", event, **detail)

    def ws(self, event: str, **detail: Any) -> None:
        self.trace("WS", event, **detail)

    def error(self, event: str, **detail: Any) -> None:
        self.trace("ERROR", event, **detail)

    # -- debounced helpers (keep the hot paths cheap) ----------------------

    def note_change(
        self,
        category: str,
        event: str,
        key: str,
        new_value: Any,
        **detail: Any,
    ) -> None:
        """Emit a trace line ONLY when ``new_value`` differs from the last value
        seen under ``key``. Used for the 10Hz state refresh + level transitions
        so an unchanged field never produces a line.

        The detail records ``from`` / ``to`` so deltas are reconstructable.
        """
        if not self.enabled:
            return
        try:
            prev = self._last.get(key, _SENTINEL)
            if prev == new_value:
                return
            self._last[key] = new_value
            payload = {"key": key, "from": prev if prev is not _SENTINEL else None, "to": new_value}
            payload.update(detail)
            self.trace(category, event, **payload)
        except Exception:
            pass

    # -- lifecycle ----------------------------------------------------------

    def close(self) -> None:
        """Close the trace file. Best-effort; safe to call on a disabled tracer
        and safe to call more than once."""
        try:
            if self._f is not None:
                self.trace("STATE", "trace_close")
                self._f.flush()
                self._f.close()
        except Exception:
            pass
        finally:
            self._f = None
            self.enabled = False

    # per-instance debounce memory for note_change. Created lazily on first use
    # via __getattr__-free explicit attribute so disabled tracers stay cheap.
    @property
    def _last(self) -> dict[str, Any]:
        d = self.__dict__.get("_last_cache")
        if d is None:
            d = {}
            self.__dict__["_last_cache"] = d
        return d


# Unique sentinel so ``None`` is a legitimate tracked value distinct from "unset".
_SENTINEL: Any = object()
