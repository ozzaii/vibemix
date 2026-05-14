# SPDX-License-Identifier: Apache-2.0
"""coach_loop — verbatim port of cohost_v4.py:1754-1852, with Plan 19-05
runtime wiring for AckBank + CancelGate + TTFTMeter + PlaybackQueue, plus
Plan 20-04 periodic ipc.session.citation publish to the Tauri Settings →
Diagnostics surface (GROUND-06 anti-slop telemetry channel).

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

Plan 19-05 wiring (additive — backward compatible):
- ``ack_bank``, ``cancel_gate``, ``ttft_meter``, ``playback`` are NEW kwargs
  with default None. When ALL non-None, the wired path runs:
    1. cancel-and-refire: if a stale in-flight handle exists in
       ``trigger_state``, query CancelGate.try_cancel(handle, incoming,
       in_flight). On True: ``await agent.invalidate_cache()`` so the refire
       starts with a fresh cached prefix.
    2. ack pre-fire: ``ack_bank.should_fire(rolling_ttft_avg_ms,
       last_ack_at, last_response_at, cancel_cooldown_active)``. On True:
       ``ack_bank.pick_for_event(ev) → playback.push(pcm.tobytes())`` and
       ``recorder.log_event("ack_fire", bucket=, sample_index=, reason=)``.
    3. ``session.generate_reply(allow_interruptions=True)`` — flips True so
       the SpeechHandle.interrupt(force=True) chokepoint inside CancelGate
       can actually preempt the playout.
- When ANY of the four kwargs is None, the legacy path runs verbatim with
  ``allow_interruptions=False`` to preserve the byte-identical Phase 4
  contract for existing callers / tests.

Plan 20-04 wiring (additive — backward compatible):
- ``ipc_bus`` + ``citation_telemetry`` are NEW kwargs with default None.
  When both are non-None, the loop publishes ``ipc.session.citation`` every
  ``CITATION_PUBLISH_INTERVAL_S`` (2.0s) seconds via ``ipc_bus.emit(dict)``
  with payload ``{slop_ratio, stripped_rate_15s, last_unverified_response,
  bypass_active}`` sourced from the telemetry callable.
- A telemetry-callable failure prints to stderr ``[coach citation publish
  err]`` and STILL bumps the publish_at debounce so a chronically-broken
  callable cannot spam the log faster than once per interval.
- When either kwarg is None, the publish gate is skipped and the legacy
  Plan 19-05 path runs unchanged (byte-identical for existing tests).
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from vibemix.audio import AI_TALK_THRESHOLD, MIC_TALK_THRESHOLD, Levels, VoiceRecorder
from vibemix.runtime.cancel import CANCEL_COOLDOWN_S
from vibemix.state import EventDetector, MusicState
from vibemix.ui_bus import SessionCitation

if TYPE_CHECKING:
    from livekit.agents import AgentSession

    from vibemix.agent import DJCoHostAgent
    from vibemix.agent.ack_bank import AckBank
    from vibemix.audio import PlaybackQueue
    from vibemix.runtime.cancel import CancelGate
    from vibemix.runtime.ttft import TTFTMeter
    from vibemix.runtime.ws_bus import IpcBus

# Plan 20-04 — periodic ipc.session.citation publish cadence (0.5Hz). Lower
# than ipc.session.snapshot's 30Hz because slop_ratio + stripped_rate_15s
# evolve slowly (15s rolling window + cumulative ratio).
CITATION_PUBLISH_INTERVAL_S = 2.0


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
    *,
    ack_bank: AckBank | None = None,
    cancel_gate: CancelGate | None = None,
    ttft_meter: TTFTMeter | None = None,
    playback: PlaybackQueue | None = None,
    ipc_bus: IpcBus | None = None,
    citation_telemetry: Callable[[], dict] | None = None,
) -> None:
    """Polls MusicState for events at 10Hz. On event → prompt AI. Single
    in-flight generation at a time. Mic detection happens here against
    ``levels``, not ``state`` — ``levels.mic`` comes from MicBuffer
    pre-attenuation so the AI's own voice doesn't leak in as Kaan.

    Verbatim port of cohost_v4.py:1754-1852, with Plan 19-05 ack/cancel/cache
    wiring (see module docstring).
    """
    await asyncio.sleep(2.0)

    last_ai_voice_at = 0.0
    last_citation_publish_at = 0.0
    mic_active_frames = 0
    mic_silence_since = 0.0

    wired = (
        ack_bank is not None
        and cancel_gate is not None
        and ttft_meter is not None
        and playback is not None
    )
    citation_wired = ipc_bus is not None and citation_telemetry is not None

    while not stop_event.is_set():
        await asyncio.sleep(0.1)
        now = time.time()

        # Plan 20-04 — periodic ipc.session.citation publish (0.5Hz). Runs
        # before the in_flight skip so anti-slop telemetry keeps flowing
        # even while a reaction is generating. The whole gate is wrapped in
        # try/except + always bumps last_citation_publish_at so a broken
        # telemetry callable cannot spam stderr faster than the interval.
        if citation_wired and (now - last_citation_publish_at) >= CITATION_PUBLISH_INTERVAL_S:
            try:
                tel = citation_telemetry()  # type: ignore[misc]
                msg = SessionCitation.make(
                    slop_ratio=float(tel.get("slop_ratio", 0.0)),
                    stripped_rate_15s=float(tel.get("stripped_rate_15s", 0.0)),
                    last_unverified_response=tel.get("last_unverified_response"),
                    bypass_active=bool(tel.get("bypass_active", False)),
                )
                await ipc_bus.emit(json.loads(msg.to_json()))  # type: ignore[union-attr]
            except Exception as e:
                print(f"\n[coach citation publish err] {e}", file=sys.stderr)
            finally:
                last_citation_publish_at = now

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

            if wired:
                # ---- Plan 19-05 — cancel-and-refire on stale in-flight ----
                # Reachable when the prior tick's wait_for_playout TimeoutError'd
                # but left in_flight_handle/in_flight_ev populated. Also the
                # seam v2.x asynchronous fan-in will use.
                in_flight_handle = trigger_state.get("in_flight_handle")
                in_flight_prev_ev = trigger_state.get("in_flight_ev")
                if in_flight_handle is not None and in_flight_prev_ev is not None:
                    if cancel_gate.try_cancel(in_flight_handle, ev, in_flight_prev_ev):
                        await agent.invalidate_cache()
                        trigger_state["in_flight_handle"] = None
                        trigger_state["in_flight_ev"] = None

                # ---- Plan 19-05 — ack pre-fire ----
                cancel_cooldown_active = (
                    cancel_gate.last_cancel_at != 0.0
                    and (time.monotonic() - cancel_gate.last_cancel_at) < CANCEL_COOLDOWN_S
                )
                fire, reason = ack_bank.should_fire(
                    rolling_ttft_avg_ms=ttft_meter.rolling_avg_ms(),
                    last_ack_at=trigger_state.get("last_ack_at"),
                    last_response_at=trigger_state.get("last_response_at"),
                    cancel_cooldown_active=cancel_cooldown_active,
                )
                if fire:
                    bucket, pcm, sample_idx = ack_bank.pick_for_event(ev)
                    playback.push(pcm.tobytes())
                    trigger_state["last_ack_at"] = time.monotonic()
                    recorder.log_event(
                        "ack_fire",
                        bucket=bucket,
                        sample_index=sample_idx,
                        reason=reason,
                    )

            # Hand the event to the agent so llm_node can build the grounded
            # multimodal prompt (text evidence + audio Part + screen Part).
            agent.set_next_event(ev)

            try:
                if wired:
                    handle = session.generate_reply(allow_interruptions=True)
                    trigger_state["in_flight_handle"] = handle
                    trigger_state["in_flight_ev"] = ev
                else:
                    handle = session.generate_reply(allow_interruptions=False)
                # generate_reply returns a SpeechHandle; wait for playout
                await asyncio.wait_for(handle.wait_for_playout(), timeout=20.0)
                if wired:
                    trigger_state["last_response_at"] = time.monotonic()
            except TimeoutError:
                print("[coach] generate_reply timed out", file=sys.stderr)
            finally:
                trigger_state["in_flight"] = False
                if wired:
                    # Clear handle/ev so the next tick's cancel branch does
                    # not see a stale handle from a normal completion.
                    trigger_state["in_flight_handle"] = None
                    trigger_state["in_flight_ev"] = None
        except Exception as e:
            trigger_state["in_flight"] = False
            print(f"\n[coach err] {e}", file=sys.stderr)
