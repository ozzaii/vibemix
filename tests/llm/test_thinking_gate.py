# SPDX-License-Identifier: Apache-2.0
"""Plan 41-03 / Task 1 — thinking_gate validator unit tests (LAT-08).

Pins the live-coach config invariants:

- thinking_level on live coach MUST be MINIMAL (anything higher = 7s+ TTFT
  regression per CONTEXT D-LAT-08).
- service_tier on live coach MUST NOT be FLEX (Pitfall 3 — Flex SLA is
  1-15 min P99 60 min = live UX collapse).
- Pass cases cover: MINIMAL via enum / lowercase string / uppercase string,
  STANDARD / PRIORITY tier, no tier set, no thinking config set.
- Fail cases cover: LOW / MEDIUM / HIGH thinking, FLEX tier as enum or
  string, and the both-violations aggregated message.
"""

from __future__ import annotations

import pytest
from google.genai.types import (
    GenerateContentConfig,
    ServiceTier,
    ThinkingConfig,
    ThinkingLevel,
)

from vibemix.llm.thinking_gate import LiveCoachConfigError, validate_live_config


# ---------------------------------------------------------------------------
# Pass cases — validator returns None
# ---------------------------------------------------------------------------


def test_minimal_thinking_passes() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.MINIMAL),
    )
    assert validate_live_config(cfg) is None


def test_minimal_string_lowercase_passes() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level="minimal"),
    )
    assert validate_live_config(cfg) is None


def test_minimal_string_uppercase_passes() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level="MINIMAL"),
    )
    assert validate_live_config(cfg) is None


def test_standard_tier_passes() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.MINIMAL),
        service_tier=ServiceTier.STANDARD,
    )
    assert validate_live_config(cfg) is None


def test_priority_tier_passes() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.MINIMAL),
        service_tier=ServiceTier.PRIORITY,
    )
    assert validate_live_config(cfg) is None


def test_no_service_tier_passes() -> None:
    # SDK default tier is fine — validator must not raise on None.
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.MINIMAL),
        service_tier=None,
    )
    assert validate_live_config(cfg) is None


def test_no_thinking_config_passes() -> None:
    # Defensive: when thinking_config is None Gemini's default behavior
    # applies. Production live coach explicitly sets MINIMAL; the validator
    # only rejects EXPLICIT non-MINIMAL overrides, not absence.
    cfg = GenerateContentConfig(thinking_config=None)
    assert validate_live_config(cfg) is None


# ---------------------------------------------------------------------------
# Fail cases — validator raises LiveCoachConfigError
# ---------------------------------------------------------------------------


def test_low_thinking_raises() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.LOW),
    )
    with pytest.raises(LiveCoachConfigError, match=r"thinking_level.*MINIMAL"):
        validate_live_config(cfg)


def test_medium_thinking_raises() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.MEDIUM),
    )
    with pytest.raises(LiveCoachConfigError, match=r"thinking_level.*MINIMAL"):
        validate_live_config(cfg)


def test_high_thinking_raises() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.HIGH),
    )
    with pytest.raises(LiveCoachConfigError, match=r"thinking_level.*MINIMAL"):
        validate_live_config(cfg)


def test_flex_tier_raises() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.MINIMAL),
        service_tier=ServiceTier.FLEX,
    )
    with pytest.raises(LiveCoachConfigError, match=r"service_tier.*Flex SLA"):
        validate_live_config(cfg)


def test_flex_tier_string_raises() -> None:
    # CaseInSensitiveEnum accepts the lowercase string too — validator
    # must normalize and still catch it.
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.MINIMAL),
        service_tier="flex",
    )
    with pytest.raises(LiveCoachConfigError, match=r"service_tier.*Flex SLA"):
        validate_live_config(cfg)


def test_both_violations_reports_both() -> None:
    cfg = GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.HIGH),
        service_tier=ServiceTier.FLEX,
    )
    with pytest.raises(LiveCoachConfigError) as exc:
        validate_live_config(cfg)
    msg = str(exc.value)
    assert "thinking_level" in msg
    assert "service_tier" in msg


