# SPDX-License-Identifier: Apache-2.0
"""AckBank — pre-recorded "yo!" / "nice!" / "yeah?" placeholder bank.

Phase 19 latency-stack v1, plan 04. Closes Pitfall 8 (ack rotation
collision) and respects Pitfall 1 (cancel-budget blowout, closed in
Plan 19-01) via the ``cancel_cooldown_active`` guard in ``should_fire``.

The bank ships 40 OPUS files split as 5 event-class buckets × 8 clips
each (CONTEXT D-08 + LATENCY-03 dispatch table):

    drop_hit       ← DROP, PHASE          (high-energy moments)
    track_change   ← TRACK_CHANGE         (transition acks)
    mix_move       ← MIX_MOVE             (filter / EQ acks)
    silence_break  ← KAAN_SPOKE, MANUAL   (re-engagement acks)
    generic_filler ← LAYER_ARRIVAL, HEARTBEAT  (steady-state texture)

The placeholder OPUS files are silent stubs; ``scripts/generate_placeholder_acks.py``
writes them. KAAN-ACTION before v2.0 RC: replace with Gemini Achird-voice TTS
recordings (see plan 19-04 ``<kaan_action_required>`` and
``.planning/NEXT-SESSION.md`` "P19-04 followup"). The runtime path
(loader + rotation + four-gate ``should_fire``) is fully testable on the
silent payload; only the file bytes change.

When fired (decision in ``should_fire``), ``pick_for_event`` returns the
decoded PCM ndarray ready for direct ``PlaybackQueue.push`` injection
(bypasses the LiveKit TTS path per LATENCY-01).

This module does NOT auto-load the bank on import — ``AckBank()`` must be
constructed explicitly. Tests of constants + bucket map remain cheap.

Runtime wiring into ``runtime/coach.py`` is a deferred follow-up — Plan 19-04
ships only the bank API; the coach loop calls ``should_fire`` /
``pick_for_event`` in a separate task tracked in NEXT-SESSION.md
("P19-04 followup: AckBank wiring in coach loop").
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

import av
import numpy as np

if TYPE_CHECKING:  # pragma: no cover — typing-only
    from vibemix.state.event import Event


# ---------------------------------------------------------------------------
# LOAD-BEARING constants — locked by tests/agent/test_ack_bank.py.
# ---------------------------------------------------------------------------

# Bucket order locked to scripts/generate_placeholder_acks.py BUCKETS.
ACK_BUCKETS: tuple[str, ...] = (
    "drop_hit",
    "track_change",
    "mix_move",
    "silence_break",
    "generic_filler",
)

# 40 / 5 — the loader asserts each bucket has exactly this many .opus files.
ACKS_PER_BUCKET: int = 8

# LATENCY-04 trigger gate: only fire an ack when the rolling TTFT average
# is degrading (Gemini is slow → user perceives a gap → bridge it).
ACK_TTFT_GATE_MS: float = 800.0

# LATENCY-05 minimum gap to the previous AI response (and to the previous
# ack itself) — prevents back-to-back acks and ack-on-the-heels-of-reply.
ACK_MIN_GAP_S: float = 0.4

# LATENCY-02 + Pitfall 8: per-bucket rotation deque depth. >ACKS_PER_BUCKET
# so the "available indices" set is never empty in steady state, but the
# LRU fallback path is unit-tested for the maxlen<=ACKS_PER_BUCKET edge.
ACK_ROTATION_MAXLEN: int = 10

# Default bank location — runtime ships <repo>/src/vibemix/audio/ack_bank/.
ACK_BANK_DIR: Path = Path(__file__).parent.parent / "audio" / "ack_bank"

# Decoded clip target rate — matches OUTPUT_SR / PlaybackQueue / sounddevice
# AI-voice output stream (vibemix.audio.constants.OUTPUT_SR = 24000).
_DECODE_RATE_HZ: int = 24000


# Event-type → bucket dispatch table. CONTEXT D-08 + plan 19-04 <interfaces>.
# All 8 known event types (Plan 19-01 reserved DROP slot included) MUST
# appear; the constructor's bucket loader and pick_for_event both depend
# on this completeness. Frozen via MappingProxyType to prevent runtime
# tampering — tampering would silently re-route acks to the wrong bucket.
BUCKET_FOR_EVENT: MappingProxyType = MappingProxyType(
    {
        # drop_hit — high-energy "yo!" / "bring it!"
        "DROP": "drop_hit",
        "PHASE": "drop_hit",
        # track_change — "fresh!" / "ohh, switching it"
        "TRACK_CHANGE": "track_change",
        # mix_move — "nice!" / "oh that's clean"
        "MIX_MOVE": "mix_move",
        # silence_break — "yeah?" / "what's up"
        "KAAN_SPOKE": "silence_break",
        "MANUAL": "silence_break",
        # generic_filler — "mhm" / "yeah this is groovy"
        "LAYER_ARRIVAL": "generic_filler",
        "HEARTBEAT": "generic_filler",
    }
)


class AckBankError(Exception):
    """Raised at AckBank() construction when the on-disk bank shape is wrong.

    Catch sites: the runtime caller (Plan 19-04 follow-up) treats this as a
    fatal init error — without a populated bank the ack path is dead, and
    silent fallback would mask a bundling regression (CONTEXT D-08
    AIza-key scan also runs over the same files at P21).
    """


class AckBank:
    """40-OPUS pre-recorded ack bank with per-bucket rotation + four-gate fire.

    Construction loads + decodes all 40 clips eagerly so subsequent
    ``pick_for_event`` calls are zero-I/O. Memory cost: 40 × ~5 KB int16
    PCM ≈ 200 KB resident — negligible.

    Thread-safety: NOT thread-safe. The coach loop is single-threaded
    asyncio; every call to ``pick_for_event`` and ``should_fire`` happens
    on the event loop. Same contract as ``runtime.cancel.CancelGate``.
    """

    def __init__(
        self,
        dir: Path = ACK_BANK_DIR,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self._dir = dir
        self._time_fn = time_fn
        self._clips: dict[str, list[np.ndarray]] = {}
        # Per-bucket rotation deque — maxlen=10 > ACKS_PER_BUCKET=8 so the
        # "available indices" set is non-empty in steady state.
        self._rot: dict[str, deque[int]] = {
            bucket: deque(maxlen=ACK_ROTATION_MAXLEN) for bucket in ACK_BUCKETS
        }
        self._load()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        for bucket in ACK_BUCKETS:
            bucket_dir = self._dir / bucket
            if not bucket_dir.is_dir():
                raise AckBankError(
                    f"bucket {bucket} directory not found at {bucket_dir}"
                )
            files = sorted(bucket_dir.glob("*.opus"))
            if len(files) != ACKS_PER_BUCKET:
                raise AckBankError(
                    f"bucket {bucket} has {len(files)} files, expected {ACKS_PER_BUCKET}"
                )
            self._clips[bucket] = [self._decode_opus(f) for f in files]

    @staticmethod
    def _decode_opus(path: Path) -> np.ndarray:
        """Decode an OPUS file to int16 mono 24kHz PCM (1-D ndarray).

        Uses av.AudioResampler so source-rate (typically 48kHz) is
        downsampled to ``_DECODE_RATE_HZ`` (24kHz) on the fly. The flush
        pass with ``resampler.resample(None)`` drains the resampler's
        internal buffer — without it the last few samples (~10ms worst
        case) get truncated, which would skew the duration assertion in
        ``test_decoded_pcm_is_int16_mono_24khz``.
        """
        chunks: list[np.ndarray] = []
        with av.open(str(path)) as container:
            stream = next(s for s in container.streams if s.type == "audio")
            resampler = av.AudioResampler(
                format="s16",
                layout="mono",
                rate=_DECODE_RATE_HZ,
            )
            for frame in container.decode(stream):
                for resampled in resampler.resample(frame):
                    chunks.append(resampled.to_ndarray())
            # Flush the resampler.
            for resampled in resampler.resample(None):
                chunks.append(resampled.to_ndarray())

        if not chunks:
            return np.zeros(0, dtype=np.int16)

        # Each chunk shape is (channels=1, samples) for mono s16. Flatten
        # to a 1-D array — PlaybackQueue.push consumes raw int16 bytes.
        pcm = np.concatenate(chunks, axis=-1).astype(np.int16, copy=False).flatten()
        return pcm

    # ------------------------------------------------------------------
    # Dispatch + pick
    # ------------------------------------------------------------------

    def bucket_for_event(self, ev_type: str) -> str:
        """Return the bucket name for an event type.

        Raises ``KeyError`` on unknown types — the caller (coach loop)
        should never request an ack for an event type outside
        ``BUCKET_FOR_EVENT``; if it does, that's a wiring bug worth
        surfacing loudly (vs. silently routing to a default bucket).
        """
        return BUCKET_FOR_EVENT[ev_type]

    def pick_for_event(self, ev: "Event") -> tuple[str, np.ndarray, int]:
        """Pick the next ack clip for an event.

        Returns ``(bucket_name, pcm_ndarray, sample_index)``. Picks an
        index that is NOT currently in the per-bucket rotation deque,
        appends the picked index to the deque (which is maxlen-bounded so
        the oldest auto-evicts), and returns the decoded PCM ready for
        ``PlaybackQueue.push``.

        Deterministic pick order: when multiple indices are "available"
        (not in the deque) the lowest-numbered one is picked. Tests can
        assert the exact sequence; deterministic > random for ack rotation
        because real human DJs benefit from a predictable rotation more
        than from per-call entropy.

        LRU fallback: when ALL ``ACKS_PER_BUCKET`` indices live in the
        deque (only possible when a future caller monkey-patches
        ``maxlen <= ACKS_PER_BUCKET``), pick the deque's oldest index
        (left-most = least-recently-used). Guards against IndexError on
        the empty-available-list edge.
        """
        bucket = self.bucket_for_event(ev.type)
        rot = self._rot[bucket]
        available = [i for i in range(ACKS_PER_BUCKET) if i not in rot]
        if available:
            idx = available[0]
        else:
            # LRU fallback — deque[0] is the oldest entry. Guarded by the
            # test_pick_for_event_lru_fallback_when_all_indices_in_deque case.
            idx = rot[0]
        rot.append(idx)
        return (bucket, self._clips[bucket][idx], idx)
