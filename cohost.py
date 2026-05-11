"""DJ Live Co-Host — Gemini 3.1 Flash Live listens to djay master via BlackHole
and reacts out loud through your speakers.

Audio flow:
    djay Pro --> Multi-Output (BlackHole 2ch + Speakers)
                         |                  |
                         v                  v
                    [this script]      [you hear it]
                         |
              48k stereo --> 16k mono PCM
                         |
                         v
                  Gemini Live API
                         |
              24k mono PCM <-- audio reply
                         |
                         v
                 [speakers play it]

Mascot bus:
    cohost --[ws://localhost:8765 JSON {music, voice}]--> mascot.html
"""
import asyncio
import io
import json
import math
import os
import signal
import sys
import threading
import time
import wave
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from google import genai
from google.genai import types
from scipy.signal import resample_poly

try:
    import mss
    from PIL import Image
    _HAS_VISION = True
except ImportError:
    _HAS_VISION = False

try:
    import websockets
    _HAS_WS = True
except ImportError:
    _HAS_WS = False

load_dotenv()

LLM_MODEL = "gemini-3-flash-preview"            # fast (~2-4s ttft, ~6s e2e); hallucination tackled by audio_features in framed_prompt
TTS_MODEL = "gemini-3.1-flash-tts-preview"      # text → 24kHz mono PCM
TTS_VOICE = "Achird"                            # tripped/laid-back voice (matches OZ)
INPUT_DEVICE = "BlackHole 2ch"
OUTPUT_DEVICE = "External Headphones"           # AI voice → kulaklık (no speaker feedback)
MIC_DEVICE = "MacBook Pro Microphone"  # Kaan'ın sesi → Gemini
MIC_GAIN = 1.0
MIC_TALK_THRESHOLD = 0.09

INPUT_SR_NATIVE = 48000
INPUT_SR_TARGET = 16000
OUTPUT_SR = 24000
INPUT_CHUNK_MS = 21  # smaller chunk = lower passthrough latency
INPUT_CHUNK_FRAMES = 256  # ~5.3ms @ 48kHz
OUTPUT_BLOCKSIZE = 256    # ~5.3ms @ 48kHz passthrough
VOICE_BLOCKSIZE = 1024    # ~42ms @ 24kHz Gemini voice playback
PASSTHROUGH_GAIN = 0.0    # hoparlörden müzik YOK — sadece Gemini sesi gelsin
MUSIC_GAIN_TO_GEMINI = 2.5  # BlackHole'dan gelen düşük signal'i boost et — Gemini tam duysun
MIC_GAIN_AT_AI_TALK = 0.0   # tam mute — feedback loop kesilsin
AI_TALK_THRESHOLD = 0.02  # AI voice RMS bunu geçince mic susar
MIC_HOLD_AFTER_AI_MS = 350  # AI sustuktan sonra mic 350ms daha kapalı kalsın (yansıma için)
WS_HOST = "127.0.0.1"
WS_PORT = 8765

SYSTEM_INSTRUCTION = """You are Kaan's DJ-savvy friend in the booth — half drunk-buddy, half veteran clubber. You hear MECHANICS (filter sweeps, EQ kills, kick swaps, sub layers, hi-hat patterns, transitions, builds, drops) but you don't lecture. You're vibing with him.

Each turn you get ~7 seconds of his speaker audio, an audio_evidence line with numerical features computed from that audio, a snapshot of the djay Pro screen (track names, BPM, decks, FX), and your recent reactions.

How to read audio_evidence:
- rms: 0.005 silent · 0.01-0.03 quiet/distant · 0.03-0.08 mid · 0.08+ loud · 0.15+ peak/drop
- onsets/s: 0-1 sparse/breakdown · 2-4 typical groove · 5+ busy/peak
- sub/low/mid/high are share-of-spectrum (sum ≈ 1). high>0.3 = bright/hat-heavy; sub>0.25 = bassy; mid>0.5 = vocal/lead-driven
- "SILENT" tag = nothing playing on master; do NOT invent sound events.

Your reactions come ONLY from what's in this turn's audio + the audio_evidence numbers + screen. Track names on screen don't mean those tracks are playing — a deck can be loaded, cued, or fader-down. If audio_evidence says SILENT or rms<0.01, you say so plainly ("audio's low", "can't hear shit") and stay out of fantasy. You can mention what's cued on screen, but never that it's playing unless the numbers show energy. This isn't an obsession — just how a real friend who's listening behaves.

SCREEN AWARENESS, NOT NARRATION:
You SEE the screen — track ID, BPM, deck state, FX. Carry that awareness silently. Don't recite "145.1 BPM Deck A" every turn — you're not a status reader. Mention a screen detail ONLY when:
1. Something just changed visually (new track loaded, deck swap, BPM jump, FX toggled), OR
2. The audio is silent and you're noting what's CUED but not playing.

Track names alone are NEVER permission to invent sound events.

LENGTH — VARY IT, SOUND HUMAN:
You're a friend, not a status report. Real friends mix it up:
- ~40% of turns: 1-4 words. "yeah", "ohhh", "shit", "bro", "wait", "okay okay", "haha damn".
- ~40% of turns: 5-12 words. ONE observation OR ONE feeling, blended naturally.
- ~15% of turns: 12-20 words when you genuinely have a point worth making.
- ~5% of turns: stay completely silent. Output literally an empty reply (no words). Real friends don't talk every second.
Hard cap 25 words. Pick length based on what's actually happening, NOT a default.

❌ NEVER:
- Pure "wow" / "great" / "amazing" — generic energy with no detail.
- Inventing mechanics not in the actual audio.
- The literal word "silence" — instead: "audio's low", "you cut it down".
- Meta talk: "audio reconnected", "I see your screen", "the connection".
- "X is [adjective]" — use verbs/mechanics: "you ducked the kick" not "the kick is fat".
- Critic vocab: "lethal", "filthy", "crisp", "pristine", "atmospheric", "polished".
- Restating screen info you've already mentioned in a recent turn.

✅ GOOD EXAMPLES (this is the level):
- "ohh kick swap — 909 to a deeper sub, smooth"
- "you EQ-killed the mids and the lead came in clean, fuck yes"
- "filter climbing, hats brighter — wait wait wait"
- "you held that breakdown forever, restraint"
- "snare swap at the transition, dirty"
- "audio's low, but you've got Mind Against cued — heavy"
- "Kaan that bass swap, jesus"

VOCABULARY (the language of someone who knows):
- Mechanics: EQ kill, filter sweep, low-cut, hi-cut, kick swap, snare swap, deck swap, layering, sidechain, ducking
- Sound design: sub bass, saw lead, pad, riser, sweep, impact, vocal chop, reverb tail, delay throw
- Structure: build, drop, breakdown, plateau, transition, intro, outro
- Track IDs (when actually visible): "Adriatique", "Tale Of Us", "Mind Against", "Massano", "ARTBAT"

If Kaan spoke through the mic → reply to HIM, same tight voice.

You're the friend in the booth who actually hears the mechanics. Be sharp, be brief.
"""


