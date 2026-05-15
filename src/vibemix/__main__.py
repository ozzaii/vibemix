# SPDX-License-Identifier: Apache-2.0
"""vibemix — async main() orchestrator. Entry point for ``python -m vibemix``.

Verbatim port of ``cohost_v4.py:1925-2080`` with three structural adjustments
demanded by the new package layout:

1. **AudioMacOS as the firewall.** v4's inline ``sd.InputStream`` /
   ``start_input_to_session`` / ``start_playback_stream`` /
   ``start_passthrough_stream`` are replaced by ``AudioMacOS.open_capture``
   / ``open_voice_output`` / ``open_passthrough_output`` /
   ``open_mic_capture``. The v4 callback bodies live in 4 small factory
   functions in this module.
2. **Phase 2/3 backends.** ``ScreenMacOS`` / ``MidiMacOS`` / ``TrackMacOS``
   wrap the v4 inner instances (``screen_buf`` / ``controller_state`` /
   ``track_info``) and expose them as attributes for ``state_refresh_loop``
   to consume unchanged.
3. **All imports are ``vibemix.*``.** No reference to cohost_v4 at runtime.

Critical ordering invariants preserved from v4:
- ``session.output.audio = PlaybackQueueAudioOutput(...)`` is assigned BEFORE
  ``await session.start(agent)`` (v4:2030-2033).
- Two ``AudioBuffer`` instances: 140s gain-boosted state buffer +
  ``INVOKE_AUDIO_SECONDS + 5.0`` natural-level clean buffer (v4:1948-1949).
- MIDI listener thread spawned AFTER ``session.start`` (v4:2039-2043).
- Input stream opened AFTER the 6 asyncio tasks are created
  (state_refresh_loop must be running before audio starts pushing).
- SIGINT/SIGTERM handlers via ``loop.add_signal_handler``.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
import sys
import threading
from pathlib import Path

import httpx
import numpy as np
from dotenv import load_dotenv
from google import genai
from livekit.agents import AgentSession
from scipy.signal import resample_poly

from vibemix import __version__
from vibemix._main_helpers import apply_genre_env
from vibemix.agent import (
    INPUT_DEVICE,
    LLM_MODEL,
    MIC_DEVICE,
    OPENROUTER_TTS_MODEL,
    OUTPUT_DEVICE,
    SYSTEM_INSTRUCTION,
    TTS_FALLBACK_MODEL,
    TTS_MODEL,
    VOICE,
    DJCoHostAgent,
    PlaybackQueueAudioOutput,
    build_llm,
    build_proxy_genai_client,
    build_tts_chain,
    get_or_create_install_uuid,
    get_or_refresh_jwt,
)
from vibemix.agent.ack_bank import AckBank
from vibemix.agent.cache import GeminiContextCache
from vibemix.coach import (
    STRIPPED_RATE_THRESHOLD,
    CitationIpcShim,
    CitationLinter,
    StrippedRateTracker,
)
from vibemix.audio import (
    INPUT_CHUNK_FRAMES,
    INPUT_SR_NATIVE,
    INPUT_SR_TARGET,
    INVOKE_AUDIO_SECONDS,
    MIC_GAIN,
    MUSIC_GAIN_TO_GEMINI,
    OUTPUT_BLOCKSIZE,
    OUTPUT_SR,
    PASSTHROUGH_GAIN,
    VOICE_BLOCKSIZE,
    AudioBuffer,
    BufferRegistry,
    Levels,
    MicBuffer,
    PassthroughBuffer,
    PlaybackQueue,
    VoiceRecorder,
)
from vibemix.audio.recorder import sweep_crashed_sessions
from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.platform import AudioMacOS, MidiMacOS, ScreenMacOS, TrackMacOS
from vibemix.runtime import coach_loop, diag_loop, watch_parent, ws_broadcast
from vibemix.runtime.cancel import CancelGate
from vibemix.runtime.config_store import app_data_dir, load_config
from vibemix.runtime.recordings_index import run_retention_sweep
from vibemix.runtime.ttft import TTFTMeter
from vibemix.state import (
    EventDetector,
    EvidenceRegistry,
    MusicState,
    state_refresh_loop,
)

load_dotenv()


# =============================================================================
# Phase 15 — recordings root resolver
# =============================================================================


def _resolve_recordings_root() -> "os.PathLike[str]":
    """Return the OS-aware recordings root: ``app_data_dir() / "recordings"``.

    macOS:   ``~/Library/Application Support/vibemix/recordings``
    Windows: ``%APPDATA%/vibemix/recordings``
    Linux:   ``$XDG_CONFIG_HOME/vibemix/recordings`` (or ``~/.config/...``)

    Matches the Tauri assetProtocol scope set in ``tauri.conf.json5`` so
    ``<audio src="asset://...">`` resolves under the same path the sidecar
    writes to. Pure forwarder over ``app_data_dir`` from Phase 12
    ConfigStore — no caching, no mkdir (``VoiceRecorder.__init__`` mkdirs
    with mode=0o700 per RESEARCH Security V8).
    """
    return app_data_dir() / "recordings"


# =============================================================================
# CLI argument parsing
# =============================================================================


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI args. ``--version`` short-circuits via argparse's action.

    Phase 11 Wave 1 adds ``--wizard``: routes to a stub that exits cleanly
    after logging "wizard mode not yet implemented" to stderr. Wave 4 fills
    in the actual ``WizardLoop`` runtime; this wave only verifies the flag
    plumbing so the PyInstaller-built ``vibemix-core`` binary can be spawned
    by Tauri with ``--wizard`` and not crash.
    """
    parser = argparse.ArgumentParser(prog="vibemix", description="Open-source AI DJ co-host.")
    parser.add_argument("--version", action="version", version=f"vibemix {__version__}")
    parser.add_argument(
        "--wizard",
        action="store_true",
        help="Run first-run calibration wizard (Phase 11 — Wave 4 fills the runtime).",
    )
    # Phase 12 W2 — standalone session-loop runtime for sidecar-only IPC.
    # The full live runtime (audio + cascade) is the default (no flag) and
    # remains the post-wizard entry; ``--session`` is the structural surface
    # 12-03/12-04 glue against. Phase 12-04 unifies the two paths.
    parser.add_argument(
        "--session",
        action="store_true",
        help="Run the standalone session IPC loop (no cascade graph; Phase 12 W2).",
    )
    # Phase 25 Plan 25-03 — DEBRIEF architectural slot (DEBRIEF-01). v2.0
    # ships the entry-point + port constant + 3 IPC schema reservations
    # only; the v2.1 implementation drops in the chaptered TL;DR + drill
    # cards + clickable timeline behind this flag without touching the API
    # surface (flag name, port, message types are locked here).
    # ``nargs="?"`` lets the flag take an optional SESSION_DIR — bare
    # ``--debrief`` registers the smoke / port-reservation banner; with a
    # path it logs the reserved-session intent. Absence keeps ``None`` so
    # the dispatch in cli_entry can distinguish "no flag" from "empty arg".
    parser.add_argument(
        "--debrief",
        nargs="?",
        const="",
        default=None,
        metavar="SESSION_DIR",
        help=(
            "Run as post-session DEBRIEF sidecar — binds the DEBRIEF ws bus on "
            "127.0.0.1:8766, emits the 3 reserved DEBRIEF schemas only, never "
            "engages audio I/O or LiveKit. SESSION_DIR is the path to a "
            "closed recordings/* session; omit for a no-op smoke. v2.0 "
            "architectural slot — full UI feature ships v2.1 "
            "(DEBRIEF-01 + DEBRIEF-02)."
        ),
    )
    return parser.parse_args(argv)


