# SPDX-License-Identifier: Apache-2.0
"""DeckPoller — the read-only deck-state producer (Phase 59-04 DECK-02/05).

The THIRD external snapshot producer after ``midi.state.ControllerState`` and
``platform._track_macos.TrackInfo``. Like them it owns a ``threading.Lock`` and
a ``.snapshot()`` that returns copies the caller cannot mutate. It NEVER writes
``MusicState`` — ``state_refresh_loop._tick_once`` is the only thing that copies
``snapshot()`` into ``MusicState.deck_state`` under ``state._lock`` (the
single-writer rule, DECK-04).

Source ladder (highest-confidence-wins, RESEARCH §Pattern 2):

    ① pyrekordbox XML library match   (PRIMARY enrichment, this phase)
    ② Gemini-vision deck-panel read   (UNIVERSAL identity, Plan 59-05 — slot only)
    ③ numpy KS/Temperley key estimate (FALLBACK, deferred Open Q2 — slot only)

The first source clearing its confidence floor wins; below every floor a deck
reads as honest ``unknown`` (``confidence=0``, ``source="unknown"``, all harmonic
fields ``None``). The ``camelot`` field is left ``None`` here on purpose — the
single-writer normalizes it via ``harmonics.to_camelot`` inside the lock batch so
the pure ``µs``-cost transform stays on the writer side (RESEARCH §Code Examples).

Cross-deck suppression (RESEARCH §Pattern 3 + Pitfall 4): a deck the poller
cannot INDEPENDENTLY resolve gets ``confidence=0`` — the silent / non-audible
deck must resolve via its own source signal (a future vision badge or a
confidently-attributed library match), NEVER by "the other now-playing title".
This is what makes Phase 60's cross-deck clash uncitable-by-construction.

Read-only guarantee (DECK-05): the poller reuses the already-loaded, cache-warm
``RekordboxLibrary`` (XML import path only) — it opens NO DJ-software DB and the
banned SQLCipher live-database class stays dead behind the grep-gate + dormancy
test + the ``pyproject.toml`` wheel exclusion (asserted by
``tests/repo/test_repo_scrub.py::test_deck_readonly``).

Graceful degradation (mirrors ``TrackInfo.poll_once``): every external read
swallows its own exception and returns last-known state — no exception escapes
``poll_once()`` / ``snapshot()``. No log spam.
"""

from __future__ import annotations

import asyncio
import sys
import threading
import time
from typing import TYPE_CHECKING

from vibemix.state.deck_state import DeckTrack
from vibemix.state.track_resolver import derive_audible_deck

if TYPE_CHECKING:
    from vibemix.library.rekordbox import RekordboxLibrary

# ---------------------------------------------------------------------- #
# Confidence floors / citation gate                                       #
# ---------------------------------------------------------------------- #

# Per-source confidence floors. XML is a pre-analyzed tag (high trust); vision
# is a runtime badge read whose misread is a silent error (lower trust, set when
# Plan 59-05 lands its accuracy eval); numpy is a last-resort estimate.
#
# Rationale (RESEARCH A3/A4): a vision misread is the SAME hallucination class as
# a wrong library tag, so vision-sourced keys must clear a HIGHER floor than XML
# before they are citable. The numpy estimator is the weakest signal of all.
XML_CONF_FLOOR: float = 0.6
VISION_CONF_FLOOR: float = 0.7  # consumed by Plan 59-05 when the vision leg lands
NUMPY_CONF_FLOOR: float = 0.5  # consumed when the deferred KS estimator lands

# The floor _tick_once gates the change-only `key:`/`track:` registry writes on
# (RESEARCH Spike 3, A4 — mirrors the audible_track_confidence 0.5 gate, set a
# touch higher so only confident keys are ever citable).
DECK_CITE_MIN_CONF: float = 0.6