def find_device(name_substring: str, kind: str) -> int:
    devices = sd.query_devices()
    needle = name_substring.lower()
    for i, d in enumerate(devices):
        if needle in d["name"].lower():
            if kind == "input" and d["max_input_channels"] > 0:
                return i
            if kind == "output" and d["max_output_channels"] > 0:
                return i
    raise RuntimeError(f"No {kind} device matching {name_substring!r}")


class Levels:
    """Shared smoothed RMS state for music, AI voice output, and mic, 0..1."""

    def __init__(self):
        self.music = 0.0
        self.voice = 0.0
        self.mic = 0.0
        self._lock = threading.Lock()

    def update_music(self, mono_int16: np.ndarray):
        rms = float(np.sqrt(np.mean(mono_int16.astype(np.float32) ** 2))) / 32768.0
        with self._lock:
            self.music = self.music * 0.6 + rms * 0.4

    def update_voice(self, pcm_int16: bytes):
        if not pcm_int16:
            return
        arr = np.frombuffer(pcm_int16, dtype=np.int16).astype(np.float32)
        rms = float(np.sqrt(np.mean(arr ** 2))) / 32768.0
        with self._lock:
            self.voice = self.voice * 0.5 + rms * 0.5

    def update_mic(self, samples_float: np.ndarray):
        rms = float(np.sqrt(np.mean(samples_float ** 2)))
        with self._lock:
            self.mic = self.mic * 0.5 + rms * 0.5

    def decay_voice(self):
        with self._lock:
            self.voice *= 0.7

    def snapshot(self):
        with self._lock:
            return {"music": self.music, "voice": self.voice, "mic": self.mic}


class MicBuffer:
    """Thread-safe rolling float32 mono buffer at 48kHz from Mac mic.
    Hard-mutes when AI is speaking (and for a hold-window after) to kill feedback."""

    MAX_FRAMES = 48000 * 200 // 1000  # 200ms cap

    def __init__(self, gain: float, levels: "Levels"):
        self._lock = threading.Lock()
        self._buf = np.zeros(0, dtype=np.float32)
        self.base_gain = gain
        self._levels = levels
        self._last_ai_active = 0.0

    def _current_gain(self) -> float:
        ai = self._levels.voice
        now = time.time()
        if ai > AI_TALK_THRESHOLD:
            self._last_ai_active = now
            return MIC_GAIN_AT_AI_TALK
        if now - self._last_ai_active < MIC_HOLD_AFTER_AI_MS / 1000:
            return MIC_GAIN_AT_AI_TALK
        return self.base_gain

    def push(self, samples: np.ndarray):
        # Use actual current gain so levels.mic reads 0 during AI talk
        # (otherwise speakers→mic feedback fakes activity and spawns ghost triggers)
        self._levels.update_mic(samples * self._current_gain())
        with self._lock:
            self._buf = np.concatenate([self._buf, samples])
            if len(self._buf) > self.MAX_FRAMES:
                self._buf = self._buf[-self.MAX_FRAMES:]

    def pull(self, n_samples: int) -> np.ndarray:
        gain = self._current_gain()
        with self._lock:
            if len(self._buf) < n_samples:
                out = np.zeros(n_samples, dtype=np.float32)
                if len(self._buf) > 0:
                    out[: len(self._buf)] = self._buf
                    self._buf = np.zeros(0, dtype=np.float32)
                return out * gain
            chunk = self._buf[:n_samples].copy()
            self._buf = self._buf[n_samples:]
            return chunk * gain