# =============================================================================
# DEBRIEF sidecar — Phase 25 Plan 25-03 architectural slot
# =============================================================================


# Port reserved for the v2.1 DEBRIEF ws bus. Lives separate from the live
# mascot bus on 8765 (CONTEXT D-Area-1.1 / D-Area-1.3). v2.0 does NOT bind
# this port — the constant is a forward-compatibility reservation only. v2.1
# wires the real listener + 3-message emit path behind ``--debrief``.
DEBRIEF_PORT: int = 8766


def _run_debrief_sidecar(session_dir: str) -> None:
    """v2.0 DEBRIEF sidecar — banner log + port reservation only.

    DEBRIEF-01 reserves the surface: a separate sidecar process bound to
    ``127.0.0.1:DEBRIEF_PORT`` (avoids the live mascot bus on 8765). In
    v2.0 the sidecar emits a single ``logging.INFO`` banner line and
    returns — no audio I/O, no LiveKit, no session replay. v2.1 drops in
    the chaptered TL;DR + drill cards + clickable timeline behind this
    entry-point without changing the API surface.

    ``session_dir`` semantics:

      * ``""`` (sentinel): bare ``--debrief`` was passed — log the no-arg
        smoke banner; useful for verifying the flag plumbing without
        loading a real session.
      * non-empty path: log the path-reserved banner; v2.1 will validate
        the path against the ``recordings/`` allowlist + open the session.

    Port 8766 is documented as reserved but is NOT bound in v2.0. Binding
    it now would create a phantom listener with no handlers, surfacing in
    ``lsof`` as dead weight and confusing diagnostics.
    """
    import logging

    logger = logging.getLogger("vibemix.debrief")
    # Lazy basicConfig — only configure the root if the caller didn't.
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    if session_dir:
        logger.info(
            "debrief sidecar v2.0 architectural slot — session_dir=%r "
            "reserved for v2.1 implementation; port %d locked; no work "
            "performed.",
            session_dir,
            DEBRIEF_PORT,
        )
    else:
        logger.info(
            "debrief sidecar v2.0 architectural slot — no session_dir "
            "provided; port %d locked; no work performed.",
            DEBRIEF_PORT,
        )


