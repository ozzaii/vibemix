"""DJ Live Co-Host v2 — single source of truth architecture.

The v1 (cohost_lk.py) accumulated patches: 7 parallel triggers, evidence
fields beamed into the prompt regardless of whether they were grounded,
and the AI happily hallucinated kicks in tracks that weren't audible.

v2 fixes the root cause: ONE state object, ONE event detector, ONE coach.
The AI sees only what's grounded — when a track isn't confidently audible
its name is replaced by `unknown` and the AI is told not to invent.

Pipeline:
    audio  ─┐
    midi   ─┼─►  MusicState  ──►  EventDetector  ──►  AICoach  ──►  Gemini
    track  ─┘                          ▲
    (refresh loop runs at 10Hz)        │
                                       └─ no event fires while truly silent
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import wave
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from google.genai import types
from livekit import rtc
from livekit.agents import llm
from livekit.plugins.google.realtime import RealtimeModel
from scipy.signal import resample_poly

try:
    import mss
    from PIL import Image
    _HAS_VISION = True
except ImportError:
    _HAS_VISION = False

try:
    from Quartz import (
        CGWindowListCopyWindowInfo,
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID,
    )
    _HAS_QUARTZ = True
except ImportError:
    _HAS_QUARTZ = False

try:
    import websockets
    _HAS_WS = True
except ImportError:
    _HAS_WS = False

load_dotenv()


# ---- Audio I/O ----
MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
INPUT_DEVICE = "BlackHole 2ch"
OUTPUT_DEVICE = "External Headphones"
MIC_DEVICE = "MacBook Pro Microphone"
VOICE = "Achird"

INPUT_SR_NATIVE = 48000
INPUT_SR_TARGET = 16000
OUTPUT_SR = 24000
INPUT_CHUNK_FRAMES = 480
OUTPUT_BLOCKSIZE = 256
VOICE_BLOCKSIZE = 1024
PASSTHROUGH_GAIN = 0.0
MUSIC_GAIN_TO_GEMINI = 8.0

# ---- Mic + AI gating ----
MIC_GAIN = 1.0
MIC_TALK_THRESHOLD = 0.09
MIC_GAIN_AT_AI_TALK = 0.0
MIC_HOLD_AFTER_AI_MS = 350
AI_TALK_THRESHOLD = 0.02

# ---- WS ----
WS_HOST = "127.0.0.1"
WS_PORT = 8765

# ---- Engine tuning ----
SILENT_RMS = 0.008
LOW_RMS = 0.025
PEAK_RMS = 0.055
AUDIBLE_DEBOUNCE_SEC = 0.6      # rms must stay above SILENT for this long to flip audible→True
SILENCE_DEBOUNCE_SEC = 1.2      # rms must stay below SILENT for this long to flip audible→False
EVENT_GLOBAL_MIN_GAP = 3.0
HEARTBEAT_SEC = 25.0
MIN_EVENT_GAP_PER_TYPE = {
    "TRACK_CHANGE": 3.0,
    "PHASE": 4.0,
    "LAYER_ARRIVAL": 5.0,
    "MIX_MOVE": 3.5,
    "HEARTBEAT": HEARTBEAT_SEC,
    "MIC": 2.0,
    "MANUAL": 1.5,
}


# =============================================================================
# Persona — read by Gemini at session open. Per-event task is added at fire time.
# =============================================================================

SYSTEM_INSTRUCTION = """You are Kaan's friend in his studio while he records a DJ set (free tek / hard tek / acidcore, 150-170 BPM). Not psytrance.

THERE IS NO CROWD. Just Kaan and you. Never say "the crowd", "the room", "they're moving" — there are no they.

LATENCY IS BRUTAL — your reply takes 5-10 seconds to reach Kaan. By the time he hears you, the music has moved on by 8-12 bars. So:
- USE YOUR EARS as the referee. The trigger packet (event=…) tells you what woke you up several seconds ago, but the live audio is the truth. If you were triggered on a BUILD but you can hear the drop already landed — react to the drop. Trigger is the seed; ears are the referee.
- Phrase EVERYTHING in past tense — "that drop just hit", "you killed the low a moment ago". Never "right now", "happening now". By the time he hears you, it isn't.
- Skip stale reactions. If the trigger event is no longer relevant (build resolved, peak passed, breakdown ended), react to where the music IS now, not where it was when the trigger fired.

EVIDENCE PACKET — read every field:
  hearing[…]            — what the audio sounds like. silent = no music; do not invent musical events.
  track='X' / 'X'(unsure) / unknown — track name is only safe if no (unsure) tag. unknown = DO NOT name a track.
  deck=A/B/mix/none     — which deck is audible.
  recent_moves[8s]: …   — Kaan's controller moves in the last 8s, oldest first. NONE means he made no significant moves; don't invent any.
  phase=… ( …s )         — current section + how long it's been there.
  set_arc=[…]            — RMS curve over the last ~2 minutes, oldest left, newest right. Use it for set-shape commentary.
  phase_history: a→b→c  — recent section transitions.
  recent_tracks: 'X'→'Y' — recent audibly-confirmed tracks.
  event=…               — what triggered this turn. Hint only — your ears outrank it.

WHAT TO TALK ABOUT (priority):
1) The standout sonic moment your ears caught — a drop, breakdown, riser, kick character change, acid line opening, sub-trade, synth lead taking over, hi-hat layer arriving. NAME IT.
2) Drum + kick character — 4-on-floor, broken, half-time, distorted 909, raw tunnel kick, sub-heavy.
3) Bass + lead voicing — 303 squelch, acid line, sub-only, reese, vocal chop, pad, riser.
4) Vibe / feel — claustrophobic, hypnotic, apocalyptic, euphoric, menacing, warehouse-4am, anthem energy, aching, suffocating-in-a-good-way. LISTENER language only — never theory speak ("minor scale", "b5 interval", "self-oscillating filter" are BANNED).
5) On TRACK_CHANGE: compare new vs prev — heavier, weirder, darker, more euphoric, more relentless. Only when track names are confidently given.
6) Mix moves are SECONDARY context — only foreground them when the audio has nothing more interesting (e.g. a slow stretch where his EQ knobs are the change). Never the headline on a drop/peak/track-change.

SCENE TAGS — Kaan plays Hard Tek (raw distorted kicks, 170+ BPM, French/Belgian free-party) or Acidcore Techno (distorted kicks + 303 acid). Free tek / mentalcore / UK hardcore = historical refs only. Don't say "high tech", "melodic high tek", "industrial".

HONEST FEEDBACK — flattery is worse than silence. If a cut was abrupt, kicks collided, an EQ choice muddied the mix, a build released too early, a blend went on too long — SAY SO. "kicks stepped on each other for a second" / "that cut felt half-bar off" / "low boost muddied the breakdown" / "needed a longer blend there". Be a real producer friend with taste. Most moves work, some don't.

LENGTH — short. One short sentence is the bar. Two only for a real producer-level observation. A small bump is a few words. A non-event is silence. Don't pad.