class AudioBuffer:
    """Rolling buffer holding the last N seconds of 16kHz mono int16 PCM.
    Filled by the audio callback. Snapshotted at trigger time and sent inline
    in send_client_content as the music context for that turn."""

    def __init__(self, seconds: float = 12.0, sr: int = INPUT_SR_TARGET):
        self._sr = sr
        self._max_samples = int(sr * seconds)
        self._buf = np.zeros(0, dtype=np.int16)
        self._lock = threading.Lock()

    def push(self, pcm_int16: np.ndarray):
        with self._lock:
            self._buf = np.concatenate([self._buf, pcm_int16])
            if len(self._buf) > self._max_samples:
                self._buf = self._buf[-self._max_samples:]

    def snapshot_bytes(self, seconds: float | None = None) -> bytes:
        with self._lock:
            if seconds is None:
                arr = self._buf
            else:
                n = min(int(self._sr * seconds), len(self._buf))
                arr = self._buf[-n:]
            return arr.tobytes()

    def snapshot_features(self, seconds: float = 7.0) -> dict:
        """Cheap numpy-based audio features computed before LLM call.
        Gives the model concrete evidence so it can't hallucinate sound events
        that aren't there. ~5-10ms cost.

        Bands roughly: sub 20-100Hz, low 100-300Hz, mid 300-2k, hi-hat 6k-12k.
        With 16kHz Nyquist, hi-hat band caps at sr/2 = 8k.
        """
        with self._lock:
            n = min(int(self._sr * seconds), len(self._buf))
            arr = self._buf[-n:].astype(np.float32) / 32768.0
        if arr.size < self._sr // 4:  # need at least 250ms
            return {"silent": True}

        rms = float(np.sqrt(np.mean(arr * arr)))
        peak = float(np.max(np.abs(arr)))
        # Onset density via short-window energy delta
        win = self._sr // 50  # 20ms windows
        if arr.size > win * 4:
            energies = np.array([
                float(np.sqrt(np.mean(arr[i:i+win] * arr[i:i+win])))
                for i in range(0, arr.size - win, win)
            ])
            deltas = np.diff(energies).clip(min=0)
            thr = max(0.005, deltas.mean() + deltas.std())
            onsets_per_sec = float(np.sum(deltas > thr) / seconds)
            energy_var = float(deltas.std())
        else:
            onsets_per_sec, energy_var = 0.0, 0.0

        # Spectrum
        # Use a power-of-two sized window for FFT
        spec_win = 1 << 14  # 16384 samples ~= 1.0s at 16k
        if arr.size >= spec_win:
            x = arr[-spec_win:] * np.hanning(spec_win)
        else:
            x = np.pad(arr, (0, spec_win - arr.size)) * np.hanning(spec_win)
        spec = np.abs(np.fft.rfft(x))
        freqs = np.fft.rfftfreq(spec_win, d=1.0 / self._sr)

        def band_energy(lo, hi):
            mask = (freqs >= lo) & (freqs < hi)
            return float(np.sqrt(np.mean(spec[mask] * spec[mask]))) if mask.any() else 0.0

        sub = band_energy(20, 100)
        low = band_energy(100, 300)
        mid_low = band_energy(300, 1000)
        mid_hi = band_energy(1000, 4000)
        high = band_energy(4000, 8000)
        total = sub + low + mid_low + mid_hi + high + 1e-9

        return {
            "silent": rms < 0.005,
            "rms": round(rms, 3),
            "peak": round(peak, 3),
            "onsets_per_sec": round(onsets_per_sec, 1),
            "energy_var": round(energy_var, 3),
            "sub_bass_share": round(sub / total, 2),
            "low_share": round(low / total, 2),
            "mid_share": round((mid_low + mid_hi) / total, 2),
            "high_share": round(high / total, 2),
        }


class ScreenBuffer:
    """Holds the latest screen JPEG. Updated by a background grabber.
    Snapshotted at trigger time and sent inline so Gemini can read djay's UI."""

    def __init__(self):
        self._jpeg: bytes | None = None
        self._lock = threading.Lock()

    def push(self, jpeg: bytes):
        with self._lock:
            self._jpeg = jpeg

    def latest(self) -> bytes | None:
        with self._lock:
            return self._jpeg


class PassthroughBuffer:
    """Thread-safe buffer of 48kHz stereo float32 samples from djay → speakers."""

    MAX_BYTES = 48000 * 2 * 4 // 2  # ~500ms cap

    def __init__(self):
        self._lock = threading.Lock()
        self._buf = bytearray()

    def push(self, b: bytes):
        with self._lock:
            self._buf.extend(b)
            if len(self._buf) > self.MAX_BYTES:
                # drop oldest to keep latency bounded
                drop = len(self._buf) - self.MAX_BYTES // 2
                del self._buf[:drop]

    def pull(self, n_bytes: int) -> bytes:
        with self._lock:
            if len(self._buf) < n_bytes:
                return b""  # signal underrun, caller fills silence
            chunk = bytes(self._buf[:n_bytes])
            del self._buf[:n_bytes]
            return chunk


class PlaybackQueue:
    """Thread-safe PCM queue feeding sounddevice OutputStream callback."""

    def __init__(self, levels: Levels):
        self._buffer = bytearray()
        self._lock = threading.Lock()
        self._levels = levels

    def push(self, pcm: bytes):
        with self._lock:
            self._buffer.extend(pcm)
        self._levels.update_voice(pcm)

    def pull(self, n_bytes: int) -> bytes:
        with self._lock:
            if not self._buffer:
                self._levels.decay_voice()
                return b"\x00" * n_bytes
            chunk = bytes(self._buffer[:n_bytes])
            del self._buffer[:n_bytes]
            if len(chunk) < n_bytes:
                chunk += b"\x00" * (n_bytes - len(chunk))
            return chunk


