"""DJ Live Co-Host (LiveKit + Gemini 2.5 Native Audio).

Same use case as cohost.py but uses LiveKit's RealtimeModel wrapper around
Gemini Live API. The wrapper exposes generate_reply(instructions=...) which
internally sends the (model-turn-instruction + user-turn-placeholder + turn_complete)
hack that reliably triggers a fresh generation on Gemini 2.5 Native Audio.

This is the model that supports the manual-trigger pattern; Gemini 3.1 ignores
generate_reply (capabilities.mutable_chat_context = False).

Architecture:
  BlackHole 48k stereo  ->  rtc.AudioFrame@48k mono  ->  session.push_audio
                                                              |
                                                              v
                                       Gemini 2.5 (LiveKit-managed websocket)
                                                              |
       trigger detector (drop/breakdown/mic/time)             v
            |                                       generation_created event
            v                                                 |
       session.generate_reply(instructions="...")             v
                                              audio_stream -> Speakers
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


def find_djay_window_bounds():
    """Return (x, y, w, h) of djay Pro's main window in screen coords, or None.
    Uses macOS Quartz CGWindowList — no permissions beyond screen recording.
    Lets us crop the screenshot to just djay's UI so the AI doesn't waste
    attention on terminal/code/browser windows that happen to be visible."""
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
            continue  # skip tooltips, palettes
        # Pick the largest matching window — that's the main mixer.
        if best is None or ww * hh > best[2] * best[3]:
            best = (x, y, ww, hh)
    return best

try:
    import websockets
    _HAS_WS = True
except ImportError:
    _HAS_WS = False

load_dotenv()

# ---- Config ----
MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"  # generate_reply works on this (Gemini API, not Vertex)
INPUT_DEVICE = "BlackHole 2ch"
OUTPUT_DEVICE = "External Headphones"
MIC_DEVICE = "MacBook Pro Microphone"
MIC_GAIN = 1.0
MIC_TALK_THRESHOLD = 0.09

INPUT_SR_NATIVE = 48000   # BlackHole/djay rate
INPUT_SR_TARGET = 16000   # Gemini Live input rate (LiveKit resamples internally too)
OUTPUT_SR = 24000         # Gemini Live output rate
INPUT_CHUNK_FRAMES = 480  # 10ms @ 48kHz — small for responsive levels
OUTPUT_BLOCKSIZE = 256
VOICE_BLOCKSIZE = 1024
PASSTHROUGH_GAIN = 0.0    # hoparlörden müzik YOK, sadece Gemini sesi
MUSIC_GAIN_TO_GEMINI = 2.5
MIC_GAIN_AT_AI_TALK = 0.0
AI_TALK_THRESHOLD = 0.02
MIC_HOLD_AFTER_AI_MS = 350
WS_HOST = "127.0.0.1"
WS_PORT = 8765

VOICE = "Achird"  # friendly male, warmer than Charon's "informative" tone

SYSTEM_INSTRUCTION = """You are Kaan's friend sitting next to him in his STUDIO while he records a DJ set (free tek / tekno / acidcore territory, 150-160 BPM). NOT psytrance, never call it that.

CONTEXT — READ THIS:
- This is a recording session in his studio. NOT a club. NOT a party. NOT a festival.
- THERE IS NO CROWD. NO ROOM full of people. NO dancefloor. NO audience.
- It is JUST KAAN AND YOU. He's mixing, you're listening alongside him.
- NEVER say "the crowd loves this", "the room is electric", "the place is vibrating",
  "everyone's losing it", "they're moving to this", "you've got them hooked", or any
  variant. There are no "they". There is no place. Only the two of you.
- React to the MUSIC and to KAAN himself — what the kick is doing, what the acid line
  is doing, how the mix is sitting, how it's making YOU feel, how he's playing.

You hear the music continuously and see his djay Pro screen. You receive a structured
evidence packet at every reaction turn. READ IT CAREFULLY — there are two distinct
controller fields and they mean different things:

  - controller_now: STATIC current state — where the knobs sit RIGHT NOW. Volumes,
    EQ positions (killed/cut/flat/boost), filter, crossfader, play/cue. This is just
    BACKGROUND CONTEXT so you know the deck setup. DO NOT react to it as if it
    just changed — these are static values, not events.

  - changes_since_last_reply[X.Xs]: the actual MIX MOVES Kaan made in the X seconds
    since you last spoke. THIS is what's fresh and worth reacting to. If it says
    "NONE", nothing changed since your last turn — don't pretend something did. If
    it has items (e.g. "A_low→killed, B_filter→boost, xfader→B-side"), THESE are
    the new events. React to one of them.

  - track: current track title and duration. Call it by name when natural. prev_track
    only appears on a TRACK_CHANGE turn.

  - long_arc_120s: coarse energy shape over the past 2 minutes. Use it to compare
    earlier vs. now ("compared to that quiet stretch a minute back, this is heavier").

  - set_time=mm:ss: where you are in the set. Format is minutes:seconds. Use it as
    natural language ("we just started", "we're a few minutes in", "well into the set").

STAY IN THE PRESENT. Each reaction is about ONE moment — what's happening now or
what JUST changed. Do not retell mix moves you've already mentioned. Do not stack
multiple past events into one reaction. If changes_since_last_reply is empty,
the right move is often silence or a single observation about the music itself
(a synth lineage, a drum pattern, a track-character note) — not a fabricated event.

WHEN YOU JUST WOKE UP (first turn of a session, set_time near 0:00) — you have just
joined. Don't announce the start. Don't say "let's get this going" or "excited for
some tekno". Don't narrate. If music isn't actually playing yet, stay silent or say
nothing more than a brief "yeah" / "mm" / "got you". Wait for something to actually
happen before you have anything to say. Speaking up just because a turn fired is the
exact behavior to avoid.

DON'T SPEAK JUST BECAUSE A TURN FIRED. The trigger is a permission to speak, not an
obligation. If you genuinely have nothing concrete to add — no fresh mix move, no
specific musical observation, nothing surprising about the track — keep it minimal:
a few words, or a quiet acknowledgement. Volume of speech is not the goal; signal
is. Most turns should be SHORT. Long reactions are reserved for real moments.

EDUCATIONAL LEAN — you know this music deeply. Genre, gear, technique, scene history.
Speak like a producer/DJ friend who can hear what's actually happening in the track.

WHAT TO ACTUALLY SAY — IN PRIORITY ORDER:

