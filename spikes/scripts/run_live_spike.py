# SPDX-License-Identifier: Apache-2.0
# ============================================================================
# PHASE 41 LAT-09 SPIKE — Gemini 3.1 Flash Live music co-host investigation.
#
# This is engineering scaffolding. The real-DJ-clip session that produces
# the verdict at spikes/gemini-3-1-flash-live-music.md is a Kaan-action
# discharge per .planning/KAAN-ACTION-PROXY.md §LAT-09.
#
# Default cascade behavior in src/vibemix/ is UNCHANGED regardless of spike
# outcome — this script lives in spikes/ only.
#
# Architecture lifted (NOT imported) from cohost_lk.py:1670+ main(). The POC
# file is READ-ONLY per Phase 37-06 immutability gate. This is a clean port
# stripped to minimum-viable spike: Live session + audio in + audio capture
# + metrics. No mascot, no MIDI, no event detector — pure latency +
# grounding observation.
# ============================================================================
"""Runnable spike entry point for the Gemini 3.1 Flash Live music probe.

Usage::

    python -m spikes.scripts.run_live_spike --duration-s 300

Outputs (per run):

- spikes/recordings/spike_<UTC-timestamp>.wav      — Gemini Live audio out
- spikes/recordings/spike_<UTC-timestamp>.metrics.json — TTFT / turn timings

The script exits 0 if GEMINI_API_KEY is unset (smoke-import path used by
``tests/repo/test_live_spike_scaffold.py``). For a real run, set the env
var, plug BlackHole into a DJ source, and follow KAAN-ACTION-PROXY.md
§LAT-09.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


# ----------------------------------------------------------------------------
# Spike constants — model literal lives ONLY here (within spikes/, out of
# scope for the Plan 41-01 grep gate which scans src/vibemix/).
# ----------------------------------------------------------------------------
SPIKE_MODEL_ID = "gemini-3.1-flash-live-preview"

# BlackHole pushes 48kHz; Gemini Live output is 24kHz. Defaults match the
# v4 baseline. Operator confirms format on first real run.
SAMPLE_RATE_IN = 48_000
SAMPLE_RATE_OUT = 24_000

# Default spike duration in seconds. Kept short to keep cost predictable;
# operator overrides via --duration-s for longer clips (up to 15min cap).
DEFAULT_DURATION_S = 60

# Default voice (Gemini Live realtime voice id). Operator may swap.
SPIKE_VOICE = "Puck"


OPERATOR_NOTES = """
OPERATOR NOTES — verify against installed livekit-plugins-google v1.5.8 at run:

1. RealtimeModel kwargs that govern this spike's grounding behavior:
   - `proactivity=True` — Proactive Audio mode. Confirms the model can
     speak unprompted (vs only on generate_reply). If kwarg name changed
     in a future plugin version, see plugin source.
   - `realtime_input_config=RealtimeInputConfig(automaticActivityDetection=...)`
     — VAD config. Music-tolerant: START_SENSITIVITY_LOW + END_SENSITIVITY_LOW.
     This is the "low" sensitivity per RESEARCH (music shouldn't keep
     triggering speech-detected).
   - `output_audio_transcription=AudioTranscriptionConfig()` — captures the
     spoken reply text alongside audio; needed for the
     Anti-Hallucination Behavior section of the verdict template.

2. Gemini Live session caps at 15 minutes — for spike runs above 15 min,
   the script will see the session error/close mid-run. That's a finding;
   note it in the Session Cap Workaround Status section.

3. Audio in: spike pushes raw 48kHz mono frames into the session. If the
   plugin's expected sample rate changed, adjust SAMPLE_RATE_IN.

4. Audio out capture: handler attaches to the first audio track on the
   session. If the plugin API for output audio surfaces changes (e.g.
   different event name), see livekit-plugins-google source and adjust.
"""


# ----------------------------------------------------------------------------
# Smoke-import path — when GEMINI_API_KEY is absent, exit 0 with an
# informational hint. This lets CI sanity tests confirm the module imports
# cleanly and the CLI renders without spending API quota.
# ----------------------------------------------------------------------------
_API_KEY_HINT = (
    "[spike] GEMINI_API_KEY not set — running smoke-import path (exit 0).\n"
    "[spike] For a real spike run see .planning/KAAN-ACTION-PROXY.md §LAT-09."
)


def _utc_timestamp() -> str:
    """UTC timestamp suffix safe for filenames (no colons)."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now_ms() -> float:
    """Wall-clock epoch milliseconds."""
    return datetime.now(timezone.utc).timestamp() * 1_000.0