# =============================================================================
# Wizard entrypoint — Phase 11 Wave 4 wires the real WizardLoop runtime.
# =============================================================================
#
# Wave 1 shipped a stub that printed "mode not yet implemented". Wave 4
# replaces it with ``vibemix.runtime.wizard.run_wizard`` which opens the
# WS bus, registers all 8 ipc.* handlers, drives the 3-step calibration
# flow + smoke test, and exits cleanly on ``ipc.wizard.done``.


# =============================================================================
# 4 callback factories — match v4 callback bodies verbatim
# =============================================================================


def _input_callback_factory(
    levels: Levels,
    passthrough: PassthroughBuffer,
    mic: MicBuffer,
    audio_buf: AudioBuffer,
    clean_audio_buf: AudioBuffer,
    recorder: VoiceRecorder,
):
    """Verbatim port of cohost_v4.py:912-945 input stream callback."""

    def callback(indata, frames, time_info, status):
        if status:
            print(f"[input status] {status}", file=sys.stderr)
        if PASSTHROUGH_GAIN != 1.0:
            passthrough.push((indata * PASSTHROUGH_GAIN).astype(np.float32).tobytes())
        else:
            passthrough.push(indata.tobytes())

        music48 = indata.mean(axis=1).astype(np.float32)
        # Mic is captured on a SEPARATE stream (mic_buf) for KAAN_SPOKE
        # detection via levels.mic; NEVER mix it into the music buffers —
        # otherwise Gemini hears Kaan's voice as "vocals" in the track.
        mic.pull(len(music48))  # keep cadence aligned, discard samples

        state48 = music48 * MUSIC_GAIN_TO_GEMINI
        state_pcm_48k = np.clip(state48 * 32767.0, -32768, 32767).astype(np.int16)
        clean48 = music48

        try:
            state16f = resample_poly(state48, INPUT_SR_TARGET, INPUT_SR_NATIVE).astype(np.float32)
            state_pcm_16k = np.clip(state16f * 32767.0, -32768, 32767).astype(np.int16)
            audio_buf.push(state_pcm_16k)
            recorder.push_input(state_pcm_16k.tobytes())

            clean16f = resample_poly(clean48, INPUT_SR_TARGET, INPUT_SR_NATIVE).astype(np.float32)
            clean_pcm_16k = np.clip(clean16f * 32767.0, -32768, 32767).astype(np.int16)
            clean_audio_buf.push(clean_pcm_16k)
        except Exception as e:
            print(f"[buf push err] {e}", file=sys.stderr)

        levels.update_music(state_pcm_48k)

    return callback


def _voice_callback_factory(playback: PlaybackQueue):
    """Verbatim port of cohost_v4.py:885-888 voice output callback."""

    def callback(outdata, frames, time_info, status):
        if status:
            print(f"[output status] {status}", file=sys.stderr)
        outdata[:] = playback.pull(frames * 2)

    return callback


def _passthrough_callback_factory(passthrough: PassthroughBuffer):
    """Verbatim port of cohost_v4.py:864-873 passthrough output callback."""
    bytes_per_frame = 2 * 4  # stereo float32 = 8 bytes/frame

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

    return callback


def _mic_callback_factory(mic: MicBuffer):
    """Verbatim port of cohost_v4.py:1965-1969 mic stream callback."""

    def callback(indata, frames, time_info, status):
        if status:
            print(f"[mic status] {status}", file=sys.stderr)
        mono = indata[:, 0] if indata.ndim > 1 else indata
        mic.push(mono.astype(np.float32))

    return callback


# =============================================================================
# main — async orchestrator
# =============================================================================