# ---------------------------------------------------------------------------
# Task 2 — wiring into llm_factory + DJCoHostAgent
# ---------------------------------------------------------------------------
# These tests assert the validator is called at the two construction seams
# (llm_factory.build_llm + DJCoHostAgent.__init__) and that the per-turn hot
# path NEVER re-invokes it (zero per-turn overhead invariant).

from pathlib import Path  # noqa: E402 — keep Task 1 imports tidy above
from typing import Any  # noqa: E402

from livekit.agents import Agent  # noqa: E402
from livekit.plugins import google as google_plugin  # noqa: E402


def test_llm_factory_passes_with_default_config(mocker) -> None:
    """build_llm("k") (direct, default Phase 4 path) returns a wrapper —
    the validator passes because the factory hardcodes thinking_level=minimal
    and never sets service_tier."""
    mocker.patch.object(google_plugin.LLM, "__init__", return_value=None)
    from vibemix.agent import llm_factory as factory_mod  # noqa: PLC0415

    factory_spy = mocker.spy(factory_mod, "validate_live_config")
    inst = factory_mod.build_llm("dummy-key")
    assert inst is not None
    assert factory_spy.call_count == 1
    # The validator was called with a GenerateContentConfig; sanity-check
    # that it carries the minimal thinking_level the factory hardcodes.
    cfg = factory_spy.call_args.args[0]
    level = cfg.thinking_config.thinking_level
    assert str(getattr(level, "value", level)).lower() == "minimal"


def test_llm_factory_raises_on_bad_thinking_override(mocker) -> None:
    """If the factory is monkeypatched to assemble a non-MINIMAL config,
    build_llm raises LiveCoachConfigError BEFORE constructing the LLM."""
    mocker.patch.object(google_plugin.LLM, "__init__", return_value=None)
    from vibemix.agent import llm_factory as factory_mod  # noqa: PLC0415

    # Replace _build_direct's GenerateContentConfig assembly site by patching
    # the inner builder to inject a HIGH thinking_level. Use the public seam:
    # patch types.ThinkingConfig to return a HIGH-level config when the
    # factory builds its default. Simpler: just swap the gen_cfg via a
    # wrapper. We monkey-patch the validate function to verify the factory
    # invokes it ON a config we craft to fail.
    from google.genai.types import ThinkingConfig, ThinkingLevel  # noqa: PLC0415

    orig_thinkingconfig = factory_mod.types.ThinkingConfig

    def _high_thinkingconfig(*_args, **_kwargs):
        return ThinkingConfig(thinking_level=ThinkingLevel.HIGH)

    mocker.patch.object(factory_mod.types, "ThinkingConfig", _high_thinkingconfig)
    try:
        with pytest.raises(LiveCoachConfigError, match=r"thinking_level.*MINIMAL"):
            factory_mod.build_llm("dummy-key")
    finally:
        # Restore — defensive (mocker should already roll back, but be explicit).
        mocker.patch.object(factory_mod.types, "ThinkingConfig", orig_thinkingconfig)


# ---- DJCoHostAgent init-gate helpers (mirror tests/agent/test_dj_cohost.py) ----


class _FakeRecorder:
    """Minimal recorder stub for the agent gate tests."""

    def __init__(self, session_dir: Path) -> None:
        self.session_dir = session_dir
        self.events: list[tuple[str, dict]] = []

    def log_event(self, kind: str, **fields: Any) -> None:
        self.events.append((kind, fields))

    def push_voice(self, pcm: bytes) -> None:  # pragma: no cover — unused here
        pass


def _build_state():
    from vibemix.state import MusicState  # noqa: PLC0415

    s = MusicState()
    s.audible = True
    s.audible_deck = "A"
    s.audible_track = "Test - Track"
    s.audible_track_confidence = 0.8
    s.phase = "peak"
    s.rms = 0.05
    s.bpm = 128.0
    return s