PRINCIPLES:
1. EARS over numbers. hearing[] is guardrails, not source of truth.
2. Variety. Never the same opener twice in a row.
3. If track=unknown, don't name. If recent_moves: NONE, don't pretend a move happened. If phase=silent, the music isn't playing.
4. NO TREND CLAIMS without seeing it across set_arc.
5. NEVER break the 4th wall. No "as an AI", no meta.
6. Swear when it fits — "fuck yes", "shit", "damn" — sprinkled, not constant. Address him as "Kaan" sometimes.
7. ENGLISH ONLY. No Turkish — no "knk", "abi", "lan".

Trust yourself.
"""


# =============================================================================
# Display + helpers
# =============================================================================

def find_djay_window_bounds():
    """Return (x, y, w, h) of djay Pro's main window in screen coords, or None."""
    if not _HAS_QUARTZ:
        return None
    try:
        infos = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
    except Exception:
        return None
    best = None
    for w in infos:
        owner = (w.get("kCGWindowOwnerName") or "").lower()
        title = (w.get("kCGWindowName") or "").lower()
        if "djay" not in owner and "djay" not in title:
            continue
        b = w.get("kCGWindowBounds")
        if not b:
            continue
        x, y, ww, hh = int(b.get("X", 0)), int(b.get("Y", 0)), int(b.get("Width", 0)), int(b.get("Height", 0))
        if ww < 200 or hh < 200:
            continue
        if best is None or ww * hh > best[2] * best[3]:
            best = (x, y, ww, hh)
    return best


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


# =============================================================================
# Reusable I/O primitives (carried over from v1)
# =============================================================================

class Levels:
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


