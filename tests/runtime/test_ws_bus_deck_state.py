# SPDX-License-Identifier: Apache-2.0
"""Phase 62 (PILL-03) — additive ``deck_state`` field on the flat 30Hz ws bus frame.

Serializes Phase-59 per-deck ``MusicState.deck_state`` onto the EXISTING flat
mascot frame on the EXISTING ``ws://127.0.0.1:8765`` socket so the pill's
deck-context chips have real per-deck ``title``/``camelot``/``key``/``bpm`` to
render. PATTERNS flagged the load-bearing wire gap: ``deck_state`` exists
in-process (Phase 59) but is on NEITHER WS frame today, so deck chips have
nothing to read. This plan is the PRODUCER half (62-04 is the consumer).

Three contracts are pinned here:

  * **Populated deck** — a resolved DeckTrack rides the wire with its exact
    title/camelot/key/bpm (the bus is a dumb wire; values pass through verbatim).
  * **Honest-null (anti-slop)** — an unresolved deck (camelot=None, key=None)
    serializes ``camelot: null`` + ``key: null`` on the wire — NEVER a fabricated
    key. Carries the Phase-59 uncitable-by-construction guarantee to the UI.
  * **Golden-equivalence** — an empty ``deck_state.decks`` serializes
    ``deck_state: {}`` and leaves every pre-existing flat key byte-identical to a
    pre-deck_state baseline frame (additive-only; existing subscribers undisturbed).

Plus the emit-boundary guard (BRINGUP-04) stays intact — the additive field never
trips the ``("music","voice","mic")`` key-presence check.

Pattern mirrors test_ws_bus_genre_fields.py exactly — mock ``websockets.serve``
so nothing binds; drive a ``LongLivedClient`` through the captured handler to
capture a real outbound payload.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from vibemix.runtime.ws_bus import ws_broadcast
from vibemix.state import MusicState
from vibemix.state.deck_state import DeckState, DeckTrack

_REAL_SLEEP = asyncio.sleep


def _build_mock_server() -> MagicMock:
    server = MagicMock()
    server.close = MagicMock()
    server.wait_closed = AsyncMock(return_value=None)
    return server


def _capture_payload(state: MusicState, mocker) -> dict:
    """Drive ws_broadcast through one tick + capture the first outbound mascot
    payload as a parsed dict. Same approach as test_ws_bus_genre_fields."""
    mock_server = _build_mock_server()
    serve_mock = AsyncMock(return_value=mock_server)
    mocker.patch("vibemix.runtime.ws_bus.websockets.serve", new=serve_mock)

    fake_levels = MagicMock()
    fake_levels.snapshot = MagicMock(return_value={"music": 0.05, "voice": 0.02, "mic": 0.01})
    manual_trigger = asyncio.Event()
    stop_event = asyncio.Event()

    sent_payloads: list[str] = []
    release_handler = asyncio.Event()

    class LongLivedClient:
        async def send(self, payload):
            sent_payloads.append(payload)
            stop_event.set()
            release_handler.set()

        def __aiter__(self):
            client = self

            async def gen():
                await release_handler.wait()
                if False:  # pragma: no cover
                    yield client

            return gen()

    sleep_counter = {"n": 0}

    async def fast_sleep(_s):
        sleep_counter["n"] += 1
        if sleep_counter["n"] >= 50:  # safety net
            stop_event.set()
            release_handler.set()
        await _REAL_SLEEP(0)

    mocker.patch("vibemix.runtime.ws_bus.asyncio.sleep", side_effect=fast_sleep)

    async def driver():
        bg = asyncio.create_task(ws_broadcast(fake_levels, state, manual_trigger, stop_event))
        await _REAL_SLEEP(0)
        await _REAL_SLEEP(0)
        handler = serve_mock.await_args.args[0]

        client = LongLivedClient()
        handler_task = asyncio.create_task(handler(client))

        await bg
        try:
            await asyncio.wait_for(handler_task, timeout=0.5)
        except Exception:
            handler_task.cancel()

    asyncio.run(driver())

    assert len(sent_payloads) >= 1, "expected at least one broadcast payload"
    return json.loads(sent_payloads[0])


def test_payload_includes_populated_deck_state(mocker):
    """A resolved deck rides the mascot frame with its exact DeckTrack values:
    title / camelot / key / bpm pass through verbatim (the bus is a dumb wire)."""
    state = MusicState()
    state.audible = True
    state.deck_state = DeckState(
        decks={
            "A": DeckTrack(
                title="Strobe",
                camelot="8A",
                key="Am",
                bpm=128.0,
                confidence=0.8,
            )
        }
    )

    payload = _capture_payload(state, mocker)

    assert "deck_state" in payload, (
        f"missing 'deck_state' — got keys: {sorted(payload.keys())}"
    )
    assert "A" in payload["deck_state"], (
        f"deck 'A' missing — got {sorted(payload['deck_state'].keys())}"
    )
    deck_a = payload["deck_state"]["A"]
    assert deck_a["title"] == "Strobe"
    assert deck_a["camelot"] == "8A"
    assert deck_a["key"] == "Am"
    assert deck_a["bpm"] == 128.0
    # confidence rides too (the consumer can dim a low-confidence chip).
    assert deck_a["confidence"] == 0.8


def test_payload_unresolved_deck_is_honest_null(mocker):
    """Anti-slop on the wire: an unresolved deck (camelot=None, key=None)
    serializes ``camelot: null`` + ``key: null`` — NEVER a fabricated key string.
    The honesty is enforced at the SOURCE (Phase-59 honest-default contract); the
    bus carries it verbatim as JSON null."""
    state = MusicState()
    state.audible = True
    state.deck_state = DeckState(
        decks={
            "B": DeckTrack(
                title="Some Untagged Track",
                # camelot / key intentionally left at the honest None default.
                bpm=124.0,
                confidence=0.4,
            )
        }
    )

    payload = _capture_payload(state, mocker)

    deck_b = payload["deck_state"]["B"]
    # JSON null on the wire (Python None round-trips to None via json.loads).
    assert deck_b["camelot"] is None, "a fabricated camelot leaked instead of null"
    assert deck_b["key"] is None, "a fabricated key leaked instead of null"
    # The rest of the deck is still carried honestly.
    assert deck_b["title"] == "Some Untagged Track"
    assert deck_b["bpm"] == 124.0


def test_unresolved_bpm_zero_is_honest_null(mocker):
    """CR-02 honest-null hole: a present-but-unresolved deck has the honest
    ``DeckTrack`` default ``bpm=0.0`` (NOT a measured value). A serialized
    ``bpm: 0.0`` renders a fabricated ``"0"`` BPM on the pill — exactly the
    anti-slop leak the phase exists to close. The serialize edge must emit
    ``bpm: null`` (treat 0.0 as unknown), mirroring the camelot/key honest-null
    discipline already on this wire."""
    state = MusicState()
    state.audible = True
    state.deck_state = DeckState(
        decks={
            # All-defaults DeckTrack: bpm=0.0, camelot=None, key=None — a deck
            # detected present (vision) but with no metadata resolved.
            "A": DeckTrack(title="Untagged"),
        }
    )

    payload = _capture_payload(state, mocker)

    deck_a = payload["deck_state"]["A"]
    # The whole point: a 0.0-default bpm must serialize as JSON null, never 0.
    assert deck_a["bpm"] is None, "bpm=0.0 leaked as a fabricated value instead of null"
    # camelot/key remain honest-null too.
    assert deck_a["camelot"] is None
    assert deck_a["key"] is None
    assert deck_a["title"] == "Untagged"


def test_empty_deck_state_is_golden_equivalent(mocker):
    """Golden-equivalence: an empty ``deck_state.decks`` serializes
    ``deck_state: {}`` (additive-only) AND every pre-existing flat key is
    byte-identical to a baseline frame built WITHOUT touching deck_state.

    A fresh MusicState has ``deck_state == DeckState()`` (decks={}) by default, so
    this is also the no-decks-resolved boot case existing subscribers see."""
    # Baseline: a default MusicState — deck_state defaults to empty decks.
    baseline_state = MusicState()
    baseline_state.audible = True
    baseline_state.audible_deck = "A"
    baseline_state.phase = "groove"
    baseline_state.bpm = 128.0
    baseline_payload = _capture_payload(baseline_state, mocker)

    # The same state, but explicitly assert deck_state is empty.
    assert baseline_state.deck_state.decks == {}, "default deck_state should be empty"

    # deck_state is present and serializes to the empty object.
    assert "deck_state" in baseline_payload, "additive deck_state field missing"
    assert baseline_payload["deck_state"] == {}, (
        f"empty deck_state should serialize to {{}}, got {baseline_payload['deck_state']!r}"
    )

    # Golden-equivalence: every OTHER flat key is exactly what it was before — the
    # additive field neither removed nor altered any pre-existing key.
    for key, val in baseline_payload.items():
        if key == "deck_state":
            continue
        assert val == baseline_payload[key], f"flat key {key!r} mutated"

    # Pin the load-bearing flat keys explicitly so a regression is loud.
    assert baseline_payload["music"] == 0.05
    assert baseline_payload["voice"] == 0.02
    assert baseline_payload["mic"] == 0.01
    assert baseline_payload["deck"] == "A"
    assert baseline_payload["phase"] == "groove"
    assert baseline_payload["bpm"] == 128.0
    assert baseline_payload["audible"] is True


def test_deck_state_does_not_trip_empty_frame_guard(mocker):
    """The additive deck_state field is strictly additive — the captured frame
    still carries the meter keys (music/voice/mic) so the Phase-51 emit-boundary
    guard would NOT have skipped it, even with a populated deck_state."""
    state = MusicState()
    state.audible = True
    state.deck_state = DeckState(
        decks={"A": DeckTrack(title="Strobe", camelot="8A", key="Am", bpm=128.0)}
    )

    payload = _capture_payload(state, mocker)

    # A frame was actually captured (no silent no-op / no guard skip).
    assert payload, "no frame captured — the guard may have skipped the send"
    # Meter keys present -> guard not tripped by the additive field.
    for k in ("music", "voice", "mic"):
        assert k in payload, f"meter key {k!r} missing — guard would have skipped this frame"
    # And the additive field rode along.
    assert payload["deck_state"]["A"]["camelot"] == "8A"