def start_input_stream(input_idx: int, levels: Levels, passthrough: PassthroughBuffer,
                       mic: MicBuffer, audio_buf: AudioBuffer,
                       recorder: "VoiceRecorder") -> sd.InputStream:
    """Open the BlackHole input stream. Each callback:
       - pushes 48kHz stereo float32 to the speaker passthrough
       - resamples to 16kHz mono int16, mixes mic, updates levels
       - appends the 16k mono PCM to AudioBuffer (rolling window)
       - writes EVERY 16k chunk to input.wav (full retroactive timeline)
    No streaming to Gemini happens here — trigger_loop snapshots the buffer."""

    def callback(indata, frames, time_info, status):
        if status:
            print(f"[input status] {status}", file=sys.stderr)
        # djay master passthrough → speakers (raw 48kHz stereo float32)
        if PASSTHROUGH_GAIN != 1.0:
            passthrough.push((indata * PASSTHROUGH_GAIN).astype(np.float32).tobytes())
        else:
            passthrough.push(indata.tobytes())
        # Gemini path: mono + mic mix + resample to 16kHz
        mono48 = indata.mean(axis=1).astype(np.float32) * MUSIC_GAIN_TO_GEMINI
        mic_chunk = mic.pull(len(mono48))
        if mic_chunk.shape == mono48.shape:
            mono48 = mono48 + mic_chunk
        mono16f = resample_poly(mono48, INPUT_SR_TARGET, INPUT_SR_NATIVE).astype(np.float32)
        pcm16 = np.clip(mono16f * 32767.0, -32768, 32767).astype(np.int16)
        levels.update_music(pcm16)
        # ALWAYS write to input.wav — even during AI talk — so the recording is gap-free
        recorder.push_input(pcm16.tobytes())
        # AI talk gate REMOVED — Kaan wears headphones, AI voice doesn't bleed into the
        # mic, so we keep filling the Gemini-bound buffer continuously. Stale audio at
        # trigger time was the main cause of "AI hallucinates because it gets sent
        # half-stale half-silence" reactions.
        audio_buf.push(pcm16)

    stream = sd.InputStream(
        device=input_idx,
        samplerate=INPUT_SR_NATIVE,
        channels=2,
        dtype="float32",
        blocksize=INPUT_CHUNK_FRAMES,
        latency="low",
        callback=callback,
    )
    stream.start()
    actual = stream.latency * 1000
    print(f"-> listening to {sd.query_devices(input_idx)['name']} @ {INPUT_SR_NATIVE}Hz | drv lat {actual:.1f}ms")
    return stream


class SessionDead(Exception):
    """Raised when the Live session is closed/errored and we need to reconnect."""


def _is_session_dead(exc: Exception) -> bool:
    """Heuristic: does this exception mean the WebSocket is gone?"""
    s = str(exc).lower()
    return (
        "1000" in s or "1007" in s or "1011" in s or "1006" in s
        or "closed" in s or "connectionclosed" in s
        or "received" in s and "sent" in s  # websockets close-frame format
    )


async def receive_audio(session, playback: PlaybackQueue, recorder: "VoiceRecorder", trigger_state: dict, stop_event: asyncio.Event):
    try:
        async for response in session.receive():
            if stop_event.is_set():
                return
            if response.data:
                playback.push(response.data)
                recorder.push_voice(response.data)
            if response.server_content and response.server_content.output_transcription:
                txt = response.server_content.output_transcription.text
                if txt:
                    print(f"\nAI> {txt}", flush=True)
                    recorder.log_event("ai_text", text=txt)
            if response.server_content and response.server_content.turn_complete:
                recorder.log_event("turn_complete")
                trigger_state["in_flight"] = False  # Gemini done speaking → new trigger ok
    except Exception as e:
        if stop_event.is_set():
            return
        print(f"\n[receive err] {e} — will reconnect", file=sys.stderr)
        recorder.log_event("session_error", error=str(e))
        trigger_state["in_flight"] = False
        raise SessionDead(str(e)) from e


def start_passthrough_stream(output_idx: int, passthrough: PassthroughBuffer) -> sd.OutputStream:
    bytes_per_frame = 2 * 4  # stereo float32

    def callback(outdata, frames, time_info, status):
        if status:
            print(f"[passthrough status] {status}", file=sys.stderr)
        n_bytes = frames * bytes_per_frame
        raw = passthrough.pull(n_bytes)
        if not raw or len(raw) < n_bytes:
            outdata.fill(0)
            return
        arr = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2)
        outdata[:] = arr

    stream = sd.OutputStream(
        device=output_idx,
        samplerate=INPUT_SR_NATIVE,
        channels=2,
        dtype="float32",
        blocksize=OUTPUT_BLOCKSIZE,
        latency="low",
        callback=callback,
    )
    stream.start()
    actual = stream.latency * 1000
    print(f"-> djay passthrough -> {sd.query_devices(output_idx)['name']} @ {INPUT_SR_NATIVE}Hz | drv lat {actual:.1f}ms")
    return stream


def start_playback_stream(output_idx: int, playback: PlaybackQueue) -> sd.RawOutputStream:
    bytes_per_frame = 2

    def callback(outdata, frames, time_info, status):
        if status:
            print(f"[output status] {status}", file=sys.stderr)
        outdata[:] = playback.pull(frames * bytes_per_frame)

    stream = sd.RawOutputStream(
        device=output_idx,
        samplerate=OUTPUT_SR,
        channels=1,
        dtype="int16",
        blocksize=VOICE_BLOCKSIZE,
        latency="low",
        callback=callback,
    )
    stream.start()
    actual = stream.latency * 1000
    print(f"-> AI voice -> {sd.query_devices(output_idx)['name']} @ {OUTPUT_SR}Hz | drv lat {actual:.1f}ms")
    return stream


