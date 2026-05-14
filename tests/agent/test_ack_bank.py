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


def test_constructor_raises_on_wrong_count(populated_bank_dir):
    from vibemix.agent.ack_bank import AckBank, AckBankError

    victim = sorted((populated_bank_dir / "mix_move").glob("*.opus"))[0]
    victim.unlink()

    with pytest.raises(AckBankError) as excinfo:
        AckBank(dir=populated_bank_dir)
    msg = str(excinfo.value)
    assert "has 7 files" in msg


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
# Task 2 — should_fire gate truth table + 60-fire rotation burst (added in Task 2 commit)
# ---------------------------------------------------------------------------