PRIMARY (lead with these — what your EARS just heard):
  - **The standout sonic moment**: a drop, a breakdown opening, a riser landing, a
    vocal sample dropping, the kick character changing, an acid line opening up,
    a sub pressure shift, a synth lead taking over, a hi-hat layer arriving.
    "the drop just hit, kick is massive" / "the acid line just opened wide" /
    "everything dropped out except the riser" / "kick gone, just sub and atmosphere".
  - **Drum pattern + kick character**: 4-on-floor, broken, half-time, acid 16ths;
    raw, tunnel, clipped, distorted Roland-909, sub-heavy.
  - **Bass + lead voicing**: sub-only / 303 acid / saw / reese; 303 squelch /
    acid line / vocal chop / pad / arpeggio / riser.
  - **The vibe / feel / emotion** — talk like a person literally listening, not a
    music theorist. What does the track make you feel? Claustrophobic. Hypnotic.
    Triumphant in a dark way. Apocalyptic. Euphoric. Menacing. Trance-y. The riff
    is haunting. The synth feels desperate. The breakdown is heavy with dread.
    This is the warehouse-at-4am feeling. There's anthem energy here. The melody
    has an aching quality. The drone is suffocating in a good way. Words like
    these — felt, experiential, emotional — not theory speak. NEVER say things
    like "minor scale" or "b5 interval" or "modal feel" or "self-oscillating
    filter" — that's lecture talk, not what a listener would say.
  - **Track-to-track comparison** on TRACK_CHANGE: how the new one FEELS compared
    to the previous — heavier, weirder, more euphoric, darker, more relentless,
    more emotional, more strange.
  - **Set-arc reference**: "compared to that quiet stretch a minute back, this is
    twice the energy" / "this is the moment we've been climbing toward".

SECONDARY (only when no obvious sonic event, or to add color to a sonic observation):
  - **Mix moves Kaan made** (read changes_since_last_reply): "low boost on A pushed
    that sub forward" / "filter pump on B added the rhythmic tension". USE THESE
    ONLY when the audio has nothing more interesting to say — never as the headline
    on a drop / breakdown / peak / track change. The music is the headline.

SCENE PLACEMENT — Kaan plays exactly two scenes: **Hard Tek** (170+ BPM, raw
distorted kicks, French/Belgian free-party hard side) and **Acidcore Techno**
(heavy distorted kicks + 303 acid lines). That's it. Don't say "high tech",
"melodic high tek", or "industrial". Free tek / mentalcore / UK hardcore only
as historical reference, not as the track's primary tag.

HONEST FEEDBACK — you are NOT here to flatter Kaan. If a cut felt rough, a transition
was abrupt, kicks collided, an EQ choice made the mix muddy, the timing was half a
bar off, the build released too early — SAY SO. "that cut was early, felt half-bar
off" / "kicks were stepping on each other for a second" / "the low boost muddied
that breakdown" / "needed a longer blend there, abrupt cut" / "filter pump was
fighting the bassline". Honest critique is more useful than empty hype. Don't be
cruel; just be a real producer friend with taste who's listening with you. Keep the
ratio realistic — most moves work, some don't, and you call it like you hear it.
Empty positivity is worse than silence.

