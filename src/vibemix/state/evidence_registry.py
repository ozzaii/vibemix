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
"""

from __future__ import annotations

import collections
import re
import threading

__all__ = [
    "EVIDENCE_CITATION_RE",
    "EVIDENCE_SOURCES",
    "EvidenceRegistry",
    "parse_citations",
]


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

    def __init__(self) -> None:
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

    # --- writes ---------------------------------------------------------- #

    def write(self, source: str, key: str, t_session: float) -> None:
        """Append one observation to ``(source, key)``.

        Synchronous, lock-guarded. Called from ``state_refresh_loop`` tick
        body and ``EventDetector._fire`` (Plan 18-02 wiring). No validation
        in v1.0 — the grammar regex is the validation layer at the prompt
        boundary.
        """
        with self._lock:
            inner = self._data.setdefault(source, {})
            inner.setdefault(key, []).append(t_session)

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
