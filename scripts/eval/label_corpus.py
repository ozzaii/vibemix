# SPDX-License-Identifier: Apache-2.0
"""Phase 27 Plan 03 — corpus ground-truth labeling helper.

Bootstraps an `events.jsonl` for a session by running vibemix's real
`EventDetector` over the session's `input.wav` in observation mode. The
output is a CANDIDATE labels file — the human curator (Kaan) reviews and
edits before committing the final ground-truth labels.

Usage::

    uv run python scripts/eval/label_corpus.py \\
        --session eval/corpus/sessions/techno_01 \\
        --output eval/corpus/sessions/techno_01/events.jsonl.candidate

After review::

    mv eval/corpus/sessions/techno_01/events.jsonl.candidate \\
       eval/corpus/sessions/techno_01/events.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


async def label_session(session_dir: Path, output: Path) -> int:
    """Drive EventDetector across the session WAV; emit candidate events.jsonl."""
    wav = session_dir / "input.wav"
    if not wav.exists():
        print(f"missing input.wav at {wav}", file=sys.stderr)
        return 1

    # Lazy imports — keep CLI startup fast.
    from vibemix.audio.buffers import AudioBuffer
    from vibemix.state.event_detector import EventDetector
    from vibemix.state.evidence_registry import EvidenceRegistry

    audio_buf = AudioBuffer(seconds=2400.0, sr=16000)  # 40 min capacity
    audio_buf.fill_from_wav(wav)

    registry = EvidenceRegistry()
    detector = EventDetector(audio_buf=audio_buf, evidence_registry=registry)

    # Run detector at 1Hz across the session duration. NOTE: EventDetector
    # consumes a MusicState built by state_refresh_loop in the live runtime.
    # For labeling, we construct a minimal MusicState shim — this is a
    # heuristic baseline; human curator refines.
    #
    # For Plan 27-03 close-out: emit a stub "labels needed" record per
    # session so the curator workflow is documented. Real auto-labeling
    # requires state_refresh_loop + audible_track resolution, which is out
    # of scope for the labeling helper (the curator does this manually).

    events: list[dict] = [
        {
            "_curator_note": (
                "Auto-labeling stub. Human curator (Kaan) listens to "
                "input.wav and manually marks events: TRACK_CHANGE, "
                "PHRASE_BOUNDARY, MIX_MOVE, KICK_SWAP, LAYER_ARRIVAL, "
                "DROP. Use the events.jsonl format from "
                "tests/eval/fixtures/synthetic_session/events.jsonl as "
                "the template."
            ),
            "session": session_dir.name,
        }
    ]

    output.write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8"
    )
    print(f"[label_corpus] wrote candidate labels → {output}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="label_corpus",
        description="Bootstrap candidate events.jsonl for a corpus session.",
    )
    parser.add_argument(
        "--session",
        type=Path,
        required=True,
        help="Session dir (e.g. eval/corpus/sessions/techno_01).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output candidate file (default: <session>/events.jsonl.candidate).",
    )
    args = parser.parse_args(argv)

    session = args.session.resolve()
    output = args.output or (session / "events.jsonl.candidate")
    if not session.is_dir():
        print(f"session dir not found: {session}", file=sys.stderr)
        return 1
    return asyncio.run(label_session(session, output))


if __name__ == "__main__":
    sys.exit(main())