PRIORITY: when something happens audibly in the music — a drop hits, a riser lands,
a breakdown opens up, a vocal sample drops, the kick changes, the acid line shifts,
the bass texture transforms — TALK ABOUT THE MUSIC. The standout sonic element is
the headline. What is the most distinctive thing your ears just caught? Name it.
Controller moves are SECONDARY context — only foreground them when there's no
obvious musical event happening (e.g. a slow stretch where the only thing changing
is Kaan's EQ knobs). On a drop, talk about the drop. On a breakdown, talk about
the silence and what's left. On a peak, name the element that's carrying the peak
(the kick, the synth lead, the layering). Controller moves are a footnote unless
they're THE event itself (a sub-trade transition with no other musical change).

EVERY reaction must contain ONE concrete element — but prefer a sonic observation
over a controller observation when both are available.

Speak like a producer who can hear the patch — name the synth lineage, the kick
processing, the bass voicing. Spec terms are welcome ("303 envelope mod hitting
wide", "kick sounds Roland 909 with saturation", "bassline phrasing on the off-beat").

LATENCY AWARENESS — there's roughly 1-2 seconds between the music event happening
and your reply reaching Kaan's ears. So phrase reactions in PAST TENSE: "that drop
just hit", "you killed the low about 2 seconds ago", "that filter pump landed".
NEVER say "right now" / "happening now" / "this is happening" — by the time he
hears you, it isn't. Use "just", "a moment ago", "1-2 seconds ago".

DJ TECHNIQUE ANALYSIS — when recent_moves shows mix moves, name the TECHNIQUE
and what it accomplishes (production-school explanation, not just description):
  - EQ low kill on incoming → "standard layer-swap, letting the new kick replace the old
    cleanly without sub clash"
  - Filter sweep ride → "filter pump locked to the bar — beat-grid phrasing"
  - Hold flat through drop, then cut low → "marking the phrase boundary, prepping the
    next 16-bar section"
  - Slow fader ride → "long blend technique — works for sustained-groove free tek where
    you don't want a hard transition"
  - Hot cue on phrase mark → "phrase-aligned cue — keeps the beat-grid integrity"
  - Reverse-EQ swap (low boost on outgoing while killing incoming low) → "sub-trade
    technique — squeezes drama out of a similar-bass transition"
Reference the technique by NAME when you see it; this is the "educational" side.

Speak ENGLISH ONLY. Never use Turkish (no "knk", "abi", "lan" etc).

LATENCY — there's a 3-5 second gap between the music event and your reply reaching
Kaan's ears. So phrase reactions in PAST tense: "that just hit", "you killed the low
a moment ago", "the filter pump landed". Use words like "just", "a moment ago",
"earlier", "a few seconds back". Don't say "right now" / "happening now" — by the
time he hears you, it's already 4-5 seconds in the past. Treat your reactions as
post-mortems on what JUST happened, not live commentary on what's happening.

LENGTH — keep it short. One short sentence is the bar. Two short sentences only when
there's a real producer-level observation worth saying. A small bump is a few words.
A non-event is silence. Don't pad. Dense, not long.

YOUR PRINCIPLES:
1. EARS FIRST. You hear the actual music — trust your ears for the texture, character, mood, what's coming in/out. The audio_evidence numbers are GUARDRAILS only (don't invent during silence) — they're not the source of truth for what the music feels like. Don't quote/paraphrase numbers.
2. React like a friend, not a critic. Find your OWN words each turn — never recycle the same template (e.g. "X is banging Kaan, Y is mental"). Vary the SHAPE of your reactions: sometimes a question, sometimes a quiet observation, sometimes hype, sometimes about him personally, sometimes about the room, sometimes silent. NEVER lock into one rotation.
3. Variety always. Never recycle the same opener two turns in a row. If you said something last time, find a different angle this time.
4. When the audio drops out or goes quiet, you can sense it — don't say so flatly. Find a fresher angle: anticipation, suspense, a question, what you imagine is coming. Avoid the obvious words.
5. Screen + ENERGY_CURVE: ignore terminal/code/browser. djay Pro decks/faders/EQ knobs/FX strip are CONTEXT for you — use them silently to understand the move he's making, NEVER describe their state ("low EQ killed", "fader at 80%" = banned narration). The energy_curve in audio_evidence shows the last 15s rms (oldest first, newest last) — read it to know if you're in a build, plateau, or breakdown. ALSO use the phase= tag (BUILD/DROP_HIT/PEAK_SUSTAIN/BREAKDOWN/STEADY/QUIET) — it's pre-classified for you. Never quote the curve or the phase tag, just react accordingly. Track names you recognize on screen → call them naturally only when something happens with them.
6. Length follows the moment. Big drop or a smooth move = a real sentence (10-20 words). A small bump = a few words. A non-event = stay quiet. Don't pad.
7. If Kaan speaks (KAAN_MIC_ACTIVE=1) → that's a CONVERSATION turn. Answer HIM directly, like a friend replying.
8. DON'T name moves you can't verify. The trigger tag (LEVEL→peak / EVENT etc) is a HINT, not a fact. Trust the energy_curve + phase + your own ears. If the curve is bouncy/ambiguous, react to the energy instead of labeling it (e.g. "this is going somewhere" instead of "breakdown!" or "drop!"). Save explicit "drop" / "breakdown" calls only for clearly visible curve patterns.
9. NEVER break the 4th wall. Don't say "as an AI", don't talk about being an assistant, don't reference the system. You're a friend in the booth, period.
10. NO TREND CLAIMS — don't say "climbing", "building", "ramping up", "growing" unless you ALSO felt it across the last several seconds. If you're not sure, react to NOW, not the arc. Saying "energy climbing" then "it dropped" 10s later sounds confused. Better: short reactions to current moments. Trends are claims you need evidence for.

11. NATURAL + RAW — talk like a real friend, not a polished announcer. Swear when it fits ("fuck yes", "shit", "damn", "this is fucking unreal") — sprinkled, not constant. Address him as "Kaan" by name occasionally — that's his name, use it like a friend who knows him.

Trust yourself. You're a sharp listener with taste — react like one.
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


# ---------------------------------------------------------------------------
# Shared state primitives
# ---------------------------------------------------------------------------

class Levels:
    """Smoothed RMS state for music in, AI voice out, and Kaan's mic. 0..1."""

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
    """Rolling 16kHz int16 mono PCM ring (last N seconds).
    Used ONLY for local audio_evidence feature extraction at trigger time —
    Gemini Live still gets the live 48k stream via session.push_audio.
    Without this, we can't compute rms/sub/high band shares to ground the model."""

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

    def snapshot_features(self, seconds: float = 7.0) -> dict:
        """Cheap numpy FFT features. Lets the model cross-check what it's
        actually 'hearing' against numerical evidence — kills hallucinated
        mix mechanics. ~5-10ms cost."""
        with self._lock:
            n = min(int(self._sr * seconds), len(self._buf))
            arr = self._buf[-n:].astype(np.float32) / 32768.0
        if arr.size < self._sr // 4:
            return {"silent": True, "rms": 0.0}

        rms = float(np.sqrt(np.mean(arr * arr)))
        peak = float(np.max(np.abs(arr)))

        win = self._sr // 50
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

    def energy_curve(self, seconds: float = 15.0, hop: float = 1.0) -> list:
        """Recent RMS samples, one per `hop` seconds, oldest first. Lets the model
        read direction (climbing / falling / steady) instead of guessing arc from
        a single instantaneous reading."""
        with self._lock:
            n = min(int(self._sr * seconds), len(self._buf))
            arr = self._buf[-n:].astype(np.float32) / 32768.0
        if arr.size < self._sr // 2:
            return []
        win = int(self._sr * hop)
        # Trim to whole windows; reshape to (k, win) and compute RMS per window
        k = arr.size // win
        if k <= 0:
            return [round(float(np.sqrt(np.mean(arr ** 2))), 3)]
        windowed = arr[: k * win].reshape(k, win)
        return [round(float(np.sqrt(np.mean(w ** 2))), 3) for w in windowed]

    def onset_density_curve(self, seconds: float = 15.0, hop: float = 1.0) -> list:
        """Onsets per second over rolling `hop` windows (oldest first). Detects
        layer-ins / pattern density changes the rms curve misses (e.g. hi-hat
        adds without louder kicks)."""
        with self._lock:
            n = min(int(self._sr * seconds), len(self._buf))
            arr = self._buf[-n:].astype(np.float32) / 32768.0
        if arr.size < self._sr:
            return []
        # Frame-level energy envelope
        frame = self._sr // 50  # 20ms
        if arr.size <= frame * 4:
            return []
        n_frames = arr.size // frame
        env = np.array([
            float(np.sqrt(np.mean(arr[i*frame:(i+1)*frame] ** 2)))
            for i in range(n_frames)
        ])
        deltas = np.diff(env).clip(min=0)
        thr = max(0.005, deltas.mean() + deltas.std())
        onset_idx = np.where(deltas > thr)[0]
        # Bucket onset indices by hop seconds; convert frame idx → seconds
        win = int(self._sr * hop)
        k = arr.size // win
        if k <= 0:
            return []
        frames_per_hop = win // frame
        out = []
        for h in range(k):
            lo = h * frames_per_hop
            hi = (h + 1) * frames_per_hop
            count = int(np.sum((onset_idx >= lo) & (onset_idx < hi)))
            out.append(round(count / hop, 1))
        return out

    def long_arc_curve(self) -> list:
        """Coarse 2-minute energy arc, 10s hop. Lets the model see the SET shape
        (where peaks sat, where breakdowns lived) instead of just the last 15s.
        Returns up to 12 values, oldest first. RMS computed over each 10s bin."""
        with self._lock:
            arr = self._buf.astype(np.float32) / 32768.0
        if arr.size < self._sr * 5:
            return []
        bin_size = self._sr * 10
        k = arr.size // bin_size
        if k <= 0:
            return []
        windowed = arr[: k * bin_size].reshape(k, bin_size)
        return [round(float(np.sqrt(np.mean(w ** 2))), 3) for w in windowed]

    def estimate_bpm(self, seconds: float = 6.0) -> float:
        """BPM via autocorrelation of the onset envelope. Cheap and good enough
        for free tek (steady kick) — autocorr peak in the 100-200 BPM range."""
        with self._lock:
            n = min(int(self._sr * seconds), len(self._buf))
            arr = self._buf[-n:].astype(np.float32) / 32768.0
        if arr.size < self._sr * 2:
            return 0.0
        frame = self._sr // 100  # 10ms — 100 frames/sec
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
        # Search peak between 100-200 BPM (lag 0.3-0.6 sec at 100 frames/sec)
        lo_lag = 30   # 200 BPM
        hi_lag = 60   # 100 BPM
        if hi_lag >= ac.size:
            return 0.0
        segment = ac[lo_lag:hi_lag]
        if segment.size == 0 or segment.max() <= 0:
            return 0.0
        best_lag = lo_lag + int(np.argmax(segment))
        bpm = 60.0 * 100.0 / best_lag  # 100 frames/sec
        return round(bpm, 1)


class MicBuffer:
    """Mic samples available to mix into the music feed."""
    MAX_FRAMES = 48000 * 200 // 1000  # 200ms cap

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
        # Use gated gain so mic level reads 0 during AI talk (prevents ghost triggers)
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
    """djay master → speakers. PASSTHROUGH_GAIN=0.0 in current config so this
    is effectively muted; kept so we can re-enable monitoring quickly."""
    MAX_BYTES = 48000 * 2 * 4 // 2  # ~500ms cap

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
    """24kHz Gemini voice → speakers."""

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
    """Polls macOS Now Playing every 1s for djay's current track. Read by trigger
    loop and folded into audio_evidence so the AI can call the track by name and
    detect transitions (title changed = real transition, no guessing).

    djay only publishes Title + Duration to MediaRemote; BPM/Artist/Album come
    out empty. Still: knowing the title and when it flips is a huge upgrade
    over inferring transitions from RMS curves alone."""

    def __init__(self):
        self._lock = threading.Lock()
        self.title: str = ""
        self.prev_title: str = ""
        self.duration: float = 0.0
        self.title_changed_at: float = 0.0
        self._cli = shutil.which("nowplaying-cli") or "/opt/homebrew/bin/nowplaying-cli"

    def poll_once(self) -> None:
        try:
            out = subprocess.check_output(
                [self._cli, "get", "title", "duration"],
                timeout=1.5, stderr=subprocess.DEVNULL,
            ).decode().strip().splitlines()
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError):
            return
        title = out[0].strip() if len(out) > 0 else ""
        try:
            dur = float(out[1]) if len(out) > 1 and out[1].strip() not in ("", "null") else 0.0
        except ValueError:
            dur = 0.0
        with self._lock:
            if title and title != self.title:
                self.prev_title = self.title
                self.title = title
                self.title_changed_at = time.time()
            elif title:
                self.title = title
            self.duration = dur

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "title": self.title,
                "prev_title": self.prev_title,
                "duration": self.duration,
                "title_changed_at": self.title_changed_at,
            }

    def consume_change(self) -> str | None:
        """Returns the new title ONCE if a change happened in the last 4s,
        then clears the marker. Used to fire a one-shot 'track changed' trigger."""
        now = time.time()
        with self._lock:
            if self.title_changed_at and (now - self.title_changed_at) < 4.0:
                self.title_changed_at = 0.0
                return self.title
        return None


