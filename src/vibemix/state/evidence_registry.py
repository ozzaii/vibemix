# SPDX-License-Identifier: Apache-2.0
"""EvidenceRegistry — runtime anchor of cohost_v4's "trust the audio" rule.

The registry records every citable observation the AI may reference
(``ev`` event fires, ``aud`` audio features, ``midi`` controller moves,
``track`` IDs, ``screen`` captures, ``mix`` derived deck state,
``tend`` Kaan-profile facts) keyed by source + key, storing the
``t_session`` timestamp at append-only insertion.

EvidenceRegistry is the runtime anchor of cohost_v4's "trust the audio"
rule — the linter in Phase 20 reads it to verify every Gemini citation
maps to a real observation. v1.0 is **prompt-only seeding**: we record
observations and teach Gemini the citation grammar, but we do NOT enforce
or strip uncited / unbacked output. Phase 20 (GROUND-04..08) closes
threat T-18-01-05 by adding the linter + ack-bank fallback.

## Concurrency

The registry is a **single-Lock-guarded sync writer** — closes Pitfall P12
(registry race). Two threads write concurrently in production:
``state_refresh_loop`` (10Hz refresh-tick body) and
``EventDetector._fire`` (event-fire callback). Both run synchronously
inside their respective threads / loops, so a ``threading.Lock`` (NOT
``asyncio.Lock``) guards every mutation — matching the established
``MusicState`` pattern in ``src/vibemix/state/music_state.py``.

``snapshot()`` returns a deep copy with tuple-frozen inner lists so
readers (``AICoach.build_prompt``, the Phase 20 linter) can iterate
without holding the lock — closes T-18-01-03.

## Grammar regex

``EVIDENCE_CITATION_RE`` matches the EBNF grammar locked in
``18-CONTEXT.md §EBNF Grammar``: a bracketed ``source:body`` pair, with
optional comma-separated additional ``source:body`` pairs (the
multi-citation form). Whitespace inside brackets is rejected (the
linter in Phase 20 strips invalid forms; v1.0 just declines to match).

The body shape is intentionally permissive in v1.0 — we accept any
non-bracket, non-whitespace, non-comma sequence so prompt-only seeding
does not reject valid Gemini output that drifts in shape early. Phase 20
will tighten per-source body grammar.

Plan 25-02 adds ``register_library`` so ``[track:<id>]`` citations
resolve against the user's real Rekordbox collection.
"""

from __future__ import annotations

import asyncio
import collections
import re
import sys
import threading
from typing import TYPE_CHECKING, Any, Awaitable, Callable

if TYPE_CHECKING:  # pragma: no cover — type-only import
    from vibemix.library.rekordbox import RekordboxLibrary

__all__ = [
    "EVIDENCE_CITATION_RE",
    "EVIDENCE_SOURCES",
    "EvidenceRegistry",
    "parse_citations",
]


# --------------------------------------------------------------------------- #
# Plan 41-02 — mutation-driven cache refresh defaults                          #
# --------------------------------------------------------------------------- #

#: Debounce window — observations land in bursts during track changes and
#: mixing, so we wait this long after the LAST mutation before firing the
#: cache refresh. 5s is the lower bound from the locked design (research
#: §Pattern 2). Tests parameterize to sub-second values for fast execution.
DEFAULT_MUTATION_DEBOUNCE_S: float = 5.0

#: Minimum interval between cache.refresh() invocations. Even under sustained
#: churn we will not re-create the explicit cache more than once per 30s —
#: the implicit Gemini cache absorbs the unchanging prefix anyway, and the
#: explicit cache.create() round-trips are not free.
DEFAULT_MIN_REFRESH_INTERVAL_S: float = 30.0


# --------------------------------------------------------------------------- #
# Locked grammar surface                                                       #
# --------------------------------------------------------------------------- #