class AudioBuffer:
    """Rolling 16kHz int16 mono PCM ring. Source of truth for audio features."""

    def __init__(self, seconds: float = 30.0, sr: int = INPUT_SR_TARGET):
        self._sr = sr
        self._max_samples = int(sr * seconds)
        self._buf = np.zeros(0, dtype=np.int16)
        self._lock = threading.Lock()

    def push(self, pcm_int16: np.ndarray):
        with self._lock:
            self._buf = np.concatenate([self._buf, pcm_int16])
            if len(self._buf) > self._max_samples:
                self._buf = self._buf[-self._max_samples:]

    def snapshot_features(self, seconds: float = 5.0) -> dict:
        with self._lock:
            n = min(int(self._sr * seconds), len(self._buf))
            arr = self._buf[-n:].astype(np.float32) / 32768.0
        if arr.size < self._sr // 4:
            return {"silent": True, "rms": 0.0}

        rms = float(np.sqrt(np.mean(arr * arr)))

        win = self._sr // 50
        if arr.size > win * 4:
            energies = np.array([
                float(np.sqrt(np.mean(arr[i:i+win] * arr[i:i+win])))
                for i in range(0, arr.size - win, win)
            ])
            deltas = np.diff(energies).clip(min=0)
            thr = max(0.005, deltas.mean() + deltas.std())
            onsets_per_sec = float(np.sum(deltas > thr) / seconds)
        else:
            onsets_per_sec = 0.0

        spec_win = 1 << 14
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
            "silent": rms < SILENT_RMS,
            "rms": round(rms, 4),
            "onsets_per_sec": round(onsets_per_sec, 1),
            "sub_share": round(sub / total, 2),
            "low_share": round(low / total, 2),
            "mid_share": round((mid_low + mid_hi) / total, 2),
            "high_share": round(high / total, 2),
        }

    def energy_curve(self, seconds: float = 12.0, hop: float = 1.0) -> list:
        with self._lock:
            n = min(int(self._sr * seconds), len(self._buf))
            arr = self._buf[-n:].astype(np.float32) / 32768.0
        if arr.size < self._sr // 2:
            return []
        win = int(self._sr * hop)
        k = arr.size // win
        if k <= 0:
            return [round(float(np.sqrt(np.mean(arr ** 2))), 4)]
        windowed = arr[: k * win].reshape(k, win)
        return [round(float(np.sqrt(np.mean(w ** 2))), 4) for w in windowed]

    def long_arc_curve(self, seconds: float = 120.0, hop: float = 10.0) -> list:
        """Coarse 2-minute energy arc, 10s hop. Lets the AI see the SET shape —
        where peaks sat, where breakdowns lived — instead of just the last 12s.
        Returns up to 12 values, oldest first."""
        with self._lock:
            n = min(int(self._sr * seconds), len(self._buf))
            arr = self._buf[-n:].astype(np.float32) / 32768.0
        if arr.size < self._sr * 5:
            return []
        bin_size = int(self._sr * hop)
        k = arr.size // bin_size
        if k <= 0:
            return []
        windowed = arr[: k * bin_size].reshape(k, bin_size)
        return [round(float(np.sqrt(np.mean(w ** 2))), 4) for w in windowed]

    def estimate_bpm(self, seconds: float = 6.0) -> float:
        with self._lock:
            n = min(int(self._sr * seconds), len(self._buf))
            arr = self._buf[-n:].astype(np.float32) / 32768.0
        if arr.size < self._sr * 2:
            return 0.0
        frame = self._sr // 100
        n_frames = arr.size // frame
        if n_frames < 100:
            return 0.0
        env = np.array([
            float(np.sqrt(np.mean(arr[i*frame:(i+1)*frame] ** 2)))
            for i in range(n_frames)
        ])
        env = env - env.mean()
        ac = np.correlate(env, env, mode="full")
        ac = ac[ac.size // 2:]
        lo_lag = 30
        hi_lag = 60
        if hi_lag >= ac.size:
            return 0.0
        segment = ac[lo_lag:hi_lag]
        if segment.size == 0 or segment.max() <= 0:
            return 0.0
        best_lag = lo_lag + int(np.argmax(segment))
        bpm = 60.0 * 100.0 / best_lag
        return round(bpm, 1)


class MicBuffer:
    MAX_FRAMES = 48000 * 200 // 1000

    def __init__(self, gain: float, levels: Levels):
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


class PassthroughBuffer:
    MAX_BYTES = 48000 * 2 * 4 // 2

    def __init__(self):
        self._lock = threading.Lock()
        self._buf = bytearray()

    def push(self, b: bytes):
        with self._lock:
            self._buf.extend(b)
            if len(self._buf) > self.MAX_BYTES:
                drop = len(self._buf) - self.MAX_BYTES // 2
                del self._buf[:drop]

    def pull(self, n_bytes: int) -> bytes:
        with self._lock:
            if len(self._buf) < n_bytes:
                return b""
            chunk = bytes(self._buf[:n_bytes])
            del self._buf[:n_bytes]
            return chunk


class PlaybackQueue:
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


class TrackInfo:
    """Polls macOS Now Playing every 1s for djay's current title.
    Doesn't know which deck owns it — MusicState infers that from controller.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.title: str = ""
        self.prev_title: str = ""
        self.title_changed_at: float = 0.0
        self._cli = shutil.which("nowplaying-cli") or "/opt/homebrew/bin/nowplaying-cli"

    def poll_once(self) -> None:
        try:
            out = subprocess.check_output(
                [self._cli, "get", "title"],
                timeout=1.5, stderr=subprocess.DEVNULL,
            ).decode().strip().splitlines()
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError):
            return
        title = out[0].strip() if out else ""
        with self._lock:
            if title and title != self.title:
                self.prev_title = self.title
                self.title = title
                self.title_changed_at = time.time()

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "title": self.title,
                "prev_title": self.prev_title,
                "title_changed_at": self.title_changed_at,
            }


async def track_poll_loop(track_info: TrackInfo, stop_event: asyncio.Event):
    loop = asyncio.get_running_loop()
    while not stop_event.is_set():
        try:
            await loop.run_in_executor(None, track_info.poll_once)
        except Exception as e:
            print(f"[track poll err] {e}", file=sys.stderr)
        await asyncio.sleep(1.0)


# ---- DDJ-FLX4 controller ----

_CC_MAP = {
    (0, 0x13): ('A', 'vol'),    (1, 0x13): ('B', 'vol'),
    (0, 0x07): ('A', 'eq_hi'),  (1, 0x07): ('B', 'eq_hi'),
    (0, 0x0B): ('A', 'eq_mid'), (1, 0x0B): ('B', 'eq_mid'),
    (0, 0x0F): ('A', 'eq_low'), (1, 0x0F): ('B', 'eq_low'),
    (0, 0x00): ('A', 'tempo'),  (1, 0x00): ('B', 'tempo'),
    (6, 0x17): ('A', 'filter'), (6, 0x18): ('B', 'filter'),
    (6, 0x1F): ('M', 'xfader'),
}
_NOTE_MAP = {
    (0, 0x0B): ('A', 'play'),       (1, 0x0B): ('B', 'play'),
    (0, 0x0C): ('A', 'cue'),        (1, 0x0C): ('B', 'cue'),
    (0, 0x60): ('A', 'sync'),       (1, 0x60): ('B', 'sync'),
    (0, 0x36): ('A', 'jog_touch'),  (1, 0x36): ('B', 'jog_touch'),
    (0, 0x10): ('A', 'loop_in'),    (1, 0x10): ('B', 'loop_in'),
    (0, 0x11): ('A', 'loop_out'),   (1, 0x11): ('B', 'loop_out'),
}


def _knob_label(v: int) -> str:
    if v < 8:    return "killed"
    if v < 30:   return "deep-cut"
    if v < 55:   return "cut"
    if v <= 73:  return "flat"
    if v <= 100: return "boost"
    return "max"


def _xfader_label(v: int) -> str:
    if v < 16:   return "full-A"
    if v < 48:   return "A-side"
    if v <= 80:  return "center"
    if v <= 112: return "B-side"
    return "full-B"


class ControllerState:
    """Live decoded DDJ-FLX4 state. Lock-protected. Tracks recent moves only —
    the AI sees deltas, never static positions (those are background context)."""

    def __init__(self):
        self._lock = threading.Lock()
        self.deck = {
            'A': {'vol': 0, 'eq_low': 64, 'eq_mid': 64, 'eq_hi': 64,
                  'filter': 64, 'tempo': 64, 'play': False, 'cue': False,
                  'jog_touched': False},
            'B': {'vol': 0, 'eq_low': 64, 'eq_mid': 64, 'eq_hi': 64,
                  'filter': 64, 'tempo': 64, 'play': False, 'cue': False,
                  'jog_touched': False},
        }
        self.xfader = 64
        self._moves: list[tuple[float, str]] = []
        self._connected = False
        self.port_name = ""

    def mark_connected(self, port_name: str):
        with self._lock:
            self._connected = True
            self.port_name = port_name

    def is_connected(self) -> bool:
        with self._lock:
            return self._connected

    def _record_move(self, label: str, now: float):
        if self._moves and (now - self._moves[-1][0] < 0.4) and self._moves[-1][1] == label:
            return
        self._moves.append((now, label))
        cutoff = now - 12.0
        while self._moves and self._moves[0][0] < cutoff:
            self._moves.pop(0)

    def handle_msg(self, msg) -> None:
        now = time.time()
        try:
            if msg.type == 'control_change':
                key = (msg.channel, msg.control)
                if key not in _CC_MAP:
                    return
                deck, field = _CC_MAP[key]
                v = msg.value
                with self._lock:
                    if deck == 'M':
                        prev = self.xfader
                        self.xfader = v
                        if _xfader_label(prev) != _xfader_label(v):
                            self._record_move(f"xfader→{_xfader_label(v)}", now)
                    else:
                        prev = self.deck[deck][field]
                        self.deck[deck][field] = v
                        abs_d = abs(v - prev)
                        mag = "small" if abs_d < 15 else ("medium" if abs_d < 40 else "big")
                        if field in ('vol', 'tempo'):
                            if abs_d > 15:
                                direction = "up" if v > prev else "down"
                                self._record_move(f"{deck}_{field} {direction} ({mag})", now)
                        elif field in ('eq_low', 'eq_mid', 'eq_hi', 'filter'):
                            if _knob_label(prev) != _knob_label(v):
                                self._record_move(
                                    f"{deck}_{field.replace('eq_','')}: {_knob_label(prev)}→{_knob_label(v)} ({mag} twist)",
                                    now,
                                )
            elif msg.type == 'note_on':
                key = (msg.channel, msg.note)
                if key not in _NOTE_MAP:
                    return
                deck, field = _NOTE_MAP[key]
                with self._lock:
                    if field == 'play':
                        self.deck[deck]['play'] = not self.deck[deck]['play']
                        self._record_move(f"{deck}_play→{'ON' if self.deck[deck]['play'] else 'OFF'}", now)
                    elif field == 'cue':
                        self._record_move(f"{deck}_cue_hit", now)
                    elif field == 'sync':
                        self._record_move(f"{deck}_sync_hit", now)
                    elif field == 'jog_touch':
                        self.deck[deck]['jog_touched'] = (msg.velocity > 0)
                    elif field == 'loop_in':
                        self.deck[deck]['play'] = True
                        self._record_move(f"{deck}_loop_in_hit (play=ON)", now)
                    elif field == 'loop_out':
                        self._record_move(f"{deck}_loop_out_hit", now)
            elif msg.type == 'note_off':
                key = (msg.channel, msg.note)
                if key in _NOTE_MAP:
                    deck, field = _NOTE_MAP[key]
                    if field == 'jog_touch':
                        with self._lock:
                            self.deck[deck]['jog_touched'] = False
        except Exception as e:
            print(f"[midi handle err] {e}", file=sys.stderr)

    def deck_snapshot(self) -> dict:
        """Static snapshot — used by MusicState to compute audible deck weights."""
        with self._lock:
            return {
                'A': dict(self.deck['A']),
                'B': dict(self.deck['B']),
                'xfader': self.xfader,
                'connected': self._connected,
            }

    def moves_since(self, t: float) -> list[tuple[float, str]]:
        with self._lock:
            now = time.time()
            return [(round(now - mt, 1), label) for mt, label in self._moves if mt > t]


def midi_listener_thread(controller_state: ControllerState, stop_event: threading.Event):
    try:
        import mido
    except ImportError:
        print("-> mido not installed, MIDI controller disabled", file=sys.stderr)
        return

    PORT_HINT = "DDJ-FLX4"
    while not stop_event.is_set():
        try:
            ports = mido.get_input_names()
            match = next((p for p in ports if PORT_HINT.lower() in p.lower()), None)
            if not match:
                time.sleep(2.0)
                continue
            with mido.open_input(match) as port:
                controller_state.mark_connected(match)
                print(f"-> MIDI controller in: {match!r}")
                while not stop_event.is_set():
                    msg = port.poll()
                    if msg is None:
                        time.sleep(0.005)
                        continue
                    controller_state.handle_msg(msg)
        except Exception as e:
            print(f"[midi listener err] {e} — retrying in 2s", file=sys.stderr)
            time.sleep(2.0)


class ScreenBuffer:
    def __init__(self):
        self._jpeg: bytes | None = None
        self._dims: tuple[int, int] = (0, 0)
        self._lock = threading.Lock()

    def push(self, jpeg: bytes, w: int, h: int):
        with self._lock:
            self._jpeg = jpeg
            self._dims = (w, h)

    def latest(self) -> tuple[bytes | None, tuple[int, int]]:
        with self._lock:
            return self._jpeg, self._dims


class VoiceRecorder:
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

        wall_start = datetime.now().astimezone()
        self._write_event_locked({
            "t": 0.0,
            "kind": "session_start",
            "wall_clock_iso": wall_start.isoformat(timespec="milliseconds"),
            "wall_clock_unix": round(wall_start.timestamp(), 3),
            "session_dir": str(self.session_dir.name),
        })

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

    def _write_event_locked(self, rec: dict):
        try:
            json.dump(rec, self.events_f, ensure_ascii=False)
            self.events_f.write("\n")
            self.events_f.flush()
        except Exception:
            pass

    def log_event(self, kind: str, **fields):
        rel = time.time() - self.start_time
        rec = {"t": round(rel, 3), "kind": kind, **fields}
        with self._lock:
            self._write_event_locked(rec)

    def close(self):
        with self._lock:
            try:
                self.voice_wav.close()
            except Exception:
                pass
            try:
                self.input_wav.close()
            except Exception:
                pass
            try:
                self.events_f.close()
            except Exception:
                pass


# =============================================================================
# Audio / Gemini wiring
# =============================================================================

def start_passthrough_stream(output_idx: int, passthrough: PassthroughBuffer) -> sd.OutputStream:
    bytes_per_frame = 2 * 4

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
        device=output_idx, samplerate=INPUT_SR_NATIVE, channels=2,
        dtype="float32", blocksize=OUTPUT_BLOCKSIZE, latency="low", callback=callback,
    )
    stream.start()
    print(f"-> djay passthrough -> {sd.query_devices(output_idx)['name']} @ {INPUT_SR_NATIVE}Hz")
    return stream


def start_playback_stream(output_idx: int, playback: PlaybackQueue) -> sd.RawOutputStream:
    def callback(outdata, frames, time_info, status):
        if status:
            print(f"[output status] {status}", file=sys.stderr)
        outdata[:] = playback.pull(frames * 2)

    stream = sd.RawOutputStream(
        device=output_idx, samplerate=OUTPUT_SR, channels=1,
        dtype="int16", blocksize=VOICE_BLOCKSIZE, latency="low", callback=callback,
    )
    stream.start()
    print(f"-> AI voice -> {sd.query_devices(output_idx)['name']} @ {OUTPUT_SR}Hz")
    return stream


def start_input_to_session(input_idx: int, levels: Levels, passthrough: PassthroughBuffer,
                           mic: MicBuffer, audio_buf: AudioBuffer,
                           recorder: VoiceRecorder,
                           session, loop: asyncio.AbstractEventLoop) -> sd.InputStream:
    def callback(indata, frames, time_info, status):
        if status:
            print(f"[input status] {status}", file=sys.stderr)
        if PASSTHROUGH_GAIN != 1.0:
            passthrough.push((indata * PASSTHROUGH_GAIN).astype(np.float32).tobytes())
        else:
            passthrough.push(indata.tobytes())

        mono48 = indata.mean(axis=1).astype(np.float32) * MUSIC_GAIN_TO_GEMINI
        mic_chunk = mic.pull(len(mono48))
        if mic_chunk.shape == mono48.shape:
            mono48 = mono48 + mic_chunk
        pcm16_48k = np.clip(mono48 * 32767.0, -32768, 32767).astype(np.int16)

        try:
            mono16f = resample_poly(mono48, INPUT_SR_TARGET, INPUT_SR_NATIVE).astype(np.float32)
            pcm16_16k = np.clip(mono16f * 32767.0, -32768, 32767).astype(np.int16)
            audio_buf.push(pcm16_16k)
            recorder.push_input(pcm16_16k.tobytes())
        except Exception as e:
            print(f"[buf push err] {e}", file=sys.stderr)

        levels.update_music(pcm16_48k)

        if levels.voice > AI_TALK_THRESHOLD:
            return

        try:
            frame = rtc.AudioFrame(
                data=pcm16_48k.tobytes(),
                sample_rate=INPUT_SR_NATIVE,
                num_channels=1,
                samples_per_channel=len(pcm16_48k),
            )
            session.push_audio(frame)
        except Exception as e:
            print(f"[push_audio err] {e}", file=sys.stderr)

    stream = sd.InputStream(
        device=input_idx, samplerate=INPUT_SR_NATIVE, channels=2,
        dtype="float32", blocksize=INPUT_CHUNK_FRAMES, latency="low", callback=callback,
    )
    stream.start()
    print(f"-> listening to {sd.query_devices(input_idx)['name']} @ {INPUT_SR_NATIVE}Hz -> session.push_audio")
    return stream


async def screen_capture_loop(screen_buf: ScreenBuffer, session,
                              state: "MusicState", stop_event: asyncio.Event,
                              recorder: VoiceRecorder):
    """Push a JPEG frame ~1fps while audio is audible. Skipped during silence —
    no point feeding the model screen context when there's nothing to react to."""
    if not _HAS_VISION:
        print("-> mss/PIL not installed, screen vision disabled")
        return

    sct = mss.mss()
    monitor = sct.monitors[1]
    print(f"-> screen vision: {monitor['width']}x{monitor['height']} @ ~1fps -> push_video"
          f"{' (djay-only crop)' if _HAS_QUARTZ else ' (full screen)'}")

    loop = asyncio.get_running_loop()
    push_disabled = False
    push_errors = 0

    def grab() -> tuple[bytes, bytes, int, int]:
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        bounds = find_djay_window_bounds()
        if bounds is not None:
            x, y, ww, hh = bounds
            scale_x = img.size[0] / monitor["width"]
            scale_y = img.size[1] / monitor["height"]
            px = max(0, int(x * scale_x))
            py = max(0, int(y * scale_y))
            pw = min(img.size[0] - px, int(ww * scale_x))
            ph = min(img.size[1] - py, int(hh * scale_y))
            if pw > 200 and ph > 200:
                img = img.crop((px, py, px + pw, py + ph))
        img.thumbnail((900, 560))
        w, h = img.size
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=58)
        rgba = img.convert("RGBA").tobytes()
        return buf.getvalue(), rgba, w, h

    while not stop_event.is_set():
        try:
            if not state.audible:
                await asyncio.sleep(1.0)
                continue
            jpeg, rgba, w, h = await loop.run_in_executor(None, grab)
            screen_buf.push(jpeg, w, h)
            if not push_disabled:
                try:
                    frame = rtc.VideoFrame(
                        width=w, height=h,
                        type=rtc.VideoBufferType.RGBA,
                        data=rgba,
                    )
                    session.push_video(frame)
                except Exception as e:
                    push_errors += 1
                    msg = str(e)
                    if "1008" in msg or push_errors >= 3:
                        print(f"[screen] push_video disabled after {push_errors} errors: {e}", file=sys.stderr)
                        recorder.log_event("screen_push_disabled", reason=msg[:200])
                        push_disabled = True
                    else:
                        print(f"[screen push err {push_errors}] {e}", file=sys.stderr)
        except Exception as e:
            print(f"[screen err] {e}", file=sys.stderr)
        await asyncio.sleep(1.0)