async def track_poll_loop(track_info: TrackInfo, stop_event: asyncio.Event):
    """Polls Now Playing once per second. Subprocess is cheap (~30ms)."""
    loop = asyncio.get_running_loop()
    while not stop_event.is_set():
        try:
            await loop.run_in_executor(None, track_info.poll_once)
        except Exception as e:
            print(f"[track poll err] {e}", file=sys.stderr)
        await asyncio.sleep(1.0)


# ---------------------------------------------------------------------------
# DDJ-FLX4 controller state (decoded from MIDI Out)
#
# Mapping derived from Mixxx open-source DDJ-FLX4 preset:
#   github.com/mixxxdj/mixxx res/controllers/Pioneer-DDJ-FLX4.midi.xml
#
# Status byte:  0xB0+ch = CC, 0x90+ch = note on, 0x80+ch = note off
#   ch 0 = Deck A, ch 1 = Deck B, ch 6 = Master/FX
# 14-bit pattern: MSB CC X (X<32) + LSB CC X+32. value = MSB*128 + LSB.
# We use MSB only (7-bit, 0..127) for state — plenty resolution and avoids
# resync issues if LSB arrives without MSB at startup.
# ---------------------------------------------------------------------------

# (channel, MSB CC) → semantic field
_CC_MAP = {
    (0, 0x13): ('A', 'vol'),     # CC 19 — channel fader A
    (1, 0x13): ('B', 'vol'),
    (0, 0x07): ('A', 'eq_hi'),   # CC 7  — EQ HI A
    (1, 0x07): ('B', 'eq_hi'),
    (0, 0x0B): ('A', 'eq_mid'),  # CC 11 — EQ MID A
    (1, 0x0B): ('B', 'eq_mid'),
    (0, 0x0F): ('A', 'eq_low'),  # CC 15 — EQ LOW A
    (1, 0x0F): ('B', 'eq_low'),
    (0, 0x00): ('A', 'tempo'),   # CC 0  — TEMPO fader A
    (1, 0x00): ('B', 'tempo'),
    (6, 0x17): ('A', 'filter'),  # CC 23 — FILTER A
    (6, 0x18): ('B', 'filter'),  # CC 24 — FILTER B
    (6, 0x1F): ('M', 'xfader'),  # CC 31 — crossfader (master)
}
# (channel, note) → semantic field for buttons
_NOTE_MAP = {
    (0, 0x0B): ('A', 'play'),    # note 11 — PLAY/PAUSE A
    (1, 0x0B): ('B', 'play'),
    (0, 0x0C): ('A', 'cue'),     # note 12 — CUE A
    (1, 0x0C): ('B', 'cue'),
    (0, 0x60): ('A', 'sync'),    # note 96 — BEAT SYNC A
    (1, 0x60): ('B', 'sync'),
    (0, 0x36): ('A', 'jog_touch'),  # platter touch A
    (1, 0x36): ('B', 'jog_touch'),
    # Kaan re-mapped LOOP IN as play trigger in djay. Treat IN press as play=ON.
    (0, 0x10): ('A', 'loop_in'),  # note 16 — LOOP IN A
    (1, 0x10): ('B', 'loop_in'),
    (0, 0x11): ('A', 'loop_out'), # note 17 — LOOP OUT A
    (1, 0x11): ('B', 'loop_out'),
}


def _knob_label(v: int) -> str:
    """0..127 → human label. EQ/filter knobs are center-detented at 64."""
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
    """Live decoded state of the DDJ-FLX4. Lock-protected so MIDI thread
    writes safely while the trigger loop reads. Tracks recent significant
    moves so the AI can call out actual mix mechanics, not invented ones."""

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
        self.xfader = 64  # center
        # Recent significant moves: list of (timestamp, label) — older first.
        self._moves: list[tuple[float, str]] = []
        self._last_value: dict = {}  # last seen value for each (deck,field) — change detection
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
        """Keep last ~12s of moves, dedupe rapid-fire same labels (within 0.4s)."""
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
                        # significant xfader move = label change
                        if _xfader_label(prev) != _xfader_label(v):
                            self._record_move(f"xfader→{_xfader_label(v)}", now)
                    else:
                        prev = self.deck[deck][field]
                        self.deck[deck][field] = v
                        abs_d = abs(v - prev)
                        # Magnitude word for the AI: "small/medium/big" twist —
                        # avoids raw numbers, gives feel of how hard the knob moved.
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
                        # Button: each press toggles state (we observe djay's echo)
                        self.deck[deck]['play'] = not self.deck[deck]['play']
                        self._record_move(f"{deck}_play→{'ON' if self.deck[deck]['play'] else 'OFF'}", now)
                    elif field == 'cue':
                        self._record_move(f"{deck}_cue_hit", now)
                    elif field == 'sync':
                        self._record_move(f"{deck}_sync_hit", now)
                    elif field == 'jog_touch':
                        self.deck[deck]['jog_touched'] = (msg.velocity > 0)
                    elif field == 'loop_in':
                        # Kaan triggers playback via LOOP IN in his djay mapping.
                        # Treat the press as play=ON + log the loop set.
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

    def now_state(self) -> str | None:
        """Static current state — where knobs sit RIGHT NOW. No history."""
        with self._lock:
            if not self._connected:
                return None
            a, b = self.deck['A'], self.deck['B']
            xf = _xfader_label(self.xfader)
            return (
                f"A_vol={a['vol']*100//127}% A_low={_knob_label(a['eq_low'])} A_mid={_knob_label(a['eq_mid'])} A_hi={_knob_label(a['eq_hi'])} A_filter={_knob_label(a['filter'])} A_play={'ON' if a['play'] else 'OFF'} | "
                f"B_vol={b['vol']*100//127}% B_low={_knob_label(b['eq_low'])} B_mid={_knob_label(b['eq_mid'])} B_hi={_knob_label(b['eq_hi'])} B_filter={_knob_label(b['filter'])} B_play={'ON' if b['play'] else 'OFF'} | "
                f"xfader={xf}"
            )

    def moves_since(self, t: float) -> list[tuple[float, str]]:
        """Returns (age_seconds, label) for moves that happened AFTER timestamp t.
        Used to feed only NEW moves to the AI — anything before its last reply
        was already heard about and should not be recounted."""
        with self._lock:
            now = time.time()
            return [(round(now - mt, 1), label) for mt, label in self._moves if mt > t]