#: The 7 EBNF source identifiers locked in 18-CONTEXT.md §EBNF Grammar.
#: ``ev`` = event-detector fire; ``aud`` = audio feature (RMS/BPM/bands);
#: ``midi`` = controller move; ``track`` = nowplaying-cli track id;
#: ``screen`` = djay screen-capture region; ``mix`` = derived mix state
#: (``audible_deck`` etc.); ``tend`` = Kaan-profile fact (Phase 26 hook).
#: Phase 20 linter consumes this for source-validity checks.
EVIDENCE_SOURCES: frozenset[str] = frozenset(
    {"ev", "aud", "midi", "track", "screen", "mix", "tend"}
)


# Inner-form atom: ``<source>:<body>`` where body is non-bracket, non-whitespace,
# non-comma. Comma is excluded so the multi-citation regex can split cleanly
# on it. Bracket + whitespace exclusion enforces the LOCKED grammar
# (no nested brackets, no internal spaces).
_SOURCE_ALT = "ev|aud|midi|track|screen|mix|tend"
_INNER_ATOM = rf"(?:{_SOURCE_ALT}):[^\s,\]]+"

#: Compiled regex matching the LOCKED EBNF grammar:
#:
#:   citation := '[' atom ( ',' atom )* ']'
#:   atom     := source ':' body
#:   source   := 'ev' | 'aud' | 'midi' | 'track' | 'screen' | 'mix' | 'tend'
#:   body     := one-or-more chars excluding whitespace, ']', ','
#:
#: Matches the 7 single-citation forms + the comma-joined multi-citation
#: form in one pass. Empty ``[]`` is rejected (body requires at least one
#: char). Whitespace inside brackets is rejected.
EVIDENCE_CITATION_RE: re.Pattern[str] = re.compile(
    rf"\[{_INNER_ATOM}(?:,{_INNER_ATOM})*\]"
)


# --------------------------------------------------------------------------- #
# Registry                                                                     #
# --------------------------------------------------------------------------- #


