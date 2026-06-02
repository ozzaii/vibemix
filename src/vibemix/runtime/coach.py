# SPDX-License-Identifier: Apache-2.0
"""coach_loop — verbatim port of cohost_v4.py:1754-1852, with the
latency-stack wiring that replaced the retired ack-bank (CancelGate +
TTFTMeter + PlaybackQueue; the ack-bank was deleted 2026-05-19 — strip-to-
silence replaced pre-canned acks) and Plan 20-04 periodic ipc.session.citation
publish to the Tauri Settings → Diagnostics surface (GROUND-06 anti-slop
telemetry channel).

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

Wiring (additive — backward compatible):
- ``cancel_gate``, ``ttft_meter``, ``playback`` are NEW kwargs with
  default None. When ALL non-None, the wired path runs cancel-and-refire:
  if a stale in-flight handle exists in ``trigger_state``, query
  CancelGate.try_cancel(handle, incoming, in_flight). On True:
  ``await agent.invalidate_cache()`` so the refire starts with a fresh
  cached prefix; then
  ``session.generate_reply(allow_interruptions=True)`` — flips True so
  the SpeechHandle.interrupt(force=True) chokepoint inside CancelGate
  can actually preempt the playout.
- When ANY kwarg is None, the legacy path runs verbatim with
  ``allow_interruptions=False`` to preserve the byte-identical Phase 4
  contract for existing callers / tests.

(The ack-bank pre-fire branch was retired with the placeholder OPUS
clips — pre-recorded "yeah/oh/nice" reactions injected English
placeholders into Turkish sessions and fought the anti-slop thesis.
Latency is now mitigated by the cache + ModelRouter alone.)

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
from typing import TYPE_CHECKING, Any

from vibemix.audio import AI_TALK_THRESHOLD, MIC_TALK_THRESHOLD, Levels, VoiceRecorder
from vibemix.state import EventDetector, MusicState
from vibemix.state.deck_context import (
    DECK_CONTEXT_TRUSTED_SOURCES,
    live_claim_policy,
    render_audio_delta_items,
    render_audio_window_context,
    render_context_feed_contract,
    render_deck_audio_context,
    render_deck_audio_delta_context,
    render_deck_audio_features_context,
    render_deck_audio_separation_context,
    render_deck_audio_window_context,
    render_deck_change_context,
    render_deck_lane_context,
    render_deck_reference_context,
    render_deck_source_context,
    render_live_evidence_context,
    render_move_context,
    render_move_effect_context,
)
from vibemix.ui_bus import SessionCitation

from .set_plan_voice import build_set_progress_voice_line
from .suggestion_voice import build_next_suggestion_voice_line
from .transition_verdict_voice import build_transition_verdict_voice_line

if TYPE_CHECKING:
    from livekit.agents import AgentSession

    from vibemix.agent import DJCoHostAgent
    from vibemix.audio import PlaybackQueue
    from vibemix.runtime.cancel import CancelGate
    from vibemix.runtime.ttft import TTFTMeter
    from vibemix.runtime.ws_bus import IpcBus
    from vibemix.state.evidence_registry import EvidenceRegistry

# Plan 20-04 — periodic ipc.session.citation publish cadence (0.5Hz). Lower
# than ipc.session.snapshot's 30Hz because slop_ratio + stripped_rate_15s
# evolve slowly (15s rolling window + cumulative ratio).
CITATION_PUBLISH_INTERVAL_S = 2.0


def _safe_print(*args: object, **kwargs: object) -> None:
    """Best-effort runtime logging; a broken parent pipe must not kill coaching."""
    try:
        print(*args, **kwargs)
    except (BrokenPipeError, OSError):
        pass


def _log_suggestion_error(fut: Any) -> None:
    """Done-callback for the off-loop suggestion compute — surface its error to
    stderr without ever propagating into the reaction loop."""
    try:
        exc = fut.exception()
    except Exception:
        return
    if exc is not None:
        _safe_print(f"\n[coach suggestion err] {exc}", file=sys.stderr)


def _credit_live_skill_demo(
    ev: Any,
    state: MusicState,
    *,
    evidence_registry: EvidenceRegistry | None,
    learn_progress: Any | None,
    speak: Callable[[str], None] | None = None,
) -> list[str]:
    """Credit the v11.0 skill(s) a CITED live event demonstrates (the
    ``§EARNED-LIVE-MASTERED-VERIFY`` backend wiring — finally giving the
    until-now-orphaned ``learn/skill_recognizer.recognize`` a live call site).

    The recognizer is the MAST-02/03 anti-slop spine: it maps ``ev.type`` to the
    skill(s) it demonstrates over the REAL event taxonomy and grants Mastered
    credit ONLY when an INJECTED citation predicate resolves — so a fabricated /
    un-cited event moves no bar (Invariants #2 + #3). Here that predicate closes
    over the live ``EvidenceRegistry`` written by ``EventDetector._fire`` for
    THIS event a moment ago.

    The session-relative ``t`` the registry was keyed with is NOT on the
    ``Event`` (it carries only type/state/extra/priority); the detector wrote it
    as ``max(0.0, now - state.set_start_at)`` (event_detector.py:508, wall
    clock), so we recompute the same value here and pass it explicitly — the
    ±1.0s ``has`` tolerance absorbs the few-ms gap since detect() returned.

    Returns the skill ids whose ``live_proof_count`` actually advanced (``[]``
    when the gate is off, the event maps to no skill, or its citation does not
    resolve). NEVER raises — a skill-credit failure must never wedge the
    reaction loop (belt-and-braces over recognize's own never-raises posture).
    Persists the live-portion via ``save_progress`` only on a real credit;
    imports are function-local to keep ``runtime/`` free of a top-level
    ``learn/`` dependency.
    """
    if evidence_registry is None or learn_progress is None:
        return []
    try:
        from datetime import UTC, datetime

        from vibemix.learn.progress import save_progress
        from vibemix.learn.skill_recognizer import recognize

        set_start_at = float(getattr(state, "set_start_at", 0.0) or 0.0)
        t_session = max(0.0, time.time() - set_start_at)
        iso_now = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        # SURF-03 — snapshot each skill's Mastered flag BEFORE crediting so we can
        # detect the rare not-mastered→mastered FLIP afterward (recognize mutates
        # learn_progress.skills in place). Scalar copies, not the aliased dicts.
        before_mastered = {
            sid: bool(blk.get("mastered", False))
            for sid, blk in (getattr(learn_progress, "skills", {}) or {}).items()
            if isinstance(blk, dict)
        }

        credited = recognize(
            ev,
            citation_check=lambda s, k, t: evidence_registry.has(s, k, t, tol=1.0),
            progress=learn_progress,
            now=iso_now,
            event_t=t_session,
        )
        if credited:
            # SURF-03 — the single, rare, earned "Mastered" unlock vocal. Fires
            # ONLY on a skill that JUST flipped to Mastered this event (not on a
            # normal demo, not again after the flip). Hand-authored fixture copy
            # via the existing co-host ``speak`` path (no LLM, no new provider).
            # Guarded never-raises: a vocal failure must never wedge the loop.
            if speak is not None:
                from vibemix.learn.mastered_vocal import mastered_unlock_line

                for sid in credited:
                    now_mastered = bool(
                        (learn_progress.skills.get(sid) or {}).get("mastered", False)
                    )
                    if now_mastered and not before_mastered.get(sid, False):
                        line = mastered_unlock_line(sid, was_mastered=False, now_mastered=True)
                        if line:
                            try:
                                speak(line)
                            except Exception as exc:  # vocal failure ≠ credit failure
                                _safe_print(
                                    f"\n[coach mastered-vocal err] {exc}",
                                    file=sys.stderr,
                                )
            # SAFETY: this LearnProgress is the SAME object the LessonRuntime
            # holds; both mutate-then-save it. That is clobber-free ONLY because
            # both run as coroutines on the one asyncio loop and each
            # mutate→save_progress window has no intervening ``await`` (the save
            # serializes the whole object, so skills + lessons coexist). A future
            # off-loop driver of either side would reintroduce a real RMW race.
            save_progress(learn_progress)
        return credited
    except Exception as exc:  # never wedge the reaction loop on a credit failure
        _safe_print(f"\n[coach skill-credit err] {exc}", file=sys.stderr)
        return []


async def _emit_earned_wall_refresh(
    credited: list[str],
    learn_progress: Any | None,
    ipc_bus: IpcBus | None,
) -> None:
    """After ``_credit_live_skill_demo`` advances the Earned Wall on a live cited
    demo, push the refreshed skill-wall to the shell so the trophy updates
    WITHOUT a reload.

    The credit path mutates + persists ``learn_progress`` but emits no IPC, and
    the periodic ``ipc.session.snapshot`` does NOT carry learn progress — the
    SkillWall only repaints on an ``ipc.learn.progress_state`` envelope. So a
    live Mastered unlock stayed invisible until the next progress_state request
    (effectively a reload). This closes that gap. Fail-soft: a refresh-emit
    failure must NEVER perturb the reaction loop or the credit that already
    landed. Imports are function-local to keep ``runtime/`` free of a top-level
    ``learn/`` dependency (mirrors ``_credit_live_skill_demo``).
    """
    if not credited or ipc_bus is None or learn_progress is None:
        return
    try:
        from vibemix.ui_bus.learn_messages import LearnProgressState

        snapshot = learn_progress.snapshot()
        if not isinstance(snapshot, dict):
            snapshot = None
        env = LearnProgressState.make(
            action="snapshot",
            was_recovered=False,
            progress=snapshot,
        ).to_dict()
        await ipc_bus.emit(env)
    except Exception as exc:  # refresh failure ≠ credit failure
        _safe_print(f"\n[coach earned-wall refresh err] {exc}", file=sys.stderr)


def _make_mastered_speak(session: Any) -> Callable[[str], None] | None:
    """Build the SURF-03 ``speak`` hook from the live co-host session — the
    FIXED-TEXT path (``session.say``), NOT ``generate_reply`` (no LLM, no slop, no
    new provider). Returns ``None`` when the session can't speak fixed text; the
    credit still lands, only the rare vocal is skipped. The fixed line is not
    appended to chat context; it should be heard once, not fed back into later
    LLM turns. The actual TTS tone is the parked
    ``§EARNED-MASTERED-VOCAL-EAR`` ear-pass."""
    say = getattr(session, "say", None)
    if not callable(say):
        return None

    def _speak(line: str) -> None:
        # Fire-and-forget fixed text; the SpeechHandle is not awaited (the Mastered
        # unlock is rare and one-shot, never competing with the reaction cadence).
        say(line, add_to_chat_ctx=False)

    return _speak


def _credit_judged_transition(
    verdict: Any,
    state: MusicState,
    *,
    evidence_registry: EvidenceRegistry | None,
    learn_progress: Any | None,
    speak: Callable[[str], None] | None = None,
) -> list[str]:
    """4d — the live Judge join's post-judge credit glue.

    ``judge_and_record`` writes the ``[judge:transition@t]`` voice-citation, but
    ``skill_recognizer.recognize`` gates Mastered credit on an
    ``[ev:transition_judged]`` citation (it hardcodes ``citation_check("ev",
    ev_type, t)``). So on a JUDGED verdict we ALSO ground the ``ev`` atom — at the
    same wall-clock ``t`` that ``_credit_live_skill_demo`` recomputes, so it
    resolves under the ±1.0s ``has`` tolerance — then feed the existing
    live-credit path: a COMPATIBLE harmonic component credits harmonic_mixing, a
    clash credits nothing.

    Abstain-first: an ``abstained`` verdict writes no citation and credits
    nothing (honest-null — the abstain row was already logged by
    ``judge_and_record``). NEVER raises — a producer hiccup must not wedge the
    reaction loop. Returns the skill ids whose ``live_proof_count`` advanced.
    """
    if verdict is None or getattr(verdict, "verdict_state", None) != "judged":
        return []
    try:
        from vibemix.intel.transition_judge import TRANSITION_JUDGED_KIND
        from vibemix.state.event import Event

        set_start_at = float(getattr(state, "set_start_at", 0.0) or 0.0)
        t_session = max(0.0, time.time() - set_start_at)
        if evidence_registry is not None:
            evidence_registry.write("ev", TRANSITION_JUDGED_KIND, t_session)
        judged_ev = Event(
            type=TRANSITION_JUDGED_KIND,
            state=state,
            extra={"components": dict(getattr(verdict, "components", {}) or {})},
        )
        return _credit_live_skill_demo(
            judged_ev,
            state,
            evidence_registry=evidence_registry,
            learn_progress=learn_progress,
            speak=speak,
        )
    except Exception as exc:  # never wedge the loop
        _safe_print(f"[judge-credit err] {exc}", file=sys.stderr)
        return []


def _run_live_judge(
    deck_audio_capture: Any,
    state: MusicState,
    *,
    policy: str,
    evidence_registry: EvidenceRegistry | None,
    recorder: Any | None,
    learn_progress: Any | None,
    speak: Callable[[str], None] | None = None,
    judge_voice_lines: list[str] | None = None,
) -> Any | None:
    """4d — run the Vibe Judge on the live capture for a transition, abstain-first.

    Resolves per-lane meta (camelot / source-trust / track-id) from the SAME
    deck-state the prompt reads — READ-ONLY, single-writer respected — assembles
    the typed ``LiveSignalFrame`` from the live rings, judges + persists the
    verdict (``judge_and_record`` grounds ``[judge:transition@t]`` and writes the
    ``transition_judged`` row), then credits any demonstrated v11 skill
    (``_credit_judged_transition`` grounds the ``[ev:transition_judged]``
    credit-gate atom the recognizer hardcodes).

    Abstain-first by construction: ``None`` capture -> ``None``; Kaan's common
    master-only rig (routing disabled, one stereo mix) or any policy short of
    ``supported_verdict`` -> the Judge abstains (no citation, no score, no
    credit — the honest-null default, not a bug). NEVER raises: a Judge hiccup
    must not wedge the reaction loop. Returns the verdict, or ``None``.
    """
    if deck_audio_capture is None:
        return None
    try:
        from vibemix.audio.deck_signal import signal_frame_from_capture
        from vibemix.intel.judge_voice import verdict_evidence_line
        from vibemix.state.transition_judge_runtime import judge_and_record, verdict_citation_id

        decks = getattr(getattr(state, "deck_state", None), "decks", None) or {}
        lane_meta: dict[str, dict[str, object]] = {}
        for side in ("A", "B"):
            deck = decks.get(side)
            if deck is None:
                continue
            lane_meta[side] = {
                "camelot": getattr(deck, "camelot", None),
                "source_trusted": str(getattr(deck, "source", "") or "").strip().lower()
                in DECK_CONTEXT_TRUSTED_SOURCES,
                "track_id": getattr(deck, "track_id", None),
            }
        set_start_at = float(getattr(state, "set_start_at", 0.0) or 0.0)
        t_session = max(0.0, time.time() - set_start_at)
        frame = signal_frame_from_capture(
            deck_audio_capture,
            t_session=t_session,
            policy=policy,
            lane_meta=lane_meta,
        )
        verdict = judge_and_record(
            frame,
            registry=evidence_registry,
            recorder=recorder,
            track_a=lane_meta.get("A", {}).get("track_id"),  # type: ignore[arg-type]
            track_b=lane_meta.get("B", {}).get("track_id"),  # type: ignore[arg-type]
        )
        if judge_voice_lines is not None:
            line = verdict_evidence_line(verdict, citation_id=verdict_citation_id(t_session))
            if line:
                judge_voice_lines.append(line)
        _credit_judged_transition(
            verdict,
            state,
            evidence_registry=evidence_registry,
            learn_progress=learn_progress,
            speak=speak,
        )
        return verdict
    except Exception as exc:  # never wedge the loop
        _safe_print(f"[judge-run err] {exc}", file=sys.stderr)
        return None


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
    cancel_gate: CancelGate | None = None,
    ttft_meter: TTFTMeter | None = None,
    playback: PlaybackQueue | None = None,
    ipc_bus: IpcBus | None = None,
    citation_telemetry: Callable[[], dict] | None = None,
    suggestion_service: Any | None = None,
    tracer: Any | None = None,
    audio_capture_context: dict[str, object] | None = None,
    evidence_registry: EvidenceRegistry | None = None,
    learn_progress: Any | None = None,
    deck_audio_capture: Any | None = None,
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

    wired = cancel_gate is not None and ttft_meter is not None and playback is not None
    citation_wired = ipc_bus is not None and citation_telemetry is not None
    # SURF-03 — the rare grounded "Mastered" unlock vocal hook (fixed-text co-host
    # path). Built once; None when the session can't speak (credit still lands).
    mastered_speak = _make_mastered_speak(session)

    # SessionTracer hook — additive, side-effect-free, fully fail-soft. A None
    # tracer (or a tracer raising) must NEVER perturb the in_flight gate or the
    # reaction control flow below. ``_tr`` is a tiny shim so call-sites stay terse.
    def _tr(method: str, ev_name: str, **detail: object) -> None:
        if tracer is None:
            return
        try:
            getattr(tracer, method)(ev_name, **detail)
        except Exception:
            pass

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
                _safe_print(f"\n[coach citation publish err] {e}", file=sys.stderr)
            finally:
                last_citation_publish_at = now

        # Don't fire while a generation is in-flight
        if trigger_state.get("in_flight"):
            age = now - trigger_state.get("in_flight_at", 0)
            if age > 12.0:
                _safe_print(f"\n[coach] in_flight stale {age:.1f}s — clearing", file=sys.stderr)
                trigger_state["in_flight"] = False
                _tr("ai_call", "in_flight_stale_clear", age_s=round(age, 2))
            else:
                _tr("ai_call", "skipped_in_flight", age_s=round(age, 2))
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

        # STATE delta trace — debounced, only logs when a tracked field changes
        # (note_change is a no-op on unchanged values, so the 10Hz tick stays cheap).
        if tracer is not None:
            try:
                tracer.note_change("STATE", "phase", "state.phase", state.phase)
                tracer.note_change(
                    "STATE", "audible_track", "state.audible_track", state.audible_track
                )
                tracer.note_change(
                    "STATE", "audible_deck", "state.audible_deck", state.audible_deck
                )
                tracer.note_change("STATE", "bpm", "state.bpm", round(float(state.bpm or 0.0), 1))
                tracer.note_change(
                    "STATE",
                    "context_feed_contract",
                    "state.context_feed_contract",
                    render_context_feed_contract(state, surface="session_event"),
                )
                tracer.note_change(
                    "STATE",
                    "deck_lane_context",
                    "state.deck_lane_context",
                    render_deck_lane_context(state),
                )
                tracer.note_change(
                    "STATE",
                    "deck_reference_context",
                    "state.deck_reference_context",
                    render_deck_reference_context(state),
                )
                tracer.note_change(
                    "STATE",
                    "deck_source_context",
                    "state.deck_source_context",
                    render_deck_source_context(state),
                )
                tracer.note_change(
                    "STATE",
                    "deck_audio_context",
                    "state.deck_audio_context",
                    render_deck_audio_context(state),
                )
                tracer.note_change(
                    "STATE",
                    "deck_audio_separation_context",
                    "state.deck_audio_separation_context",
                    render_deck_audio_separation_context(audio_capture_context),
                )
                tracer.note_change(
                    "STATE",
                    "deck_audio_features_context",
                    "state.deck_audio_features_context",
                    render_deck_audio_features_context(audio_capture_context),
                )
                tracer.note_change(
                    "STATE",
                    "deck_audio_delta_context",
                    "state.deck_audio_delta_context",
                    render_deck_audio_delta_context(audio_capture_context),
                )
                tracer.note_change(
                    "STATE",
                    "deck_audio_window_context",
                    "state.deck_audio_window_context",
                    render_deck_audio_window_context(audio_capture_context),
                )
                tracer.note_change(
                    "STATE",
                    "audio_delta",
                    "state.audio_delta",
                    tuple(render_audio_delta_items(state)),
                )
                tracer.note_change(
                    "STATE",
                    "live_evidence_context",
                    "state.live_evidence_context",
                    render_live_evidence_context(
                        state,
                        audio_capture_context=audio_capture_context,
                    ),
                )
            except Exception:
                pass

        if ev is not None and isinstance(audio_capture_context, dict):
            ev.extra.setdefault("audio_capture_context", audio_capture_context)

        if ev is not None:
            # §EARNED-LIVE-MASTERED-VERIFY — credit the v11.0 skill(s) this CITED
            # live event demonstrates (no-op when Learn handles are absent, the
            # event maps to no skill, or its citation does not resolve). Fires
            # independent of whether this event also triggers an AI reaction.
            credited = _credit_live_skill_demo(
                ev,
                state,
                evidence_registry=evidence_registry,
                learn_progress=learn_progress,
                speak=mastered_speak,
            )
            # A live cited demo just advanced the Earned Wall — push the refresh
            # to the shell so the SkillWall trophy updates without a reload.
            await _emit_earned_wall_refresh(credited, learn_progress, ipc_bus)
            _tr(
                "event",
                "emit",
                type=ev.type,
                manual=manual,
                kaan_just_spoke=kaan_just_spoke,
                audible=state.audible,
                deck=state.audible_deck,
            )

        # PILL next-suggestion (additive, off-loop): the seed track changed, so
        # the "what's next" must change. Use the service scheduler when present
        # so TRACK_CHANGE and the 30Hz bus share one in-flight guard; fallback to
        # the legacy executor path for duck-typed test holders. Independent of
        # whether this event also fires an AI reaction.
        if suggestion_service is not None and ev is not None and ev.type == "TRACK_CHANGE":
            try:
                if hasattr(suggestion_service, "maybe_schedule_compute_from_state"):
                    scheduled = suggestion_service.maybe_schedule_compute_from_state(state)
                    _tr(
                        "suggestion",
                        "recompute_scheduled" if scheduled else "recompute_held",
                        seed_track=state.audible_track,
                    )
                    if tracer is not None:
                        tracer.suggestion(
                            "dispatch",
                            chosen=state.audible_track,
                            why="scheduled" if scheduled else "held",
                        )
                else:
                    _tr("suggestion", "recompute_dispatched", seed_track=state.audible_track)
                    fut = asyncio.get_running_loop().run_in_executor(
                        None, suggestion_service.compute_from_state, state
                    )

                    def _trace_suggestion_done(f: Any) -> None:
                        _log_suggestion_error(f)
                        if tracer is None:
                            return
                        try:
                            if f.exception() is not None:
                                return
                            result = f.result()
                            if result is None:
                                tracer.suggestion("result", chosen=None, why="no_candidate")
                            else:
                                tracer.suggestion(
                                    "result",
                                    chosen=result.get("track_id") or result.get("title"),
                                    detail=result,
                                )
                        except Exception:
                            pass

                    fut.add_done_callback(_trace_suggestion_done)
            except Exception as e:
                _safe_print(f"\n[coach suggestion] {e}", file=sys.stderr)

        if ev is None:
            continue

        if ev.type in (
            "TRACK_CHANGE",
            "TRANSITION_OPPORTUNITY",
        ):
            try:
                if suggestion_service is not None:
                    current_suggestion = None
                    if hasattr(suggestion_service, "current_for_state"):
                        current_suggestion = suggestion_service.current_for_state(state)
                    elif hasattr(suggestion_service, "current"):
                        current_suggestion = suggestion_service.current()
                    voice_line = build_next_suggestion_voice_line(
                        current_suggestion,
                        event_type=ev.type,
                        evidence_registry=evidence_registry,
                    )
                    if voice_line:
                        ev.extra["next_suggestion_voice_line"] = voice_line
                    transition_line = build_transition_verdict_voice_line(
                        current_suggestion,
                        event_type=ev.type,
                        evidence_registry=evidence_registry,
                    )
                    if transition_line:
                        ev.extra["transition_verdict_voice_line"] = transition_line
                set_line = build_set_progress_voice_line(
                    getattr(state, "set_progress", None),
                    event_type=ev.type,
                    evidence_registry=evidence_registry,
                )
                if set_line:
                    ev.extra["set_progress_voice_line"] = set_line
            except Exception as e:
                _safe_print(f"\n[coach suggestion voice] {e}", file=sys.stderr)

        try:
            trigger_state["in_flight"] = True
            trigger_state["in_flight_at"] = now
            tag = ev.type
            _safe_print(
                f"\n[event {tag}] audible={state.audible} deck={state.audible_deck} "
                f"track={state.audible_track!r}({state.audible_track_confidence:.1f}) "
                f"phase={state.phase}"
            )
            event_payload = {
                "type": tag,
                "audible": state.audible,
                "deck": state.audible_deck,
                "track": state.audible_track,
                "track_conf": round(state.audible_track_confidence, 2),
                "phase": state.phase,
            }
            audio_delta_items = render_audio_delta_items(state)
            moves = ev.extra.get("moves", []) if isinstance(ev.extra, dict) else []
            context_feed_contract = render_context_feed_contract(
                state,
                moves,
                surface="session_event",
            )
            if context_feed_contract:
                event_payload["context_feed_contract"] = context_feed_contract
            deck_lane_context = render_deck_lane_context(state)
            if deck_lane_context:
                event_payload["deck_lane_context"] = deck_lane_context
            deck_reference_context = render_deck_reference_context(state)
            if deck_reference_context:
                event_payload["deck_reference_context"] = deck_reference_context
            deck_source_context = render_deck_source_context(state)
            if deck_source_context:
                event_payload["deck_source_context"] = deck_source_context
            deck_audio_context = render_deck_audio_context(state)
            if deck_audio_context:
                event_payload["deck_audio_context"] = deck_audio_context
            deck_audio_separation_context = render_deck_audio_separation_context(
                audio_capture_context
            )
            if deck_audio_separation_context:
                event_payload["deck_audio_separation_context"] = deck_audio_separation_context
            deck_audio_features_context = render_deck_audio_features_context(audio_capture_context)
            if deck_audio_features_context:
                event_payload["deck_audio_features_context"] = deck_audio_features_context
            deck_audio_delta_context = render_deck_audio_delta_context(audio_capture_context)
            if deck_audio_delta_context:
                event_payload["deck_audio_delta_context"] = deck_audio_delta_context
            deck_audio_window_context = render_deck_audio_window_context(audio_capture_context)
            if deck_audio_window_context:
                event_payload["deck_audio_window_context"] = deck_audio_window_context
            if audio_delta_items:
                event_payload["audio_delta"] = audio_delta_items[:4]
            if moves:
                audio_window_context = render_audio_window_context(state, moves)
                if audio_window_context:
                    event_payload["audio_window_context"] = audio_window_context
            live_evidence_context = render_live_evidence_context(
                state,
                moves if moves else None,
                audio_delta_items=audio_delta_items,
                audio_capture_context=audio_capture_context,
            )
            if live_evidence_context:
                event_payload["live_evidence_context"] = live_evidence_context
            if moves:
                move_context = render_move_context(state, moves)
                deck_change_context = render_deck_change_context(state, moves)
                move_effect_context = render_move_effect_context(
                    state,
                    moves,
                    audio_delta_items=audio_delta_items,
                    audio_capture_context=audio_capture_context,
                )
                if move_context:
                    event_payload["move_context"] = move_context
                if deck_change_context:
                    event_payload["deck_change_context"] = deck_change_context
                if move_effect_context:
                    event_payload["move_effect_context"] = move_effect_context
            recorder.log_event("event", **event_payload)

            # 4d — the live Vibe Judge grades the blend the instant a track
            # change lands, BEFORE the reaction fires, so the grounded
            # [judge:transition@t] citation is already in the registry if the
            # co-host voices the verdict. Abstain-first: on the master-only rig
            # (routing off / one stereo mix) or any policy short of
            # supported_verdict it records an honest-null row and credits
            # nothing; only a grounded two-deck verdict advances a v11 skill.
            # live_claim_policy mirrors dj_cohost.py's reaction-time resolution
            # so the Judge sees the same evidence the prompt does.
            if deck_audio_capture is not None and tag == "TRACK_CHANGE":
                judge_policy, _judge_reason = live_claim_policy(
                    state,
                    moves,
                    audio_capture_context=audio_capture_context,
                    audio_delta_items=audio_delta_items,
                )
                judge_voice_lines: list[str] = []
                _run_live_judge(
                    deck_audio_capture,
                    state,
                    policy=judge_policy,
                    evidence_registry=evidence_registry,
                    recorder=recorder,
                    learn_progress=learn_progress,
                    speak=mastered_speak,
                    judge_voice_lines=judge_voice_lines,
                )
                if judge_voice_lines:
                    ev.extra["judge_evidence_line"] = judge_voice_lines[0]

            if wired:
                # ---- cancel-and-refire on stale in-flight ----
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

            # Hand the event to the agent so llm_node can build the grounded
            # multimodal prompt (text evidence + audio Part + screen Part).
            agent.set_next_event(ev)

            _tr("ai_call", "generate_reply", type=tag, wired=wired)
            _call_started = time.time()
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
                _tr(
                    "ai_resp",
                    "playout_done",
                    type=tag,
                    latency_ms=round((time.time() - _call_started) * 1000, 1),
                )
            except TimeoutError:
                _tr(
                    "ai_resp",
                    "playout_timeout",
                    type=tag,
                    latency_ms=round((time.time() - _call_started) * 1000, 1),
                )
                _safe_print("[coach] generate_reply timed out", file=sys.stderr)
            finally:
                trigger_state["in_flight"] = False
                if wired:
                    # Clear handle/ev so the next tick's cancel branch does
                    # not see a stale handle from a normal completion.
                    trigger_state["in_flight_handle"] = None
                    trigger_state["in_flight_ev"] = None
        except Exception as e:
            trigger_state["in_flight"] = False
            _tr("error", "coach_loop", err=str(e))
            _safe_print(f"\n[coach err] {e}", file=sys.stderr)
