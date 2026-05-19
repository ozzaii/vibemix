# SPDX-License-Identifier: Apache-2.0
"""AckBank — Phase 19 Plan 04 unit tests.

Pins the LATENCY-01..05 invariants for the 40-OPUS placeholder bank:
- 5 buckets × 8 clips per bucket = 40 files (LATENCY-03 dispatch table).
- Per-bucket rotation deque(maxlen=10) prevents in-window collisions
  (Pitfall 8, LATENCY-02).
- Bucket dispatch covers all 8 event types (KAAN_SPOKE / MANUAL /
  TRACK_CHANGE / PHASE / LAYER_ARRIVAL / MIX_MOVE / HEARTBEAT / DROP).

Task 2 (added below) extends this with the should_fire four-gate truth
table and the 60-fire-burst rotation invariant.

The fixture writes silent-OPUS placeholders into a tmp dir using the same
generator script the runtime ships, so tests are independent of whether
src/vibemix/audio/ack_bank/ has been pre-populated on the developer's
checkout.
"""

from __future__ import annotations

import importlib.util
import sys
from collections import deque
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Generator import — load scripts/generate_placeholder_acks.py by file path
# (scripts/ is not a package importable via `import scripts.foo`).
# ---------------------------------------------------------------------------

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "generate_placeholder_acks.py"


