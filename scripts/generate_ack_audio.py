# SPDX-License-Identifier: Apache-2.0
"""Phase 27 Plan 08 / LATENCY-15 — offline Achird-voice TTS batch render for AckBank.

Replaces ``scripts/generate_placeholder_acks.py``'s silent-OPUS placeholders
with REAL Gemini 3.1 Flash TTS Achird-voice audio. Reads
``assets/ack_bank/manifest.json`` (40 entries: 5 buckets × 8 ids), invokes
the Gemini TTS API once per entry, encodes the returned PCM as OPUS-in-OGG
via PyAV, and writes to ``src/vibemix/audio/ack_bank/<bucket>/<id>.opus``.

Idempotent: by default skips entries whose .opus file already exists. Pass
``--force`` to regenerate everything.

Pitfall LATENCY-15 (CRITICAL):
    - NEVER echo the API key to stdout/stderr/disk.
    - NEVER write a JSON manifest with response metadata (would leak request
      bodies that contain the key in repr-form).
    - Status logging is one line per file: ``OK <bucket>/<id>.opus (<n> bytes)``.
    - The API key flows .env → os.environ → genai.Client constructor; never
      crosses any other boundary.

Cost: 40 TTS calls × ~$0.005 each ≈ $0.20 per full regeneration. CI does
NOT re-run this script — CI only verifies the bytes via
``tests/runtime_closeouts/test_ack_bank_real_audio.py`` +
``tests/runtime_closeouts/test_ack_bank_aiza_scan.py``.

Usage::

    uv run python scripts/generate_ack_audio.py
    uv run python scripts/generate_ack_audio.py --force
    uv run python scripts/generate_ack_audio.py --dry-run
    uv run python scripts/generate_ack_audio.py --bucket drop_hit  # single bucket

After running: commit the regenerated .opus files. The REC-09 sidecar build
job (Plan 27-06) picks up the new bundle automatically.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Project root resolves from this script's location:
#   <repo>/scripts/generate_ack_audio.py → <repo>/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_MANIFEST = _PROJECT_ROOT / "assets" / "ack_bank" / "manifest.json"
_DEFAULT_OUTPUT = _PROJECT_ROOT / "src" / "vibemix" / "audio" / "ack_bank"

# Locked TTS model + voice. MUST match src/vibemix/agent/config.py so the
# offline Achird voice IS the same Achird voice the live runtime emits.
# Verified against cohost_v4.py:98 (TTS_MODEL) and config.py:26 (VOICE).
TTS_MODEL = "gemini-3.1-flash-tts-preview"
TTS_FALLBACK_MODEL = "gemini-2.5-flash-preview-tts"
VOICE = "Achird"

# Gemini TTS Achird voice returns PCM 24kHz s16le mono (per cohost_v4.py
# comment + google-genai 2.0.1 docs).
TTS_SAMPLE_RATE = 24000

# Retry budget per entry on transient failures.
MAX_RETRIES = 3
RETRY_BACKOFF_S = 2.0

# Inter-call delay to stay under Gemini TTS free-tier 10 req/min limit.
# 6.5s gap → ~9 req/min sustained, well under the cap.
INTER_CALL_DELAY_S = 6.5

# 429 backoff — Gemini API surfaces a retryDelay field in the error body;
# parse + sleep when present, otherwise fall back to fixed backoff.
RATE_LIMIT_FALLBACK_S = 60.0


def _load_manifest(path: Path) -> list[dict[str, str]]:
    """Load + validate the 40-entry manifest."""
    if not path.exists():
        raise FileNotFoundError(f"manifest not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"manifest must be a list; got {type(data).__name__}")
    expected_buckets = {
        "drop_hit",
        "track_change",
        "mix_move",
        "silence_break",
        "generic_filler",
    }
    seen_buckets: set[str] = set()
    for entry in data:
        for key in ("bucket", "id", "text"):
            if key not in entry:
                raise ValueError(f"manifest entry missing key {key!r}: {entry}")
        seen_buckets.add(entry["bucket"])
    missing = expected_buckets - seen_buckets
    if missing:
        raise ValueError(f"manifest missing expected buckets: {sorted(missing)}")
    extra = seen_buckets - expected_buckets
    if extra:
        raise ValueError(f"manifest has unexpected buckets: {sorted(extra)}")
    if len(data) != 40:
        raise ValueError(f"manifest must have exactly 40 entries; got {len(data)}")
    return data


def _encode_pcm_to_opus(pcm_bytes: bytes, sample_rate: int = TTS_SAMPLE_RATE) -> bytes:
    """Encode raw 16-bit PCM mono into OPUS-in-OGG bytes via PyAV.

    Returns the full container bytes ready to write to a .opus file. Mirrors
    the encoding pattern from scripts/generate_placeholder_acks.py but
    sources real PCM samples instead of zeros.
    """
    import io

    import av
    import numpy as np

    samples = np.frombuffer(pcm_bytes, dtype=np.int16)
    if samples.size == 0:
        raise ValueError("empty PCM bytes")

    out_io = io.BytesIO()
    container = av.open(out_io, "w", format="ogg")
    try:
        stream = container.add_stream("libopus", rate=sample_rate)
        stream.layout = "mono"
        frame = av.AudioFrame.from_ndarray(
            samples.reshape(1, -1), format="s16", layout="mono"
        )
        frame.rate = sample_rate
        frame.sample_rate = sample_rate
        for packet in stream.encode(frame):
            container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
    finally:
        container.close()
    return out_io.getvalue()


def _call_gemini_tts(
    client: Any,
    text: str,
    *,
    model: str = TTS_MODEL,
    voice: str = VOICE,
) -> bytes:
    """Invoke Gemini TTS once. Returns raw PCM 24kHz s16le mono bytes.

    Per the google-genai 2.0.1 surface used by tts_chain.py (verified):
    response.candidates[0].content.parts[0].inline_data.data is the audio.
    """
    # Lazy import keeps the script importable for --help / --dry-run without
    # google-genai installed.
    from google import genai
    from google.genai import types

    response = client.models.generate_content(
        model=model,
        contents=[text],
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            ),
        ),
    )

    # Defensive extraction — the API may add a wrapper layer in future
    # versions; the canonical path is candidates[0].content.parts[0].inline_data.data.
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        raise RuntimeError("no candidates in TTS response")
    parts = candidates[0].content.parts if candidates[0].content else []
    if not parts:
        raise RuntimeError("no parts in TTS response candidate")
    inline = getattr(parts[0], "inline_data", None)
    if inline is None or not getattr(inline, "data", None):
        raise RuntimeError("no inline_data in TTS response part")
    return inline.data


def _generate_one(
    client: Any,
    entry: dict[str, str],
    output_root: Path,
    *,
    force: bool,
    dry_run: bool,
) -> tuple[str, int]:
    """Generate one OPUS file per manifest entry. Returns (status, byte_count)."""
    bucket = entry["bucket"]
    entry_id = entry["id"]
    text = entry["text"]
    out_path = output_root / bucket / f"{entry_id}.opus"

    if dry_run:
        return ("dry-run", 0)
    if out_path.exists() and not force:
        return ("skip", out_path.stat().st_size)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    last_err: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            pcm = _call_gemini_tts(client, text)
            opus = _encode_pcm_to_opus(pcm)
            out_path.write_bytes(opus)
            return ("ok", len(opus))
        except Exception as e:  # noqa: BLE001 — defensive: any error retries
            last_err = e
            err_str = str(e)
            # Rate-limit backoff: parse retryDelay from the error body if
            # present; otherwise use the fallback timeout.
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                # Best-effort parse of "retryDelay': 'NNs'" from the dict-repr
                import re as _re

                m = _re.search(r"'retryDelay':\s*'(\d+)s'", err_str)
                wait_s = (
                    float(m.group(1)) + 1.0 if m else RATE_LIMIT_FALLBACK_S
                )
                time.sleep(wait_s)
            elif attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_S * attempt)
            continue
    # All retries exhausted — surface the LAST error as the status string.
    # Per Pitfall LATENCY-15: do NOT include response body / API key in the
    # error string. Pass through the exception class + its str() form only.
    err_msg = f"failed: {type(last_err).__name__}: {last_err}"
    return (err_msg, 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generate_ack_audio",
        description=(
            "Phase 27 Plan 08 / LATENCY-15: offline Achird TTS batch render "
            "for the AckBank. Replaces silent placeholders with real audio."
        ),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=_DEFAULT_MANIFEST,
        help="Path to the 40-entry manifest JSON (default: assets/ack_bank/manifest.json).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help="Output root for <bucket>/<id>.opus (default: src/vibemix/audio/ack_bank/).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even when target .opus file already exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate manifest + script wiring without invoking the API.",
    )
    parser.add_argument(
        "--bucket",
        type=str,
        default=None,
        help="Optionally restrict to a single bucket (drop_hit / track_change / mix_move / silence_break / generic_filler).",
    )
    args = parser.parse_args(argv)

    manifest = _load_manifest(args.manifest)
    if args.bucket:
        manifest = [e for e in manifest if e["bucket"] == args.bucket]
        if not manifest:
            print(f"no entries for bucket {args.bucket!r}", file=sys.stderr)
            return 1

    if args.dry_run:
        # Print one line per entry; don't load the API client.
        print(f"[dry-run] {len(manifest)} entries from {args.manifest}", file=sys.stderr)
        for entry in manifest:
            out = args.output / entry["bucket"] / f"{entry['id']}.opus"
            existing = "exists" if out.exists() else "missing"
            print(f"  [{existing}] {entry['bucket']}/{entry['id']}.opus  text={entry['text']!r}")
        return 0

    # Lazy load env + client — defer ImportError to here so --dry-run works
    # without google-genai installed.
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print(
            "[generate_ack_audio] FATAL: GEMINI_API_KEY not set in environment "
            "(load via .env or export). NEVER paste the key on the command line.",
            file=sys.stderr,
        )
        return 1

    from google import genai

    client = genai.Client(api_key=api_key)
    # Defensive: explicitly drop the api_key local from the python frame
    # before the per-entry loop runs. The client object holds the only
    # reference now.
    api_key = ""  # noqa: F841 — intentional shadow

    successes = 0
    failures = 0
    skips = 0
    api_call_count = 0
    for entry in manifest:
        # Inter-call rate-limit pacing — only wait when the previous step
        # actually hit the API (skip path doesn't count).
        if api_call_count > 0:
            time.sleep(INTER_CALL_DELAY_S)
        status, n_bytes = _generate_one(
            client, entry, args.output, force=args.force, dry_run=False
        )
        if status == "ok":
            print(
                f"OK {entry['bucket']}/{entry['id']}.opus ({n_bytes} bytes)",
                file=sys.stderr,
            )
            successes += 1
            api_call_count += 1
        elif status == "skip":
            print(
                f"SKIP {entry['bucket']}/{entry['id']}.opus (exists, {n_bytes} bytes; --force to regen)",
                file=sys.stderr,
            )
            skips += 1
        else:
            print(
                f"FAILED {entry['bucket']}/{entry['id']}.opus: {status}",
                file=sys.stderr,
            )
            failures += 1
            # Failed paths still consumed quota; count them.
            api_call_count += 1

    total = successes + failures + skips
    print(
        f"\n[generate_ack_audio] {successes} ok, {skips} skip, {failures} failed "
        f"out of {total} entries. "
        f"Run AIza scan via tests/runtime_closeouts/test_ack_bank_aiza_scan.py "
        f"before committing.",
        file=sys.stderr,
    )
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