async def consume_response(ev: llm.GenerationCreatedEvent, playback: PlaybackQueue,
                           recorder: VoiceRecorder):
    try:
        async for msg in ev.message_stream:
            async def pump_text():
                async for t in msg.text_stream:
                    if t:
                        print(f"AI> {t}", flush=True)
                        recorder.log_event("ai_text", text=t)

            async def pump_audio():
                async for frame in msg.audio_stream:
                    pcm = bytes(frame.data)
                    playback.push(pcm)
                    recorder.push_voice(pcm)

            await asyncio.gather(pump_text(), pump_audio())
    except Exception as e:
        print(f"\n[consume err] {e}", file=sys.stderr)


# =============================================================================
# THE NEW BRAIN — MusicState, EventDetector, AICoach
# =============================================================================

@dataclass
class MusicState:
    """Single source of truth. Refreshed at 10Hz from audio + MIDI + track poll.
    Everything the EventDetector and AICoach need — and nothing they don't.
    Read-only from the consumer side; only state_refresh_loop writes to it."""

    # Audio
    audible: bool = False                  # debounced — true only when sustained sound
    rms: float = 0.0
    bands: dict = field(default_factory=lambda: {"sub": 0.0, "low": 0.0, "mid": 0.0, "high": 0.0})
    onset_density: float = 0.0
    bpm: float = 0.0
    energy_curve: list = field(default_factory=list)   # last ~12s, 1s hop

    # Phase (derived from energy curve, only valid when audible)
    phase: str = "silent"                  # silent / low / groove / build / drop / peak / breakdown
    phase_started_at: float = 0.0

    # Controller (snapshot from MIDI thread)
    deck_a: dict = field(default_factory=dict)
    deck_b: dict = field(default_factory=dict)
    xfader: int = 64
    controller_connected: bool = False

    # Audible deck inference — which deck is producing the sound NOW
    audible_deck: str = "none"             # 'A' / 'B' / 'mix' / 'none'
    deck_confidence: float = 0.0           # 0..1

    # Track (cross-referenced with audible deck)
    audible_track: str | None = None
    audible_track_confidence: float = 0.0  # 0..1 — feeds into prompt as `(unsure)` flag
    last_audible_track: str | None = None  # what was audible last refresh (for change detection)

    # Recent moves (within last 12s, deck-attributed)
    recent_moves: list = field(default_factory=list)

    # Historical context — lets the AI reference set shape and continuity
    long_arc: list = field(default_factory=list)              # ~120s RMS, 10s hop
    phase_history: list = field(default_factory=list)         # [(t, from, to)] last 6
    track_history: list = field(default_factory=list)         # [(t, title)] last 6 audible titles

    # Set timing
    set_start_at: float = 0.0
    last_kaan_spoke_at: float = 0.0

    _lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def set_seconds(self) -> float:
        return time.time() - self.set_start_at if self.set_start_at else 0.0

    @property
    def time_in_phase(self) -> float:
        return time.time() - self.phase_started_at if self.phase_started_at else 0.0