def test_dj_cohost_init_passes_with_default_config(mocker, tmp_path: Path) -> None:
    """Constructing DJCoHostAgent with the production _gen_cfg succeeds and
    invokes validate_live_config exactly ONCE at init."""
    mocker.patch.object(Agent, "__init__", return_value=None)
    from vibemix.agent import dj_cohost as agent_mod  # noqa: PLC0415

    spy = mocker.spy(agent_mod, "validate_live_config")
    agent_mod.DJCoHostAgent(
        genai_client=mocker.MagicMock(),
        clean_audio_buf=mocker.MagicMock(),
        screen_buf=mocker.MagicMock(),
        state=_build_state(),
        recorder=_FakeRecorder(tmp_path),
        llm_inst=mocker.MagicMock(),
        tts_inst=mocker.MagicMock(),
    )
    assert spy.call_count == 1
    cfg = spy.call_args.args[0]
    level = cfg.thinking_config.thinking_level
    assert str(getattr(level, "value", level)).lower() == "minimal"


def test_dj_cohost_init_raises_on_flex_tier(mocker, tmp_path: Path) -> None:
    """If the agent's _gen_cfg assembly is monkeypatched to carry
    service_tier=FLEX, __init__ raises LiveCoachConfigError BEFORE returning."""
    mocker.patch.object(Agent, "__init__", return_value=None)
    from google.genai.types import GenerateContentConfig as _Cfg  # noqa: PLC0415
    from google.genai.types import ServiceTier  # noqa: PLC0415
    from vibemix.agent import dj_cohost as agent_mod  # noqa: PLC0415

    # Wrap GenerateContentConfig so the agent assembles a FLEX-tier config.
    orig = agent_mod.types.GenerateContentConfig

    def _flex_cfg(*args, **kwargs):
        kwargs["service_tier"] = ServiceTier.FLEX
        return orig(*args, **kwargs)

    mocker.patch.object(agent_mod.types, "GenerateContentConfig", _flex_cfg)
    with pytest.raises(LiveCoachConfigError, match=r"service_tier.*Flex SLA"):
        agent_mod.DJCoHostAgent(
            genai_client=mocker.MagicMock(),
            clean_audio_buf=mocker.MagicMock(),
            screen_buf=mocker.MagicMock(),
            state=_build_state(),
            recorder=_FakeRecorder(tmp_path),
            llm_inst=mocker.MagicMock(),
            tts_inst=mocker.MagicMock(),
        )
    # Silence unused-import warning — _Cfg keeps the import readable for
    # future maintainers spotting the type the wrapper closes over.
    _ = _Cfg


def test_validate_not_called_per_turn(mocker, tmp_path: Path) -> None:
    """Spy on validate_live_config; drive llm_node 5 times; assert
    call_count == 1 (the init call only, never per-turn)."""
    import asyncio  # noqa: PLC0415

    mocker.patch.object(Agent, "__init__", return_value=None)
    from vibemix.agent import dj_cohost as agent_mod  # noqa: PLC0415

    # Stub out the audio + filesystem side effects llm_node performs.
    mocker.patch.object(agent_mod, "snapshot_wav", return_value=b"WAVE")

    genai_client = mocker.MagicMock()

    async def _stream(**_kwargs):
        async def _gen():
            yield type("Chunk", (), {"text": "ok"})()

        return _gen()

    genai_client.aio.models.generate_content_stream = _stream

    agent = agent_mod.DJCoHostAgent(
        genai_client=genai_client,
        clean_audio_buf=mocker.MagicMock(),
        screen_buf=mocker.MagicMock(),
        state=_build_state(),
        recorder=_FakeRecorder(tmp_path),
        llm_inst=mocker.MagicMock(),
        tts_inst=mocker.MagicMock(),
    )
    # Spy AFTER __init__ — the init call has already happened. We assert
    # the per-turn loop adds ZERO more calls.
    spy = mocker.spy(agent_mod, "validate_live_config")

    async def _drive() -> None:
        for _ in range(5):
            async for _txt in agent.llm_node(chat_ctx=None, tools=[], model_settings=None):
                pass

    asyncio.run(_drive())
    assert spy.call_count == 0  # zero per-turn calls; init call was pre-spy.
