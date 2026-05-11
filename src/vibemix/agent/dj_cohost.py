# SPDX-License-Identifier: Apache-2.0
"""DJCoHostAgent — verbatim port of cohost_v4.py:1441-1593.

Hijacks ``llm_node`` to bypass LiveKit's text-only cascade and call
``google.genai`` directly with the last INVOKE_AUDIO_SECONDS of audio attached
as a multimodal Part. The LLM literally hears the music.

ONE STRUCTURAL ADJUSTMENT FROM V4: Phase 2 promoted ``snapshot_wav`` from an
``AudioBuffer`` method to a free function in ``vibemix.audio.features``. The
v4:1489 call site ``self._clean_audio_buf.snapshot_wav(INVOKE_AUDIO_SECONDS)``
becomes ``snapshot_wav(self._clean_audio_buf, INVOKE_AUDIO_SECONDS)`` — same
return bytes, same peak-normalize behavior.

Every other line is byte-for-byte v4 — including the load-bearing comment at
v4:1502 (``# Single-modality: audio only. Screen + MIDI metadata caused
hallucination.``) and the ``screen_jpeg = None`` deliberate single-modality
gate (v4:1503). The ``if screen_jpeg:`` conditional include path is kept as
dead code per CONTEXT.md so the v4 shape is preserved; Phase 10 may revisit.
"""

from __future__ import annotations

import collections
import json
import sys
import time
from collections.abc import AsyncGenerator

from google import genai
from google.genai import types
from livekit.agents import Agent, ModelSettings
from livekit.agents import llm as agents_llm
from livekit.agents import tts as agents_tts

from vibemix.agent.config import LLM_MODEL
from vibemix.agent.persona import SYSTEM_INSTRUCTION
from vibemix.audio import INVOKE_AUDIO_SECONDS, AudioBuffer, VoiceRecorder, snapshot_wav
from vibemix.state import AICoach, Event, MusicState


class DJCoHostAgent(Agent):
    """Hijacks llm_node to bypass LiveKit's text-only cascade and call
    google.genai directly with the last 10s of audio + the latest screen
    frame attached as multimodal Parts. The LLM literally hears the music."""

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
    ):
        super().__init__(
            instructions=SYSTEM_INSTRUCTION,
            llm=llm_inst,
            tts=tts_inst,
            allow_interruptions=False,
        )
        self._genai_client = genai_client
        self._clean_audio_buf = clean_audio_buf
        self._screen_buf = screen_buf
        self._state = state
        self._recorder = recorder
        self._pending_event: Event | None = None
        self._ai_text_history: collections.deque = collections.deque(maxlen=10)
        self._gen_cfg = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            thinking_config=types.ThinkingConfig(thinking_level="minimal"),
            temperature=1.0,
            max_output_tokens=220,
        )

    def set_next_event(self, ev: Event) -> None:
        self._pending_event = ev

    async def llm_node(
        self,
        chat_ctx: agents_llm.ChatContext,
        tools: list,
        model_settings: ModelSettings,
    ) -> AsyncGenerator:
        ev = self._pending_event
        self._pending_event = None

        # Build grounded text packet (same evidence + task v2 used)
        if ev is not None:
            text_prompt = AICoach.build_prompt(ev)
        else:
            # No event context (e.g. generate_reply called without prep) — fall back
            text_prompt = AICoach.build_prompt(Event(type="MANUAL", state=self._state, extra={}))

        audio_wav = snapshot_wav(self._clean_audio_buf, INVOKE_AUDIO_SECONDS)
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
                f"\n\nAttached: last {int(INVOKE_AUDIO_SECONDS)}s of audio (mix + mic). "
                f"Your ears are the referee — the evidence above is grounded context."
            )
            + history_clause,
            types.Part.from_bytes(data=audio_wav, mime_type="audio/wav"),
        ]
        if screen_jpeg:
            contents.append(types.Part.from_bytes(data=screen_jpeg, mime_type="image/jpeg"))

        ev_tag = ev.type if ev else "MANUAL"
        full_prompt = contents[0] if contents else text_prompt
        try:
            (invoke_dir / "prompt.txt").write_text(full_prompt)
        except Exception:
            pass

        self._recorder.log_event(
            "llm_invoke",
            event=ev_tag,
            audible=self._state.audible,
            deck=self._state.audible_deck,
            track=self._state.audible_track,
            phase=self._state.phase,
            audio_bytes=len(audio_wav),
            has_screen=bool(screen_jpeg),
            prompt=text_prompt,
            invoke_dir=str(invoke_dir),
        )
        print(
            f"\n[llm {ev_tag} #{invoke_n:04d}] audio={len(audio_wav) // 1024}KB "
            f"screen={'yes' if screen_jpeg else 'no'} dump={invoke_dir.name}"
        )

        full_text = ""
        t_start = time.time()
        llm_err: str | None = None
        try:
            stream = await self._genai_client.aio.models.generate_content_stream(
                model=LLM_MODEL,
                contents=contents,
                config=self._gen_cfg,
            )
            async for chunk in stream:
                txt = getattr(chunk, "text", None) or ""
                if not txt:
                    continue
                print(txt, end="", flush=True)
                full_text += txt
                yield txt
        except Exception as e:
            llm_err = repr(e)
            print(f"\n[llm err] {e}", file=sys.stderr)
        finally:
            print()
            elapsed = time.time() - t_start
            stripped = full_text.strip()
            if stripped:
                print(f"[ai_text] {stripped!r}", flush=True)
                self._recorder.log_event("ai_text", text=full_text, latency_s=round(elapsed, 2))
                self._ai_text_history.append(stripped[:140])
            else:
                print("[ai_text] <empty> (skip TTS)", flush=True)
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
                            "audio_seconds": INVOKE_AUDIO_SECONDS,
                            "llm_latency_s": round(elapsed, 2),
                            "llm_error": llm_err,
                            "response_chars": len(full_text),
                        },
                        indent=2,
                        ensure_ascii=False,
                    )
                )
            except Exception:
                pass