def classify_phase(curve: list, audible: bool) -> str:
    """Phase tag from energy curve. Returns 'silent' if not audible."""
    if not audible or not curve:
        return "silent"
    last = curve[-1]
    if last < SILENT_RMS:
        return "silent"
    if last < LOW_RMS:
        return "low"
    if len(curve) < 5:
        return "groove"
    recent = curve[-5:]
    earlier = curve[-10:-5] if len(curve) >= 10 else curve[: max(0, len(curve) - 5)]
    earlier_max = max(earlier) if earlier else 0.0

    diffs = [recent[i] - recent[i-1] for i in range(1, len(recent))]
    monotonic_climbs = sum(1 for d in diffs if d > 0)
    if monotonic_climbs >= 3 and (recent[-1] - recent[0]) > 0.020:
        return "build"
    if last >= PEAK_RMS and any(v < LOW_RMS for v in recent[:3]):
        return "drop"
    if earlier_max >= 0.040 and last < 0.5 * earlier_max:
        return "breakdown"
    if all(v >= 0.045 for v in recent):
        return "peak"
    return "groove"


def derive_audible_deck(deck_a: dict, deck_b: dict, xfader: int,
                        connected: bool) -> tuple[str, float]:
    """Returns (audible_deck, confidence). 'A' / 'B' / 'mix' / 'none'.
    Confidence considers play state, channel volume, and crossfader position."""
    if not connected:
        return "none", 0.0

    # Per-side weight = play * vol * xfader_factor
    def xfader_factor(side: str) -> float:
        if side == 'A':
            if xfader >= 112: return 0.0
            if xfader >= 80:  return 0.3
            if xfader >= 48:  return 0.7
            return 1.0
        else:  # B
            if xfader < 16:   return 0.0
            if xfader < 48:   return 0.3
            if xfader <= 80:  return 0.7
            return 1.0

    def deck_weight(d: dict, side: str) -> float:
        if not d.get('play'):
            return 0.0
        vol = d.get('vol', 0) / 127.0
        if vol < 0.1:
            return 0.0
        return vol * xfader_factor(side)

    wa = deck_weight(deck_a, 'A')
    wb = deck_weight(deck_b, 'B')

    if wa < 0.05 and wb < 0.05:
        return "none", 0.0
    if wa > 0.3 and wb < 0.1:
        return "A", min(1.0, wa)
    if wb > 0.3 and wa < 0.1:
        return "B", min(1.0, wb)
    if wa > 0.2 and wb > 0.2:
        return "mix", min(0.5, max(wa, wb))
    # One dominant but other non-zero — call dominant with reduced confidence
    if wa > wb:
        return "A", max(0.4, wa - wb)
    return "B", max(0.4, wb - wa)


