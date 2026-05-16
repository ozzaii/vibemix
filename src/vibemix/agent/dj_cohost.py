# SPDX-License-Identifier: Apache-2.0
"""DJCoHostAgent — Phase 10 cascade with prompt-matrix dispatch + anti-slop.

Hijacks ``llm_node`` to bypass LiveKit's text-only cascade and call
``google.genai`` directly with the last INVOKE_AUDIO_SECONDS of audio attached
as a multimodal Part. The LLM literally hears the music.

PHASE 10 ADDITIONS (on top of the Phase 4 v4-port):

1. **Env-var prompt dispatch** — ``__init__`` reads ``VIBEMIX_SKILL_LEVEL``
   and ``VIBEMIX_MODE`` (defaults: ``intermediate`` / ``hype``) and selects the
   right cell from ``vibemix.prompts.matrix.build_system_instruction(...)``.
   Default = HYPE_INTERMEDIATE = byte-identical v4 SYSTEM_INSTRUCTION.

2. **<silence/> short-circuit** — ``llm_node`` accumulates the LLM stream into
   a buffer; if the stripped output is exactly ``<silence/>`` (or starts with
   it), the entire turn is suppressed (no chunks yielded → no TTS → no
   playback) and a ``silence_short_circuit`` event is logged.

3. **Slop filter (post-hoc)** — after silence check, the accumulated text is
   passed through ``filter_for_slop``; if any banned phrase matches, the turn
   is suppressed and a ``slop_suppressed`` event is logged with the matched
   phrases. Otherwise chunks are yielded in their original order.

   Streaming behavior change vs Phase 4: chunks are now buffered until the
   stream completes, then yielded in one batch (after the silence + slop
   gate). Adds ~1 LLM-stream-duration of latency to the TTS path (~1-2s for
   short replies) — acceptable for v1; Phase 14 may revisit with progressive
   streaming if the latency cost shows in Coach feedback.

Other lines remain byte-for-byte v4 — the v4:1502 anti-hallucination comment
stays at its load-bearing position; ``screen_jpeg = None`` deliberate
single-modality gate is preserved.
"""

from __future__ import annotations

import collections
import json
import os
import sys
import time
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from google import genai
from google.genai import types
from livekit.agents import Agent, ModelSettings
from livekit.agents import llm as agents_llm
from livekit.agents import tts as agents_tts

from vibemix.agent._streaming_pipe import find_sentence_end, passes_head_gate
from vibemix.agent.ack_bank import BUCKET_FOR_EVENT
from vibemix.agent.cache import GeminiContextCache
from vibemix.agent.config import LLM_MODEL
from vibemix.audio import (
    INVOKE_AUDIO_SECONDS,
    MIC_AUDIO_PART_PRESENCE_RMS,
    MIC_AUDIO_PART_RECENCY_S,
    MIC_AUDIO_PART_SECONDS,
    AudioBuffer,
    VoiceRecorder,
    snapshot_wav,
)
from vibemix.coach import CitationLinter, StrippedRateTracker
from vibemix.prompts import build_parts_description, build_system_instruction, filter_for_slop
from vibemix.runtime.llm_to_tts_delta_meter import LLMToTTSDeltaMeter
from vibemix.runtime.ttft import TTFTMeter
from vibemix.state import AICoach, Event, EvidenceRegistry, MusicState, parse_citations
from vibemix.state.coach import ACK_ELIGIBLE_EVENTS
from vibemix.ui_bus import SessionOverlayHighlight

if TYPE_CHECKING:  # pragma: no cover — typing-only
    from vibemix.agent.ack_bank import AckBank
    from vibemix.audio.buffers import PlaybackQueue
    from vibemix.audio.lookahead import LookaheadProvider
    from vibemix.runtime.ws_bus import IpcBus

# Sentinel suppression-token the LLM emits when nothing's worth reacting to.
# The cascade swallows it. See ``vibemix.prompts.matrix`` for the prompt-side
# instruction.
SILENCE_TOKEN = "<silence/>"

# Plan 19-02 — events where the screen Part is ALWAYS skipped, even if a
# screen frame is available. CONTEXT D-08 rule: MIX_MOVE + HEARTBEAT keep the
# diet payload tight (text + 6s audio only). Pre-wires the v2.x re-enable
# path with the diet rule already enforced — for v2.0 the screen Part is
# always None (v4 anti-hallucination invariant), so this guard is a no-op
# today; it becomes load-bearing the day the screen Part comes back.
SCREEN_SKIP_EVENTS: frozenset[str] = frozenset({"MIX_MOVE", "HEARTBEAT"})

# Plan 19-02 — diet audio window for ack-eligible events. Trims from the
# default 18s INVOKE_AUDIO_SECONDS to 6s — saves ≥500ms TTFT (CONTEXT D-08
# Pitfall 9) by reducing the multimodal payload size.
DIET_AUDIO_SECONDS: float = 6.0

# Env-var names — public contract, surfaced in CLI / Settings UI in Phase 11/12.
ENV_SKILL_LEVEL = "VIBEMIX_SKILL_LEVEL"
ENV_MODE = "VIBEMIX_MODE"
# Phase 13-05 — mood persona env override. Default "hype-man" preserves
# Phase 10 backward compat (the byte-identical-to-v4 invariant) — the
# Coach prompt template renders the mood only for COACH cells.
ENV_MOOD = "VIBEMIX_MOOD"

# Defaults — preserve Phase 4 v4 behavior for callers that don't set env vars.
DEFAULT_SKILL_LEVEL = "intermediate"
DEFAULT_MODE = "hype"
DEFAULT_MOOD = "hype-man"

# Plan 24-02 — overlay-highlight defaults.
# 1300ms = 200ms fade-in + 800ms hold + 300ms fade-out per CDJ Whisper v5
# ring animation timing. Matches the Rust overlay.html CSS keyframe.
OVERLAY_DURATION_MS: int = 1300
OVERLAY_COLOR: str = "amber"