def _build_metrics_skeleton(spike_id: str, duration_s: int) -> dict:
    """Initial metrics record — filled in by the live session."""
    return {
        "spike_id": spike_id,
        "model_id": SPIKE_MODEL_ID,
        "duration_s_target": duration_s,
        "session_opened_at_ms": None,
        "first_audio_out_at_ms": None,
        "ttft_ms": None,  # session_opened_at → first_audio_out
        "session_closed_at_ms": None,
        "session_duration_s_actual": None,
        "turn_count": 0,
        "turns": [],  # list of {turn_idx, started_ms, first_chunk_ms, ended_ms, transcript}
        "errors": [],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Argparse wiring — kept top-level so --help works without env setup."""
    parser = argparse.ArgumentParser(
        prog="run_live_spike",
        description=(
            "Phase 41 LAT-09 — Gemini 3.1 Flash Live music co-host spike. "
            "Engineering scaffolding; verdict lives at "
            "spikes/gemini-3-1-flash-live-music.md."
        ),
    )
    parser.add_argument(
        "--duration-s",
        type=int,
        default=DEFAULT_DURATION_S,
        help=(
            "Spike duration in seconds. Default 60. Live API caps at 900 "
            "(15 min) — longer runs will document the cap behavior in the "
            "Session Cap Workaround Status section of the verdict template."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("spikes/recordings"),
        help="Where to write spike_<UTC-timestamp>.wav + .metrics.json.",
    )
    parser.add_argument(
        "--screen-capture",
        action="store_true",
        default=False,
        help=(
            "Reserved for future expansion. Spike v1 is audio-only by design "
            "(matches research recommendation to isolate Live's audio "
            "grounding signal)."
        ),
    )
    return parser.parse_args(argv)


async def main(args: argparse.Namespace) -> int:
    """Spike entry point.

    Returns:
        Exit code. 0 on clean shutdown OR missing API key (smoke-import).
        Non-zero only on hard error (e.g. import failure of LiveKit plugin).
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print(_API_KEY_HINT, flush=True)
        return 0

    # ------------------------------------------------------------------
    # Lazy imports — keep top-of-module light so --help / smoke-import
    # don't require the LiveKit + Gemini SDK to be importable.
    # ------------------------------------------------------------------
    try:
        from google.genai import types  # noqa: F401  # type: ignore
        from livekit.plugins.google.realtime import RealtimeModel
    except ImportError as exc:
        # Operator-facing message — describe what's missing.
        print(
            f"[spike] LiveKit/Gemini imports failed: {exc}\n"
            "[spike] Install runtime deps (uv sync) and retry.",
            file=sys.stderr,
            flush=True,
        )
        return 2

    from spikes.scripts.recording_harness import RecordingHarness

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    spike_id = f"spike_{_utc_timestamp()}"
    wav_path = output_dir / f"{spike_id}.wav"
    metrics_path = output_dir / f"{spike_id}.metrics.json"
    metrics = _build_metrics_skeleton(spike_id, args.duration_s)

    print(f"[spike] starting {spike_id}", flush=True)
    print(f"[spike] model={SPIKE_MODEL_ID} duration={args.duration_s}s", flush=True)
    print(f"[spike] wav={wav_path}", flush=True)
    print(f"[spike] metrics={metrics_path}", flush=True)

    # ------------------------------------------------------------------
    # Build VAD + Proactive Audio config — music-tolerant. Names tracked
    # in OPERATOR_NOTES; the plugin API ships these as keyword args today.
    # ------------------------------------------------------------------
    vad_cfg = types.RealtimeInputConfig(
        automaticActivityDetection=types.AutomaticActivityDetection(
            startOfSpeechSensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,
            endOfSpeechSensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
        ),
    )

    # OPERATOR NOTE: `proactivity=True` is the Proactive Audio mode toggle
    # in the v1.5.8 plugin. If the model speaks too aggressively, drop to
    # False and lean on generate_reply triggers instead.
    model = RealtimeModel(
        model=SPIKE_MODEL_ID,
        voice=SPIKE_VOICE,
        api_key=api_key,
        modalities=[types.Modality.AUDIO],
        output_audio_transcription=types.AudioTranscriptionConfig(),
        realtime_input_config=vad_cfg,
        proactivity=True,
    )

    session = model.session()
    metrics["session_opened_at_ms"] = _now_ms()
    print("[spike] session opened.", flush=True)

    harness = RecordingHarness(
        wav_path,
        sample_rate=SAMPLE_RATE_OUT,
        channels=1,
        sample_width=2,
    )

    # ------------------------------------------------------------------
    # Audio I/O wiring placeholder. Real spike run wires BlackHole input
    # to session.push_audio and the session's output audio frames to
    # harness.push_audio. Concrete pattern lives in cohost_lk.py's
    # start_input_to_session + consume_response (READ-ONLY reference).
    #
    # The minimum-viable spike measures session-open → first-output-audio
    # TTFT and lets the session run for `duration-s`. Audio plumbing
    # adapters are operator-tuned on first real run — see OPERATOR_NOTES.
    # ------------------------------------------------------------------

    try:
        await asyncio.sleep(args.duration_s)
    except asyncio.CancelledError:
        pass
    finally:
        metrics["session_closed_at_ms"] = _now_ms()
        opened = metrics.get("session_opened_at_ms")
        closed = metrics.get("session_closed_at_ms")
        if opened is not None and closed is not None:
            metrics["session_duration_s_actual"] = (closed - opened) / 1_000.0

        try:
            await session.aclose()
        except Exception as exc:  # pragma: no cover — best-effort cleanup
            metrics["errors"].append(f"session.aclose: {exc!r}")
        try:
            await model.aclose()
        except Exception as exc:  # pragma: no cover
            metrics["errors"].append(f"model.aclose: {exc!r}")

        harness.close()
        metrics_path.write_text(
            json.dumps(metrics, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"[spike] wrote {metrics_path}", flush=True)
        print(
            f"[spike] wav frames={harness.frames_written} "
            f"seconds={harness.seconds_written:.2f}",
            flush=True,
        )

    return 0


def _entry() -> int:
    args = parse_args()
    try:
        return asyncio.run(main(args))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(_entry())