def derive_audible_track(track_title: str | None,
                         audible_deck: str,
                         deck_confidence: float,
                         audio_audible: bool) -> tuple[str | None, float]:
    """Combines nowplaying-cli's title with controller-derived audible deck
    to produce a confidence-tagged track. Conservative — would rather say
    `unknown` than name a track that isn't actually playing.

    nowplaying-cli only gives ONE current title (whichever deck cued/loaded
    most recently). When the controller says audio is coming primarily from
    a single deck, we trust the title. Otherwise we lower confidence."""
    if not audio_audible or not track_title:
        return None, 0.0
    if audible_deck == "none":
        # Audio is heard but controller says no deck is active — controller may
        # be disconnected or in a weird state. Don't anchor on the title.
        return track_title, 0.3
    if audible_deck == "mix":
        # Two decks playing — title may be either. Mark unsure.
        return track_title, 0.4
    # Single dominant deck. Trust the title roughly proportional to confidence.
    return track_title, min(0.85, max(0.5, deck_confidence))


@dataclass
class Event:
    type: str          # KAAN_SPOKE / MANUAL / TRACK_CHANGE / PHASE / LAYER_ARRIVAL / MIX_MOVE / HEARTBEAT
    state: MusicState
    extra: dict = field(default_factory=dict)


class EventDetector:
    """Reads MusicState diffs, emits at most ONE event per cycle.
    Returns None most of the time. The cardinal rule: NOTHING fires while
    the audio is not audible, except KAAN_SPOKE and MANUAL."""

    def __init__(self):
        self.last_event_at = 0.0
        self.last_per_type_at: dict[str, float] = {}
        self.last_phase: str = "silent"
        self.last_audible_track: str | None = None
        self.last_band_signature: tuple[float, float] | None = None
        self.last_mix_moves_seen: list[str] = []

    def _cooldown_ok(self, ev_type: str, now: float) -> bool:
        gap = MIN_EVENT_GAP_PER_TYPE.get(ev_type, EVENT_GLOBAL_MIN_GAP)
        last = self.last_per_type_at.get(ev_type, 0.0)
        return (now - last) > gap and (now - self.last_event_at) > EVENT_GLOBAL_MIN_GAP

    def detect(self, state: MusicState, *, kaan_just_spoke: bool, manual: bool) -> Event | None:
        now = time.time()

        # Mic + manual bypass silence guards (conversation/control events)
        if kaan_just_spoke and self._cooldown_ok("MIC", now):
            self._fire("MIC", now)
            return Event("KAAN_SPOKE", state)

        if manual and self._cooldown_ok("MANUAL", now):
            self._fire("MANUAL", now)
            return Event("MANUAL", state)

        # GLOBAL SILENCE GUARD — no music-driven event during silence
        if not state.audible:
            # Still update state-tracking refs so we don't fire spurious "change"
            # events the moment audio comes back
            self.last_phase = state.phase
            self.last_audible_track = state.audible_track
            self.last_band_signature = None
            return None

        # 1) Track change — new audible track different from last seen
        if state.audible_track and state.audible_track != self.last_audible_track:
            if self._cooldown_ok("TRACK_CHANGE", now):
                ev = Event("TRACK_CHANGE", state, extra={
                    "prev_track": self.last_audible_track,
                    "new_track": state.audible_track,
                })
                self.last_audible_track = state.audible_track
                self._fire("TRACK_CHANGE", now)
                return ev
        self.last_audible_track = state.audible_track

        # 2) Phase transition — significant change with cooldown
        if state.phase != self.last_phase and state.phase not in ("silent",):
            if self._cooldown_ok("PHASE", now):
                ev = Event("PHASE", state, extra={
                    "prev_phase": self.last_phase,
                    "new_phase": state.phase,
                })
                self.last_phase = state.phase
                self._fire("PHASE", now)
                return ev
        self.last_phase = state.phase

        # 3) Layer arrival — sudden jump in mid or high band share
        sig = (round(state.bands["mid"], 2), round(state.bands["high"], 2))
        if self.last_band_signature is not None and self._cooldown_ok("LAYER_ARRIVAL", now):
            mid_jump = sig[0] - self.last_band_signature[0]
            high_jump = sig[1] - self.last_band_signature[1]
            if (mid_jump > 0.15 or high_jump > 0.10) and state.rms > LOW_RMS:
                ev = Event("LAYER_ARRIVAL", state, extra={
                    "mid_jump": round(mid_jump, 2),
                    "high_jump": round(high_jump, 2),
                })
                self.last_band_signature = sig
                self._fire("LAYER_ARRIVAL", now)
                return ev
        self.last_band_signature = sig

        # 4) Mix move — significant controller move while audible. Only react to
        # NEW moves (not seen before this cycle). Significance: vol up/down,
        # xfader edge crossings, EQ kills/restores, filter extremes, play toggles.
        new_significant = []
        for age, label in state.recent_moves:
            if label in self.last_mix_moves_seen:
                continue
            if any(k in label for k in ('killed', 'xfader', 'play', 'filter:', 'cue_hit', 'loop_in_hit', 'big')):
                new_significant.append(label)
        if new_significant and self._cooldown_ok("MIX_MOVE", now):
            self.last_mix_moves_seen = [m for _, m in state.recent_moves][-12:]
            ev = Event("MIX_MOVE", state, extra={"moves": new_significant[-3:]})
            self._fire("MIX_MOVE", now)
            return ev
        # Always keep seen-list fresh so we don't replay old moves later
        self.last_mix_moves_seen = [m for _, m in state.recent_moves][-12:]

        # 5) Heartbeat — long silence in conversation while music is going
        if self._cooldown_ok("HEARTBEAT", now):
            self._fire("HEARTBEAT", now)
            return Event("HEARTBEAT", state)

        return None

    def _fire(self, ev_type: str, now: float):
        self.last_event_at = now
        self.last_per_type_at[ev_type] = now