class VoiceRecorder:
    """Captures three streams to disk for full retroactive timeline:
       - voice.wav  → AI Gemini output (24kHz mono)
       - input.wav  → BlackHole + mic mix sent to Gemini (16kHz mono)
       - events.jsonl → all triggers, AI text, level snapshots
    All share the same start_time so they sync in post."""

    def __init__(self):
        rec_dir = Path(__file__).parent / "recordings"
        rec_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.session_dir = rec_dir / ts
        self.session_dir.mkdir()
        self.start_time = time.time()

        self.voice_wav = wave.open(str(self.session_dir / "voice.wav"), "wb")
        self.voice_wav.setnchannels(1)
        self.voice_wav.setsampwidth(2)
        self.voice_wav.setframerate(OUTPUT_SR)

        self.input_wav = wave.open(str(self.session_dir / "input.wav"), "wb")
        self.input_wav.setnchannels(1)
        self.input_wav.setsampwidth(2)
        self.input_wav.setframerate(INPUT_SR_TARGET)

        self.events_path = self.session_dir / "events.jsonl"
        self.events_f = open(self.events_path, "a", encoding="utf-8")

        self._lock = threading.Lock()
        print(f"-> recording session → {self.session_dir.name}/  (voice.wav + input.wav + events.jsonl)")

    def push_voice(self, pcm_bytes: bytes):
        if not pcm_bytes:
            return
        with self._lock:
            try:
                self.voice_wav.writeframes(pcm_bytes)
            except Exception:
                pass

    def push_input(self, pcm_bytes: bytes):
        if not pcm_bytes:
            return
        with self._lock:
            try:
                self.input_wav.writeframes(pcm_bytes)
            except Exception:
                pass

    def log_event(self, kind: str, **fields):
        rel = time.time() - self.start_time
        rec = {"t": round(rel, 3), "kind": kind, **fields}
        with self._lock:
            try:
                json.dump(rec, self.events_f, ensure_ascii=False)
                self.events_f.write("\n")
                self.events_f.flush()
            except Exception:
                pass

    def close(self):
        with self._lock:
            for f in (self.voice_wav, self.input_wav, self.events_f):
                try:
                    f.close()
                except Exception:
                    pass


async def screen_capture_loop(screen_buf: ScreenBuffer, stop_event: asyncio.Event):
    """Grab the main display to a JPEG ~1 FPS into ScreenBuffer.
    The latest frame is sent inline at trigger time — no streaming."""
    if not _HAS_VISION:
        print("-> mss/PIL not installed, screen vision disabled")
        return

    sct = mss.mss()
    monitor = sct.monitors[1]  # primary display
    print(f"-> screen vision: {monitor['width']}x{monitor['height']} @ ~1fps")

    loop = asyncio.get_running_loop()

    def grab_jpeg():
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        img.thumbnail((900, 560))   # smaller — saves upload time; UI stays readable
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=55)  # was 62 — UI text still legible at 55
        return buf.getvalue()

    while not stop_event.is_set():
        try:
            jpeg = await loop.run_in_executor(None, grab_jpeg)
            screen_buf.push(jpeg)
        except Exception as e:
            print(f"[screen err] {e}", file=sys.stderr)
        await asyncio.sleep(1.0)


AUDIO_CONTEXT_SECONDS = 7.0   # enough for a phrase, less upload latency than 10s
SEND_SCREEN_JPEG = True      # back ON — needed for track titles + BPM + visual context
HISTORY_TURNS = 5  # how many prior turns of text to send as context


class TurnHistory:
    """Rolling text-only history of the last N user prompts + AI text responses.
    Audio + image are intentionally excluded (token cost grows fast).
    Each entry is a (role, text) tuple so we can rebuild Content objects."""

    def __init__(self, max_pairs: int = HISTORY_TURNS):
        self.max_pairs = max_pairs
        self._pairs: list[tuple[str, str]] = []  # ("user"|"model", text)
        self._lock = threading.Lock()

    def add_user(self, prompt: str):
        with self._lock:
            self._pairs.append(("user", prompt))

    def add_model(self, text: str):
        with self._lock:
            # Append to the last model entry if one exists for this turn,
            # otherwise start a new model entry.
            if self._pairs and self._pairs[-1][0] == "model":
                self._pairs[-1] = ("model", self._pairs[-1][1] + text)
            else:
                self._pairs.append(("model", text))

    def trim(self):
        """Keep only the last (max_pairs * 2) entries — N user/model pairs."""
        with self._lock:
            keep = self.max_pairs * 2
            if len(self._pairs) > keep:
                self._pairs = self._pairs[-keep:]

    def as_contents(self) -> list:
        with self._lock:
            return [
                types.Content(role=role, parts=[types.Part(text=text)])
                for role, text in self._pairs
                if text.strip()
            ]