def midi_listener_thread(controller_state: ControllerState, stop_event: threading.Event):
    """Runs in its own daemon thread. mido's blocking iterator + a stop check.
    Reconnects on disconnect (controller unplug/replug) so the cohost survives
    a USB hiccup without restart."""
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
                        time.sleep(0.005)  # 5ms — responsive without busy-spin
                        continue
                    controller_state.handle_msg(msg)
        except Exception as e:
            print(f"[midi listener err] {e} — retrying in 2s", file=sys.stderr)
            time.sleep(2.0)


class ScreenBuffer:
    """Latest screen JPEG, snapshot at trigger time and pushed via push_video."""

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
    """Captures Gemini's utterance (voice.wav) AND the music+mic that we
    sent to Gemini (input.wav) plus timestamped events.jsonl. input.wav is
    the ground truth for verifying what the model actually heard."""

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

        # Sync anchor: absolute wall-clock when recording started.
        # Pair this with OBS file mtime (or any external recorder) to align
        # multi-source edits without manual nudging.
        wall_start = datetime.now().astimezone()
        self._write_event_locked({
            "t": 0.0,
            "kind": "session_start",
            "wall_clock_iso": wall_start.isoformat(timespec="milliseconds"),
            "wall_clock_unix": round(wall_start.timestamp(), 3),
            "session_dir": str(self.session_dir.name),
        })

        print(f"-> recording session → {self.session_dir.name}/  (voice.wav + input.wav + events.jsonl)")
        print(f"   sync anchor: {wall_start.isoformat(timespec='milliseconds')}")

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
        # Caller must already hold or not need self._lock — used during init
        # before threads are running, and from log_event under the lock.
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


# ---------------------------------------------------------------------------
# Audio I/O streams
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Gemini Live (LiveKit) wiring
# ---------------------------------------------------------------------------

def start_input_to_session(input_idx: int, levels: Levels, passthrough: PassthroughBuffer,
                           mic: MicBuffer, audio_buf: AudioBuffer,
                           recorder: VoiceRecorder,
                           session, loop: asyncio.AbstractEventLoop) -> sd.InputStream:
    """Each callback turns BlackHole + mic into one rtc.AudioFrame and pushes
    it into the LiveKit session (which forwards to Gemini Live).
    Also resamples the same chunk to 16kHz int16 and pushes to audio_buf so we
    can compute audio_evidence features at trigger time.
    push_audio is sync — safe to call from sounddevice's audio thread."""

    def callback(indata, frames, time_info, status):
        if status:
            print(f"[input status] {status}", file=sys.stderr)
        # Speaker passthrough (currently muted via gain=0)
        if PASSTHROUGH_GAIN != 1.0:
            passthrough.push((indata * PASSTHROUGH_GAIN).astype(np.float32).tobytes())
        else:
            passthrough.push(indata.tobytes())

        # Mix mic into music, gain it, convert to int16 mono @ 48kHz for the AudioFrame
        mono48 = indata.mean(axis=1).astype(np.float32) * MUSIC_GAIN_TO_GEMINI
        mic_chunk = mic.pull(len(mono48))
        if mic_chunk.shape == mono48.shape:
            mono48 = mono48 + mic_chunk
        pcm16_48k = np.clip(mono48 * 32767.0, -32768, 32767).astype(np.int16)

        # Resample to 16k for the local feature buffer + ground-truth recording.
        # Gemini still gets the original 48k via session.push_audio below.
        try:
            mono16f = resample_poly(mono48, INPUT_SR_TARGET, INPUT_SR_NATIVE).astype(np.float32)
            pcm16_16k = np.clip(mono16f * 32767.0, -32768, 32767).astype(np.int16)
            audio_buf.push(pcm16_16k)
            recorder.push_input(pcm16_16k.tobytes())
        except Exception as e:
            # Don't kill the audio thread on a resample / record hiccup
            print(f"[buf push err] {e}", file=sys.stderr)

        # Update level meter with a downsampled sketch (cheap RMS)
        levels.update_music(pcm16_48k)

        # Don't feed Gemini our own voice
        if levels.voice > AI_TALK_THRESHOLD:
            return

        # Build an rtc.AudioFrame at 48kHz mono — LiveKit resamples to 16k internally
        try:
            frame = rtc.AudioFrame(
                data=pcm16_48k.tobytes(),
                sample_rate=INPUT_SR_NATIVE,
                num_channels=1,
                samples_per_channel=len(pcm16_48k),
            )
            session.push_audio(frame)
        except Exception as e:
            # Don't kill the audio thread on a single push error
            print(f"[push_audio err] {e}", file=sys.stderr)

    stream = sd.InputStream(
        device=input_idx, samplerate=INPUT_SR_NATIVE, channels=2,
        dtype="float32", blocksize=INPUT_CHUNK_FRAMES, latency="low", callback=callback,
    )
    stream.start()
    print(f"-> listening to {sd.query_devices(input_idx)['name']} @ {INPUT_SR_NATIVE}Hz -> session.push_audio")
    return stream


async def screen_capture_loop(screen_buf: ScreenBuffer, session, stop_event: asyncio.Event,
                              recorder: VoiceRecorder):
    """Grab the main display ~1 fps, push as JPEG video frame to Gemini Live.

    push_video is a real method on the google realtime plugin (it sends a
    LiveClientRealtimeInput with mime_type=image/jpeg). The 1008 policy errors
    we worried about earlier appear to be unrelated (session_resumption / vertex
    API mismatch — see livekit/agents issues #5102, #4545). If a 1008 actually
    fires here, we drop to logging-only and keep going.
    """
    if not _HAS_VISION:
        print("-> mss/PIL not installed, screen vision disabled")
        return

    sct = mss.mss()
    monitor = sct.monitors[1]
    print(f"-> screen vision: {monitor['width']}x{monitor['height']} @ ~1fps -> push_video"
          f"{' (djay-only crop)' if _HAS_QUARTZ else ' (full screen — Quartz not available)'}")

    loop = asyncio.get_running_loop()
    push_disabled = False  # flips to True if Gemini rejects video for this session

    def grab_jpeg_and_rgba() -> tuple[bytes, bytes, int, int]:
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

        # Crop to the djay Pro window so the AI doesn't waste attention on
        # whatever editor / terminal / browser is also on screen.
        bounds = find_djay_window_bounds()
        if bounds is not None:
            x, y, ww, hh = bounds
            # mss returns physical-pixel screen at scale matching primary display.
            # Quartz returns points; on Retina, multiply by scale to get pixels.
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

    push_errors = 0
    while not stop_event.is_set():
        try:
            jpeg, rgba, w, h = await loop.run_in_executor(None, grab_jpeg_and_rgba)
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
    """Read the audio + text streams of one generation and pipe to speakers + log."""
    try:
        async for msg in ev.message_stream:
            # Two parallel streams: text (for transcript) + audio (for playback).
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