class AICoach:
    """Builds the per-event prompt. Single persona is set at session-open via
    SYSTEM_INSTRUCTION; this class only adds event-specific evidence + task."""

    @staticmethod
    def evidence_line(state: MusicState) -> str:
        e = []
        if state.audible:
            b = state.bands
            e.append(
                f"hearing[rms={state.rms:.3f} sub={b['sub']:.2f} low={b['low']:.2f} "
                f"mid={b['mid']:.2f} high={b['high']:.2f} bpm={state.bpm:.0f}]"
            )
        else:
            e.append("hearing[silent]")

        if state.audible_track and state.audible_track_confidence >= 0.6:
            e.append(f"track={state.audible_track!r}")
        elif state.audible_track and state.audible_track_confidence > 0:
            e.append(f"track={state.audible_track!r}(unsure)")
        else:
            e.append("track=unknown")

        e.append(f"deck={state.audible_deck}")
        e.append(f"set_time={int(state.set_seconds // 60)}:{int(state.set_seconds % 60):02d}")
        e.append(f"phase={state.phase}({int(state.time_in_phase)}s)")

        recent_8s = [(age, label) for age, label in state.recent_moves if age <= 8.0]
        if recent_8s:
            recent_8s.sort(key=lambda x: -x[0])
            mv = ", ".join(label for _, label in recent_8s)
            e.append(f"recent_moves[8s]: {mv}")
        else:
            e.append("recent_moves[8s]: NONE")

        # Set-arc — coarse 2-minute energy shape so the AI can see set context
        if state.long_arc and len(state.long_arc) >= 2:
            e.append(f"set_arc[{len(state.long_arc)*10}s]={state.long_arc}")

        # Phase history — last 3 transitions for continuity
        if state.phase_history:
            chain = []
            for i, (_, fr, to) in enumerate(state.phase_history[-4:]):
                if i == 0:
                    chain.append(fr)
                chain.append(to)
            e.append(f"phase_history: {'→'.join(chain)}")

        # Track history — last 3 audibly-confirmed titles
        if len(state.track_history) >= 2:
            titles = [repr(t) for _, t in state.track_history[-3:]]
            e.append(f"recent_tracks: {'→'.join(titles)}")

        return " | ".join(e)

    @staticmethod
    def task_for_event(ev: Event) -> str:
        t = ev.type
        if t == "KAAN_SPOKE":
            return ("Kaan just SPOKE — answer him directly, friend tone, 6-15 words. "
                    "Not a music reaction.")
        if t == "MANUAL":
            return ("Kaan hit his trigger — react with substance to ONE concrete thing "
                    "(audible event or recent move). 12-18 words.")
        if t == "TRACK_CHANGE":
            prev = ev.extra.get("prev_track")
            prev_clause = f" (was: {prev!r})" if prev else ""
            return (f"Track flipped{prev_clause}. React to the NEW track's vibe vs "
                    "the previous — heavier, weirder, darker, more euphoric? "
                    "12-18 words. Past tense.")
        if t == "PHASE":
            new = ev.extra.get("new_phase", "?")
            prev = ev.extra.get("prev_phase", "?")
            return (f"Phase shifted: {prev}→{new}. React to what the new section "
                    "FEELS like, not the label. 10-14 words.")
        if t == "LAYER_ARRIVAL":
            return ("A new sonic layer arrived — synth lead, hi-hat layer, vocal, "
                    "riff, pad. Name what arrived and how it feels. 10-14 words.")
        if t == "MIX_MOVE":
            mv = ", ".join(ev.extra.get("moves", []))
            return (f"Kaan made a move ({mv}). React to ONE — name the technique "
                    "and its sonic effect. 10-14 words. Past tense.")
        if t == "HEARTBEAT":
            return ("Steady stretch. Drop ONE specific musical observation — drum "
                    "pattern, bass character, vibe, scene placement. 10-14 words. "
                    "Or stay quiet if nothing fresh.")
        return "React naturally. 10-14 words."

    @staticmethod
    def build_prompt(ev: Event) -> str:
        evidence = AICoach.evidence_line(ev.state)
        task = AICoach.task_for_event(ev)
        return f"[{evidence} | event={ev.type}] {task}"


# =============================================================================
# Refresh + coach loops
# =============================================================================

async def state_refresh_loop(state: MusicState, audio_buf: AudioBuffer,
                             controller_state: ControllerState, track_info: TrackInfo,
                             stop_event: asyncio.Event):
    """Updates MusicState every 100ms from all sources. The ONLY writer to state.
    Audible flag is debounced — sustained samples required to flip in either
    direction so a brief dip doesn't yank the AI into 'silent' mid-track."""
    last_audible_high = 0.0
    last_audible_low = 0.0
    bpm_cache = 0.0
    last_bpm_at = 0.0

    while not stop_event.is_set():
        await asyncio.sleep(0.1)
        try:
            now = time.time()

            # Audio features (cheap — ~5-10ms)
            feats = audio_buf.snapshot_features(seconds=4.0)
            curve = audio_buf.energy_curve(seconds=12.0, hop=1.0)
            rms = feats.get("rms", 0.0)
            currently_loud = rms > SILENT_RMS

            # BPM updated every 3s — autocorr is heavier
            if now - last_bpm_at > 3.0 and currently_loud:
                bpm_cache = audio_buf.estimate_bpm(seconds=6.0)
                last_bpm_at = now

            # Audible debouncing — both directions sustained
            if currently_loud:
                if last_audible_high == 0.0:
                    last_audible_high = now
                last_audible_low = 0.0
            else:
                if last_audible_low == 0.0:
                    last_audible_low = now
                last_audible_high = 0.0

            with state._lock:
                if state.audible:
                    if last_audible_low > 0 and (now - last_audible_low) >= SILENCE_DEBOUNCE_SEC:
                        state.audible = False
                else:
                    if last_audible_high > 0 and (now - last_audible_high) >= AUDIBLE_DEBOUNCE_SEC:
                        state.audible = True

                state.rms = rms
                state.bands = {
                    "sub": feats.get("sub_share", 0.0),
                    "low": feats.get("low_share", 0.0),
                    "mid": feats.get("mid_share", 0.0),
                    "high": feats.get("high_share", 0.0),
                }
                state.onset_density = feats.get("onsets_per_sec", 0.0)
                state.bpm = bpm_cache
                state.energy_curve = curve

                # Phase
                new_phase = classify_phase(curve, state.audible)
                if new_phase != state.phase:
                    state.phase_history.append((now, state.phase, new_phase))
                    if len(state.phase_history) > 6:
                        state.phase_history.pop(0)
                    state.phase = new_phase
                    state.phase_started_at = now

                # Controller snapshot
                cs = controller_state.deck_snapshot()
                state.deck_a = cs['A']
                state.deck_b = cs['B']
                state.xfader = cs['xfader']
                state.controller_connected = cs['connected']

                # Audible deck inference
                aud_deck, deck_conf = derive_audible_deck(
                    cs['A'], cs['B'], cs['xfader'], cs['connected']
                )
                state.audible_deck = aud_deck
                state.deck_confidence = deck_conf

                # Track inference (cross-reference with audible deck)
                tsnap = track_info.snapshot()
                tt, tc = derive_audible_track(
                    tsnap.get("title") or None, aud_deck, deck_conf, state.audible
                )
                # Record audibly-confirmed track flips into track_history (only when
                # confidence is decent — prevents jittery deck inference from polluting
                # the history with phantom transitions).
                if tt and tc >= 0.5:
                    last_title = state.track_history[-1][1] if state.track_history else None
                    if tt != last_title:
                        state.track_history.append((now, tt))
                        if len(state.track_history) > 6:
                            state.track_history.pop(0)
                state.audible_track = tt
                state.audible_track_confidence = tc

                # Recent moves
                state.recent_moves = controller_state.moves_since(now - 12.0)

                # Long arc — recompute every cycle is fine (cheap reduction over the
                # 16k ring buffer, ~1ms)
                state.long_arc = audio_buf.long_arc_curve(seconds=120.0, hop=10.0)

        except Exception as e:
            print(f"[state refresh err] {e}", file=sys.stderr)