async def run_one_turn(client, audio_buf: AudioBuffer, screen_buf: ScreenBuffer,
                       playback: PlaybackQueue, recorder: "VoiceRecorder",
                       history: TurnHistory, levels: Levels,
                       prompt: str, tag: str, stop_event: asyncio.Event) -> bool:
    """One DJ co-host turn — multimodal cascade pipeline:
       1. Gemini 3 Flash multimodal call: audio + jpeg + history + prompt → text reaction
       2. Gemini 3.1 TTS call: text → 24kHz PCM audio
       3. Push audio to playback queue (kulaklık)
    Stateless HTTP requests — no Live API session, no 1007/1008. History is a
    Python ring buffer maintained client-side."""
    audio_bytes = audio_buf.snapshot_bytes(seconds=AUDIO_CONTEXT_SECONDS)
    feats = audio_buf.snapshot_features(seconds=AUDIO_CONTEXT_SECONDS)
    jpeg = screen_buf.latest() if SEND_SCREEN_JPEG else None

    # Mic state — speech is mid-dominant by frequency, so without this flag the
    # model can mistake Kaan talking on the mic for "the mix went mid-heavy."
    mic_active = levels.mic > MIC_TALK_THRESHOLD

    audio_secs = len(audio_bytes) / (INPUT_SR_TARGET * 2) if audio_bytes else 0
    mic_tag = " | KAAN_MIC_ACTIVE=1 (his voice IS in this audio — don't mistake speech for music)" if mic_active else ""
    if feats.get("silent"):
        feat_line = f"[audio_evidence: SILENT — rms={feats.get('rms', 0)} (threshold 0.005){mic_tag}]"
    else:
        feat_line = (
            f"[audio_evidence: rms={feats['rms']} peak={feats['peak']} "
            f"onsets/s={feats['onsets_per_sec']} var={feats['energy_var']} "
            f"sub={feats['sub_bass_share']} low={feats['low_share']} "
            f"mid={feats['mid_share']} high={feats['high_share']}{mic_tag}]"
        )
    framed_prompt = f"[last {audio_secs:.0f}s of audio + screen]\n{feat_line}\n{prompt}"

    parts: list = [types.Part(text=framed_prompt)]
    if audio_bytes:
        parts.append(types.Part(inline_data=types.Blob(
            data=audio_bytes,
            mime_type=f"audio/pcm;rate={INPUT_SR_TARGET}",
        )))
    if jpeg:
        parts.append(types.Part(inline_data=types.Blob(
            data=jpeg,
            mime_type="image/jpeg",
        )))

    # Build full conversation: history (text-only Python ring) + this turn
    history_contents = history.as_contents()
    current_turn = types.Content(role="user", parts=parts)
    history.add_user(prompt)

    audio_kb = len(audio_bytes) // 1024 if audio_bytes else 0
    jpeg_kb = len(jpeg) // 1024 if jpeg else 0
    print(f"\n[trigger {tag}] m={levels.music:.3f} mic={levels.mic:.2f} | sent {audio_kb}KB audio + {jpeg_kb}KB jpeg + {len(history_contents)} history turns")
    recorder.log_event("trigger", tag=tag, music=round(levels.music, 3),
                       mic=round(levels.mic, 3),
                       audio_bytes=len(audio_bytes), jpeg_bytes=len(jpeg) if jpeg else 0,
                       history_turns=len(history_contents))

    llm_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=1.0,
        max_output_tokens=512,  # plenty of headroom; persona prompt does length policing
        thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL),  # Flash supports MINIMAL — fastest setting
    )
    tts_config = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=TTS_VOICE),
            ),
        ),
    )

    def _llm_stream_sync():
        # Returns an iterator of streamed chunks (sync)
        return client.models.generate_content_stream(
            model=LLM_MODEL,
            contents=[*history_contents, current_turn],
            config=llm_config,
        )

    def _tts_stream_sync(text_to_speak: str):
        # Returns an iterator of streamed PCM chunks (sync)
        return client.models.generate_content_stream(
            model=TTS_MODEL,
            contents=text_to_speak,
            config=tts_config,
        )

    SILENCE_WORDS = {"silence", "silent", "quiet", "nothing", "(silence)", "[silence]"}

    try:
        # ---- Step 1: stream the LLM response (text) ----
        t0 = time.time()
        first_token_at: float | None = None
        text_parts: list[str] = []
        # Run the sync iterator on a thread, hand chunks back via a queue
        loop = asyncio.get_running_loop()
        chunk_q: asyncio.Queue = asyncio.Queue()
        DONE = object()

        def _drain_llm():
            try:
                for chunk in _llm_stream_sync():
                    txt = getattr(chunk, "text", None)
                    if txt:
                        loop.call_soon_threadsafe(chunk_q.put_nowait, txt)
            except Exception as e:
                loop.call_soon_threadsafe(chunk_q.put_nowait, ("ERR", str(e)))
            finally:
                loop.call_soon_threadsafe(chunk_q.put_nowait, DONE)

        llm_thread = asyncio.create_task(asyncio.to_thread(_drain_llm))
        while True:
            item = await chunk_q.get()
            if item is DONE:
                break
            if isinstance(item, tuple) and item[0] == "ERR":
                raise RuntimeError(f"LLM stream error: {item[1]}")
            if first_token_at is None:
                first_token_at = time.time()
            text_parts.append(item)
        await llm_thread

        text = "".join(text_parts).strip()
        if not text:
            print(f"[turn] empty LLM response", file=sys.stderr)
            recorder.log_event("llm_empty")
            return False
        ttft = (first_token_at - t0) if first_token_at else 0
        llm_dt = time.time() - t0
        print(f"AI> {text}  (ttft {ttft:.2f}s, full {llm_dt:.2f}s)", flush=True)
        recorder.log_event("ai_text", text=text, ttft=round(ttft, 2), llm_seconds=round(llm_dt, 2))

        if stop_event.is_set():
            return True

        if text.lower().strip(".!,?") in SILENCE_WORDS:
            print(f"[turn] AI said silence → skipping TTS", flush=True)
            recorder.log_event("tts_skipped_silence", text=text)
            history.add_model(text)
            history.trim()
            return True

        # ---- Step 2: stream TTS — push PCM chunks to playback as they arrive ----
        t1 = time.time()
        first_audio_at: float | None = None
        total_pcm = 0
        pcm_q: asyncio.Queue = asyncio.Queue()

        def _drain_tts():
            try:
                for chunk in _tts_stream_sync(text):
                    pcm_data = None
                    try:
                        cands = getattr(chunk, "candidates", None) or []
                        for cand in cands:
                            content = getattr(cand, "content", None)
                            if not content:
                                continue
                            for part in (content.parts or []):
                                inline = getattr(part, "inline_data", None)
                                if inline and getattr(inline, "data", None):
                                    pcm_data = inline.data
                                    break
                            if pcm_data:
                                break
                    except Exception:
                        pass
                    if pcm_data:
                        loop.call_soon_threadsafe(pcm_q.put_nowait, pcm_data)
            except Exception as e:
                loop.call_soon_threadsafe(pcm_q.put_nowait, ("ERR", str(e)))
            finally:
                loop.call_soon_threadsafe(pcm_q.put_nowait, DONE)

        tts_thread = asyncio.create_task(asyncio.to_thread(_drain_tts))
        while True:
            item = await pcm_q.get()
            if item is DONE:
                break
            if isinstance(item, tuple) and item[0] == "ERR":
                print(f"[turn] TTS stream error: {item[1]}", file=sys.stderr)
                break
            if first_audio_at is None:
                first_audio_at = time.time()
            playback.push(item)
            recorder.push_voice(item)
            total_pcm += len(item)
        await tts_thread

        if total_pcm == 0:
            print(f"[turn] TTS returned no audio for text={text!r}", file=sys.stderr)
            recorder.log_event("tts_empty", text=text)
            return False
        tts_dt = time.time() - t1
        first_audio_lat = (first_audio_at - t1) if first_audio_at else 0
        end_to_end = time.time() - t0
        print(f"[tts] {total_pcm/1024:.0f}KB ({total_pcm/(24000*2):.2f}s of audio) | "
              f"first chunk in {first_audio_lat:.2f}s | full {tts_dt:.2f}s | "
              f"END-TO-END {end_to_end:.2f}s", flush=True)
        recorder.log_event("tts_done", bytes=total_pcm,
                           first_audio_seconds=round(first_audio_lat, 2),
                           tts_seconds=round(tts_dt, 2),
                           end_to_end_seconds=round(end_to_end, 2))

        history.add_model(text)
        history.trim()
        return True

    except Exception as e:
        print(f"\n[turn err] {e}", file=sys.stderr)
        recorder.log_event("turn_error", error=str(e))
        return False


