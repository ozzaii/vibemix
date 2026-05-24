# SPDX-License-Identifier: Apache-2.0
"""OSS-02 client-side proxy fallback matrix (Plan 69-03).

Pins the 4 trigger classes (5xx / timeout / connection_refused / bad_body) +
the 4xx fall-through boundary + the recovery flow + the direct-mode (BYO)
bypass. The DJCoHostAgent's three new helpers
(``_maybe_emit_proxy_unavailable`` / ``_maybe_emit_proxy_recovery`` /
``_check_proxy_health_canary``) are driven directly via a minimum-stub agent;
the underlying ``classify_proxy_error`` + ``probe_proxy_health`` surfaces
are exercised via httpx.MockTransport.

ALL tests carry ``@pytest.mark.integration`` per Plan 69-03 acceptance —
the default ``uv run pytest -q`` grid stays unaffected; the matrix lifts
``pytest -m integration`` from 16 (P67/P68 baseline) to ≥ 26.

Live discharge (real api.altidus.world induced-503 → recovery walk) rides
KAAN-ACTION-LEGAL.md §V7-PROXY synthetic-abuse snippet 5.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
from google.genai import errors as genai_errors
from livekit.agents import Agent

from vibemix.agent import DJCoHostAgent
from vibemix.agent.proxy_client import (
    ProxyUnavailable,
    classify_proxy_error,
    probe_proxy_health,
)
from vibemix.state import MusicState


# ---------- shared helpers ----------


def _make_5xx_exc(code: int = 503) -> genai_errors.ServerError:
    """Build a google.genai.errors.ServerError that mirrors the SDK's real
    5xx construction shape (executor verified at write time: ServerError
    sets .code on __init__; .code is what classify_proxy_error inspects).
    """
    resp = httpx.Response(status_code=code)
    return genai_errors.ServerError(
        code=code, response_json={"error": "unavailable"}, response=resp
    )


def _make_4xx_exc(code: int = 401) -> genai_errors.ClientError:
    """Build a google.genai.errors.ClientError for the 4xx anti-regression
    boundary. The SDK uses ClientError for 4xx by design.
    """
    resp = httpx.Response(status_code=code)
    return genai_errors.ClientError(
        code=code, response_json={"error": "client"}, response=resp
    )


class _FakeRecorder:
    """Minimum-stub recorder duck-typed for ``log_event(kind, **fields)``."""

    def __init__(self, session_dir: Path) -> None:
        self.session_dir = session_dir
        self.events: list[tuple[str, dict[str, Any]]] = []

    def log_event(self, kind: str, **fields: Any) -> None:
        self.events.append((kind, fields))

    def push_voice(self, pcm: bytes) -> None:  # pragma: no cover — unused
        pass


def _build_state() -> MusicState:
    s = MusicState()
    s.audible = True
    s.audible_deck = "A"
    s.audible_track = "Test - Track"
    s.audible_track_confidence = 0.8
    s.phase = "peak"
    s.rms = 0.05
    s.bpm = 128.0
    return s


def _build_agent(
    mocker, tmp_path: Path, *, mode: str = "proxy", monkeypatch=None
):
    """Build a minimum-stub DJCoHostAgent. The transcript_sink is a real
    deque so emissions are captured + asserted; mode toggles
    VIBEMIX_LLM_MODE (and thus _proxy_base_url resolution at __init__).
    """
    import collections

    if monkeypatch is not None:
        monkeypatch.setenv("VIBEMIX_LLM_MODE", mode)
        monkeypatch.setenv(
            "VIBEMIX_PROXY_BASE_URL", "https://example.invalid"
        )

    mocker.patch.object(Agent, "__init__", return_value=None)
    state = _build_state()
    recorder = _FakeRecorder(tmp_path)
    transcript_sink: collections.deque = collections.deque(maxlen=100)
    agent = DJCoHostAgent(
        genai_client=mocker.MagicMock(),
        clean_audio_buf=mocker.MagicMock(),
        screen_buf=mocker.MagicMock(),
        state=state,
        recorder=recorder,
        llm_inst=mocker.MagicMock(),
        tts_inst=mocker.MagicMock(),
        transcript_sink=transcript_sink,
    )
    return agent, transcript_sink, recorder


# ---------- classifier unit tests ----------


@pytest.mark.integration
@pytest.mark.parametrize("code", [500, 502, 503, 504])
def test_classify_proxy_error_5xx_returns_unavailable(code: int) -> None:
    """5xx (500 / 502 / 503 / 504) → ProxyUnavailable with reason == '5xx'."""
    exc = _make_5xx_exc(code=code)
    result = classify_proxy_error(exc)
    assert isinstance(result, ProxyUnavailable), f"expected ProxyUnavailable, got {result!r} for {code}"
    assert result.reason == "5xx", f"reason mismatch for {code}: {result.reason!r}"
    assert result.original is exc


@pytest.mark.integration
@pytest.mark.parametrize(
    "exc_factory",
    [
        lambda: httpx.TimeoutException("t"),
        lambda: httpx.ConnectTimeout("ct"),
        lambda: httpx.ReadTimeout("rt"),
        lambda: httpx.WriteTimeout("wt"),
        lambda: httpx.PoolTimeout("pt"),
    ],
)
def test_classify_proxy_error_timeout_returns_unavailable(exc_factory) -> None:
    """All httpx timeout subclasses → ProxyUnavailable with reason == 'timeout'.

    Critically: ConnectTimeout subclasses BOTH ConnectError AND TimeoutException;
    the classifier checks TimeoutException first so it gets the more-specific
    'timeout' tag rather than 'connection_refused'.
    """
    exc = exc_factory()
    result = classify_proxy_error(exc)
    assert isinstance(result, ProxyUnavailable)
    assert result.reason == "timeout", f"timeout reason mismatch: {result.reason!r}"


@pytest.mark.integration
def test_classify_proxy_error_connection_refused_returns_unavailable() -> None:
    """httpx.ConnectError → ProxyUnavailable with reason == 'connection_refused'."""
    exc = httpx.ConnectError("refused")
    result = classify_proxy_error(exc)
    assert isinstance(result, ProxyUnavailable)
    assert result.reason == "connection_refused"


@pytest.mark.integration
def test_classify_proxy_error_bad_body_returns_unavailable() -> None:
    """JSON decode error → ProxyUnavailable with reason == 'bad_body'."""
    try:
        json.loads("{not json")
    except json.JSONDecodeError as je:
        result = classify_proxy_error(je)
        assert isinstance(result, ProxyUnavailable)
        assert result.reason == "bad_body"
    else:  # pragma: no cover — defensive
        pytest.fail("json.loads should have raised JSONDecodeError")


@pytest.mark.integration
@pytest.mark.parametrize("code", [400, 401, 403, 404, 422, 429])
def test_classify_proxy_error_4xx_returns_none(code: int) -> None:
    """4xx (including 429) MUST NOT classify as unavailable — anti-regression
    test pins the 'do NOT conflate auth/quota with unavailable' boundary
    (T-69P03-01). 429 specifically already has its own per-error messaging
    path from v3.x SHIP-CUT and must not be conflated with the fallback.
    """
    exc = _make_4xx_exc(code=code)
    result = classify_proxy_error(exc)
    assert result is None, (
        f"4xx must NOT classify as ProxyUnavailable; got {result!r} for code {code}. "
        f"This is the anti-regression boundary — see Plan 69-03 / OSS-02."
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "exc",
    [
        ValueError("x"),
        RuntimeError("y"),
        KeyError("z"),
        AssertionError("a"),
        TypeError("t"),
    ],
)
def test_classify_proxy_error_random_exception_returns_none(exc: Exception) -> None:
    """Programming errors / non-network exceptions return None. KeyboardInterrupt
    + SystemExit are BaseException subclasses (not Exception) and would tear
    down the test runner if raised here; the classifier's signature
    ``exc: Exception`` documents the contract (BaseException is out of scope
    by design — those are flow control, never network errors).
    """
    assert classify_proxy_error(exc) is None


# ---------- probe_proxy_health tests ----------


@pytest.mark.integration
def test_probe_proxy_health_returns_false_on_network_error(monkeypatch) -> None:
    """probe_proxy_health NEVER raises; returns False on any network failure."""

    def _raising_client(*args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        class _C:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *args, **kwargs):
                return False

            def get(self_inner, url: str) -> httpx.Response:
                raise httpx.ConnectError("refused")

        return _C()

    monkeypatch.setattr(httpx, "Client", _raising_client)
    assert probe_proxy_health("https://example.invalid", timeout_s=1.0) is False


@pytest.mark.integration
def test_probe_proxy_health_returns_true_on_200(monkeypatch) -> None:
    """probe_proxy_health returns True iff /health returns HTTP 200."""

    def _ok_client(*args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        class _C:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *args, **kwargs):
                return False

            def get(self_inner, url: str) -> httpx.Response:
                assert url.endswith("/health"), f"canary must hit /health, got {url}"
                return httpx.Response(status_code=200)

        return _C()

    monkeypatch.setattr(httpx, "Client", _ok_client)
    assert probe_proxy_health("https://example.invalid", timeout_s=1.0) is True


@pytest.mark.integration
def test_probe_proxy_health_returns_false_on_non_200(monkeypatch) -> None:
    """probe_proxy_health returns False for any non-200 response (e.g., 503
    from cascade-degraded /health per §V7-PROXY contract)."""

    def _degraded_client(*args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        class _C:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *args, **kwargs):
                return False

            def get(self_inner, url: str) -> httpx.Response:
                return httpx.Response(status_code=503)

        return _C()

    monkeypatch.setattr(httpx, "Client", _degraded_client)
    assert probe_proxy_health("https://example.invalid", timeout_s=1.0) is False


# ---------- agent-level orchestration tests ----------


@pytest.mark.integration
@pytest.mark.parametrize("reason", ["5xx", "timeout", "connection_refused"])
def test_agent_emits_unavailable_one_shot(
    mocker, tmp_path, monkeypatch, reason: str
) -> None:
    """In proxy mode, calling ``_maybe_emit_proxy_unavailable`` lands EXACTLY
    ONE "Co-host unavailable this session" transcript line per
    unavailable-streak, regardless of how many additional unavailable ticks
    fire.

    Drives the helper directly (rather than constructing a full
    generate_content_stream mock) — the helper is the single chokepoint the
    llm_node except-branch calls, so this is the load-bearing contract.
    """
    agent, transcript_sink, recorder = _build_agent(
        mocker, tmp_path, mode="proxy", monkeypatch=monkeypatch
    )
    assert agent._proxy_base_url is not None, "proxy mode must arm _proxy_base_url"
    assert agent._proxy_unavailable is False

    # First unavailable event → emits the line + sets the flag.
    agent._maybe_emit_proxy_unavailable(reason)
    assert agent._proxy_unavailable is True
    assert agent._proxy_unavailable_message_emitted is True
    assert list(transcript_sink) == ["Co-host unavailable this session"]
    assert any(k == "proxy_unavailable" for k, _ in recorder.events)

    # Second unavailable event → NO duplicate (one-shot).
    agent._maybe_emit_proxy_unavailable(reason)
    assert list(transcript_sink) == ["Co-host unavailable this session"], (
        "duplicate emission — the one-shot guard failed"
    )

    # Third event for a different reason → still one-shot.
    agent._maybe_emit_proxy_unavailable("timeout")
    assert list(transcript_sink) == ["Co-host unavailable this session"]


@pytest.mark.integration
def test_agent_recovery_emits_back_online_one_shot(
    mocker, tmp_path, monkeypatch
) -> None:
    """After the fallback is armed, calling ``_maybe_emit_proxy_recovery``
    emits "Co-host back online" exactly once + clears the flag. A second
    call is a no-op (flag already cleared).
    """
    agent, transcript_sink, recorder = _build_agent(
        mocker, tmp_path, mode="proxy", monkeypatch=monkeypatch
    )
    # Arm the fallback first.
    agent._maybe_emit_proxy_unavailable("5xx")
    assert agent._proxy_unavailable is True
    assert list(transcript_sink) == ["Co-host unavailable this session"]

    # Recovery fires the one-shot back-online line + clears the flag.
    agent._maybe_emit_proxy_recovery()
    assert agent._proxy_unavailable is False
    assert agent._proxy_recovery_message_emitted is True
    assert list(transcript_sink) == [
        "Co-host unavailable this session",
        "Co-host back online",
    ]
    assert any(k == "proxy_recovered" for k, _ in recorder.events)

    # Second call is a no-op (flag is already cleared).
    agent._maybe_emit_proxy_recovery()
    assert list(transcript_sink) == [
        "Co-host unavailable this session",
        "Co-host back online",
    ]


@pytest.mark.integration
def test_agent_canary_60s_debounce_and_recovery(
    mocker, tmp_path, monkeypatch
) -> None:
    """The 60s canary debounce: a probe within 60s of the last probe is a
    no-op; a probe ≥ 60s later fires; on /health=200 the recovery one-shot
    fires + clears the flag.
    """
    probe_calls: list[str] = []

    def _fake_probe(url: str, timeout_s: float = 5.0) -> bool:
        probe_calls.append(url)
        # Second call (≥ 60s later) returns True; first call returns False.
        return len(probe_calls) >= 2

    monkeypatch.setattr(
        "vibemix.agent.dj_cohost.probe_proxy_health", _fake_probe
    )

    agent, transcript_sink, _recorder = _build_agent(
        mocker, tmp_path, mode="proxy", monkeypatch=monkeypatch
    )
    agent._maybe_emit_proxy_unavailable("timeout")
    assert agent._proxy_unavailable is True

    # Phase 69 review WR-01 — the canary is now an async coroutine (the
    # blocking probe is offloaded to a thread executor), so it must be driven
    # via ``asyncio.run`` rather than called synchronously. Behavior under
    # test is unchanged: debounce gate + one-shot recovery emission.
    #
    # Phase 69 review WR-02 — ``_last_proxy_health_probe`` now inits to
    # ``float("-inf")`` so the FIRST armed tick always passes the 60s gate
    # regardless of the monotonic clock origin. The original test relied on
    # the ``0.0`` init swallowing the t=10s tick; with the ``-inf`` sentinel
    # that first tick WOULD probe, so we explicitly arm the debounce to t=0.0
    # here to keep exercising the within-window no-op behavior.
    agent._last_proxy_health_probe = 0.0

    # Drive the canary at t=10s — still within the 60s window, no probe.
    asyncio.run(agent._check_proxy_health_canary(now_monotonic=10.0))
    assert probe_calls == [], "canary fired inside the 60s debounce window"

    # Drive the canary at t=60.0 — exactly 60s elapsed, probe fires (returns
    # False on first call → flag stays armed).
    asyncio.run(agent._check_proxy_health_canary(now_monotonic=60.0))
    assert len(probe_calls) == 1
    assert agent._proxy_unavailable is True
    assert list(transcript_sink) == ["Co-host unavailable this session"]

    # Drive the canary at t=121.0 — another 61s, probe fires + returns True.
    # Recovery one-shot fires.
    asyncio.run(agent._check_proxy_health_canary(now_monotonic=121.0))
    assert len(probe_calls) == 2
    assert agent._proxy_unavailable is False
    assert list(transcript_sink) == [
        "Co-host unavailable this session",
        "Co-host back online",
    ]


@pytest.mark.integration
def test_agent_direct_mode_never_arms_fallback(
    mocker, tmp_path, monkeypatch
) -> None:
    """In direct (BYO) mode, _proxy_base_url is None and EVERY fallback hook
    is a no-op. BYO users see their own network errors per existing v3.x
    behavior (no transcript spam, no flag flip, no recorder event).

    This defends the boundary against future refactors that might
    accidentally arm the fallback for direct-mode users.
    """
    monkeypatch.delenv("VIBEMIX_PROXY_BASE_URL", raising=False)
    agent, transcript_sink, recorder = _build_agent(
        mocker, tmp_path, mode="direct", monkeypatch=monkeypatch
    )
    assert agent._proxy_base_url is None, "direct mode must NOT arm proxy_base_url"

    # All three hooks must be no-ops.
    agent._maybe_emit_proxy_unavailable("5xx")
    agent._maybe_emit_proxy_recovery()
    # Phase 69 review WR-01 — canary is now async; direct mode still returns
    # early (``_proxy_base_url is None``) before any offload, but the call
    # must be awaited via ``asyncio.run``.
    asyncio.run(agent._check_proxy_health_canary(now_monotonic=999.0))

    assert agent._proxy_unavailable is False
    assert list(transcript_sink) == []
    assert not any(
        k in ("proxy_unavailable", "proxy_recovered") for k, _ in recorder.events
    )


# ---------- RELEASE-AUTH: loud connection-error surfacing ----------


@pytest.mark.integration
def test_emit_connection_error_logs_event_and_transcript(
    mocker, tmp_path, monkeypatch
) -> None:
    """RELEASE-AUTH Fix 2: an UNCLASSIFIED LLM failure (auth/DNS/connect) must
    surface LOUDLY — a ``connection_error`` event to events.jsonl AND a UI
    transcript line — instead of dying to stderr only (the "events fire but
    the co-host never speaks and nothing is logged" release blocker).

    Works in direct (BYO) mode too — this is the path classify_proxy_error
    deliberately does NOT cover (4xx auth errors), which is exactly the
    missing-key class.
    """
    agent, transcript_sink, recorder = _build_agent(
        mocker, tmp_path, mode="direct", monkeypatch=monkeypatch
    )

    err = RuntimeError("401 UNAUTHORIZED: API key not valid")
    agent._emit_connection_error(err)

    # events.jsonl line written, classified as auth, secret-free.
    conn_events = [f for k, f in recorder.events if k == "connection_error"]
    assert len(conn_events) == 1
    assert conn_events[0]["error_kind"] == "auth"
    assert conn_events[0]["error"] == "RuntimeError"

    # UI transcript got the user-visible "it's broken" signal.
    assert any("can't reach Gemini" in line for line in transcript_sink)


@pytest.mark.integration
def test_emit_connection_error_is_one_shot(
    mocker, tmp_path, monkeypatch
) -> None:
    """The loud surface fires ONCE per error streak — a persistent auth
    failure (10Hz coach loop) must not spam events.jsonl / the transcript."""
    agent, transcript_sink, recorder = _build_agent(
        mocker, tmp_path, mode="direct", monkeypatch=monkeypatch
    )
    for _ in range(5):
        agent._emit_connection_error(RuntimeError("403 permission denied"))

    conn_events = [f for k, f in recorder.events if k == "connection_error"]
    assert len(conn_events) == 1, "must be one-shot per streak"
    assert sum("can't reach Gemini" in line for line in transcript_sink) == 1


@pytest.mark.integration
@pytest.mark.parametrize(
    "msg,expected_kind",
    [
        ("401 unauthorized", "auth"),
        ("API key not valid", "auth"),
        ("getaddrinfo failed", "dns"),
        ("connection refused", "connection"),
        ("request timed out", "connection"),
        ("something weird happened", "unknown"),
    ],
)
def test_emit_connection_error_classification(
    mocker, tmp_path, monkeypatch, msg, expected_kind
) -> None:
    """Coarse, secret-free classification used for the log line."""
    agent, _sink, recorder = _build_agent(
        mocker, tmp_path, mode="direct", monkeypatch=monkeypatch
    )
    agent._emit_connection_error(RuntimeError(msg))
    conn = [f for k, f in recorder.events if k == "connection_error"]
    assert conn and conn[0]["error_kind"] == expected_kind
