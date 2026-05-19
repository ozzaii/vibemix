# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for vibemix.runtime tests.

Fakes for the LiveKit AgentSession + DJCoHostAgent (interface-level only —
coach_loop uses only ``agent.set_next_event`` + ``session.generate_reply``
+ ``handle.wait_for_playout``). Fake Levels + VoiceRecorder + Event for
deterministic mic-detection + event-fire scenarios.

MusicState fixtures use the real Phase 3 dataclass so the ``state._lock``
write inside coach_loop's mic-detection branch is exercised end-to-end
(no MagicMock substitution for state itself).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vibemix.state import MusicState


@pytest.fixture
def fake_handle():
    """SpeechHandle stub — ``wait_for_playout`` is an AsyncMock returning None."""
    handle = MagicMock()
    handle.wait_for_playout = AsyncMock(return_value=None)
    return handle


@pytest.fixture
def fake_session(fake_handle):
    """AgentSession stub — ``generate_reply`` returns a SpeechHandle stub."""
    s = MagicMock()
    s.generate_reply = MagicMock(return_value=fake_handle)
    return s


@pytest.fixture
def fake_agent():
    """DJCoHostAgent stub — ``set_next_event`` records the most recent ev.
    Plan 19-05: ``invalidate_cache`` is an AsyncMock so the cancel-and-refire
    branch can ``await agent.invalidate_cache()``."""
    a = MagicMock()
    a.set_next_event = MagicMock()
    a.invalidate_cache = AsyncMock(return_value=None)
    return a


@pytest.fixture
def fake_levels():
    """Levels stub — ``voice`` / ``mic`` are simple attributes the test sets
    per tick. snapshot() returns a dict shape matching the real Levels API."""
    lv = MagicMock()
    lv.voice = 0.0
    lv.mic = 0.0
    lv.music = 0.0
    lv.snapshot = MagicMock(return_value={"music": 0.0, "voice": 0.0, "mic": 0.0})
    return lv


@pytest.fixture
def fake_recorder():
    """VoiceRecorder stub — ``log_event`` records all kwargs for assertion."""
    r = MagicMock()
    r.log_event = MagicMock()
    return r


@pytest.fixture
def fake_event_detector():
    """EventDetector stub — ``detect`` returns None by default; tests set
    ``return_value`` or ``side_effect`` as needed."""
    ed = MagicMock()
    ed.detect = MagicMock(return_value=None)
    return ed


@pytest.fixture
def music_state():
    """Real MusicState dataclass — has a real threading.Lock so the
    ``with state._lock:`` write inside coach_loop's mic-detection branch
    exercises the real lock acquire/release path."""
    return MusicState()


@pytest.fixture
def fake_event(music_state):
    """A canonical TRACK_CHANGE Event referencing the real music_state."""
    from vibemix.state import Event

    return Event(type="TRACK_CHANGE", state=music_state, extra={})


# ---------------------------------------------------------------------------
# Latency-stack fixtures (cancel_gate / ttft_meter / playback). The
# ack_bank fixture was retired alongside the placeholder OPUS clip
# system — see test_coach_cancel_wiring.py for the surviving wired path.
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_playback():
    """PlaybackQueue stub — push records bytes for assertion."""
    p = MagicMock()
    p.push = MagicMock()
    return p


@pytest.fixture
def fake_cancel_gate():
    """CancelGate stub — last_cancel_at=0.0 (no prior cancel); try_cancel
    returns False by default."""
    gate = MagicMock()
    gate.last_cancel_at = 0.0
    gate.try_cancel = MagicMock(return_value=False)
    return gate


@pytest.fixture
def fake_ttft_meter():
    """TTFTMeter stub — rolling_avg_ms returns the sentinel 1500.0 by default
    so any UI-side TTFT display has a deterministic value."""
    meter = MagicMock()
    meter.rolling_avg_ms = MagicMock(return_value=1500.0)
    return meter