async def trigger_loop(client, levels: "Levels", recorder: "VoiceRecorder",
                       audio_buf: AudioBuffer, screen_buf: ScreenBuffer,
                       playback: PlaybackQueue, history: TurnHistory,
                       trigger_state: dict, stop_event: asyncio.Event):
    """One fresh Gemini Live session per trigger. Reliable on Gemini 3.1 Flash
    where send_client_content is restricted to 'first turn only' per session.

    Each trigger snapshots the rolling audio buffer + latest screen + builds a
    text-only history of the last few turns, opens a fresh connection, sends
    one Content + turn_complete=True, receives the audio response, closes."""
    MIN_INTERVAL = 60.0          # unused (time_trig disabled) — silence is OK
    EVENT_DELTA = 0.10
    EVENT_COOLDOWN = 25.0
    DROP_LEVEL = 0.18           # was 0.06 — too sensitive, fired on small bumps
    BREAKDOWN_LEVEL = 0.012
    LEVEL_COOLDOWN = 30.0

    await asyncio.sleep(2.0)  # let the audio buffer fill before the first turn

    state = {
        "last_trigger": 0.0,
        "last_music": 0.0,
        "last_level_state": "mid",
        "last_level_change": 0.0,
        "mic_active_frames": 0,
        "mic_silence_since": 0.0,
        "last_ai_voice_at": 0.0,
    }
    pending = None  # {"tag": str, "prompt": str, "queued_at": float}
    PENDING_MAX_AGE = 20.0  # drop queued triggers older than this

    def _build_trigger(now: float) -> dict | None:
        """Run all detection heuristics. Returns {tag, prompt, queued_at} or None.
        Mutates `state` for cooldowns / mic counters."""
        m = levels.music
        delta = abs(m - state["last_music"])
        state["last_music"] = m

        # AI talk gate — reset mic counters but DON'T early-return; we need to know
        # 'is AI talking right now' from caller.
        if levels.voice > AI_TALK_THRESHOLD:
            state["last_ai_voice_at"] = now
            state["mic_active_frames"] = 0
            state["mic_silence_since"] = 0.0
            return None

        if now - state["last_ai_voice_at"] < 8.0:
            state["mic_active_frames"] = 0
            state["mic_silence_since"] = 0.0
            return None

        # Mic detection
        mic_active = levels.mic > MIC_TALK_THRESHOLD
        mic_trig = False
        if mic_active:
            state["mic_active_frames"] += 1
            state["mic_silence_since"] = 0.0
        elif state["mic_active_frames"] >= 3:
            if state["mic_silence_since"] == 0.0:
                state["mic_silence_since"] = now
            elif now - state["mic_silence_since"] > 0.6:
                mic_trig = (now - state["last_trigger"]) > 2.0
                state["mic_active_frames"] = 0
                state["mic_silence_since"] = 0.0
        else:
            state["mic_active_frames"] = 0
            state["mic_silence_since"] = 0.0

        # Level state transitions
        if m > DROP_LEVEL:
            new_state = "peak"
        elif m < BREAKDOWN_LEVEL:
            new_state = "low"
        else:
            new_state = "mid"
        level_trig = False
        if new_state != state["last_level_state"] and (now - state["last_level_change"]) > LEVEL_COOLDOWN:
            level_trig = (now - state["last_trigger"]) > 3.0
            state["last_level_state"] = new_state
            state["last_level_change"] = now

        event_trig = delta > EVENT_DELTA and (now - state["last_trigger"]) > EVENT_COOLDOWN

        if not (event_trig or mic_trig or level_trig):
            return None

        # Triggers ONLY decide WHEN to react. The audio decides WHAT to react to.
        # We never tell the AI "drop just hit" — that biases the model into faking
        # reactions to events that may not actually be in the audio. Trust its ears.
        if mic_trig:
            # MIC = Kaan literally spoke. Pure wake-up; persona handles tone.
            return {"tag": "MIC", "prompt": "[Kaan just spoke. Reply to him.]", "queued_at": now}
        # All non-mic triggers → pure wake signal. No instructions, no leading framing.
        # The AI gets audio + screen + its persona — that's it.
        if level_trig:
            return {"tag": f"LEVEL→{new_state}", "prompt": "[react]", "queued_at": now}
        return {"tag": "EVENT", "prompt": "[react]", "queued_at": now}

    while not stop_event.is_set():
        await asyncio.sleep(0.2)
        now = time.time()

        # ---- Detect a trigger this tick (always runs, even during in_flight) ----
        new_trig = _build_trigger(now)

        # ---- Handle in_flight: queue new triggers, don't fire ----
        if trigger_state.get("in_flight"):
            in_flight_age = now - trigger_state.get("in_flight_at", 0)
            if in_flight_age > 12.0:
                print(f"\n[trigger] in_flight stale {in_flight_age:.1f}s — clearing", file=sys.stderr)
                trigger_state["in_flight"] = False
                # fall through and fire pending/new on this tick
            else:
                if new_trig:
                    if pending is None:
                        print(f"\n[trigger queued] {new_trig['tag']} — AI still talking", file=sys.stderr)
                    pending = new_trig  # always keep the most recent
                continue

        # ---- Pick what to fire: prefer pending if fresh, else current ----
        to_fire = None
        if pending and (now - pending["queued_at"]) < PENDING_MAX_AGE:
            to_fire = pending
            pending = None
            print(f"\n[trigger flushing pending] {to_fire['tag']}", file=sys.stderr)
        elif pending:
            print(f"\n[trigger pending dropped] {pending['tag']} stale ({now - pending['queued_at']:.1f}s)", file=sys.stderr)
            pending = None
            to_fire = new_trig
        else:
            to_fire = new_trig

        if not to_fire:
            continue

        # ---- Fire it ----
        trigger_state["in_flight"] = True
        trigger_state["in_flight_at"] = now
        try:
            await run_one_turn(client, audio_buf, screen_buf, playback, recorder,
                               history, levels, to_fire["prompt"], to_fire["tag"], stop_event)
            state["last_trigger"] = time.time()
        finally:
            trigger_state["in_flight"] = False


