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

from google import genai
from google.genai import types
from livekit.agents import Agent, ModelSettings
from livekit.agents import llm as agents_llm
from livekit.agents import tts as agents_tts

from vibemix.agent.cache import GeminiContextCache
from vibemix.agent.config import LLM_MODEL
from vibemix.audio import INVOKE_AUDIO_SECONDS, AudioBuffer, VoiceRecorder, snapshot_wav
from vibemix.prompts import build_system_instruction, filter_for_slop
from vibemix.runtime.ttft import TTFTMeter
from vibemix.state import AICoach, Event, EvidenceRegistry, MusicState, parse_citations
from vibemix.state.coach import ACK_ELIGIBLE_EVENTS

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

        contents: list = [
            text_prompt
            + (
                f"\n\nAttached: last {int(audio_seconds)}s of audio (mix + mic). "
                f"Your ears are the referee — the evidence above is grounded context."
            )
            + history_clause,
            types.Part.from_bytes(data=audio_wav, mime_type="audio/wav"),
        ]
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
        print(
            f"\n[llm {ev_tag} #{invoke_n:04d}] audio={len(audio_wav) // 1024}KB"
            f"({int(audio_seconds)}s) diet={diet} cache={cache_state} "
            f"screen={'yes' if screen_jpeg else 'no'} dump={invoke_dir.name}"
        )

        # Phase 10: BUFFER chunks until the stream completes, then run the
        # silence + slop gate. Yield chunks only if both gates pass.
        # See module docstring for the latency-vs-correctness rationale.
        full_text = ""
        buffered_chunks: list[str] = []
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
        except Exception as e:
            llm_err = repr(e)
            print(f"\n[llm err] {e}", file=sys.stderr)

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

        if suppression == "silence":
            self._recorder.log_event(
                "silence_short_circuit",
                event=ev_tag,
                response_chars=len(full_text),
                latency_s=round(elapsed, 2),
            )
            print("[ai_text] <silence/> (suppressed)", flush=True)
        elif suppression == "slop":
            self._recorder.log_event(
                "slop_suppressed",
                event=ev_tag,
                matches=slop_matches,
                response_chars=len(full_text),
                latency_s=round(elapsed, 2),
            )
            print(f"[ai_text] <slop suppressed: {slop_matches}>", flush=True)
        else:
            # Clean turn — yield the buffered chunks in their original order
            # and run the v4 ai_text logging path (history append + log event).
            for txt in buffered_chunks:
                yield txt
            if stripped:
                print(f"[ai_text] {stripped!r}", flush=True)
                self._recorder.log_event("ai_text", text=full_text, latency_s=round(elapsed, 2))
                self._ai_text_history.append(stripped[:140])
            else:
                print("[ai_text] <empty> (skip TTS)", flush=True)

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
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
        except Exception:
            pass

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