# Plan 41-04 — silence-pad payload pushed to ``PlaybackQueue`` when a
# speculatively-emitted head is invalidated by the post-stream gate
# (slop / citation_failure). 500ms of 24kHz int16 mono zero-fill ==
# 24000 bytes. The pad replaces the audio that would have been the
# trailing slop; the LiveKit OPUS pipeline plays it as ~half a second of
# audible silence — a perceptible "cut" rather than a hard click.
#
# Per Pitfall 8: if the LiveKit TTS path has already committed the head
# audio frames into the OPUS encoder, the silence-pad APPENDS to the
# queue — it does NOT preempt frames already in flight. The realistic
# user experience is "head plays, then a brief silence where the slop
# would have been". The cleaner cancel (mid-utterance cut) is documented
# as a known degrade — see CONTEXT.md Open Q2.
SILENCE_PAD_MS: int = 500
SILENCE_PAD_BYTES: int = 24000 * 2 * SILENCE_PAD_MS // 1000  # 24kHz * 2B * 0.5s = 24000B


def _resolve_prompt_cell(mood: str | None = None) -> str:
    """Read the env vars and dispatch to the right matrix cell.

    Re-evaluated per ``DJCoHostAgent`` instantiation (no module-level
    caching) so unit tests can monkeypatch and Settings UI can hot-swap
    by re-instantiating the agent (Phase 11/12).

    Args:
        mood: Phase 13-05 mood override. When None (default), reads
            ``VIBEMIX_MOOD`` env var, falling back to ``"hype-man"``. A
            non-None ``mood`` arg wins over the env var (used by Plan
            13-06's agent-rebuild-on-mood-change path).

    Raises ``ValueError`` on unknown skill, mode, or mood (fail loud —
    silent fallback would mask env-var typos).
    """
    skill = os.environ.get(ENV_SKILL_LEVEL, DEFAULT_SKILL_LEVEL)
    mode = os.environ.get(ENV_MODE, DEFAULT_MODE)
    if mood is None:
        mood = os.environ.get(ENV_MOOD, DEFAULT_MOOD)
    return build_system_instruction(skill, mode, mood)


