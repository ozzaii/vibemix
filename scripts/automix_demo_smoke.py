# SPDX-License-Identifier: Apache-2.0
"""Manual demo: HEAR the AI call the drop — the owned-deck auto-mix reaction reel.

Composes the whole viral vertical end to end on real hardware:

  load 2 tracks -> -60 dB cues (audio/cues) -> transition plan (state/transition_clock)
  -> reaction reel (runtime/automix_demo) -> MiniDeck plays the mix, the crossfader
  sweeps by transition_progress, and each reaction beat PRINTS the instant it fires.

The fromDeck is seeked to ``--lead`` seconds before the drop so the demo is the
shareable ~20-30 s window around the transition, not the whole track. The incoming
deck is seeked to its cued start the moment the fade begins, then the equal-power
crossfader sweeps A -> B locked to the deck's real position (not wall-clock), so the
beats land ON the mix — "drop_incoming" -> "mixing_in" -> "landed_clean" (a hard cut
prints "slammed_cut" with no blend beat).

Routes to the system default output (Mac speakers — the FLX4 headphone jack is
broken) unless ``--device`` is given. With no track paths it synthesizes two tones
so it runs anywhere; ``--dry-run`` prints the plan + reel + schedule and opens NO
audio (the headless check).

Run:
    uv run python scripts/automix_demo_smoke.py TRACK_A.mp3 TRACK_B.mp3
    uv run python scripts/automix_demo_smoke.py --dry-run            # no audio, just the plan
    uv run python scripts/automix_demo_smoke.py                      # synth tones, audible
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

from vibemix.audio.cues import track_cues_from_audio
from vibemix.audio.miniplayer import MiniDeck
from vibemix.audio.voice_mix import mix_voice_over
from vibemix.runtime.automix_demo import build_automix_reel
from vibemix.runtime.drop_reaction import narrate_reel
from vibemix.state.transition_clock import TransitionMode, step_progress

_MODES = {m.name.lower(): m for m in TransitionMode}


def _prerender_voice(texts: list[str], *, target_sr: int) -> dict[str, np.ndarray]:
    """Synthesize each unique reaction line in the LIVE co-host voice, once, up front.

    Drives the exact local MOSS-only line voice via ``agent.line_voice`` and
    resamples each line to the deck rate so the audio
    callback can mix it sample-accurately. The reel is deterministic, so every line
    is known before audio starts — no mid-playback provider stall. Missing local
    model/runtime support degrades to ``{}`` (print-only), never crashes the demo.
    """
    import asyncio

    from vibemix.agent.line_voice import build_default_line_adapter, synthesize_line
    from vibemix.audio.resample import resample_audio

    async def _run() -> dict[str, np.ndarray]:
        adapter = build_default_line_adapter()
        out: dict[str, np.ndarray] = {}
        try:
            for text in texts:
                pcm, sr = await synthesize_line(adapter, text)
                if pcm.shape[0] == 0:
                    continue
                if sr != target_sr:
                    left = resample_audio(pcm[:, 0], source_sr=sr, target_sr=target_sr)
                    right = resample_audio(pcm[:, 1], source_sr=sr, target_sr=target_sr)
                    pcm = np.stack([left, right], axis=1).astype(np.float32)
                out[text] = pcm
        finally:
            aclose = getattr(adapter, "aclose", None)
            if aclose is not None:
                try:
                    await aclose()
                except Exception:  # pragma: no cover — best-effort cleanup
                    pass
        return out

    try:
        return asyncio.run(_run())
    except Exception as exc:  # no key / offline / plugin hiccup — print-only, never crash
        print(f"   [voice synth unavailable: {exc}] — printing reactions only")
        return {}


def _auto_anchor(path: str, labels: tuple[str, ...]) -> tuple[float | None, str | None, float]:
    """Auto-find a structural cue with vibemix's OWN detector (cue_detect.py).

    Runs the intro/build/breakdown/drop/outro structural analysis and returns the
    ``(start_s, label, confidence)`` of the best anchor matching ``labels`` (in
    priority order, highest-confidence within a label). Returns ``(None, ...)`` when
    the detector finds no structure — the honest, anti-hallucination empty case.
    """
    from vibemix.library.cue_detect import detect_cues

    try:
        anchors = detect_cues(Path(path))
    except Exception as exc:  # decode/ffmpeg/model hiccup — degrade, never crash the demo
        print(f"   [cue-detect skipped: {exc}]")
        return None, None, 0.0
    for want in labels:
        matches = [a for a in anchors if getattr(a.label, "value", a.label) == want]
        if matches:
            best = max(matches, key=lambda a: a.confidence)
            return best.start_s, want, best.confidence
    return None, None, 0.0


def _tone(freq_hz: float, *, seconds: float, sr: int, amplitude: float = 0.2) -> np.ndarray:
    """A stereo ``(N, 2)`` float32 sine slab — the no-files fallback track."""
    n = int(seconds * sr)
    t = np.arange(n, dtype=np.float64) / sr
    wave = (amplitude * np.sin(2.0 * np.pi * freq_hz * t)).astype(np.float32)
    return np.stack([wave, wave], axis=1)


def _load(path: str | None, *, fallback_hz: float, sr: int) -> tuple[np.ndarray, int]:
    """Load a track to ``(N, 2)`` float32 + its sample rate, or synth a tone."""
    if path is None:
        return _tone(fallback_hz, seconds=40.0, sr=sr), sr
    from vibemix.library.audio_decode import load_audio_stereo

    samples, file_sr = load_audio_stereo(path)
    return np.asarray(samples, dtype=np.float32), int(file_sr)


def _resolve_device(name_hint: str | None) -> tuple[int | None, int]:
    import sounddevice as sd

    if name_hint is not None:
        for i, dev in enumerate(sd.query_devices()):
            if name_hint.lower() in dev["name"].lower() and dev["max_output_channels"] > 0:
                return i, int(dev["max_output_channels"])
    default = sd.query_devices(kind="output")
    return None, min(2, int(default["max_output_channels"]) or 2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("track_a", nargs="?", default=None, help="fromDeck audio file")
    parser.add_argument("track_b", nargs="?", default=None, help="toDeck audio file")
    parser.add_argument("--mode", default="fixed_skip_silence", choices=sorted(_MODES))
    parser.add_argument("--outro-start", type=float, default=None,
                        help="seconds into track A where the DROP / mix-out is (forces "
                             "fade_at_outro_start so the AI calls THAT, not the track end)")
    parser.add_argument("--intro-start", type=float, default=None,
                        help="seconds into track B to cue the incoming mix-in point")
    parser.add_argument("--transition", type=float, default=8.0, help="fade seconds")
    parser.add_argument("--lead", type=float, default=8.0, help="seconds of run-up before the drop")
    parser.add_argument("--tail", type=float, default=4.0, help="seconds to play after landing")
    parser.add_argument("--arm-lead", type=float, default=2.0, help="anticipation window (s)")
    parser.add_argument("--device", default=None, help="output device name substring")
    parser.add_argument("--no-auto", action="store_true",
                        help="skip the structural cue detector (default: auto-find the drop)")
    parser.add_argument("--no-voice", action="store_true",
                        help="don't speak the reactions (print-only; default: AI calls the drop aloud)")
    parser.add_argument("--duck", type=float, default=0.45,
                        help="music gain while the co-host is talking (0..1, default 0.45)")
    parser.add_argument("--dry-run", action="store_true", help="print plan+reel, no audio")
    args = parser.parse_args()

    # Load the repo-root .env so the live voice chain sees GEMINI_API_KEY /
    # CARTESIA_API_KEY (the app does this in __main__; a standalone script must too).
    try:
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    except Exception:  # pragma: no cover — python-dotenv optional; voice degrades to print
        pass

    sr = 44_100
    src_a, sr_a = _load(args.track_a, fallback_hz=220.0, sr=sr)
    src_b, sr_b = _load(args.track_b, fallback_hz=330.0, sr=sr)
    sr = sr_a
    if sr_b != sr_a:
        print(f"!! sample-rate mismatch (A={sr_a}, B={sr_b}); playing at A's rate — pitch of B will drift")

    # Auto-find the REAL drop with vibemix's own structural detector (cue_detect),
    # so the AI calls the banger drop, not the track end — and we actually benefit
    # from the system's ability instead of hand-feeding a time. Manual --outro-start
    # / --intro-start override; --no-auto disables. A/ mix-OUT prefers the drop (else
    # outro); B/ mix-IN prefers the intro (else drop).
    outro_start = args.outro_start
    intro_start = args.intro_start
    if not args.no_auto:
        if args.track_a and outro_start is None:
            outro_start, lbl, conf = _auto_anchor(args.track_a, ("drop", "outro"))
            if outro_start is not None:
                print(f"-> 🎯 A: detected {lbl} @ {outro_start:.1f}s (conf {conf:.2f}) — mix-out / drop point")
        if args.track_b and intro_start is None:
            intro_start, lbl, conf = _auto_anchor(args.track_b, ("intro", "drop"))
            if intro_start is not None:
                print(f"-> 🎯 B: detected {lbl} @ {intro_start:.1f}s (conf {conf:.2f}) — mix-in point")

    from_cues = track_cues_from_audio(src_a, sr, outro_start_sec=outro_start)
    to_cues = track_cues_from_audio(src_b, sr, intro_start_sec=intro_start)
    # an outro_start (auto-detected or manual) forces the marker-respecting mode (else
    # skip-silence only mixes the track END, calling the outro not the banger drop).
    mode = (
        TransitionMode.FADE_AT_OUTRO_START if outro_start is not None
        else _MODES[args.mode]
    )
    reel = build_automix_reel(
        from_cues, to_cues, mode=mode,
        transition_sec=args.transition, arm_lead_sec=args.arm_lead,
    )
    plan = reel.plan
    # The persona turns each cue key into the line the co-host SPEAKS (compose-existing:
    # one deterministic reel -> reaction keys -> slop-clean lines -> the live voice).
    spoken = narrate_reel(reel)
    from_total = float(len(src_a))
    fade_begin_sec = plan.from_fade_begin * plan.from_duration_sec
    fade_end_sec = plan.from_fade_end * plan.from_duration_sec
    start_sec = max(0.0, fade_begin_sec - args.lead)

    print(f"-> from: {args.track_a or 'tone 220Hz'}  ({plan.from_duration_sec:.1f}s)")
    print(f"-> to  : {args.track_b or 'tone 330Hz'}  ({plan.to_duration_sec:.1f}s)")
    print(f"-> mode={mode.name.lower()} transition={args.transition}s  cut={plan.is_cut}")
    print(f"-> fade {fade_begin_sec:.1f}s .. {fade_end_sec:.1f}s  |  play window {start_sec:.1f}s .. {fade_end_sec + args.tail:.1f}s")
    print("-> reel (the AI calls the drop):")
    for b, sb in zip(reel.beats, spoken, strict=True):
        print(f"     t={b.t_sec:7.2f}s  pos={b.from_playposition:.3f}  [{b.cue}]  “{sb.text}”")

    if args.dry_run:
        print("-> dry-run: no audio opened.")
        return

    # Pre-render every reaction line in the LIVE co-host voice BEFORE audio opens —
    # the reel is deterministic, so no synth ever runs on the audio thread.
    voice_pcm: dict[str, np.ndarray] = {}
    if not args.no_voice:
        unique_texts = list(dict.fromkeys(sb.text for sb in spoken))
        print(f"-> 🔊 voicing {len(unique_texts)} line(s) in the live co-host voice (Achird)…")
        voice_pcm = _prerender_voice(unique_texts, target_sr=sr)
        print(f"-> voiced {len(voice_pcm)}/{len(unique_texts)} line(s)"
              + ("" if voice_pcm else " — the AI will print, not speak"))

    import sounddevice as sd

    device, out_channels = _resolve_device(args.device)
    info = sd.query_devices(device) if device is not None else sd.query_devices(kind="output")
    print(f"-> output: {info['name']} ({out_channels} ch) @ {sr} Hz")

    deck = MiniDeck(src_a, src_b, rate_a=1.0, rate_b=1.0, xfader=0.0)
    deck._frame_a = start_sec * sr  # seek the fromDeck into the run-up (script-level seek)
    to_start_frame = plan.to_start * plan.to_duration_sec * sr
    state = {"fade_started": False, "prev_progress": 0.0, "fired": set()}

    # Each beat's trigger sample on deck A + the finished voice buffer for its line
    # (None when that line didn't synth — it still prints, just doesn't speak).
    voice_plan = [
        (b.from_playposition * from_total, i, sb.text, voice_pcm.get(sb.text))
        for i, (b, sb) in enumerate(zip(reel.beats, spoken, strict=True))
    ]
    duck = float(args.duck)
    vstate: dict = {"active": None, "cursor": 0, "fired": set()}

    def _callback(outdata, frames, time_info, status):  # OS audio thread
        if status:
            print(f"   [stream status] {status}")
        a_before = deck.state().a_frame
        mix = deck.render_block(frames)
        # Latch a line the instant the deck reaches its beat; the voice ducks the mix
        # under it for the length of the line, then the music comes back (mix_voice_over).
        for trig, idx, _text, pcm in voice_plan:
            if idx not in vstate["fired"] and a_before >= trig:
                vstate["fired"].add(idx)
                if pcm is not None and pcm.shape[0] > 0:
                    vstate["active"] = pcm
                    vstate["cursor"] = 0
        active = vstate["active"]
        if active is not None:
            mix, cur = mix_voice_over(mix, active, vstate["cursor"], duck_gain=duck)
            vstate["cursor"] = cur
            if cur >= active.shape[0]:
                vstate["active"] = None
        outdata.fill(0.0)
        nch = outdata.shape[1]
        for c in range(0, nch, 2):
            outdata[:, c] = mix[:, 0]
            if c + 1 < nch:
                outdata[:, c + 1] = mix[:, 1]

    stream = sd.OutputStream(
        device=device, samplerate=sr, channels=out_channels,
        dtype="float32", blocksize=512, callback=_callback,
    )
    end_sec = fade_end_sec + args.tail
    with stream:
        while True:
            frac = deck.state().a_frame / from_total
            cur_sec = frac * plan.from_duration_sec
            if not state["fade_started"] and frac >= plan.from_fade_begin:
                deck._frame_b = to_start_frame  # cue the incoming deck to its start
                state["fade_started"] = True
            progress = step_progress(plan, frac, state["prev_progress"])
            state["prev_progress"] = progress
            deck.xfader = progress  # crossfade locked to the deck's real position
            for b, sb in zip(reel.beats, spoken, strict=True):
                if b.cue not in state["fired"] and frac >= b.from_playposition:
                    print(f"   >> {cur_sec:6.2f}s  [{b.cue}]  “{sb.text}”")
                    state["fired"].add(b.cue)
            if cur_sec >= end_sec or deck.state().a_frame >= from_total - 1:
                break
            time.sleep(0.02)
    print("-> done.")


if __name__ == "__main__":
    main()