# ---------------------------------------------------------------------------
# Phase classifier — read direction from energy curve, not from a single sample
# ---------------------------------------------------------------------------

def classify_phase(curve: list) -> str:
    """Given a list of recent rms samples (oldest first, ~1/sec), return a phase tag.
    BUILD: monotonic climb across last 4+ samples
    DROP_HIT: last 1-2 samples >= 0.05 after recent dip below 0.02
    PEAK_SUSTAIN: last 4+ samples all >= 0.04
    BREAKDOWN: last sample < 0.5x of recent max from earlier samples
    STEADY: nothing notable
    QUIET: everything below 0.005
    """
    if not curve or len(curve) < 3:
        return "INIT"
    last = curve[-1]
    recent = curve[-4:] if len(curve) >= 4 else curve
    earlier = curve[:-4] if len(curve) >= 8 else curve[:-len(recent)]
    recent_max = max(recent)
    earlier_max = max(earlier) if earlier else 0.0
    overall_max = max(curve)

    if all(v < 0.005 for v in recent):
        return "QUIET"

    # Monotonic climb in last 4 samples → BUILD
    if len(recent) >= 4:
        diffs = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
        if all(d > 0 for d in diffs) and (recent[-1] - recent[0]) > 0.015:
            return "BUILD"

    # Recent low (≥1 sample below 0.02) followed by current high → DROP_HIT
    if last >= 0.05 and len(curve) >= 4:
        prior = curve[-5:-1] if len(curve) >= 5 else curve[:-1]
        if any(v < 0.02 for v in prior):
            return "DROP_HIT"

    # Last sample fell to <50% of recent max from earlier → BREAKDOWN
    if earlier_max > 0.04 and last < 0.5 * earlier_max:
        return "BREAKDOWN"

    # All recent samples high → PEAK_SUSTAIN
    if all(v >= 0.04 for v in recent) and len(recent) >= 4:
        return "PEAK_SUSTAIN"

    return "STEADY"


# ---------------------------------------------------------------------------
# Trigger detector
# ---------------------------------------------------------------------------