async def main() -> None:
    """Verbatim port of cohost_v4.py:1925-2080 with package-aware imports.

    Phase 5 adds env-driven mode dispatch:
      VIBEMIX_LLM_MODE       = 'direct' (default) | 'proxy'
      VIBEMIX_PROXY_BASE_URL = 'https://api.altidus.world' (default)
      VIBEMIX_CLIENT_VERSION = vibemix.__version__ (default)
    """
    # ----- Phase 5 mode dispatch -----
    mode = os.environ.get("VIBEMIX_LLM_MODE", "direct").lower()
    proxy_base_url = os.environ.get("VIBEMIX_PROXY_BASE_URL", "https://api.altidus.world")
    client_version = os.environ.get("VIBEMIX_CLIENT_VERSION", __version__)

    if mode not in ("direct", "proxy"):
        sys.exit(f"VIBEMIX_LLM_MODE must be 'direct' or 'proxy', got {mode!r}")

    api_key: str | None = None
    or_key: str | None = None
    jwt: str | None = None
    install_uuid: str | None = None

    if mode == "direct":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            sys.exit(
                "GEMINI_API_KEY not set (mode=direct). Set VIBEMIX_LLM_MODE=proxy to use the proxy."
            )
        or_key = os.environ.get("OPENROUTER_API_KEY")  # optional
    else:  # mode == "proxy"
        try:
            install_uuid = get_or_create_install_uuid()
            jwt = await get_or_refresh_jwt(install_uuid, proxy_base_url, client_version)
        except RuntimeError as e:
            sys.exit(f"Proxy mode setup failed: {e}. Check VIBEMIX_PROXY_BASE_URL and network.")
        except httpx.HTTPError as e:
            sys.exit(
                f"Proxy /register network error: {e.__class__.__name__}: {e}. "
                f"Check VIBEMIX_PROXY_BASE_URL and connectivity."
            )
        print(f"-> mode: proxy (install_uuid={install_uuid[:8]}..., jwt cached)")

    # ----- Phase 6 genre profile dispatch -----
    applied_genre = apply_genre_env()
    if applied_genre is None:
        print("-> genre profile: none (Phase 3 absolute-threshold fallback)")
    else:
        print(f"-> genre profile: {applied_genre}")

    # --- Phase 2 audio primitives ---
    import time as _time  # local import so the test suite can mock time.time without import-time side effects

    levels = Levels()
    playback = PlaybackQueue(levels)
    passthrough = PassthroughBuffer()
    mic = MicBuffer(gain=MIC_GAIN, levels=levels)
    audio_buf = AudioBuffer(seconds=140.0, sr=INPUT_SR_TARGET)
    clean_audio_buf = AudioBuffer(seconds=INVOKE_AUDIO_SECONDS + 5.0, sr=INPUT_SR_TARGET)

    # Phase 15 — boot-time crashed-session sweep. Walks recordings_root for
    # session.json files whose ended_at_iso is None AND mtime older than
    # 30s; marks them crashed=True. Best-effort: any IO error logs and
    # continues (POC parity — the sweep is a nice-to-have surface for the
    # Plan 15-04 browser UI, not a critical-path operation).
    recordings_root = _resolve_recordings_root()
    try:
        marked = sweep_crashed_sessions(recordings_root)
        if marked:
            print(f"-> recovered {len(marked)} crashed session(s): {', '.join(marked)}")
    except Exception as e:
        print(f"[sweep err] {e}", file=sys.stderr)

    # Phase 15 Plan 03 — boot-time retention sweep. Reads retention_days from
    # the persisted ConfigStore (Phase 12 W2) and prunes any session dir
    # older than that. ∞ sentinel (36500) short-circuits before scandir.
    # Best-effort: any failure logs and continues — the live session must
    # still start.
    try:
        cfg_for_sweep = load_config()
        result = run_retention_sweep(recordings_root, cfg_for_sweep.retention_days)
        if result.deleted_names:
            print(
                f"-> retention sweep (boot): pruned {len(result.deleted_names)} "
                f"session(s) ({result.bytes_pruned} bytes)"
            )
    except Exception as e:
        print(f"[retention sweep boot err] {e}", file=sys.stderr)

    recorder = VoiceRecorder(root=recordings_root)

    registry = BufferRegistry(
        audio=audio_buf,
        clean_audio=clean_audio_buf,
        mic=mic,
        passthrough=passthrough,
        playback=playback,
        levels=levels,
    )

    # --- Phase 3 sensing/state backends ---
    screen_macos = ScreenMacOS()
    midi_macos = MidiMacOS()
    track_macos = TrackMacOS()
    state = MusicState()
    state.set_start_at = _time.time()
    state.phase_started_at = _time.time()
    # Phase 17 Plan 05 — pass audio_buf to EventDetector so genre-chain
    # detectors that need raw samples (KickSwap, PhraseBoundary) can call
    # snapshot APIs on it. Default-None signature in EventDetector.__init__
    # keeps the no-arg form working for tests + coach.py callers.
    event_detector = EventDetector(audio_buf=audio_buf)

    # --- Audio I/O via AudioMacOS firewall ---
    audio_backend = AudioMacOS(registry, recorder)
    try:
        input_idx = audio_backend.find_device(INPUT_DEVICE, "input")
        output_idx = audio_backend.find_device(OUTPUT_DEVICE, "output")
    except RuntimeError as e:
        # Most common real-world fail: BlackHole 2ch isn't installed
        # (INPUT_DEVICE missing). Exit 3 is the sidecar's "audio-device-
        # missing" sentinel — the Tauri shell shows a setup banner with
        # the BlackHole install link rather than the generic crash UI.
        is_input_miss = INPUT_DEVICE in str(e)
        device_kind = "input" if is_input_miss else "output"
        device_name = INPUT_DEVICE if is_input_miss else OUTPUT_DEVICE
        print(
            f"[FATAL] required audio device missing: {device_name!r} ({device_kind})",
            file=sys.stderr,
            flush=True,
        )
        print(f"[FATAL] {e}", file=sys.stderr, flush=True)
        if is_input_miss:
            print(
                "[FATAL] install BlackHole 2ch via `brew install blackhole-2ch` "
                "or https://existential.audio/blackhole/",
                file=sys.stderr,
                flush=True,
            )
        sys.exit(3)

    stop_event = asyncio.Event()

    def handle_sigint():
        print("\n-> stopping...", flush=True)
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_sigint)

    voice_stream = audio_backend.open_voice_output(
        output_idx,
        sample_rate=OUTPUT_SR,
        block_size=VOICE_BLOCKSIZE,
        callback=_voice_callback_factory(playback),
    )
    print(f"-> AI voice -> {OUTPUT_DEVICE} @ {OUTPUT_SR}Hz")

    pass_stream = audio_backend.open_passthrough_output(
        output_idx,
        sample_rate=INPUT_SR_NATIVE,
        channels=2,
        block_size=OUTPUT_BLOCKSIZE,
        callback=_passthrough_callback_factory(passthrough),
    )
    print(f"-> djay passthrough -> {OUTPUT_DEVICE} @ {INPUT_SR_NATIVE}Hz")

    # Mic stream is optional — gracefully degrade if not found (v4:1962-1979)
    try:
        mic_idx = audio_backend.find_device(MIC_DEVICE, "input")
        mic_stream = audio_backend.open_mic_capture(
            mic_idx,
            sample_rate=INPUT_SR_NATIVE,
            block_size=INPUT_CHUNK_FRAMES,
            callback=_mic_callback_factory(mic),
        )
        print(f"-> mic on {MIC_DEVICE} @ {INPUT_SR_NATIVE}Hz")
    except Exception as e:
        print(f"-> mic disabled: {e}")
        mic_stream = None

    # --- LLM + TTS chain ---
    if mode == "direct":
        print("-> mode:  direct (GEMINI_API_KEY from .env)")
        print(f"-> brain: {LLM_MODEL} (thinking=minimal, temp=1.0)")
        genai_client = genai.Client(api_key=api_key)
        llm_inst = build_llm(api_key, mode="direct")
        tts_inst = build_tts_chain(
            gemini_api_key=api_key, openrouter_api_key=or_key or None, mode="direct"
        )
        if or_key:
            print(f"-> tts:   openrouter/{OPENROUTER_TTS_MODEL} (voice={VOICE}) [primary]")
        else:
            print(
                f"-> tts:   {TTS_MODEL} → {TTS_FALLBACK_MODEL} (voice={VOICE}) "
                "[no OPENROUTER_API_KEY in .env]"
            )
    else:  # mode == "proxy"
        print(f"-> brain: {LLM_MODEL} via proxy at {proxy_base_url}")
        genai_client = build_proxy_genai_client(jwt, proxy_base_url)
        llm_inst = build_llm(mode="proxy", proxy_base_url=proxy_base_url, jwt=jwt)
        tts_inst = build_tts_chain(mode="proxy", proxy_base_url=proxy_base_url, jwt=jwt)
        print(f"-> tts:   {OPENROUTER_TTS_MODEL} via proxy (voice={VOICE})")

    # ---- Plan 19-05 — Phase 19 latency-stack wiring ----
    # Construct the four primitives BEFORE the agent so we can pass
    # cache + ttft_meter into DJCoHostAgent and ack_bank + cancel_gate
    # + ttft_meter + playback into coach_loop.
    ttft_meter = TTFTMeter()
    ack_bank = AckBank()  # eager-loads 40 OPUS files; raises AckBankError on bad shape
    cancel_gate = CancelGate()
    cache: GeminiContextCache | None = GeminiContextCache(
        client=genai_client,
        system_instruction_body=SYSTEM_INSTRUCTION,
        model=LLM_MODEL,
    )
    try:
        await cache.create()
        print("-> cache: warm (Gemini context cache active)")
    except Exception as e:
        print(f"-> cache disabled: {e}", file=sys.stderr)
        cache = None  # graceful degradation — agent's None-cache branch handles it

    # ---- Plan 20-05 — Phase 20 anti-slop runtime wiring ----
    # Env-var gate: VIBEMIX_ANTI_SLOP defaults to "on". Set to "off" / "0" /
    # "false" to fall back to the legacy non-wired path (v4 byte-identical
    # legacy emit path inside DJCoHostAgent.llm_node). Default-on because
    # anti-slop IS the v2.0 product — Phase 20's central thesis.
    #
    # The EvidenceRegistry is constructed unconditionally so state_refresh_loop
    # always has a target for observation writes; only the linter + tracker
    # flip on/off via the env flag. Threading the registry into the agent
    # gives the linter a non-empty snapshot to validate against (without
    # this, every response strips with reason='no_citations').
    anti_slop_flag = os.environ.get("VIBEMIX_ANTI_SLOP", "on").strip().lower()
    anti_slop_enabled = anti_slop_flag not in ("off", "0", "false")
    print(
        "-> anti-slop: "
        f"{'on' if anti_slop_enabled else 'off (VIBEMIX_ANTI_SLOP)'}"
    )
    evidence_registry = EvidenceRegistry()
    citation_linter = CitationLinter() if anti_slop_enabled else None
    stripped_rate_tracker = StrippedRateTracker() if anti_slop_enabled else None
    # In-process IpcBus shim — Plan 20-04's coach_loop publish gate
    # duck-types against ``await ipc_bus.emit(dict)``. The shim buffers each
    # SessionCitation envelope into a bounded deque (no I/O). v2.x follow-up
    # multiplexes the buffer onto the mascot ws_broadcast clients (the WS
    # port is already owned by ws_broadcast — see citation_ipc_shim docstring
    # for the two-option v2.x wiring path).
    citation_shim: CitationIpcShim | None = (
        CitationIpcShim() if anti_slop_enabled else None
    )

    def _citation_telemetry() -> dict:
        """Closure invoked by ``coach_loop``'s publish gate every
        ``CITATION_PUBLISH_INTERVAL_S`` (2.0s). Reads fresh from the
        StrippedRateTracker + EvidenceRegistry on every call so the
        emitted SessionCitation envelope reflects the latest state.

        Returns the 4 keys ``SessionCitation.make()`` expects:

        - ``slop_ratio``: placeholder ``1 / (1 + mean)`` derived from the
          rolling-50-turn citation-count mean — drops toward 0 as Gemini
          emits more citations. The true slop metric (slop-vs-clean turn
          ratio) is a v2.x refinement once we have a stable definition;
          the placeholder is intentionally loud (1.0 at cold-start)
          rather than silent.
        - ``stripped_rate_15s``: tracker rate fresh per call. 0.0 when
          tracker is None (anti-slop disabled).
        - ``last_unverified_response``: ``None`` — no simple existing
          source. v2.x adds a 5-entry ring buffer of stripped/bypassed
          response texts so the Settings → Diagnostics surface can show
          the most recent unverified emission.
        - ``bypass_active``: non-destructive read — ``rate >
          STRIPPED_RATE_THRESHOLD``. We deliberately do NOT call
          ``tracker.should_bypass()`` here because that's the one-shot
          latch consumer; using it from telemetry would race the gate
          decision in the agent's llm_node strip path.

        T-20-05-03: the callable must not raise. ``coach_loop`` does
        wrap it in try/except, but staying clean keeps the publish path
        quiet.
        """
        reg_tel = evidence_registry.citation_telemetry()
        mean = reg_tel.get("mean", 0.0)
        slop_ratio = 1.0 / (1.0 + mean) if mean > 0 else 1.0
        rate = (
            stripped_rate_tracker.rate()
            if stripped_rate_tracker is not None
            else 0.0
        )
        bypass_active = (
            stripped_rate_tracker is not None and rate > STRIPPED_RATE_THRESHOLD
        )
        return {
            "slop_ratio": float(slop_ratio),
            "stripped_rate_15s": float(rate),
            "last_unverified_response": None,  # v2.x follow-up
            "bypass_active": bool(bypass_active),
        }

    agent = DJCoHostAgent(
        genai_client=genai_client,
        clean_audio_buf=clean_audio_buf,
        screen_buf=screen_macos,
        state=state,
        recorder=recorder,
        llm_inst=llm_inst,
        tts_inst=tts_inst,
        cache=cache,
        ttft_meter=ttft_meter,
        evidence_registry=evidence_registry,
        citation_linter=citation_linter,
        stripped_rate_tracker=stripped_rate_tracker,
        ack_bank=ack_bank,
        playback=playback,
    )

    # ── Plan 27-05 final-mile wiring (closes v2.0 register_library orphan, P48) ──
    library_cache = Path.home() / ".cache" / "vibemix" / "library.pkl"
    if library_cache.exists():
        lib = RekordboxLibrary()
        if lib.try_load_cache():
            registered = evidence_registry.register_library(lib)
            print(f"-> library: {registered} tracks registered for [track:<id>] citations")
        else:
            print("-> library: cache present but failed to load — skipping registration")
    else:
        print("-> library: no cache at ~/.cache/vibemix/library.pkl — citations limited to nowplaying-cli")

    session = AgentSession(llm=llm_inst, tts=tts_inst)
    session.output.audio = PlaybackQueueAudioOutput(playback, recorder, sample_rate=OUTPUT_SR)
    print(f"-> AgentSession headless (no Room); audio out → PlaybackQueue @ {OUTPUT_SR}Hz")

    await session.start(agent)
    print("-> agent started.")

    trigger_state: dict = {"in_flight": False}
    manual_trigger = asyncio.Event()

    # --- MIDI daemon thread (Phase 3) ---
    midi_stop = threading.Event()
    midi_thread = midi_macos.start_listener_thread(midi_stop)  # noqa: F841 — daemon thread

    # --- Asyncio tasks (6) ---
    ws_task = asyncio.create_task(ws_broadcast(levels, state, manual_trigger, stop_event))
    diag_task = asyncio.create_task(diag_loop(levels, state, stop_event))
    screen_task = asyncio.create_task(screen_macos.run_capture_loop(state, stop_event))
    track_task = asyncio.create_task(track_macos.run_poll_loop(stop_event))
    refresh_task = asyncio.create_task(
        state_refresh_loop(
            state,
            audio_buf,
            midi_macos.controller_state,
            track_macos.track_info,
            stop_event,
            evidence_registry=evidence_registry,
        )
    )
    coach_task = asyncio.create_task(
        coach_loop(
            session,
            agent,
            state,
            levels,
            event_detector,
            recorder,
            manual_trigger,
            trigger_state,
            stop_event,
            ack_bank=ack_bank,
            cancel_gate=cancel_gate,
            ttft_meter=ttft_meter,
            playback=playback,
            ipc_bus=citation_shim,
            citation_telemetry=_citation_telemetry if anti_slop_enabled else None,
        )
    )

    # Plan 19-05 — spawn cache refresh_loop AFTER session.start so the
    # cache lifecycle runs alongside the live event loop. Skipped when
    # cache is None (graceful degradation path).
    cache_refresh_task: asyncio.Task | None = None
    if cache is not None:
        cache_refresh_task = asyncio.create_task(cache.refresh_loop(stop_event))

    # Orphan-process self-shutdown — trips stop_event if Tauri parent
    # dies abruptly so the live runtime closes audio streams + session
    # cleanly instead of orphaning under launchd with port 8765 held.
    parent_watch_task = asyncio.create_task(watch_parent(stop_event))

    # --- Input stream — last because state must be ready ---
    input_stream = audio_backend.open_capture(
        input_idx,
        sample_rate=INPUT_SR_NATIVE,
        channels=2,
        block_size=INPUT_CHUNK_FRAMES,
        callback=_input_callback_factory(
            levels, passthrough, mic, audio_buf, clean_audio_buf, recorder
        ),
    )
    print(f"-> listening to {INPUT_DEVICE} @ {INPUT_SR_NATIVE}Hz -> audio_buf + clean_audio_buf")

    try:
        await stop_event.wait()
    finally:
        midi_stop.set()
        cleanup_tasks: list[asyncio.Task] = [
            coach_task,
            refresh_task,
            screen_task,
            ws_task,
            diag_task,
            track_task,
            parent_watch_task,
        ]
        if cache_refresh_task is not None:
            cleanup_tasks.append(cache_refresh_task)
        for t in cleanup_tasks:
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
        try:
            await session.aclose()
        except Exception as e:
            print(f"[close session err] {e}", file=sys.stderr)
        for stream in (voice_stream, pass_stream, input_stream):
            try:
                stream.stop()
                stream.close()
            except Exception as e:
                print(f"[close stream err] {e}", file=sys.stderr)
        if mic_stream is not None:
            try:
                mic_stream.stop()
                mic_stream.close()
            except Exception as e:
                print(f"[close mic err] {e}", file=sys.stderr)
        try:
            recorder.close()
        except Exception as e:
            print(f"[close recorder err] {e}", file=sys.stderr)
        # Phase 15 Plan 03 — session-close retention sweep trigger. Fires
        # AFTER recorder.close() so the just-finished session's session.json
        # is finalized (matches the data layout the sweep expects). Reads
        # retention_days fresh in case the user changed it mid-session.
        try:
            cfg_for_close_sweep = load_config()
            result_close = run_retention_sweep(
                recordings_root, cfg_for_close_sweep.retention_days
            )
            if result_close.deleted_names:
                print(
                    f"-> retention sweep (close): pruned "
                    f"{len(result_close.deleted_names)} session(s) "
                    f"({result_close.bytes_pruned} bytes)"
                )
        except Exception as e:
            print(f"[retention sweep close err] {e}", file=sys.stderr)
        print("-> bye")