def _load_generator_module():
    spec = importlib.util.spec_from_file_location("_ack_gen", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_ack_gen"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gen_module():
    return _load_generator_module()


@pytest.fixture()
def populated_bank_dir(tmp_path: Path, gen_module) -> Path:
    """Write 40 silent-OPUS placeholders into tmp_path/ack_bank/<bucket>/<NN>.opus."""
    bank_root = tmp_path / "ack_bank"
    for bucket in gen_module.BUCKETS:
        (bank_root / bucket).mkdir(parents=True, exist_ok=True)
        for i in range(1, gen_module.PER_BUCKET + 1):
            gen_module.write_silent_opus(bank_root / bucket / f"{i:02d}.opus")
    return bank_root


# ---------------------------------------------------------------------------
# Constants + bucket-dispatch (no fixture needed)
# ---------------------------------------------------------------------------


def test_constants_locked():
    from vibemix.agent.ack_bank import (
        ACK_BUCKETS,
        ACK_MIN_GAP_S,
        ACK_ROTATION_MAXLEN,
        ACK_TTFT_GATE_MS,
        ACKS_PER_BUCKET,
    )

    assert ACK_BUCKETS == ("drop_hit", "track_change", "mix_move", "silence_break", "generic_filler")
    assert ACKS_PER_BUCKET == 8
    assert ACK_TTFT_GATE_MS == 800.0
    assert ACK_MIN_GAP_S == 0.4
    assert ACK_ROTATION_MAXLEN == 10


def test_bucket_for_event_complete_mapping():
    from vibemix.agent.ack_bank import BUCKET_FOR_EVENT

    expected_keys = {
        "KAAN_SPOKE",
        "MANUAL",
        "TRACK_CHANGE",
        "PHASE",
        "LAYER_ARRIVAL",
        "MIX_MOVE",
        "HEARTBEAT",
        "DROP",
    }
    assert set(BUCKET_FOR_EVENT.keys()) == expected_keys
    assert len(BUCKET_FOR_EVENT) == 8


def test_bucket_dispatch_pins_per_event():
    from vibemix.agent.ack_bank import BUCKET_FOR_EVENT

    assert BUCKET_FOR_EVENT["DROP"] == "drop_hit"
    assert BUCKET_FOR_EVENT["PHASE"] == "drop_hit"
    assert BUCKET_FOR_EVENT["TRACK_CHANGE"] == "track_change"
    assert BUCKET_FOR_EVENT["MIX_MOVE"] == "mix_move"
    assert BUCKET_FOR_EVENT["KAAN_SPOKE"] == "silence_break"
    assert BUCKET_FOR_EVENT["MANUAL"] == "silence_break"
    assert BUCKET_FOR_EVENT["LAYER_ARRIVAL"] == "generic_filler"
    assert BUCKET_FOR_EVENT["HEARTBEAT"] == "generic_filler"


# ---------------------------------------------------------------------------
# Constructor / loader
# ---------------------------------------------------------------------------


def test_constructor_succeeds_on_populated_dir(populated_bank_dir):
    from vibemix.agent.ack_bank import ACK_BUCKETS, AckBank

    bank = AckBank(dir=populated_bank_dir)
    for bucket in ACK_BUCKETS:
        assert len(bank._clips[bucket]) == 8


def test_constructor_raises_on_missing_bucket(populated_bank_dir):
    from vibemix.agent.ack_bank import AckBank, AckBankError

    target = populated_bank_dir / "drop_hit"
    for f in target.glob("*.opus"):
        f.unlink()
    target.rmdir()

    with pytest.raises(AckBankError) as excinfo:
        AckBank(dir=populated_bank_dir)
    assert "drop_hit" in str(excinfo.value)


def test_constructor_accepts_partial_bucket(populated_bank_dir):
    """2026-05-18 — bucket gate relaxed from strict ``== ACKS_PER_BUCKET``
    so partial fills (e.g. mix_move with 4/8 recorded clips) don't block
    the cohost from booting. Rotation in ``pick_for_event`` keys off
    ``len(self._clips[bucket])`` and cycles only the indices present.
    """
    from vibemix.agent.ack_bank import AckBank

    victim = sorted((populated_bank_dir / "mix_move").glob("*.opus"))[0]
    victim.unlink()

    bank = AckBank(dir=populated_bank_dir)
    assert len(bank._clips["mix_move"]) == 7
    # The remaining 4 buckets retain their full 8.
    for bucket in ("drop_hit", "track_change", "silence_break", "generic_filler"):
        assert len(bank._clips[bucket]) == 8


def test_constructor_raises_on_empty_bucket(populated_bank_dir):
    """A bucket directory that exists but has zero .opus files still raises —
    relaxed gate accepts partial, not empty (an empty bucket would
    crash pick_for_event with an IndexError).
    """
    from vibemix.agent.ack_bank import AckBank, AckBankError

    target = populated_bank_dir / "mix_move"
    for f in target.glob("*.opus"):
        f.unlink()

    with pytest.raises(AckBankError) as excinfo:
        AckBank(dir=populated_bank_dir)
    assert "mix_move" in str(excinfo.value)
    assert "no .opus files" in str(excinfo.value)


def test_decoded_pcm_is_int16_mono_24khz(populated_bank_dir):
    from vibemix.agent.ack_bank import ACK_BUCKETS, AckBank

    bank = AckBank(dir=populated_bank_dir)
    for bucket in ACK_BUCKETS:
        for clip in bank._clips[bucket]:
            assert clip.dtype == np.int16, f"{bucket} clip dtype {clip.dtype}"
            assert clip.ndim == 1, f"{bucket} clip ndim {clip.ndim}"
            # 100ms at 24kHz = 2400 samples (±10% per plan).
            # OPUS framing typically rounds up to 20ms boundaries → ~2556.
            assert 2160 <= clip.shape[0] <= 2640, (
                f"{bucket} clip length {clip.shape[0]} outside 2400 ±10%"
            )


def test_generator_idempotent(tmp_path, gen_module):
    """Running the silent-OPUS generator twice produces byte-identical files."""
    target = tmp_path / "01.opus"
    gen_module.write_silent_opus(target)
    first = target.read_bytes()

    gen_module.write_silent_opus(target)
    second = target.read_bytes()

    assert first == second
    assert len(first) > 0  # sanity: not empty


# ---------------------------------------------------------------------------
# Task 2: should_fire gate truth table + per-bucket rotation invariant
# ---------------------------------------------------------------------------


@pytest.fixture()
def bank_with_clock(populated_bank_dir):
    """AckBank with an injectable monotonic clock — tests advance time deterministically."""
    from vibemix.agent.ack_bank import AckBank

    clock = SimpleNamespace(now=100.0)
    bank = AckBank(dir=populated_bank_dir, time_fn=lambda: clock.now)
    return bank, clock


def test_should_fire_ttft_below_gate_returns_false(bank_with_clock):
    bank, _ = bank_with_clock
    decision, reason = bank.should_fire(
        rolling_ttft_avg_ms=750.0,
        last_ack_at=None,
        last_response_at=None,
        cancel_cooldown_active=False,
    )
    assert decision is False
    assert reason == "ttft_ok"


def test_should_fire_ttft_above_gate_no_other_blocks(bank_with_clock):
    bank, _ = bank_with_clock
    decision, reason = bank.should_fire(
        rolling_ttft_avg_ms=850.0,
        last_ack_at=None,
        last_response_at=None,
        cancel_cooldown_active=False,
    )
    assert decision is True
    assert reason == "fire"


def test_should_fire_cancel_cooldown_active_blocks(bank_with_clock):
    """Plan 19-01 cancel-cooldown cross-cut: no ack while CancelGate is mid-cooldown.

    Firing an ack on the heels of a cancel-and-refire would mean two distinct
    reactions back-to-back (the ack + the refire) — which is exactly the
    "AI slop" failure mode the latency stack exists to prevent.
    """
    bank, _ = bank_with_clock
    decision, reason = bank.should_fire(
        rolling_ttft_avg_ms=900.0,
        last_ack_at=None,
        last_response_at=None,
        cancel_cooldown_active=True,
    )
    assert decision is False
    assert reason == "cancel_cooldown"


def test_should_fire_min_gap_to_response_blocks(bank_with_clock):
    bank, clock = bank_with_clock
    decision, reason = bank.should_fire(
        rolling_ttft_avg_ms=900.0,
        last_ack_at=None,
        last_response_at=clock.now - 0.3,
        cancel_cooldown_active=False,
    )
    assert decision is False
    assert reason == "min_gap"


def test_should_fire_min_gap_to_response_passes_at_400ms(bank_with_clock):
    bank, clock = bank_with_clock
    decision, reason = bank.should_fire(
        rolling_ttft_avg_ms=900.0,
        last_ack_at=None,
        last_response_at=clock.now - 0.41,
        cancel_cooldown_active=False,
    )
    assert decision is True
    assert reason == "fire"


def test_should_fire_min_gap_to_ack_blocks(bank_with_clock):
    bank, clock = bank_with_clock
    decision, reason = bank.should_fire(
        rolling_ttft_avg_ms=900.0,
        last_ack_at=clock.now - 0.2,
        last_response_at=None,
        cancel_cooldown_active=False,
    )
    assert decision is False
    assert reason == "min_gap"


def test_should_fire_uses_injected_time_fn(populated_bank_dir):
    from vibemix.agent.ack_bank import AckBank

    bank = AckBank(dir=populated_bank_dir, time_fn=lambda: 100.0)
    # last_response_at = 99.7 → 0.3s gap → blocked.
    decision, reason = bank.should_fire(
        rolling_ttft_avg_ms=900.0,
        last_ack_at=None,
        last_response_at=99.7,
        cancel_cooldown_active=False,
    )
    assert decision is False
    assert reason == "min_gap"


def test_should_fire_suppress_short_circuits_all_gates(populated_bank_dir):
    """``suppress_fire=True`` short-circuits before any gate runs — used at
    runtime while bank clips don't match the active persona's language.
    """
    from vibemix.agent.ack_bank import AckBank

    bank = AckBank(dir=populated_bank_dir, suppress_fire=True)
    # Inputs that would otherwise produce ``(True, "fire")`` — suppressed regardless.
    decision, reason = bank.should_fire(
        rolling_ttft_avg_ms=900.0,
        last_ack_at=None,
        last_response_at=None,
        cancel_cooldown_active=False,
    )
    assert decision is False
    assert reason == "suppressed"


# ---------------------------------------------------------------------------
# Rotation invariant — Pitfall 8 closure
# ---------------------------------------------------------------------------


def _mock_event(ev_type: str):
    return MagicMock(type=ev_type)


def test_pick_for_event_60_fire_burst_no_collision(populated_bank_dir):
    """60 picks rotated through all 8 event types — within each bucket's
    pick sequence, no idx may repeat inside any window of
    ``min(ACKS_PER_BUCKET, ACK_ROTATION_MAXLEN) - 1`` consecutive picks.

    With ACKS_PER_BUCKET=8 < ACK_ROTATION_MAXLEN=10, the strongest provable
    rotation guarantee is "no repeat within the last 7 picks per bucket"
    (pigeonhole: 8 unique slots can't avoid repetition over a window of 10).
    The deque maxlen=10 is intentionally one rung above ACKS_PER_BUCKET so
    the "available indices" set is non-empty as long as the bucket isn't
    being hammered faster than its own clip count — typical real-session
    pacing keeps each bucket well under that ceiling.
    """
    from vibemix.agent.ack_bank import (
        ACK_ROTATION_MAXLEN,
        ACKS_PER_BUCKET,
        AckBank,
        BUCKET_FOR_EVENT,
    )

    bank = AckBank(dir=populated_bank_dir)
    event_types = list(BUCKET_FOR_EVENT.keys())
    no_collision_window = min(ACKS_PER_BUCKET, ACK_ROTATION_MAXLEN) - 1  # 7

    per_bucket_picks: dict[str, list[int]] = {b: [] for b in set(BUCKET_FOR_EVENT.values())}

    for i in range(60):
        ev_type = event_types[i % len(event_types)]
        bucket, _pcm, idx = bank.pick_for_event(_mock_event(ev_type))
        per_bucket_picks[bucket].append(idx)

    for bucket, seq in per_bucket_picks.items():
        for i in range(len(seq)):
            window = seq[max(0, i - no_collision_window) : i]
            assert seq[i] not in window, (
                f"bucket {bucket} pick #{i} idx={seq[i]} collides with window {window}"
            )


def test_pick_for_event_independent_per_bucket_rotation(populated_bank_dir):
    """drop_hit and generic_filler rotation deques do not cross-contaminate."""
    from vibemix.agent.ack_bank import AckBank

    bank = AckBank(dir=populated_bank_dir)
    drop_picks = []
    filler_picks = []
    for _ in range(8):
        _, _, di = bank.pick_for_event(_mock_event("DROP"))
        drop_picks.append(di)
        _, _, fi = bank.pick_for_event(_mock_event("HEARTBEAT"))
        filler_picks.append(fi)

    # Each bucket exhausts its 8 unique indices in 8 picks (deque maxlen > bucket size).
    assert sorted(drop_picks) == list(range(8))
    assert sorted(filler_picks) == list(range(8))
    assert list(bank._rot["drop_hit"]) == drop_picks
    assert list(bank._rot["generic_filler"]) == filler_picks


def test_pick_for_event_lru_fallback_when_all_indices_in_deque(populated_bank_dir):
    """When the deque holds all 8 indices (only possible with maxlen<=8), fall
    back to the LRU (oldest in deque) without raising."""
    from vibemix.agent.ack_bank import AckBank

    bank = AckBank(dir=populated_bank_dir)
    bank._rot["drop_hit"] = deque([0, 1, 2, 3, 4, 5, 6, 7], maxlen=8)

    bucket, pcm, idx = bank.pick_for_event(_mock_event("DROP"))
    assert bucket == "drop_hit"
    assert idx in range(8)
    # LRU = the oldest in the deque BEFORE the call: 0.
    assert idx == 0
    assert isinstance(pcm, np.ndarray)


def test_pick_for_event_appends_to_rotation_deque(populated_bank_dir):
    from vibemix.agent.ack_bank import AckBank

    bank = AckBank(dir=populated_bank_dir)
    assert len(bank._rot["drop_hit"]) == 0
    _, _, idx = bank.pick_for_event(_mock_event("DROP"))
    assert idx in bank._rot["drop_hit"]
    assert len(bank._rot["drop_hit"]) == 1