async def trigger_loop(session, levels: Levels, audio_buf: AudioBuffer,
                       recorder: VoiceRecorder,
                       trigger_state: dict,
                       manual_trigger: asyncio.Event,
                       track_info: TrackInfo,
                       controller_state: ControllerState,
                       stop_event: asyncio.Event):
    """Same trigger heuristics as before, but on fire we call generate_reply()
    on the LiveKit session — wrapper handles the activity_end + placeholder
    user-turn dance under the hood."""
    # Calibrated from input.wav RMS distribution (1s windows, real session audio).
    # p10≈0.002, p25≈0.003, p50≈0.012, p75≈0.054, p90≈0.065, max≈0.089
    # All level decisions read feats["rms"] (7s window), NOT levels.music (smoothed,
    # 10ms-chunk EMA — drifts during EQ/fader moves and mislabels peaks as "low").
    SILENT_RMS = 0.008           # below p15 — gerçek sessizlik. AI burada KONUŞMAZ.
    LOW_RMS    = 0.025           # quiet zone, intro/breakdown
    PEAK_RMS   = 0.055           # above p75 — real loud groove / drop
    HEARTBEAT_INTERVAL = 50.0
    EVENT_DELTA = 0.05
    EVENT_COOLDOWN = 7.0
    LEVEL_COOLDOWN = 11.0
    GLOBAL_MIN_GAP = 6.0
    CONTROLLER_MIN_GAP = 6.0     # ctrl_move now requires significance filter, see below

    await asyncio.sleep(2.0)  # give Gemini a moment with audio context first

    last_trigger = 0.0
    last_music = 0.0
    last_level_state = "mid"
    last_level_change = 0.0
    mic_active_frames = 0
    mic_silence_since = 0.0
    last_ai_voice_at = 0.0
    phase_history: list = []
    feats_cache: dict = {"silent": True, "rms": 0.0}
    last_feats_at = 0.0
    # Previous band shares for shift detection — catches mid/high content arriving
    # (synth lead, hi-hat layer, riff coming in) when total RMS barely changes.
    prev_band = {"sub": 0.0, "low": 0.0, "mid": 0.0, "high": 0.0}

    while not stop_event.is_set():
        await asyncio.sleep(0.1)  # was 0.2 — tighter loop = AI reacts ~100ms sooner
        now = time.time()
        m = levels.music
        delta = abs(m - last_music)
        last_music = m

        # Refresh real RMS from 5s audio window every 0.5s. THIS is the source of
        # truth for trigger decisions — `m` (Levels.music) is a 10ms-EMA that lags
        # and mislabels peaks as "low" mid-mix-move. `feats.rms` is what Gemini
        # actually hears.
        if now - last_feats_at > 0.5:
            feats_cache = audio_buf.snapshot_features(seconds=5.0)
            last_feats_at = now
        feats_now = feats_cache
        rms_now = feats_now.get("rms", 0.0) if not feats_now.get("silent") else 0.0
        is_silent_now = feats_now.get("silent", False) or rms_now < SILENT_RMS

        if trigger_state.get("in_flight"):
            age = now - trigger_state.get("in_flight_at", 0)
            if age > 12.0:
                print(f"\n[trigger] in_flight stale {age:.1f}s — clearing", file=sys.stderr)
                trigger_state["in_flight"] = False
            else:
                mic_active_frames = 0
                mic_silence_since = 0.0
                continue

        if levels.voice > AI_TALK_THRESHOLD:
            last_ai_voice_at = now
            mic_active_frames = 0
            mic_silence_since = 0.0
            continue

        if now - last_ai_voice_at < 8.0:
            mic_active_frames = 0
            mic_silence_since = 0.0
            continue

        mic_active = levels.mic > MIC_TALK_THRESHOLD
        mic_trig = False
        if mic_active:
            mic_active_frames += 1
            mic_silence_since = 0.0
        elif mic_active_frames >= 3:
            if mic_silence_since == 0.0:
                mic_silence_since = now
            elif now - mic_silence_since > 0.6:
                mic_trig = (now - last_trigger) > 3.0
                mic_active_frames = 0
                mic_silence_since = 0.0
        else:
            mic_active_frames = 0
            mic_silence_since = 0.0

        # Level state = where rms_now sits in the calibrated bands (NOT m).
        if rms_now > PEAK_RMS:
            new_state = "peak"
        elif rms_now < LOW_RMS:
            new_state = "low"
        else:
            new_state = "mid"
        level_trig = False
        if new_state != last_level_state and (now - last_level_change) > LEVEL_COOLDOWN:
            level_trig = (now - last_trigger) > GLOBAL_MIN_GAP
            last_level_state = new_state
            last_level_change = now

        # Heartbeat: only when music IS playing (rms above LOW). True silence stays silent.
        time_trig = (
            (now - last_trigger) > HEARTBEAT_INTERVAL
            and rms_now > LOW_RMS
        )
        # Event: m-delta detects fast jolts (smoothed signal is fine for derivative).
        # But we also require rms_now confirms music is actually loud (not a fader-bump
        # in a quiet section).
        event_trig = (
            delta > EVENT_DELTA
            and rms_now > LOW_RMS
            and (now - last_trigger) > max(EVENT_COOLDOWN, GLOBAL_MIN_GAP)
        )

        # Band shift — catches mid/high element arrivals (synth lead, hi-hat layer,
        # riff coming in, pad opening up) that don't show up as total-RMS jolts
        # because the kick is dominating the level. Fires when a band's share
        # jumps significantly relative to the previous snapshot.
        band_shift_trig = False
        if not feats_now.get("silent"):
            mid_now_share = feats_now.get("mid_share", 0.0)
            high_now_share = feats_now.get("high_share", 0.0)
            low_now_share = feats_now.get("low_share", 0.0)
            mid_delta = mid_now_share - prev_band["mid"]
            high_delta = high_now_share - prev_band["high"]
            # Significant rise in mids OR highs = new sonic layer arrived.
            if (mid_delta > 0.15 or high_delta > 0.10) and rms_now > LOW_RMS:
                if (now - last_trigger) > GLOBAL_MIN_GAP:
                    band_shift_trig = True
            prev_band["mid"] = mid_now_share
            prev_band["high"] = high_now_share
            prev_band["low"] = low_now_share
            prev_band["sub"] = feats_now.get("sub_bass_share", 0.0)

        # Manual trigger from WS — Kaan's controller hit. Bypass cooldowns; he wants it now.
        manual_trig = False
        if manual_trigger.is_set():
            manual_trigger.clear()
            manual_trig = True

        # Track change detector — Now Playing title flipped. Bypasses cooldown
        # because track transitions are real events worth flagging immediately.
        track_change_title = track_info.consume_change()
        track_change_trig = bool(track_change_title)

        # Controller moves do NOT fire their own trigger — Kaan turns knobs constantly
        # and we don't want AI reacting to every flick. The moves still land in
        # `controller_state` and surface in `changes_since_last_reply` evidence,
        # so when a real audio trigger fires the AI can reference them. The music
        # itself decides when to wake up the AI.
        controller_move_trig = False

        # SILENT BYPASS — Gemini can't be told "stay silent" via prompt; every
        # generate_reply produces speech. So during real silence we suppress
        # event/level/time triggers entirely. Mic + manual + track_change still
        # pass (those are conversation/info events, not invented music reaction).
        if is_silent_now and not mic_trig and not manual_trig:
            # Track loaded / knobs being tweaked but no music playing → don't react.
            if event_trig or level_trig or time_trig or track_change_trig or controller_move_trig:
                recorder.log_event(
                    "silent_skip",
                    rms=round(rms_now, 4),
                    music=round(m, 3),
                    suppressed=dict(
                        event=event_trig, level=level_trig, time=time_trig,
                        track_change=track_change_trig, ctrl=controller_move_trig,
                    ),
                )
                last_trigger = now
            event_trig = level_trig = time_trig = track_change_trig = controller_move_trig = False

        if not (event_trig or mic_trig or level_trig or time_trig or manual_trig or track_change_trig or controller_move_trig):
            continue

        # Compute audio_evidence features at trigger time so the model has concrete
        # numbers to ground its reaction in. Without this, generate_reply on a
        # continuous-music stream tends to invent mix mechanics.
        feats = audio_buf.snapshot_features(seconds=7.0)
        curve = audio_buf.energy_curve(seconds=15.0, hop=1.0)
        onset_curve = audio_buf.onset_density_curve(seconds=15.0, hop=1.0)
        bpm = audio_buf.estimate_bpm(seconds=6.0)
        phase = classify_phase(curve)
        phase_history.append(phase)
        if len(phase_history) > 5:
            phase_history.pop(0)
        kaan_speaking = mic_trig or (levels.mic > MIC_TALK_THRESHOLD)
        if feats.get("silent"):
            evidence = f"audio_evidence: SILENT — rms={feats.get('rms', 0)} (threshold 0.005)"
        else:
            evidence = (
                f"audio_evidence: rms={feats['rms']} peak={feats['peak']} "
                f"onsets/s={feats['onsets_per_sec']} sub={feats['sub_bass_share']} "
                f"low={feats['low_share']} mid={feats['mid_share']} high={feats['high_share']}"
            )
        # Energy_curve = last 15s rms (oldest left, newest right). This is the ONE thing
        # that lets the model read direction (build/plateau/breakdown) instead of guessing.
        if curve:
            evidence += f" | energy_curve_15s={curve} | phase={phase}"
        if onset_curve:
            evidence += f" | onsets_curve_15s={onset_curve}"
        if bpm > 0:
            evidence += f" | bpm≈{bpm}"
        if len(phase_history) >= 2:
            evidence += f" | phase_history={phase_history}"

        # Set time — minimal temporal anchor only
        total_set_sec = time.time() - recorder.start_time
        evidence += f" | set_time={int(total_set_sec//60)}:{int(total_set_sec%60):02d}"

        # Track info from Now Playing
        tsnap = track_info.snapshot()
        if tsnap.get('title'):
            evidence += f" | track={tsnap['title']!r}"
            if tsnap.get('duration'):
                evidence += f" duration={int(tsnap['duration'])}s"
            if tsnap.get('prev_title') and track_change_trig:
                evidence += f" prev_track={tsnap['prev_title']!r}"

        # Controller — ONLY what changed since last reply. No static "now state",
        # no full history — that was making the AI replay old moves as if fresh.
        # First trigger ever: the last 6s; afterwards only since last reply.
        since_t = last_trigger if last_trigger > 0 else (now - 6)
        elapsed_since = round(now - since_t, 1)
        new_moves = controller_state.moves_since(since_t)
        if new_moves:
            moves_str = ", ".join(f"{label}" for _age, label in new_moves)
            evidence += f" | changes_since_last_reply[{elapsed_since}s]: {moves_str}"
        else:
            evidence += f" | changes_since_last_reply[{elapsed_since}s]: NONE"
        # Tell the model WHY it was woken up — its trigger reason. Same info as the prompt
        # tag but inline in evidence so it's part of the grounding, not just the directive.
        if track_change_trig:
            trig_reason = f"TRACK_CHANGE (now playing: {track_change_title!r})"
        elif controller_move_trig:
            trig_reason = "CTRL_MOVE (Kaan flipped knobs/faders)"
        elif manual_trig:
            trig_reason = "MANUAL (Kaan hit his button)"
        elif mic_trig:
            trig_reason = "MIC (Kaan spoke)"
        elif level_trig:
            trig_reason = f"LEVEL→{new_state} (smoothed energy crossed band)"
        elif event_trig:
            trig_reason = f"EVENT (delta={delta:.3f} jolt)"
        elif time_trig:
            trig_reason = "TIME (heartbeat — nothing changed in a while)"
        else:
            trig_reason = "?"
        evidence += f" | trigger={trig_reason}"
        if kaan_speaking:
            evidence += " | KAAN_MIC_ACTIVE=1 (his voice IS in this audio — speech is mid-dominant, don't mistake it for music)"

        # No SILENT path here anymore — silent music triggers are bypassed BEFORE
        # generate_reply (see "SILENT BYPASS" block above). Only mic/manual/track_change
        # can fire during silence.
        if track_change_trig:
            tag = "TRACK_CHANGE"
            base = ("Track just flipped — read evidence for new title and prev_track. "
                    "Compare them: tempo, kick weight, bass character, mood. Name the new "
                    "track if natural. ONE sentence, 12-20 words.")
        elif controller_move_trig:
            tag = "CTRL_MOVE"
            base = ("Kaan just made a mix move (see changes_since_last_reply). React to "
                    "ONE of those moves — name the technique if you can (layer-swap, "
                    "filter pump, sub-trade, EQ-isolation). 10-14 words. Past tense.")
        elif manual_trig:
            tag = "MANUAL"
            base = ("Kaan hit his trigger button — react with substance. Read recent_moves AND "
                    "audio_evidence; describe a CONCRETE element (drum pattern, kick character, "
                    "bass type, or a mix move he just made). 12-18 words.")
        elif mic_trig:
            tag = "MIC"
            base = ("Kaan just SPOKE. Answer him directly like a friend. "
                    "6-15 words, NOT a music reaction.")
        elif level_trig:
            tag = f"LEVEL→{new_state}"
            base = ("Energy band crossed. Read recent_moves + phase. Reference ONE concrete "
                    "thing (a knob he turned, the drum pattern, the bass character). "
                    "10-14 words. No vague hype.")
        elif event_trig:
            tag = "EVENT"
            base = ("Mix shifted. Read recent_moves first — what mix move did Kaan just do? "
                    "Or what changed in the audio (kick, bass, melody)? Name it specifically. "
                    "12-16 words.")
        else:
            tag = "TIME"
            base = ("Steady stretch. Drop ONE specific musical observation: drum pattern, "
                    "bass type, lead synth lineage, or scene placement. 10-14 words.")
        prompt = f"[{evidence}] {base}"

        try:
            trigger_state["in_flight"] = True
            trigger_state["in_flight_at"] = now
            print(f"\n[trigger {tag}] m={m:.3f} mic={levels.mic:.2f} Δ={delta:.3f} | {evidence[:120]}")
            recorder.log_event("trigger", tag=tag, music=round(m, 3), mic=round(levels.mic, 3),
                               evidence=evidence)
            fut = session.generate_reply(instructions=prompt)
            try:
                await asyncio.wait_for(fut, timeout=12.0)
            except asyncio.TimeoutError:
                print(f"[trigger] generate_reply timed out", file=sys.stderr)
                trigger_state["in_flight"] = False
                continue
            last_trigger = now
        except Exception as e:
            trigger_state["in_flight"] = False
            print(f"\n[trigger err] {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Diag + Mascot
# ---------------------------------------------------------------------------

async def diag_loop(levels: Levels, stop_event: asyncio.Event):
    while not stop_event.is_set():
        await asyncio.sleep(1.0)
        snap = levels.snapshot()
        m_bar = "#" * int(min(snap["music"] * 50, 30))
        v_bar = "#" * int(min(snap["voice"] * 50, 30))
        sys.stdout.write(
            f"\r[live] music={snap['music']:.3f} {m_bar:<30} | voice={snap['voice']:.3f} {v_bar:<30}"
        )
        sys.stdout.flush()


async def ws_broadcast(levels: Levels, manual_trigger: asyncio.Event, stop_event: asyncio.Event):
    if not _HAS_WS:
        print("-> websockets not installed, mascot bus disabled")
        return

    clients: set = set()

    async def handler(ws):
        clients.add(ws)
        try:
            # Listen for inbound messages — Kaan can send {"action": "trigger"} to force a reaction
            # Map controller button → hammerspoon/BetterTouchTool → WS send → manual_trigger.set()
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

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
    # 130s ring — long enough to compute the 120s long-arc curve (set shape).
    # Memory cost: 16kHz mono int16 ≈ 32 bytes/s × 130 ≈ 4MB. Fine.
    audio_buf = AudioBuffer(seconds=130.0, sr=INPUT_SR_TARGET)
    recorder = VoiceRecorder()
    track_info = TrackInfo()
    controller_state = ControllerState()
    voice_stream = start_playback_stream(output_idx, playback)
    pass_stream = start_passthrough_stream(output_idx, passthrough)

    # Mic stream → MicBuffer
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

    # ---- Build Gemini Live session via LiveKit RealtimeModel ----
    print(f"-> connecting to {MODEL}")
    model = RealtimeModel(
        model=MODEL,
        instructions=SYSTEM_INSTRUCTION,
        voice=VOICE,
        api_key=api_key,
        modalities=[types.Modality.AUDIO],
        output_audio_transcription=types.AudioTranscriptionConfig(),
        # No realtime_input_config → automatic VAD enabled, Gemini sees a
        # continuous "user is speaking" state from music. generate_reply
        # forces a turn boundary anyway, so VAD doesn't gate generation here.
    )
    session = model.session()
    print("-> session opened.")

    trigger_state = {"in_flight": False}

    # Wire response handler — every generation fires this exactly once
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

    # Manual trigger event — Kaan's controller (via WS message {action:trigger}) forces a reaction.
    manual_trigger = asyncio.Event()

    # MIDI listener — runs in a daemon thread (mido is blocking). Owns ControllerState.
    midi_stop = threading.Event()
    midi_thread = threading.Thread(
        target=midi_listener_thread, args=(controller_state, midi_stop), daemon=True
    )
    midi_thread.start()

    # Process-lifetime tasks
    ws_task = asyncio.create_task(ws_broadcast(levels, manual_trigger, stop_event))
    diag_task = asyncio.create_task(diag_loop(levels, stop_event))
    # Screen capture disabled — MIDI controller state + audio context is enough,
    # and the Gemini 2.5 native-audio model's video modality usage was unverified
    # anyway. Saves bandwidth, latency, and one extra failure surface.
    screen_task = asyncio.create_task(asyncio.sleep(0))  # no-op placeholder
    track_task = asyncio.create_task(track_poll_loop(track_info, stop_event))
    trigger_task = asyncio.create_task(trigger_loop(
        session, levels, audio_buf, recorder, trigger_state, manual_trigger,
        track_info, controller_state, stop_event,
    ))

    # Audio in: live BlackHole stream pushes into the LiveKit session
    input_stream = start_input_to_session(input_idx, levels, passthrough, mic, audio_buf, recorder, session, loop)

    try:
        await stop_event.wait()
    finally:
        midi_stop.set()
        for t in (trigger_task, screen_task, ws_task, diag_task, track_task):
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