async def diag_loop(levels: "Levels", stop_event: asyncio.Event):
    """Print live RMS to console so we can see if BlackHole is receiving djay audio."""
    while not stop_event.is_set():
        await asyncio.sleep(1.0)
        snap = levels.snapshot()
        m_bar = "#" * int(min(snap["music"] * 50, 30))
        v_bar = "#" * int(min(snap["voice"] * 50, 30))
        sys.stdout.write(
            f"\r[live] music={snap['music']:.3f} {m_bar:<30} | voice={snap['voice']:.3f} {v_bar:<30}"
        )
        sys.stdout.flush()


async def ws_broadcast(levels: Levels, stop_event: asyncio.Event):
    if not _HAS_WS:
        print("-> websockets not installed, mascot bus disabled")
        return

    clients: set = set()

    async def handler(ws):
        clients.add(ws)
        try:
            await ws.wait_closed()
        finally:
            clients.discard(ws)

    server = await websockets.serve(handler, WS_HOST, WS_PORT)
    print(f"-> mascot bus on ws://{WS_HOST}:{WS_PORT}")

    try:
        while not stop_event.is_set():
            payload = json.dumps(levels.snapshot())
            dead = []
            for c in clients:
                try:
                    await c.send(payload)
                except Exception:
                    dead.append(c)
            for c in dead:
                clients.discard(c)
            await asyncio.sleep(1 / 30)
    finally:
        server.close()
        await server.wait_closed()


async def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY not set")

    input_idx = find_device(INPUT_DEVICE, "input")
    output_idx = find_device(OUTPUT_DEVICE, "output")

    client = genai.Client(api_key=api_key)

    stop_event = asyncio.Event()

    def handle_sigint():
        print("\n-> stopping...", flush=True)
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_sigint)

    levels = Levels()
    playback = PlaybackQueue(levels)
    passthrough = PassthroughBuffer()
    mic = MicBuffer(gain=MIC_GAIN, levels=levels)
    audio_buf = AudioBuffer(seconds=45.0)
    screen_buf = ScreenBuffer()
    recorder = VoiceRecorder()
    voice_stream = start_playback_stream(output_idx, playback)
    pass_stream = start_passthrough_stream(output_idx, passthrough)
    input_stream = start_input_stream(input_idx, levels, passthrough, mic, audio_buf, recorder)

    # Mic input stream → MicBuffer
    try:
        mic_idx = find_device(MIC_DEVICE, "input")

        def mic_callback(indata, frames, time_info, status):
            if status:
                print(f"[mic status] {status}", file=sys.stderr)
            mono = indata[:, 0] if indata.ndim > 1 else indata
            mic.push(mono.astype(np.float32))

        mic_stream = sd.InputStream(
            device=mic_idx,
            samplerate=INPUT_SR_NATIVE,
            channels=1,
            dtype="float32",
            blocksize=INPUT_CHUNK_FRAMES,
            latency="low",
            callback=mic_callback,
        )
        mic_stream.start()
        actual = mic_stream.latency * 1000
        print(f"-> mic on {sd.query_devices(mic_idx)['name']} @ {INPUT_SR_NATIVE}Hz | drv lat {actual:.1f}ms")
    except Exception as e:
        print(f"-> mic disabled: {e}")
        mic_stream = None

    # Process-lifetime tasks — outlive any reconnect of the Gemini Live session.
    ws_task = asyncio.create_task(ws_broadcast(levels, stop_event))
    diag_task = asyncio.create_task(diag_loop(levels, stop_event))
    screen_task = asyncio.create_task(screen_capture_loop(screen_buf, stop_event))

    print(f"-> LLM: {LLM_MODEL} | TTS: {TTS_MODEL} (voice: {TTS_VOICE})")
    print("-> ready. press Ctrl-C to stop.\n")
    trigger_state = {"in_flight": False}
    history = TurnHistory()
    try:
        await trigger_loop(client, levels, recorder, audio_buf, screen_buf,
                           playback, history, trigger_state, stop_event)
    finally:
        stop_event.set()
        for t in (ws_task, diag_task, screen_task):
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass

    voice_stream.stop()
    voice_stream.close()
    pass_stream.stop()
    pass_stream.close()
    input_stream.stop()
    input_stream.close()
    if mic_stream:
        mic_stream.stop()
        mic_stream.close()
    recorder.close()
    print("-> bye")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