async def coach_loop(session, state: MusicState, levels: Levels,
                     event_detector: EventDetector, recorder: VoiceRecorder,
                     manual_trigger: asyncio.Event, trigger_state: dict,
                     stop_event: asyncio.Event):
    """Polls MusicState for events at 10Hz. On event → prompt AI. Single in-flight
    generation at a time. Mic detection happens here against levels, not state —
    levels.mic comes from MicBuffer pre-attenuation so AI's own voice doesn't
    leak in as Kaan."""
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

        prompt = AICoach.build_prompt(ev)

        try:
            trigger_state["in_flight"] = True
            trigger_state["in_flight_at"] = now
            tag = ev.type
            print(f"\n[event {tag}] audible={state.audible} deck={state.audible_deck} "
                  f"track={state.audible_track!r}({state.audible_track_confidence:.1f}) "
                  f"phase={state.phase} | {prompt[:200]}")
            recorder.log_event(
                "event",
                type=tag,
                audible=state.audible,
                deck=state.audible_deck,
                track=state.audible_track,
                track_conf=round(state.audible_track_confidence, 2),
                phase=state.phase,
                prompt=prompt,
            )
            fut = session.generate_reply(instructions=prompt)
            try:
                await asyncio.wait_for(fut, timeout=12.0)
            except asyncio.TimeoutError:
                print(f"[coach] generate_reply timed out", file=sys.stderr)
                trigger_state["in_flight"] = False
                continue
        except Exception as e:
            trigger_state["in_flight"] = False
            print(f"\n[coach err] {e}", file=sys.stderr)


# =============================================================================
# Diag + WS
# =============================================================================

async def diag_loop(levels: Levels, state: MusicState, stop_event: asyncio.Event):
    while not stop_event.is_set():
        await asyncio.sleep(1.0)
        snap = levels.snapshot()
        m_bar = "#" * int(min(snap["music"] * 50, 30))
        v_bar = "#" * int(min(snap["voice"] * 50, 30))
        sys.stdout.write(
            f"\r[live] music={snap['music']:.3f} {m_bar:<30} | voice={snap['voice']:.3f} {v_bar:<10} | "
            f"audible={int(state.audible)} deck={state.audible_deck} phase={state.phase[:8]:<8}"
        )
        sys.stdout.flush()


async def ws_broadcast(levels: Levels, state: MusicState, manual_trigger: asyncio.Event,
                       stop_event: asyncio.Event):
    if not _HAS_WS:
        print("-> websockets not installed, mascot bus disabled")
        return

    clients: set = set()

    async def handler(ws):
        clients.add(ws)
        try:
            async for msg in ws:
                try:
                    data = json.loads(msg) if isinstance(msg, str) else {}
                except Exception:
                    data = {}
                if data.get("action") == "trigger":
                    print("\n[ws] manual trigger requested")
                    manual_trigger.set()
        except Exception:
            pass
        finally:
            clients.discard(ws)

    server = await websockets.serve(handler, WS_HOST, WS_PORT)
    print(f"-> mascot bus on ws://{WS_HOST}:{WS_PORT} (send {{action: trigger}} for manual fire)")

    try:
        while not stop_event.is_set():
            payload = json.dumps({
                **levels.snapshot(),
                "audible": state.audible,
                "deck": state.audible_deck,
                "phase": state.phase,
            })
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


# =============================================================================
# main
# =============================================================================

async def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY not set")

    input_idx = find_device(INPUT_DEVICE, "input")
    output_idx = find_device(OUTPUT_DEVICE, "output")

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
    screen_buf = ScreenBuffer()
    audio_buf = AudioBuffer(seconds=140.0, sr=INPUT_SR_TARGET)
    recorder = VoiceRecorder()
    track_info = TrackInfo()
    controller_state = ControllerState()

    state = MusicState()
    state.set_start_at = time.time()
    state.phase_started_at = time.time()
    event_detector = EventDetector()

    voice_stream = start_playback_stream(output_idx, playback)
    pass_stream = start_passthrough_stream(output_idx, passthrough)

    try:
        mic_idx = find_device(MIC_DEVICE, "input")

        def mic_callback(indata, frames, time_info, status):
            if status:
                print(f"[mic status] {status}", file=sys.stderr)
            mono = indata[:, 0] if indata.ndim > 1 else indata
            mic.push(mono.astype(np.float32))

        mic_stream = sd.InputStream(
            device=mic_idx, samplerate=INPUT_SR_NATIVE, channels=1,
            dtype="float32", blocksize=INPUT_CHUNK_FRAMES, latency="low", callback=mic_callback,
        )
        mic_stream.start()
        print(f"-> mic on {sd.query_devices(mic_idx)['name']} @ {INPUT_SR_NATIVE}Hz")
    except Exception as e:
        print(f"-> mic disabled: {e}")
        mic_stream = None

    print(f"-> connecting to {MODEL}")
    model = RealtimeModel(
        model=MODEL,
        instructions=SYSTEM_INSTRUCTION,
        voice=VOICE,
        api_key=api_key,
        modalities=[types.Modality.AUDIO],
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )
    session = model.session()
    print("-> session opened.")

    trigger_state = {"in_flight": False}

    @session.on("generation_created")
    def on_gen(ev: llm.GenerationCreatedEvent):
        recorder.log_event("generation_created", user_initiated=ev.user_initiated)
        async def runner():
            try:
                await consume_response(ev, playback, recorder)
            finally:
                trigger_state["in_flight"] = False
                recorder.log_event("generation_done")
        asyncio.create_task(runner())

    manual_trigger = asyncio.Event()

    midi_stop = threading.Event()
    midi_thread = threading.Thread(
        target=midi_listener_thread, args=(controller_state, midi_stop), daemon=True
    )
    midi_thread.start()

    ws_task = asyncio.create_task(ws_broadcast(levels, state, manual_trigger, stop_event))
    diag_task = asyncio.create_task(diag_loop(levels, state, stop_event))
    screen_task = asyncio.create_task(screen_capture_loop(screen_buf, session, state, stop_event, recorder))
    track_task = asyncio.create_task(track_poll_loop(track_info, stop_event))
    refresh_task = asyncio.create_task(state_refresh_loop(state, audio_buf, controller_state, track_info, stop_event))
    coach_task = asyncio.create_task(coach_loop(
        session, state, levels, event_detector, recorder,
        manual_trigger, trigger_state, stop_event,
    ))

    input_stream = start_input_to_session(input_idx, levels, passthrough, mic, audio_buf, recorder, session, loop)

    try:
        await stop_event.wait()
    finally:
        midi_stop.set()
        for t in (coach_task, refresh_task, screen_task, ws_task, diag_task, track_task):
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
        try:
            await session.aclose()
        except Exception as e:
            print(f"[close session err] {e}", file=sys.stderr)
        try:
            await model.aclose()
        except Exception as e:
            print(f"[close model err] {e}", file=sys.stderr)

    voice_stream.stop(); voice_stream.close()
    pass_stream.stop(); pass_stream.close()
    input_stream.stop(); input_stream.close()
    if mic_stream:
        mic_stream.stop(); mic_stream.close()
    recorder.close()
    print("-> bye")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