class DeckPoller:
    """Read-only deck-state producer.

    Construction mirrors the other producers — dependency-injected sources, no
    globals:

        DeckPoller(library=lib, controller=controller_state, track_info=track_info)

    ``library`` may be ``None`` (the user never imported a ``collection.xml``);
    the poller then degrades every deck to honest ``unknown`` rather than
    crashing. ``controller`` and ``track_info`` are the SAME instances passed to
    ``state_refresh_loop`` — the poller only READS their snapshots.
    """

    def __init__(
        self,
        *,
        library: "RekordboxLibrary | None" = None,
        controller=None,
        track_info=None,
    ) -> None:
        self._lock = threading.Lock()
        self._library = library
        self._controller = controller
        self._track_info = track_info
        # Internal holder — the last-known resolved deck map. Empty until the
        # first successful poll. snapshot() returns COPIES of these.
        self._decks: dict[str, DeckTrack] = {}
        # Title→track_id index, built once per library object (read-only).
        self._title_index: dict[str, str] | None = None

    # ------------------------------------------------------------------ #
    # Read-only library resolution (NO XML re-parse, NO DB open)          #
    # ------------------------------------------------------------------ #

    def _resolve_title(self, title: str | None):
        """Title → ``TrackEntry`` via a read-only scan of the cache-warm library.

        ``RekordboxLibrary`` only exposes ``lookup_by_id``; this is the read-only
        title→entry helper (RESEARCH §interfaces — "add a title→TrackEntry
        resolution helper that iterates self.tracks"). Case-insensitive on the
        title. Returns ``None`` on no library / no match. NEVER writes anything.
        """
        if not title or self._library is None:
            return None
        try:
            tracks = self._library.tracks
        except Exception:
            return None
        # Build a case-folded title→id index once (bounded — collection size).
        if self._title_index is None:
            try:
                self._title_index = {
                    e.title.casefold(): tid for tid, e in tracks.items() if e.title
                }
            except Exception:
                self._title_index = {}
        tid = self._title_index.get(title.casefold())
        if tid is None:
            return None
        try:
            return tracks.get(tid)
        except Exception:
            return None

    def _xml_decktrack(self, entry, *, confidence: float, now: float) -> DeckTrack:
        """Build a ``rekordbox_xml``-sourced DeckTrack from a library entry.

        ``key`` keeps the RAW Tonality tag (``"Am"``); ``camelot`` is LEFT None
        — the single-writer normalizes it via ``harmonics.to_camelot`` inside the
        lock batch (RESEARCH §Code Examples). ``bpm`` comes from source metadata
        (``AverageBpm``), NOT audio autocorrelation.
        """
        raw_key = entry.key or None
        return DeckTrack(
            title=entry.title or None,
            track_id=entry.track_id or None,
            bpm=float(entry.bpm or 0.0),
            key=raw_key,
            camelot=None,  # normalized by _tick_once via harmonics.to_camelot
            open_key=None,
            energy=None,
            loaded_at=now,
            confidence=confidence,
            source="rekordbox_xml",
        )

    # ------------------------------------------------------------------ #
    # Poll — compose the source ladder + cross-deck suppression           #
    # ------------------------------------------------------------------ #

    def poll_once(self) -> None:
        """Resolve the current deck map and store it in the internal holder.

        Swallows ALL exceptions (graceful degradation, mirrors
        ``TrackInfo.poll_once``) — on any failure the last-known holder is kept
        untouched and no exception escapes.
        """
        now = time.time()
        try:
            decks = self._build_decks(now)
        except Exception as e:  # never let a source failure escape the poller
            print(f"[deck poll err] {e}", file=sys.stderr)
            return
        with self._lock:
            self._decks = decks

    def _build_decks(self, now: float) -> dict[str, DeckTrack]:
        """Compose the ladder for both decks with cross-deck suppression.

        Step 1 — attribution: ``derive_audible_deck`` (REUSED, never hand-rolled)
        decides WHICH deck the single now-playing title belongs to, trusting
        fader+xfader over the FLX4 play-state desync.

        Step 2 — ladder per deck: the AUDIBLE deck gets the now-playing title
        resolved against the XML library (① primary). The non-audible deck has NO
        independent source signal this phase (vision is Plan 59-05), so it is
        SUPPRESSED to ``unknown`` — never resolved by the audible deck's title
        (cross-deck suppression, DECK-05).
        """
        # Read the controller + nowplaying snapshots (read-only).
        cs = self._controller.deck_snapshot() if self._controller is not None else None
        title = None
        if self._track_info is not None:
            tsnap = self._track_info.snapshot()
            title = tsnap.get("title") or None

        decks: dict[str, DeckTrack] = {}

        # Without a controller we cannot attribute a deck — honest unknown.
        if cs is None:
            return decks

        audible_deck, deck_conf = derive_audible_deck(
            cs.get("A", {}), cs.get("B", {}), cs.get("xfader", 64), cs.get("connected", False)
        )

        # Step 2: resolve ONLY the independently-confirmed (audible) single deck.
        # "mix"/"none" are NOT a single attributable deck → suppress (no guess).
        if audible_deck in ("A", "B"):
            entry = self._resolve_title(title)
            if entry is not None:
                # XML match clears the floor → resolved DeckTrack on the audible
                # deck. Confidence is bounded by the attribution confidence so a
                # weakly-attributed deck never cites at full XML trust.
                conf = max(XML_CONF_FLOOR, min(1.0, deck_conf))
                decks[audible_deck] = self._xml_decktrack(entry, confidence=conf, now=now)

        # The second / non-audible deck is SUPPRESSED — there is no independent
        # source for it this phase. Emit NOTHING for it (no honest-unknown stub
        # that could be mistaken for a resolved deck); Phase 60's clash logic
        # cannot cite a deck the registry never saw. (Vision badge read in Plan
        # 59-05 will give the silent deck its own source signal.)
        return decks

    # ------------------------------------------------------------------ #
    # Snapshot — copies under the lock                                    #
    # ------------------------------------------------------------------ #

    def snapshot(self) -> dict[str, DeckTrack]:
        """Static snapshot — fresh ``DeckTrack`` copies the caller cannot use to
        mutate the listener-thread holder (mirrors ``ControllerState.deck_snapshot``).

        ``DeckTrack`` is a plain (non-frozen) dataclass, so ``_tick_once`` can
        set ``camelot`` on the returned copies without touching the holder.
        """
        with self._lock:
            return {side: replace_decktrack(dt) for side, dt in self._decks.items()}

    # ------------------------------------------------------------------ #
    # Cadence wrapper (mirrors TrackMacOS.run_poll_loop)                  #
    # ------------------------------------------------------------------ #

    async def run_poll_loop(self, stop_event: asyncio.Event, *, interval: float = 1.0) -> None:
        """Bounded-cadence poll loop. Offloads ``poll_once`` to an executor (the
        library scan + snapshot reads are cheap but kept off the event loop for
        symmetry with the other producers). NEVER exits on exception.

        Cadence is bounded for cost (CONTEXT lock — XML scan is cheap; the future
        vision leg will debounce to track-change/screen-change only).
        """
        loop = asyncio.get_running_loop()
        while not stop_event.is_set():
            try:
                await loop.run_in_executor(None, self.poll_once)
            except Exception as e:
                print(f"[deck poll loop err] {e}", file=sys.stderr)
            await asyncio.sleep(interval)


def replace_decktrack(dt: DeckTrack) -> DeckTrack:
    """Return a shallow copy of a ``DeckTrack`` (all fields are immutable
    scalars/None) so a caller mutating the copy cannot reach the holder."""
    return DeckTrack(
        title=dt.title,
        track_id=dt.track_id,
        bpm=dt.bpm,
        key=dt.key,
        camelot=dt.camelot,
        open_key=dt.open_key,
        energy=dt.energy,
        loaded_at=dt.loaded_at,
        confidence=dt.confidence,
        source=dt.source,
    )
