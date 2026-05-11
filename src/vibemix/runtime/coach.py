# SPDX-License-Identifier: Apache-2.0
"""coach_loop — verbatim port of cohost_v4.py:1754-1852.

Polls MusicState for events at 10Hz, fires AI reactions via
``session.generate_reply``. Single-in-flight enforcement (stale-clear at
12s). Mic detection for ``KAAN_SPOKE`` (3-frame minimum above threshold +
0.6s silence). Manual trigger fan-in from ``ws_bus``.

The two type-hint imports for ``AgentSession`` and ``DJCoHostAgent`` live
under ``TYPE_CHECKING`` — coach_loop only uses ``agent.set_next_event(ev)``
and ``session.generate_reply(...)`` which are interface-level. This keeps
the runtime dep on plan 04-02 weak and lets tests pass mock objects.

The ``with state._lock:`` guard around the ``state.last_kaan_spoke_at``
write is REQUIRED — Phase 3 invariant says ``state_refresh_loop`` is the
only writer to MusicState; this one mic-detection write is the sole
locked exception (v4:1800-1801).
"""

from __future__ import annotations

import asyncio
import sys
import time
from typing import TYPE_CHECKING

from vibemix.audio import AI_TALK_THRESHOLD, MIC_TALK_THRESHOLD, Levels, VoiceRecorder
from vibemix.state import EventDetector, MusicState

if TYPE_CHECKING:
    from livekit.agents import AgentSession

    from vibemix.agent import DJCoHostAgent


async def coach_loop(
    session: AgentSession,
    agent: DJCoHostAgent,
    state: MusicState,
    levels: Levels,
    event_detector: EventDetector,
    recorder: VoiceRecorder,
    manual_trigger: asyncio.Event,
    trigger_state: dict,
    stop_event: asyncio.Event,
) -> None:
    """Polls MusicState for events at 10Hz. On event → prompt AI. Single
    in-flight generation at a time. Mic detection happens here against
    ``levels``, not ``state`` — ``levels.mic`` comes from MicBuffer
    pre-attenuation so the AI's own voice doesn't leak in as Kaan.

    Verbatim port of cohost_v4.py:1754-1852.
    """
    await asyncio.sleep(2.0)

    last_ai_voice_at = 0.0
    mic_active_frames = 0
    mic_silence_since = 0.0

    while not stop_event.is_set():
        await asyncio.sleep(0.1)
        now = time.time()

        # Don't fire while a generation is in-flight
        if trigger_state.get("in_flight"):
            age = now - trigger_state.get("in_flight_at", 0)
            if age > 12.0:
                print(f"\n[coach] in_flight stale {age:.1f}s — clearing", file=sys.stderr)
                trigger_state["in_flight"] = False
            else:
                mic_active_frames = 0
                mic_silence_since = 0.0
                continue

        # Don't fire while AI is talking; honor a cooldown after it stops
        if levels.voice > AI_TALK_THRESHOLD:
            last_ai_voice_at = now
            mic_active_frames = 0
            mic_silence_since = 0.0
            continue
        if now - last_ai_voice_at < 7.0:
            mic_active_frames = 0
            mic_silence_since = 0.0
            continue

        # Mic detection — Kaan finished speaking
        kaan_just_spoke = False
        if levels.mic > MIC_TALK_THRESHOLD:
            mic_active_frames += 1
            mic_silence_since = 0.0
            with state._lock:
                state.last_kaan_spoke_at = now
        elif mic_active_frames >= 3:
            if mic_silence_since == 0.0:
                mic_silence_since = now
            elif now - mic_silence_since > 0.6:
                kaan_just_spoke = True
                mic_active_frames = 0
                mic_silence_since = 0.0
        else:
            mic_active_frames = 0
            mic_silence_since = 0.0

        manual = manual_trigger.is_set()
        if manual:
            manual_trigger.clear()

        ev = event_detector.detect(state, kaan_just_spoke=kaan_just_spoke, manual=manual)
        if ev is None:
            continue

        try:
            trigger_state["in_flight"] = True
            trigger_state["in_flight_at"] = now
            tag = ev.type
            print(
                f"\n[event {tag}] audible={state.audible} deck={state.audible_deck} "
                f"track={state.audible_track!r}({state.audible_track_confidence:.1f}) "
                f"phase={state.phase}"
            )
            recorder.log_event(
                "event",
                type=tag,
                audible=state.audible,
                deck=state.audible_deck,
                track=state.audible_track,
                track_conf=round(state.audible_track_confidence, 2),
                phase=state.phase,
            )

            # Hand the event to the agent so llm_node can build the grounded
            # multimodal prompt (text evidence + audio Part + screen Part).
            agent.set_next_event(ev)

            try:
                handle = session.generate_reply(allow_interruptions=False)
                # generate_reply returns a SpeechHandle; wait for playout
                await asyncio.wait_for(handle.wait_for_playout(), timeout=20.0)
            except TimeoutError:
                print("[coach] generate_reply timed out", file=sys.stderr)
            finally:
                trigger_state["in_flight"] = False
        except Exception as e:
            trigger_state["in_flight"] = False
            print(f"\n[coach err] {e}", file=sys.stderr)