class EvidenceRegistry:
    """Append-only, lock-guarded store of citable observations.

    Internal storage shape:
        ``dict[source, dict[key, list[t_session]]]``

    The registry is **permissive** in v1.0 — any string ``source`` / ``key``
    is accepted. The grammar regex enforces shape at the prompt + linter
    boundary (Phase 20), NOT at the registry. This lets future Phase 17
    detectors land new event types without a cross-plan code change.

    Thread-safety: every read + write acquires ``self._lock``. Writers
    (``state_refresh_loop`` tick body + ``EventDetector._fire``) and
    readers (``AICoach.build_prompt``, telemetry, Phase 20 linter)
    contend through the same gate. Snapshot returns a deep copy with
    tuple-frozen inner lists so callers can iterate lock-free.
    """

    def __init__(
        self,
        *,
        on_mutation: Callable[[], Awaitable[Any]] | None = None,
        mutation_debounce_s: float = DEFAULT_MUTATION_DEBOUNCE_S,
        min_refresh_interval_s: float = DEFAULT_MIN_REFRESH_INTERVAL_S,
    ) -> None:
        self._data: dict[str, dict[str, list[float]]] = {}
        self._lock: threading.Lock = threading.Lock()
        # Plan 18-04 — rolling buffer of per-turn citation counts. deque
        # maxlen=50 caps the window at the LAST 50 Gemini turns so the
        # rolling mean reflects current emission rate (not lifetime). The
        # ``_total_turns`` counter is unbounded — Phase 16 ear-test reads
        # it as the "turns observed" denominator, so it must NOT cap.
        # Same single-Lock contract as the source-dict writes (closes P12).
        self._citation_buffer: collections.deque[int] = collections.deque(maxlen=50)
        self._total_turns: int = 0
        # ----- Plan 41-02 — mutation-driven cache-refresh hook -----
        # ``on_mutation`` is a callable returning an awaitable (e.g.
        # ``lambda: cache.refresh()``). When set, every ``write()``
        # cancels-and-reschedules a debounced asyncio timer that fires the
        # callback on the running loop. Min-interval guard caps the fire
        # rate so a sustained mutation burst can re-create the cache at
        # most once per ``min_refresh_interval_s`` (Pitfall 2 — callback
        # storm during heavy mixing).
        #
        # If no running event loop exists at ``write()`` time (e.g. unit
        # tests poking the registry from sync code) the scheduler silently
        # no-ops — the callback is best-effort, not a correctness gate.
        # Production wiring runs inside ``state_refresh_loop`` so the loop
        # is always available.
        self._on_mutation: Callable[[], Awaitable[Any]] | None = on_mutation
        self._debounce_s: float = mutation_debounce_s
        self._min_interval_s: float = min_refresh_interval_s
        self._pending_refresh_handle: asyncio.TimerHandle | None = None
        self._last_refresh_at: float | None = None

    # --- writes ---------------------------------------------------------- #

    def write(self, source: str, key: str, t_session: float) -> None:
        """Append one observation to ``(source, key)``.

        Synchronous, lock-guarded. Called from ``state_refresh_loop`` tick
        body and ``EventDetector._fire`` (Plan 18-02 wiring). No validation
        in v1.0 — the grammar regex is the validation layer at the prompt
        boundary.

        Plan 41-02: every mutation also schedules a debounced cache-refresh
        callback (if ``on_mutation`` was wired at construction). The
        scheduler is a no-op when no running loop is available, so unit-test
        writers from synchronous code don't fail.
        """
        with self._lock:
            inner = self._data.setdefault(source, {})
            inner.setdefault(key, []).append(t_session)
        self._schedule_refresh()

    def clear(self) -> None:
        """Reset the registry — called from ``VoiceRecorder.close()`` per session.

        Plan 18-02 wires this into the per-session lifecycle so observations
        do not leak across DJ sessions.

        Plan 18-04: also resets the citation-count rolling buffer + total-
        turns counter so telemetry doesn't leak across sessions either.
        """
        with self._lock:
            self._data.clear()
            self._citation_buffer.clear()
            self._total_turns = 0

    # --- library wiring (Plan 25-02) ------------------------------------ #

    def register_library(
        self,
        lib: RekordboxLibrary | object,
        t_session: float = 0.0,
    ) -> int:
        """Register every track in ``lib`` as a ``track:<id>`` observation.

        Phase 18 EvidenceRegistry already lists ``track`` as a valid source
        in ``EVIDENCE_SOURCES``. The Phase 20 ``CitationLinter`` walks
        ``EVIDENCE_CITATION_RE`` matches and calls ``has(source, key, t_target)``
        to gate Gemini output — registering the user's real Rekordbox track
        IDs here lets ``[track:<id>]`` citations resolve against their
        collection instead of nowplaying-cli ghost-text only.

        ``t_session=0.0`` is the canonical "library load" timestamp — it's
        the moment of session start so any in-session citation lookup
        (tol=±1.0s live, ±2.0s debrief per GROUND-07) falls outside this
        window unless the linter explicitly skips the timestamp check for
        the ``track`` source. Plan 25-03 wires linter behavior — for v2.0
        this method just exposes the registration primitive.

        Argument typing accepts the canonical ``RekordboxLibrary`` (via
        TYPE_CHECKING import) but the runtime path uses duck-typed access
        — any object with a ``tracks`` mapping works, which keeps tests
        lightweight (no need to instantiate the full library for registry
        coverage).

        Returns the number of entries registered. Idempotent on identical
        inputs — duplicate calls append duplicate ``t_session`` values to
        the same key, but ``has()`` checks any-of so the read path is
        unaffected.
        """
        tracks_map = getattr(lib, "tracks", None)
        if not isinstance(tracks_map, dict):
            return 0
        count = 0
        with self._lock:
            inner = self._data.setdefault("track", {})
            for track_id in tracks_map:
                inner.setdefault(str(track_id), []).append(t_session)
                count += 1
        # Plan 41-02 — bulk mutation also schedules a debounced refresh
        # (debounce will coalesce this with any concurrent write() calls).
        if count:
            self._schedule_refresh()
        return count

    # --- reads ----------------------------------------------------------- #

    def snapshot(self) -> dict[str, dict[str, tuple[float, ...]]]:
        """Return a deep copy with inner lists frozen as tuples.

        Mutating the returned dict (popping a source, etc.) MUST NOT affect
        the registry — see ``test_evidence_04_snapshot_is_frozen_DLOCKED``.
        Inner tuples are immutable by construction.

        Cost is O(N) over total observations; with the cohost_v4 cooldown
        gates a 1h DJ session caps at ~500 observations across all sources,
        so a snapshot fits well under 1ms — cheap enough to call per Gemini
        prompt build (Plan 18-03 wires this into ``AICoach.build_prompt``).
        """
        with self._lock:
            return {
                src: {k: tuple(v) for k, v in inner.items()}
                for src, inner in self._data.items()
            }

    def has(
        self,
        source: str,
        key: str,
        t_target: float,
        tol: float = 1.0,
    ) -> bool:
        """Return True iff some observation at ``(source, key)`` lies within ±tol.

        Boundary INCLUSIVE at exactly ``tol`` per Phase 20
        §"per-mode tolerance bands". Phase 20 linter calls this with
        ``tol=1.0`` for live mode and ``tol=2.0`` for debrief mode per
        GROUND-07 — the API is mode-agnostic; tolerance is a kwarg.

        Missing source or key returns False (no KeyError).
        """
        with self._lock:
            inner = self._data.get(source)
            if inner is None:
                return False
            timestamps = inner.get(key)
            if timestamps is None:
                return False
            return any(abs(t - t_target) <= tol for t in timestamps)

    # --- citation telemetry (Plan 18-04) -------------------------------- #

    def record_citation_count(self, n: int) -> None:
        """Append one Gemini-turn citation count to the rolling buffer.

        Called from ``DJCoHostAgent.llm_node`` AFTER the response stream
        completes (BEFORE the suppression gate so silence/slop turns are
        also counted — Phase 16 needs Gemini's true emission rate).

        Lock-guarded — same contract as ``write()``. ``deque(maxlen=50)``
        auto-evicts the oldest entry when the buffer is full; the
        ``_total_turns`` counter is unbounded.
        """
        with self._lock:
            self._citation_buffer.append(n)
            self._total_turns += 1

    def citation_telemetry(self) -> dict[str, int | float]:
        """Return the rolling-50-turn citation-count snapshot.

        Returns:
            ``{"window_size": <int 0..50>, "mean": <float>,
               "total_turns_observed": <int>}``

        ``mean`` is a Python float; no rounding here — Phase 16 ear-test
        and the Phase 20 stripped_rate guard own display rounding.
        Empty-buffer (no record_citation_count() calls yet) returns
        ``mean=0.0`` (not NaN, not None) so callers don't have to special-
        case the cold-start state.

        Lock-guarded snapshot — call cost is O(window_size) for the sum,
        bounded at 50, so well under 1µs per call. Phase 16 may poll this
        per second without contention impact on the writer paths.
        """
        with self._lock:
            window_size = len(self._citation_buffer)
            mean = (
                sum(self._citation_buffer) / window_size if window_size else 0.0
            )
            return {
                "window_size": window_size,
                "mean": mean,
                "total_turns_observed": self._total_turns,
            }

    # --- mutation-driven refresh scheduler (Plan 41-02) ------------------ #

    def _schedule_refresh(self) -> None:
        """Cancel-and-reschedule the debounced refresh timer.

        Called from ``write()`` + ``register_library()`` after every
        observation lands. Pattern: capture the running loop; cancel any
        in-flight timer handle; compute a delay = ``max(debounce,
        min_interval - elapsed_since_last_refresh)``; schedule a fresh
        ``call_later`` that, when fired, marks ``_last_refresh_at`` and
        kicks off ``_run_callback`` as a task.

        Silently no-ops in three cases:
          - ``on_mutation`` is None (callback wiring is optional).
          - No running event loop (e.g. synchronous test code poking
            ``write()``). RuntimeError from ``get_running_loop`` is
            swallowed — the callback is a latency optimisation, not a
            correctness gate.
        """
        if self._on_mutation is None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # no running loop → silently skip; sync caller is fine

        now = loop.time()
        if self._pending_refresh_handle is not None:
            self._pending_refresh_handle.cancel()
            self._pending_refresh_handle = None

        delay = self._debounce_s
        if self._last_refresh_at is not None:
            elapsed = now - self._last_refresh_at
            if elapsed < self._min_interval_s:
                delay = max(delay, self._min_interval_s - elapsed)

        def _fire() -> None:
            self._pending_refresh_handle = None
            self._last_refresh_at = loop.time()
            asyncio.create_task(self._run_callback())

        self._pending_refresh_handle = loop.call_later(delay, _fire)

    async def _run_callback(self) -> None:
        """Invoke ``on_mutation`` exception-safe.

        Pitfall 2 — never let a cache-refresh failure kill the registry.
        The callback is best-effort. We log to stderr (matches the cohost
        ``[cache refresh]`` convention) and swallow.
        """
        callback = self._on_mutation
        if callback is None:
            return
        try:
            awaitable = callback()
            if awaitable is not None:
                await awaitable
        except Exception as exc:  # pragma: no cover — log path
            print(
                f"[evidence registry] on_mutation callback failed: {exc!r}",
                file=sys.stderr,
            )

    # --- introspection --------------------------------------------------- #

    def __len__(self) -> int:
        """Total observation count across all sources / keys.

        Used by Plan 18-04 telemetry rolling-average sanity check + Phase 20
        linter telemetry for "registry-size vs citation-count" health bars.
        """
        with self._lock:
            return sum(len(v) for inner in self._data.values() for v in inner.values())