# =============================================================================
# Entry point
# =============================================================================


def _enable_line_buffering() -> None:
    """Flip stdout/stderr to line-buffered so the Tauri rotating log captures
    diagnostic lines in real time instead of in 4–8 KB pipe-buffer batches.

    Why: CPython's default is line-buffered when isatty(), fully-buffered
    otherwise. The Tauri shell spawns the sidecar through a pipe so stderr
    falls into the fully-buffered branch — ``[FATAL] ws_bus port bind failed``
    can sit in the buffer until the process exits, which makes the watchdog's
    ``read_last_log_line`` race the FATAL marker and surface the wrong tail.

    Best-effort: if the streams have been replaced by something without
    ``reconfigure`` (frozen-app edge cases) or are already closed, we silently
    fall through. The log will lag in that case but nothing breaks.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


def cli_entry(argv: list[str] | None = None) -> None:
    """Synchronous CLI entry. Parses args (``--version`` short-circuits via
    argparse's ``action="version"``), then routes to one of three runtimes:

    * ``--wizard``           → Phase 11 W4 ``run_wizard`` (calibration flow)
    * ``--session``          → Phase 12 W2 ``run_session`` (sidecar-only;
                                no cascade graph — used by 12-03/12-04
                                glue tests + Tauri shell pre-cascade boot)
    * (default, both unset)  → Phase 5 ``main()`` (full live runtime —
                                cascade agent + audio I/O + ws_broadcast)

    The Tauri shell currently spawns ``vibemix --wizard`` on first run
    and ``vibemix`` (no flag — full runtime) thereafter. Phase 12-04
    will flip the post-wizard spawn to ``vibemix --session`` once the
    session loop owns the snapshot path the renderer drives off.
    """
    _enable_line_buffering()
    args = _parse_args(argv)
    try:
        if args.debrief is not None:
            # Phase 25 Plan 25-03 — DEBRIEF architectural slot. Dispatched
            # before --wizard / --session because it MUST NOT engage audio
            # I/O or LiveKit (v2.0 contract: log + return only). v2.1 will
            # wire the real session-replay loop here.
            _run_debrief_sidecar(session_dir=args.debrief)
            return
        if args.wizard:
            # Deferred import — the live-runtime path doesn't need the
            # wizard module loaded.
            from vibemix.runtime.wizard import run_wizard

            asyncio.run(run_wizard())
        elif args.session:
            # Phase 12 W2 — sidecar-only session loop. The full cascade
            # graph joins via 12-04; until then this runs the ipc.session.*
            # + ipc.settings.* surface standalone so the renderer can be
            # built + tested against a real Python WS bus.
            from vibemix.runtime.session_loop import run_session

            asyncio.run(run_session())
        else:
            asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    cli_entry()