class DJCoHostAgent(Agent):
    """Hijacks llm_node to bypass LiveKit's text-only cascade and call
    google.genai directly with the last 10s of audio + the latest screen
    frame attached as multimodal Parts. The LLM literally hears the music.

    Phase 10: env-var dispatch over the 6-cell prompt matrix +
    ``<silence/>`` short-circuit + post-hoc slop filter.
    """

    def __init__(
        self,
        *,
        genai_client: genai.Client,
        clean_audio_buf: AudioBuffer,
        screen_buf,  # duck-typed: has .latest() -> (bytes | None, (w, h))
        state: MusicState,
        recorder: VoiceRecorder,
        llm_inst: agents_llm.LLM,
        tts_inst: agents_tts.TTS,
        evidence_registry: EvidenceRegistry | None = None,
        cache: GeminiContextCache | None = None,
        ttft_meter: TTFTMeter | None = None,
        # Plan 20-01 — citation-linter chokepoint kwargs. ALL FOUR must be
        # non-None for the wired path; default None preserves Phase 18/19
        # backward-compat (legacy emit-everything-from-buffered-chunks
        # behavior). The all-or-nothing wiring keeps the byte-identity
        # guarantee for the existing tests/agent/test_dj_cohost.py suite.
        citation_linter: CitationLinter | None = None,
        stripped_rate_tracker: StrippedRateTracker | None = None,
        ack_bank: "AckBank | None" = None,
        playback: "PlaybackQueue | None" = None,
        # Plan 24-02 — overlay-highlight publish path. Default None
        # preserves backward compat (no overlay events). When non-None,
        # llm_node publishes ipc.session.overlay-highlight envelopes for
        # every [screen:<element>] citation in an emit-action turn.
        ipc_bus: "IpcBus | None" = None,
        # Plan 32-03 / PROFILE-04 — long-term DJ profile reference. P53
        # kwargs-only addition; None default keeps v2.0 4-kwarg construction
        # path byte-identical. P60: profile lives in GeminiContextCache
        # (vibemix.agent.cache.GeminiContextCache.profile_section), NEVER
        # in the per-turn prompt. The agent stores the reference only for
        # diagnostics; llm_node must NEVER read it (enforced by
        # tests/profile/test_profile_not_in_per_turn_prompt.py).
        profile: dict | None = None,
        # Plan 40-01 / AUDIO-01 — mic-as-2nd-Gemini-Part ring. None default
        # preserves Phase 4/18/19 backward compat (the existing 1-Part
        # request is byte-identical when mic_audio_buf is None). When non-
        # None, llm_node appends a 2nd ``audio/wav`` Part to ``contents``
        # iff (a) KAAN_SPOKE is recent (within MIC_AUDIO_PART_RECENCY_S)
        # and (b) the ring snapshot has signal (RMS > presence floor).
        # Closes hallucination class "AI invents what Kaan said" by
        # putting Kaan's literal voice in front of Gemini.
        mic_audio_buf: "AudioBuffer | None" = None,
        # Plan 40-03 / AUDIO-02 + AUDIO-04 — source-file lookahead provider.
        # None default preserves Phase 4/18/19/40-01 backward compat (the
        # 1-Part / 2-Part request shapes are byte-identical when lookahead
        # is None). When non-None, llm_node calls
        # ``self._lookahead.snapshot_wav()`` after the mic Part attach and
        # conditionally appends a 3rd ``audio/wav`` Part containing 18s
        # ending ~3s past the current playhead. The prompt-suffix labels
        # that Part with "NOT YET HEARD BY AUDIENCE" per locked CONTEXT
        # Q2 — closes the "AI claims to predict the future" hallucination
        # class that lookahead introduces.
        lookahead: "LookaheadProvider | None" = None,
    ):
        # Resolve which prompt cell to use BEFORE super().__init__ — the
        # parent Agent constructor stores ``instructions`` for LiveKit's
        # text-only fallback path. We pass the matrix-resolved cell here.
        # Phase 13-05: prefer the live MusicState.mood over the env-var
        # default so a mood-swap before agent build is honored. Plan 13-06
        # is responsible for re-instantiating the agent on subsequent swaps.
        # Plan 18-03: prompt_body now includes the citation-grammar block
        # appended via build_system_instruction's default
        # include_citation_grammar=True — Gemini SEES the grammar in the
        # system instruction (GROUND-03 prompt-only seeding).
        live_mood = getattr(state, "mood", None)
        prompt_body = _resolve_prompt_cell(mood=live_mood)
        super().__init__(
            instructions=prompt_body,
            llm=llm_inst,
            tts=tts_inst,
            allow_interruptions=False,
        )
        self._genai_client = genai_client
        self._clean_audio_buf = clean_audio_buf
        self._screen_buf = screen_buf
        self._state = state
        self._recorder = recorder
        # Plan 18-03 — evidence registry for per-turn snapshot threading.
        # Default None preserves Phase 4 backward-compat (the agent is the
        # only call site that wires the registry into AICoach.build_prompt;
        # standalone tests + legacy run paths skip the snapshot).
        self._registry: EvidenceRegistry | None = evidence_registry
        # Plan 19-03 — optional context cache. None default preserves Phase 4
        # backward compat (llm_node uses self._gen_cfg with system_instruction
        # inline). When non-None AND cache.current_name() returns a string,
        # llm_node builds a per-call gen_cfg with cached_content set.
        self._cache: GeminiContextCache | None = cache
        # Plan 19-05 — optional TTFT meter. None default preserves backward
        # compat for tests that don't drive the meter. When non-None,
        # set_next_event records the event-fired timestamp and llm_node
        # records the first non-empty stream chunk timestamp; the rolling
        # average feeds AckBank.should_fire(rolling_ttft_avg_ms=...).
        self._ttft_meter: TTFTMeter | None = ttft_meter
        # Plan 41-04 / LAT-04 — per-turn (event_fired → first_sentence
        # _yielded) delta meter. Always-on (unlike _ttft_meter which is
        # optional). Records via :meth:`llm_node` at the speculative head
        # emit point; emits ``llm_to_tts_delta_ms`` to events.jsonl when
        # a head was yielded. Skip path (no head emitted — short
        # response / suppression / strip) writes no event.
        self._llm_to_tts_meter: LLMToTTSDeltaMeter = LLMToTTSDeltaMeter()
        # Plan 20-01 — citation linter chokepoint. All four kwargs default
        # None; the wired path runs iff ALL FOUR are non-None. ``_linter_wired``
        # is computed once at __init__ to avoid four None-checks on every
        # turn (the gate runs in the LLM hot-path).
        self._linter: CitationLinter | None = citation_linter
        self._stripped_tracker: StrippedRateTracker | None = stripped_rate_tracker
        self._ack_bank: "AckBank | None" = ack_bank
        self._playback: "PlaybackQueue | None" = playback
        self._linter_wired: bool = all(
            x is not None
            for x in (citation_linter, stripped_rate_tracker, ack_bank, playback)
        )
        # Plan 24-02 — overlay-highlight publish path. Wired iff non-None.
        self._ipc_bus: "IpcBus | None" = ipc_bus
        # Plan 32-03 / PROFILE-04 — stored read-only reference. NEVER
        # accessed inside llm_node (P60 grep gate enforces this). The
        # Settings → Profile panel may read it for diagnostics without
        # re-loading from disk. If you find yourself adding self._profile
        # into the per-turn flow, STOP — that breaks the cache contract.
        self._profile: dict | None = profile
        # Plan 40-01 / AUDIO-01 — mic ring reference. Read-only consumer:
        # llm_node snapshots the ring per turn and conditionally attaches
        # Part 2 to ``contents``. The ring itself is fed by
        # ``__main__._mic_callback_factory`` on the sounddevice audio thread
        # (verbatim port of cohost_v4.py:2278-2296 with AI-talk zero-fill).
        self._mic_audio_buf: "AudioBuffer | None" = mic_audio_buf
        # Plan 40-03 / AUDIO-02 + AUDIO-04 — lookahead provider reference.
        # Read-only consumer: llm_node calls ``snapshot_wav()`` per turn
        # and conditionally appends Part 3 to ``contents``. The provider
        # is per-session (instantiated in __main__.py next to
        # clean_audio_buf); the title→path cache lives for the whole DJ
        # session per RESEARCH Open Question 3 resolution.
        self._lookahead: "LookaheadProvider | None" = lookahead
        self._pending_event: Event | None = None
        self._ai_text_history: collections.deque = collections.deque(maxlen=10)
        # Both the LiveKit-side ``instructions`` AND the google.genai-side
        # ``GenerateContentConfig.system_instruction`` use the same cell.
        self._gen_cfg = types.GenerateContentConfig(
            system_instruction=prompt_body,
            thinking_config=types.ThinkingConfig(thinking_level="minimal"),
            temperature=1.0,
            max_output_tokens=220,
        )

    def set_next_event(self, ev: Event) -> None:
        self._pending_event = ev
        # Plan 19-05 — start the TTFT measurement window. Overwriting an
        # existing pending pointer is intentional (the previous event was
        # preempted via CancelGate or failed via TimeoutError).
        if self._ttft_meter is not None:
            self._ttft_meter.record_event_fired()
        # Plan 41-04 / LAT-04 — arm the LLM→TTS delta meter at the same
        # boundary so its event_fired_at matches the TTFT meter's. Both
        # meters share the (event_fired, first_*_at) baseline; only the
        # measured RHS differs (first_chunk vs first_sentence_yielded).
        self._llm_to_tts_meter.start_turn()

    async def llm_node(
        self,
        chat_ctx: agents_llm.ChatContext,
        tools: list,
        model_settings: ModelSettings,
    ) -> AsyncGenerator:
        ev = self._pending_event
        self._pending_event = None

        # Plan 18-03 — snapshot the EvidenceRegistry FRESH per turn so the
        # AICoach.evidence_line corpus footer reflects observations written
        # by state_refresh_loop + EventDetector since the last invocation.
        # snapshot() is O(N) over total observations and lock-guarded; with
        # the cohost_v4 cooldown gates a 1h DJ session caps at ~500 obs, so
        # this fits well under 1ms per turn (cheap). When _registry is None
        # (default Phase 4 backward-compat path), pass None — AICoach skips
        # the corpus footer and the v4 byte-identical evidence_line is
        # preserved. This is the production-corpus seeding loop:
        #   registry → snapshot → AICoach evidence_corpus footer → Gemini
        # plus the citation-grammar block in the system instruction
        # (Task 1) tells Gemini HOW to cite against that corpus.
        snapshot = self._registry.snapshot() if self._registry is not None else None

        # Plan 19-02 — diet dispatch. Ack-eligible events (HEARTBEAT,
        # MIX_MOVE, LAYER_ARRIVAL, KAAN_SPOKE) shrink to a 6s audio window
        # + the compact 5-field evidence_line; non-ack events keep the full
        # 18s window + full evidence_line + corpus footer. An unknown
        # ev.type defaults safely to diet=False (full payload) — erring
        # toward correctness over latency (T-19-02-02 mitigation).
        ev_type_for_diet = ev.type if ev is not None else "MANUAL"
        diet = ev_type_for_diet in ACK_ELIGIBLE_EVENTS
        audio_seconds = DIET_AUDIO_SECONDS if diet else INVOKE_AUDIO_SECONDS
        skip_screen = ev_type_for_diet in SCREEN_SKIP_EVENTS

        # Build grounded text packet (same evidence + task v2 used)
        if ev is not None:
            text_prompt = AICoach.build_prompt(ev, registry_snapshot=snapshot, diet=diet)
        else:
            # No event context (e.g. generate_reply called without prep) — fall back
            text_prompt = AICoach.build_prompt(
                Event(type="MANUAL", state=self._state, extra={}),
                registry_snapshot=snapshot,
                diet=diet,
            )

        audio_wav = snapshot_wav(self._clean_audio_buf, audio_seconds)
        # Per-invocation dump folder — full audit trail for rapid dev.
        invoke_ts = time.strftime("%H%M%S")
        invoke_n = getattr(self, "_invoke_counter", 0) + 1
        self._invoke_counter = invoke_n
        invoke_dir = (
            self._recorder.session_dir
            / "invocations"
            / f"{invoke_n:04d}_{invoke_ts}_{ev.type if ev else 'MANUAL'}"
        )
        try:
            invoke_dir.mkdir(parents=True, exist_ok=True)
            (invoke_dir / "audio.wav").write_bytes(audio_wav)
            # Also keep top-level shortcut to the latest dump.
            (self._recorder.session_dir / "last_gemini_audio.wav").write_bytes(audio_wav)
        except Exception as _e:
            print(f"[dump err] {_e}", file=sys.stderr)
        # Single-modality: audio only. Screen + MIDI metadata caused hallucination.
        # Plan 19-02 pre-wiring: when v2.x re-enables screen capture, the
        # gate becomes ``screen_jpeg = None if skip_screen else
        # self._screen_buf.latest()[0]`` — for v2.0 the line stays None per
        # the v4 anti-hallucination invariant. The screen Part append below
        # gets a ``not skip_screen`` guard so the diet rule is enforced
        # the moment the screen frame becomes non-None.
        screen_jpeg = None

        # Short-term verbal memory — don't repeat or rephrase what you just said
        history_clause = ""
        if self._ai_text_history:
            recent = " | ".join(f'"{t}"' for t in self._ai_text_history)
            history_clause = (
                f"\n\nRECENT THINGS YOU JUST SAID (do NOT repeat or rephrase — pick a "
                f"DIFFERENT angle, or stay silent if there's nothing new): {recent}"
            )

        # Plan 40-01 / AUDIO-01 — mic-as-2nd-Gemini-Part decision. Three
        # gates; all must pass for Part 2 to attach:
        #   1. self._mic_audio_buf is not None
        #   2. now - state.last_kaan_spoke_at <= MIC_AUDIO_PART_RECENCY_S
        #   3. snapshot ring RMS > MIC_AUDIO_PART_PRESENCE_RMS * 32767
        # The snapshot/RMS work runs ONCE; the result + skip-reason feed
        # both the prompt suffix and the structured log line. Plan 40-03
        # will append a 3rd lookahead Part immediately after this block.
        mic_wav: bytes | None = None
        mic_skip_reason: str | None = None
        kaan_spoke_age_s: float | None = None
        mic_rms_int16: float = 0.0
        if self._mic_audio_buf is None:
            mic_skip_reason = "no_mic_audio_buf"
        else:
            kaan_spoke_age_s = time.time() - self._state.last_kaan_spoke_at
            if kaan_spoke_age_s > MIC_AUDIO_PART_RECENCY_S:
                mic_skip_reason = "kaan_spoke_not_recent"
            else:
                # Snapshot the ring at the v4-baseline 8s window and check
                # presence. snapshot_wav already peak-normalizes — read the
                # raw int16 pcm via buf.snapshot() for an honest RMS gate.
                import numpy as _np  # local import — keeps top-level clean

                n = int(MIC_AUDIO_PART_SECONDS * self._mic_audio_buf._sr)
                pcm = self._mic_audio_buf.snapshot(n)
                if pcm.size == 0:
                    mic_skip_reason = "mic_ring_empty"
                else:
                    mic_rms_int16 = float(
                        _np.sqrt(_np.mean(pcm.astype(_np.float32) ** 2))
                    )
                    presence_floor_int16 = MIC_AUDIO_PART_PRESENCE_RMS * 32767.0
                    if mic_rms_int16 < presence_floor_int16:
                        mic_skip_reason = "mic_silent"
                    else:
                        mic_wav = snapshot_wav(
                            self._mic_audio_buf, MIC_AUDIO_PART_SECONDS
                        )

        # Plan 40-03 / AUDIO-02 + AUDIO-04 — source-file lookahead Part 3
        # decision. Belt-and-braces try/except wrapping: the provider's
        # snapshot_wav() already returns ``(None, meta)`` on every observed
        # failure path (T-40-02-* threat register), but the wrapper here
        # guarantees ``llm_node`` cannot crash even if the provider
        # misbehaves (T-40-03-02 mitigation). When self._lookahead is
        # None (Phase 4/40-01 backward-compat default), Part 3 is never
        # attempted and the meta dict carries an explicit "no_lookahead"
        # reason — feeds the lookahead_part_skipped event below.
        lookahead_wav: bytes | None = None
        lookahead_meta: dict = {"ok": False, "reason": "no_lookahead"}
        if self._lookahead is not None:
            try:
                lookahead_wav, lookahead_meta = self._lookahead.snapshot_wav()
            except Exception as e:  # noqa: BLE001 — graceful degrade per T-40-03-02
                print(f"[lookahead err] {e}", file=sys.stderr)
                lookahead_wav = None
                lookahead_meta = {"ok": False, "reason": f"exception: {e!r}"}
        mic_attached = mic_wav is not None
        lookahead_attached = lookahead_wav is not None

        # Plan 40-03 — Part-aware prompt suffix via build_parts_description.
        # Delegates the 4-way string dispatch (1-Part baseline / mic-only /
        # lookahead-only / 3-Part full) to the locked builder in
        # vibemix.prompts.matrix. The builder encodes CONTEXT.md Q2:
        # lookahead-present variants carry "NOT YET HEARD BY AUDIENCE" +
        # anti-prediction guard language.
        parts_clause = build_parts_description(
            audio_seconds=float(audio_seconds),
            has_mic_part=mic_attached,
            has_lookahead_part=lookahead_attached,
        )

        contents: list = [
            text_prompt + parts_clause + history_clause,
            types.Part.from_bytes(data=audio_wav, mime_type="audio/wav"),
        ]
        if mic_attached:
            contents.append(types.Part.from_bytes(data=mic_wav, mime_type="audio/wav"))
            self._recorder.log_event(
                "mic_part_attached",
                duration_s=MIC_AUDIO_PART_SECONDS,
                rms_int16=mic_rms_int16,
                kaan_spoke_age_s=kaan_spoke_age_s,
                bytes=len(mic_wav),
            )
        else:
            self._recorder.log_event(
                "mic_part_skipped",
                reason=mic_skip_reason or "unknown",
                kaan_spoke_age_s=kaan_spoke_age_s,
                rms_int16=mic_rms_int16,
            )
        # Plan 40-03 — Part 3 (lookahead) attach + structured event. The
        # mic_part_* / lookahead_part_* pair forms a uniform diagnostic
        # surface for coach-loop tails + Settings → Diagnostics; per-turn
        # both events fire (one of each pair from each side). The lookahead
        # event carries the provider's full meta dict so events.jsonl
        # consumers see title / file / seek / duration / reason.
        if lookahead_attached:
            contents.append(
                types.Part.from_bytes(data=lookahead_wav, mime_type="audio/wav")
            )
            self._recorder.log_event(
                "lookahead_part_attached",
                bytes=len(lookahead_wav),
                **{k: v for k, v in lookahead_meta.items() if k != "bytes"},
            )
        else:
            self._recorder.log_event(
                "lookahead_part_skipped",
                **lookahead_meta,
            )
        if screen_jpeg and not skip_screen:
            contents.append(types.Part.from_bytes(data=screen_jpeg, mime_type="image/jpeg"))

        ev_tag = ev.type if ev else "MANUAL"
        full_prompt = contents[0] if contents else text_prompt
        try:
            (invoke_dir / "prompt.txt").write_text(full_prompt)
        except Exception:
            pass

        # ---- Plan 19-03 — context-cache dispatch ----
        # Three branches:
        #   1. cache is None at construction → cache_state="disabled", reuse
        #      self._gen_cfg by reference (Phase 4 byte-identical path).
        #   2. cache non-None but current_name()=None (warm-up window OR
        #      post-invalidate gap) → cache_state="cold", same fallback as
        #      disabled (system_instruction in self._gen_cfg drives the call).
        #   3. cache non-None AND current_name() returns a string → cache_
        #      state="warm", build a per-call gen_cfg with cached_content set
        #      and system_instruction OMITTED (Gemini rejects passing both).
        #      thinking_config + temperature + max_output_tokens preserved.
        if self._cache is None:
            gen_cfg = self._gen_cfg
            cache_state = "disabled"
        else:
            cache_name = self._cache.current_name()
            if cache_name is None:
                gen_cfg = self._gen_cfg
                cache_state = "cold"
            else:
                gen_cfg = types.GenerateContentConfig(
                    cached_content=cache_name,
                    thinking_config=types.ThinkingConfig(thinking_level="minimal"),
                    temperature=1.0,
                    max_output_tokens=220,
                )
                cache_state = "warm"

        self._recorder.log_event(
            "llm_invoke",
            event=ev_tag,
            audible=self._state.audible,
            deck=self._state.audible_deck,
            track=self._state.audible_track,
            phase=self._state.phase,
            audio_bytes=len(audio_wav),
            has_screen=bool(screen_jpeg),
            audio_seconds=int(audio_seconds),
            diet=diet,
            cache_state=cache_state,
            prompt=text_prompt,
            invoke_dir=str(invoke_dir),
        )
        # Plan 20-01: surface the linter wiring state in the per-turn
        # log line so coach-loop tails show the gate decision next to
        # cache state. Actual gate decision (valid|invalid|skip) is
        # logged after the stream — see the meta.json dump below.
        linter_state = "wired" if self._linter_wired else "skip"
        print(
            f"\n[llm {ev_tag} #{invoke_n:04d}] audio={len(audio_wav) // 1024}KB"
            f"({int(audio_seconds)}s) diet={diet} cache={cache_state} "
            f"linter={linter_state} "
            f"screen={'yes' if screen_jpeg else 'no'} dump={invoke_dir.name}"
        )

        # === Plan 41-04 streaming pipe-through (LAT-04) ===
        # Refactor: replace buffer-then-yield with streaming sentence-
        # boundary yield + dual-phase gate. The head is yielded
        # SPECULATIVELY as soon as ``find_sentence_end`` returns a
        # boundary AND ``passes_head_gate`` clears the head text. The
        # tail then streams as-it-arrives.
        #
        # ``buffered_chunks`` is still maintained so the post-stream
        # legacy emit path (citation linter + suppression) keeps its
        # contract for non-speculative paths (head never fired, short
        # response, suppression). When a head was speculatively yielded,
        # the post-stream gates run on ``full_text`` — if they fail, a
        # silence-pad frame is pushed to ``self._playback`` (cancel-on-
        # trailing-slop per Open Q2 auto-resolution; Pitfall 8 fallback
        # documented below).
        #
        # Streaming pipe state:
        #   accum             — running concat of chunk text since last
        #                       boundary scan; reset (cleared) on first
        #                       boundary, then unused (tail streams).
        #   head_yielded      — True iff the speculative head was emitted.
        #                       Drives post-stream branching (cancel-with-
        #                       silence-pad vs legacy emit-from-buffer).
        full_text = ""
        buffered_chunks: list[str] = []
        accum = ""
        head_yielded = False
        t_start = time.time()
        llm_err: str | None = None
        # Plan 19-05 — record first-chunk arrival exactly once per turn for
        # the TTFT meter. Skipped when no meter wired (Phase 4 backward-compat).
        first_chunk_recorded = False
        try:
            stream = await self._genai_client.aio.models.generate_content_stream(
                model=LLM_MODEL,
                contents=contents,
                config=gen_cfg,
            )
            async for chunk in stream:
                txt = getattr(chunk, "text", None) or ""
                if not txt:
                    continue
                if not first_chunk_recorded and self._ttft_meter is not None:
                    self._ttft_meter.record_first_chunk()
                    first_chunk_recorded = True
                print(txt, end="", flush=True)
                full_text += txt
                buffered_chunks.append(txt)
                # Plan 41-04 — speculative head emit. Run only while we
                # haven't yet committed to a streaming yield path. Once
                # ``head_yielded`` is True we stream subsequent chunks
                # as-they-arrive (the speculative commitment is the
                # binding signal — trailing audio just keeps the listener
                # in flow). The legacy buffered_chunks list is still
                # populated for post-stream citation linting on the full
                # response text.
                if not head_yielded:
                    accum += txt
                    end_idx = find_sentence_end(accum)
                    if end_idx is not None:
                        head = accum[:end_idx]
                        if passes_head_gate(head):
                            head_yielded = True
                            self._llm_to_tts_meter.record_first_sentence()
                            yield head
                            # Any trailing portion of ``accum`` past the
                            # boundary becomes the first trailing chunk
                            # — yield it now so the stream stays
                            # contiguous.
                            tail_remainder = accum[end_idx:]
                            if tail_remainder:
                                yield tail_remainder
                            accum = ""
                        # else: head failed the gate — silence-token or
                        # slop prefix. SUPPRESS the speculative emit
                        # entirely; the post-stream silence/slop pipeline
                        # is the authority and will fire the appropriate
                        # suppression event. Keep accumulating into accum
                        # so a later sentence boundary could still fire
                        # on cleaner trailing text (unlikely in practice
                        # but it's the correct boundary semantics).
                elif head_yielded:
                    # Stream trailing chunks as-they-arrive. The head
                    # already bound the speculative path; trailing audio
                    # streams without further boundary gating. The post-
                    # stream gate (citation linter) is the authority for
                    # cancel-with-silence-pad if the full response is
                    # invalid.
                    yield txt
        except Exception as e:
            llm_err = repr(e)
            print(f"\n[llm err] {e}", file=sys.stderr)
        # === end Plan 41-04 streaming pipe-through ===

        print()
        elapsed = time.time() - t_start
        stripped = full_text.strip()

        # ---- Plan 18-04: citation-count telemetry ----
        # Count citations in the FULL response text BEFORE the suppression
        # gate. Even silence/slop suppressed turns get their emissions
        # counted — Phase 16 ear-test reads ``registry.citation_telemetry()``
        # as Gemini's TRUE emission rate (not the post-suppression rate)
        # to gate Phase 20 enforcement readiness.
        #
        # response_id format ``f"{invoke_n:04d}_{invoke_ts}"`` matches the
        # per-invocation dump folder name pattern (line ~202) so the
        # events.jsonl line cross-references the dump folder trivially.
        # The recorder.log_event auto-injects ``t = time.time() -
        # self.start_time`` (recorder.py:303) — DO NOT pass ``t`` manually.
        #
        # Best-effort: every step is wrapped in try/except: pass — a
        # parser failure or recorder write failure MUST NOT break the LLM
        # response path (matches v4 anti-pattern parity, threat T-18-04-03).
        try:
            citation_pairs = parse_citations(full_text)
            citation_count = len(citation_pairs)
        except Exception:
            citation_count = 0

        response_id = f"{invoke_n:04d}_{invoke_ts}"
        try:
            self._recorder.log_event(
                "citation_count",
                count=citation_count,
                response_id=response_id,
            )
        except Exception:
            pass  # best-effort; recorder write failure must not block LLM path

        if self._registry is not None:
            try:
                self._registry.record_citation_count(citation_count)
            except Exception:
                pass  # best-effort; registry update failure must not block LLM path

        # ---- Silence + slop gate (Phase 10) ----
        suppression: str | None = None
        slop_matches: list[str] = []
        if stripped == SILENCE_TOKEN or stripped.startswith(SILENCE_TOKEN):
            suppression = "silence"
        else:
            # Run filter_for_slop on the FULL accumulated text; suppress turn
            # if any banned phrase matches.
            _filtered, slop_matches = filter_for_slop(full_text)
            if slop_matches:
                suppression = "slop"

        # Plan 20-01 meta.json fields — initialized here so the dump
        # path at the bottom can reference them regardless of which
        # branch ran. "skip" means the wired path was not taken (legacy
        # path or suppression beat the linter to it).
        citation_action: str = "skip"
        citation_lint_valid: bool | None = None
        citation_lint_reason: str | None = None
        citation_lint_missing_payload: list[list[str]] | None = None

        # Plan 41-04 — cancel-with-silence-pad on speculative-emit failure.
        # When ``head_yielded`` is True AND the post-stream gate fails
        # (silence / slop / citation_failure), push a 500ms zero-fill
        # frame into the playback queue (when wired) and emit a
        # ``streaming_cancel`` event. This is the Open Q2 auto-
        # resolution; the LiveKit cancel-race fallback (Pitfall 8) is
        # documented in the module — head may play through to completion
        # if frames are already in the OPUS encoder when we push the pad.
        def _push_silence_pad_and_cancel(reason: str) -> None:
            try:
                if self._playback is not None:
                    self._playback.push(b"\x00" * SILENCE_PAD_BYTES)
            except Exception as _e:
                print(f"[silence-pad err] {_e}", file=sys.stderr)
            try:
                self._recorder.log_event(
                    "streaming_cancel",
                    reason=reason,
                    head_yielded=True,
                    response_chars=len(full_text),
                    latency_s=round(elapsed, 2),
                )
            except Exception:
                pass

        if suppression == "silence":
            self._recorder.log_event(
                "silence_short_circuit",
                event=ev_tag,
                response_chars=len(full_text),
                latency_s=round(elapsed, 2),
            )
            print("[ai_text] <silence/> (suppressed)", flush=True)
            if head_yielded:
                _push_silence_pad_and_cancel("silence")
        elif suppression == "slop":
            self._recorder.log_event(
                "slop_suppressed",
                event=ev_tag,
                matches=slop_matches,
                response_chars=len(full_text),
                latency_s=round(elapsed, 2),
            )
            print(f"[ai_text] <slop suppressed: {slop_matches}>", flush=True)
            if head_yielded:
                _push_silence_pad_and_cancel("slop")
        else:
            # Plan 20-01 — citation linter chokepoint runs HERE, after the
            # silence/slop gate, before yielding chunks. The wired path
            # (all 4 kwargs non-None) runs the binary response-level linter
            # against the same registry snapshot already taken at line ~216
            # (REUSE — never call self._registry.snapshot() twice per turn,
            # races would be possible). The legacy path emits unchanged.
            #
            # Decision ladder (when wired AND suppression is None):
            #   1. valid → emit + tracker.record(False) + ai_text log.
            #   2. invalid + bypass → emit anyway + record(False) +
            #      citation_bypass log + "[ai_text:unverified]" stdout.
            #      Bypass is one-shot per breach window (T-20-01-02).
            #   3. invalid + strip → DO NOT yield + ack-bank PCM push
            #      (when ev.type ∈ BUCKET_FOR_EVENT) + record(True) +
            #      citation_strip log. silence > invented citation.
            if self._linter_wired and self._linter is not None:
                lint_result = self._linter.check(
                    full_text, snapshot, mode="live"
                )
                citation_lint_valid = lint_result.valid
                citation_lint_reason = lint_result.reason
                citation_lint_missing_payload = [list(t) for t in lint_result.missing]

                if lint_result.valid:
                    citation_action = "emit"
                    # Plan 41-04 — head_yielded means the streaming pipe
                    # already emitted the head + trailing chunks
                    # in-flight; the legacy re-yield from buffered_chunks
                    # would duplicate audio. Skip it.
                    if not head_yielded:
                        for txt in buffered_chunks:
                            yield txt
                    if self._stripped_tracker is not None:
                        self._stripped_tracker.record(False)
                    if stripped:
                        print(f"[ai_text] {stripped!r}", flush=True)
                        self._recorder.log_event(
                            "ai_text",
                            text=full_text,
                            latency_s=round(elapsed, 2),
                        )
                        self._ai_text_history.append(stripped[:140])
                    else:
                        print("[ai_text] <empty> (skip TTS)", flush=True)
                else:
                    # Invalid — consult the one-shot bypass before stripping.
                    bypass_active = (
                        self._stripped_tracker.should_bypass()
                        if self._stripped_tracker is not None
                        else False
                    )
                    if bypass_active:
                        citation_action = "bypass"
                        # Plan 41-04 — same head_yielded guard as the
                        # valid path: chunks already in-flight, no
                        # re-yield from buffer.
                        if not head_yielded:
                            for txt in buffered_chunks:
                                yield txt
                        # Bypass means we did NOT strip — tracker records
                        # the actual outcome (False = "we let it through").
                        if self._stripped_tracker is not None:
                            self._stripped_tracker.record(False)
                        self._recorder.log_event(
                            "citation_bypass",
                            response_id=response_id,
                            raw_text=full_text,
                            missing=citation_lint_missing_payload,
                            reason=lint_result.reason,
                            latency_s=round(elapsed, 2),
                        )
                        print(
                            f"[ai_text:unverified] {stripped!r}", flush=True
                        )
                        # History appended on bypass — the user heard the
                        # text, so the no-repeat memory must reflect it.
                        if stripped:
                            self._ai_text_history.append(stripped[:140])
                    else:
                        # Strip path — no chunks yielded, ack-bank PCM
                        # injected if the event class is in the bucket map.
                        citation_action = "strip"
                        ack_bucket: str | None = None
                        ack_sample_idx: int | None = None
                        # Plan 41-04 — when ``head_yielded`` is True the
                        # speculative head is already in flight; we
                        # cannot un-yield it. Fire cancel-with-silence-
                        # pad + ``streaming_cancel`` instead of the
                        # ack-bank substitution (ack would overlap the
                        # head audio — worse than a clean pad).
                        if head_yielded:
                            _push_silence_pad_and_cancel("citation_failure")
                        elif ev is not None and ev.type in BUCKET_FOR_EVENT:
                            try:
                                bucket, pcm, sample_idx = (
                                    self._ack_bank.pick_for_event(ev)
                                    if self._ack_bank is not None
                                    else (None, None, None)
                                )
                                if (
                                    bucket is not None
                                    and pcm is not None
                                    and self._playback is not None
                                ):
                                    self._playback.push(pcm.tobytes())
                                    ack_bucket = bucket
                                    ack_sample_idx = sample_idx
                            except Exception as _e:
                                print(
                                    f"[ack err] {_e}", file=sys.stderr
                                )
                        if self._stripped_tracker is not None:
                            self._stripped_tracker.record(True)
                        self._recorder.log_event(
                            "citation_strip",
                            response_id=response_id,
                            raw_text=full_text,
                            missing=citation_lint_missing_payload,
                            reason=lint_result.reason,
                            ack_bucket=ack_bucket,
                            ack_sample_index=ack_sample_idx,
                            latency_s=round(elapsed, 2),
                        )
                        print(
                            f"[ai_text:stripped] reason={lint_result.reason} "
                            f"ack={ack_bucket}",
                            flush=True,
                        )
                        # History NOT appended — nothing was emitted.
            else:
                # Legacy Phase 18/19 path — clean turn, yield buffered chunks
                # in their original order and run the v4 ai_text logging
                # path (history append + log event). Byte-identical to the
                # pre-Plan-20 behavior (locked by
                # tests/agent/test_dj_cohost.py + test_dj_cohost_silence_*).
                # Plan 41-04 — when ``head_yielded`` is True the streaming
                # path already emitted the chunks in-flight; skip the
                # buffer re-yield to avoid duplicate audio.
                if not head_yielded:
                    for txt in buffered_chunks:
                        yield txt
                if stripped:
                    print(f"[ai_text] {stripped!r}", flush=True)
                    self._recorder.log_event(
                        "ai_text", text=full_text, latency_s=round(elapsed, 2)
                    )
                    self._ai_text_history.append(stripped[:140])
                else:
                    print("[ai_text] <empty> (skip TTS)", flush=True)
                # Legacy path = no linter wired; treat as if citation_action
                # were "emit" for the overlay publish (the user heard the
                # text). Plan 20-01 wired-path callers set citation_action
                # explicitly in the branches above.
                if citation_action == "skip":
                    citation_action = "emit"

        # ---- Plan 24-02 — overlay-highlight publish ----
        # Fire once per [screen:<element>] citation IFF:
        #   1. ipc_bus is wired (sidecar publish path enabled).
        #   2. citation_action is a "user-heard-the-text" action — "emit"
        #      (normal flow) or "bypass" (unverified-but-spoken via the
        #      one-shot bypass guard). "strip" and "skip"-from-suppression
        #      do NOT publish: a ring without audio is ghost-firing.
        # Best-effort: every step wrapped in try/except so a malformed
        # element_id, schema validation error, or bus emit failure
        # cannot break the LLM response path (T-18-04-03-style mitigation).
        if self._ipc_bus is not None and citation_action in ("emit", "bypass"):
            try:
                for source, body in parse_citations(full_text):
                    if source != "screen":
                        continue
                    # The body of a [screen:<key>] atom is the element_id
                    # verbatim — no @t suffix per evidence_registry grammar.
                    element_id = body.strip()
                    if not element_id:
                        continue
                    msg = SessionOverlayHighlight.make(
                        element_id=element_id,
                        color=OVERLAY_COLOR,
                        duration_ms=OVERLAY_DURATION_MS,
                    )
                    await self._ipc_bus.emit(msg.to_dict())
            except Exception as e:  # noqa: BLE001 — best-effort telemetry
                print(f"\n[overlay publish err] {e}", file=sys.stderr)

        # ---- Per-invocation dump (always written, even on suppression) ----
        try:
            (invoke_dir / "response.txt").write_text(full_text)
            (invoke_dir / "meta.json").write_text(
                json.dumps(
                    {
                        "event": ev_tag,
                        "ts": invoke_ts,
                        "invoke_n": invoke_n,
                        "audible": self._state.audible,
                        "deck": self._state.audible_deck,
                        "track": self._state.audible_track,
                        "track_confidence": round(self._state.audible_track_confidence, 2),
                        "phase": self._state.phase,
                        "rms": round(self._state.rms, 4),
                        "bpm": round(self._state.bpm, 1),
                        "audio_bytes": len(audio_wav),
                        "audio_seconds": audio_seconds,
                        "diet": diet,
                        "llm_latency_s": round(elapsed, 2),
                        "llm_error": llm_err,
                        "response_chars": len(full_text),
                        "suppression": suppression,
                        "slop_matches": slop_matches,
                        # Plan 20-01 — citation linter chokepoint outcome.
                        # When wired==False, all four are None (skip path).
                        "citation_lint_valid": citation_lint_valid,
                        "citation_lint_reason": citation_lint_reason,
                        "citation_lint_missing": citation_lint_missing_payload,
                        "citation_action": citation_action,
                        # Plan 41-04 — streaming-pipe outcome. True iff
                        # the speculative head was emitted before stream
                        # completion; False on suppression/short-response.
                        "head_yielded": head_yielded,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
        except Exception:
            pass

        # Plan 41-04 — emit llm_to_tts_delta_ms event (skip when no head
        # was yielded — keeps the per-turn metric stream tight).
        try:
            self._llm_to_tts_meter.log_turn(
                self._recorder,
                extra={
                    "event": ev_tag,
                    "response_id": response_id,
                    "head_yielded": head_yielded,
                },
            )
        except Exception as _e:
            print(f"[delta-meter err] {_e}", file=sys.stderr)

    async def invalidate_cache(self) -> None:
        """Invalidate the context cache — Plan 19-03 cancel-aware chokepoint.

        Called by the cancel-and-refire path in Plan 19-01 (CancelGate
        telemetry callback) to ensure the refire starts with a fresh cache
        rather than one that may carry context from the cancelled in-flight
        turn. No-op when the agent was constructed without a cache (the
        Phase 4 backward-compat default).

        This is the single public agent-side surface for cache invalidation —
        downstream code (Plan 19-04 ack-bank wiring, future Settings UI)
        SHOULD call this method, NOT reach into self._cache directly."""
        if self._cache is not None:
            await self._cache.invalidate()