# --------------------------------------------------------------------------- #
# Parser helper                                                                #
# --------------------------------------------------------------------------- #


def parse_citations(text: str) -> list[tuple[str, str]]:
    """Walk ``text`` and yield ``(source, body)`` pairs for every citation atom.

    Handles both single-citation forms (``[ev:KICK_SWAP@45.2]``) and the
    comma-joined multi-citation form (``[ev:KICK_SWAP@45.2,aud:bpm@45.0]``)
    in a single pass via ``EVIDENCE_CITATION_RE``.

    Each atom is split on the FIRST ``:`` so the body retains any inner
    structure (the ``key@t`` shape for ``ev`` / ``aud`` / ``midi`` or the
    free-form key for ``track`` / ``screen`` / ``mix`` / ``tend``).

    v1.0 callers MUST NOT rely on the inner-body shape being parsed
    further (e.g., splitting key from ``@t``) — that's Phase 20 territory
    and locking the inner shape now would force a v2 API change when
    Phase 20 tightens per-source body grammar.

    Returns an empty list if no citations match — never raises on
    malformed input (regex misses are silently skipped, satisfying
    threat T-18-01-04 mitigation).

    Used by Plan 18-04 telemetry (citation-count parsing) and Phase 20
    linter (per-citation grounding lookup against ``EvidenceRegistry``).
    """
    out: list[tuple[str, str]] = []
    for match in EVIDENCE_CITATION_RE.finditer(text):
        # Strip the surrounding `[` `]` then split on `,` to get atoms.
        body = match.group(0)[1:-1]
        for atom in body.split(","):
            source, _, atom_body = atom.partition(":")
            out.append((source, atom_body))
    return out
