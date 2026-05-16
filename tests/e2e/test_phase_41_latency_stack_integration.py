# SPDX-License-Identifier: Apache-2.0
"""Plan 41-07 — Phase 41 latency-stack end-to-end integration test.

Composes the surfaces shipped by Plans 41-01..06 into one set of
integration scenarios. Each scenario pins a cross-plan composition that
the unit tests cannot fully cover:

  * test_router_resolves_all_paths              — Plan 41-01 (LAT-01, LAT-07)
  * test_agent_validates_live_config            — Plan 41-03 + 41-01 (LAT-08)
  * test_cache_does_not_spawn_refresh_loop_task — Plan 41-02 (LAT-02)
  * test_full_turn_streams_first_sentence_before_completion
                                                — Plan 41-04 (LAT-04)
  * test_embedding_probe_runs_at_boot_and_logs  — Plan 41-05 (LAT-05, LAT-06)

REQ-ID coverage:

  * LAT-01 — ModelRouter migration            : test_router_resolves_all_paths
  * LAT-02 — Caching cleanup + mutation hook  : test_cache_does_not_spawn_refresh_loop_task
                                                + test_evidence_registry_triggers_cache_refresh
  * LAT-03 — Gemini 3.1 Flash TTS routing     : test_router_resolves_all_paths (live_coach_tts)
  * LAT-04 — LLM→TTS streaming pipe           : test_full_turn_streams_first_sentence_before_completion
  * LAT-05 — Embedding 2 GA migration         : test_embedding_probe_runs_at_boot_and_logs
  * LAT-06 — MRL 768-dim parity (probe)       : test_embedding_probe_runs_at_boot_and_logs
  * LAT-07 — Flex tier dispatch               : test_router_resolves_all_paths (debrief/library/embedding)
  * LAT-08 — Thinking-level enforcement       : test_agent_validates_live_config
                                                + test_thinking_gate_rejects_flex_on_live
  * LAT-09 — 3.1 Flash Live spike scaffolding : test_spike_scaffold_is_not_in_runtime_path

VCR posture
-----------
Plan 41-07 originally specified VCR cassettes for streaming + embedding-
probe scenarios. After inspection of the surfaces shipped by Plans
41-04 / 41-05 we found that the relevant integration boundary is the
mocked genai client (the cassette would only re-record what we already
control). We mock at the SDK boundary directly — cleaner, no GEMINI_API_KEY
required to re-record, and zero cost surface. The integration report
notes this deliberate choice (see 41-INTEGRATION-REPORT.md §Pitfall 6).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from google.genai.types import (
    GenerateContentConfig,
    ServiceTier,
    ThinkingConfig,
)

from vibemix.agent._streaming_pipe import (
    SILENCE_TOKEN,
    find_sentence_end,
    passes_head_gate,
)
from vibemix.agent.cache import GeminiContextCache
from vibemix.llm._router_config import _ROUTES
from vibemix.llm.model_router import ROUTER_PATHS, RouterPathError, resolve
from vibemix.llm.thinking_gate import LiveCoachConfigError, validate_live_config
from vibemix.runtime.llm_to_tts_delta_meter import LLMToTTSDeltaMeter
from vibemix.state.evidence_registry import EvidenceRegistry


# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------


class _SpyRecorder:
    """Minimal recorder spy — captures `log_event(name, **kwargs)` rows."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def log_event(self, name: str, **kwargs: Any) -> None:
        row = {"type": name, **kwargs}
        self.events.append(row)


@pytest.fixture
def spy_recorder() -> _SpyRecorder:
    return _SpyRecorder()


# ---------------------------------------------------------------------------
# Scenario 1 — Plan 41-01 (LAT-01, LAT-03, LAT-07)
# Router resolves all 8 paths to the locked SKU + tier dispatch.
# ---------------------------------------------------------------------------


def test_router_resolves_all_paths() -> None:
    """All 8 router paths resolve to the locked SKU + tier per CONTEXT.md.

    Wave 1 + 2 plans depend on this seam — any path that fails to resolve
    or returns the wrong tier is a phase-level integration regression.
    """
    # Path × (model, tier) — CONTEXT.md table mirror.
    expected: dict[str, tuple[str, ServiceTier | None]] = {
        "live_coach": ("gemini-3-flash-preview", ServiceTier.STANDARD),
        "live_coach_tts": ("gemini-3.1-flash-tts-preview", ServiceTier.STANDARD),
        "live_coach_tts_fallback": (
            "gemini-2.5-flash-preview-tts",
            ServiceTier.STANDARD,
        ),
        "live_coach_tts_openrouter": (
            "google/gemini-3.1-flash-tts-preview",
            None,
        ),
        "debrief": ("gemini-3-pro-preview", ServiceTier.FLEX),
        "debrief_tts": ("gemini-3-flash-tts-preview", ServiceTier.FLEX),
        "library_auto_tag": ("gemini-3-flash-preview", ServiceTier.FLEX),
        "embedding": ("gemini-embedding-2", ServiceTier.FLEX),
    }
    # Sanity — ROUTER_PATHS and _ROUTES agree.
    assert set(ROUTER_PATHS) == set(_ROUTES.keys()) == set(expected.keys())
    for path, (want_model, want_tier) in expected.items():
        got_model, got_tier = resolve(path)
        assert got_model == want_model, (
            f"path {path!r}: model {got_model!r} != expected {want_model!r}"
        )
        assert got_tier == want_tier, (
            f"path {path!r}: tier {got_tier!r} != expected {want_tier!r}"
        )


def test_router_unknown_path_raises_with_diagnostic() -> None:
    """Unknown paths raise RouterPathError listing every valid key —
    catch-all import sanity for the integration boundary."""
    with pytest.raises(RouterPathError) as exc:
        resolve("not_a_real_path")
    msg = str(exc.value)
    for path in ROUTER_PATHS:
        assert path in msg


# ---------------------------------------------------------------------------
# Scenario 2 — Plan 41-03 + 41-01 (LAT-08)
# Live coach config must validate cleanly with production defaults; bad
# configs must raise LiveCoachConfigError.
# ---------------------------------------------------------------------------


def test_agent_validates_live_config() -> None:
    """Production-shape `_gen_cfg` passes validate_live_config without raise.

    This mirrors `DJCoHostAgent.__init__`'s actual construction (Plan 41-03
    second gate). The model + temperature + max_output_tokens fields are
    not checked by the gate — only thinking_level + service_tier matter.
    """
    cfg = GenerateContentConfig(
        system_instruction="test-system-instruction",
        thinking_config=ThinkingConfig(thinking_level="minimal"),
        temperature=1.0,
        max_output_tokens=220,
    )
    # No service_tier set (default == STANDARD on the live path).
    validate_live_config(cfg)  # MUST NOT raise


def test_thinking_gate_rejects_flex_on_live() -> None:
    """LiveCoachConfigError raised when service_tier=FLEX on the live path.

    Pitfall 3 — Flex SLA (1-15 min P99 60 min) collapses live UX. The gate
    is the only thing standing between a future config-mutation PR and a
    silent production regression.
    """
    cfg = GenerateContentConfig(
        system_instruction="test",
        thinking_config=ThinkingConfig(thinking_level="minimal"),
        service_tier=ServiceTier.FLEX,
    )
    with pytest.raises(LiveCoachConfigError) as exc:
        validate_live_config(cfg)
    msg = str(exc.value)
    assert "FLEX" in msg
    assert "Pitfall 3" in msg


def test_thinking_gate_rejects_higher_than_minimal_thinking() -> None:
    """Anything above MINIMAL adds 7s+ TTFT regression — gate must reject."""
    cfg = GenerateContentConfig(
        system_instruction="test",
        thinking_config=ThinkingConfig(thinking_level="medium"),
    )
    with pytest.raises(LiveCoachConfigError) as exc:
        validate_live_config(cfg)
    msg = str(exc.value)
    assert "thinking_level" in msg
    assert "MINIMAL" in msg


# ---------------------------------------------------------------------------
# Scenario 3 — Plan 41-02 (LAT-02)
# Cache + EvidenceRegistry compose cleanly; no refresh_loop task spawned.
# ---------------------------------------------------------------------------


class _FakeCachesAio:
    """Minimal genai.Client.aio.caches mock — supports create + delete."""

    def __init__(self) -> None:
        self.created: list[str] = []
        self._counter = 0

    async def create(self, model: str, config) -> Any:
        self._counter += 1
        name = f"cachedContents/fake-{self._counter}"
        self.created.append(name)

        class _Cache:
            def __init__(self, n: str) -> None:
                self.name = n

        return _Cache(name)

    async def delete(self, name: str) -> None:
        pass


class _FakeAio:
    def __init__(self) -> None:
        self.caches = _FakeCachesAio()


class _FakeClient:
    """Minimal genai.Client shape — Plan 41-02 cache only uses client.aio.caches.*"""

    def __init__(self) -> None:
        self.aio = _FakeAio()


def test_cache_does_not_spawn_refresh_loop_task() -> None:
    """Plan 41-02 — refresh_loop is GONE. After constructing a cache +
    registry wired via on_mutation, no background task is spawned for the
    refresh loop. The atomic-swap refresh fires ONLY on registry mutation.
    """

    async def _scenario() -> None:
        client = _FakeClient()
        cache = GeminiContextCache(
            client=client,  # type: ignore[arg-type]
            system_instruction_body="vibemix cohost system prompt",
        )

        # Wire a registry to cache.refresh. Small debounce — exercises the
        # scheduling without blocking the test.
        EvidenceRegistry(
            on_mutation=cache.refresh,
            mutation_debounce_s=0.01,
            min_refresh_interval_s=0.0,
        )

        # Snapshot running task set BEFORE writing anything to the registry.
        before_tasks = {
            t.get_name() for t in asyncio.all_tasks() if not t.done()
        }
        # No task named ``refresh_loop`` should ever appear (Plan 41-02 deletion).
        assert not any("refresh_loop" in name for name in before_tasks), (
            f"refresh_loop task still spawned in pre-mutation task set: "
            f"{before_tasks!r}"
        )

        # Bootstrap explicit create — should land one cache name.
        await cache.create()
        assert cache.current_name() is not None
        assert client.aio.caches.created == [cache.current_name()]

    asyncio.run(_scenario())


def test_evidence_registry_triggers_cache_refresh() -> None:
    """Plan 41-02 — EvidenceRegistry.write() schedules a debounced refresh
    callback. After the debounce window, cache.refresh has fired exactly
    once (the registry collapses bursty writes into a single fire)."""

    async def _scenario() -> None:
        client = _FakeClient()
        cache = GeminiContextCache(
            client=client,  # type: ignore[arg-type]
            system_instruction_body="vibemix cohost system prompt",
        )
        refresh_calls: list[float] = []
        original_refresh = cache.refresh

        async def _spy_refresh() -> None:
            refresh_calls.append(asyncio.get_running_loop().time())
            await original_refresh()

        registry = EvidenceRegistry(
            on_mutation=_spy_refresh,
            mutation_debounce_s=0.02,
            min_refresh_interval_s=0.0,
        )
        # Bootstrap so refresh has an old_name to swap.
        await cache.create()
        first_name = cache.current_name()

        # Burst of 5 writes within the debounce window — should fire ONCE.
        for i in range(5):
            registry.write(source="ev", key="KICK", t_session=float(i))

        # Wait past the debounce window (+ scheduler tolerance).
        await asyncio.sleep(0.1)

        assert len(refresh_calls) == 1, (
            f"expected exactly 1 refresh fire from 5-write burst, "
            f"got {len(refresh_calls)}: {refresh_calls!r}"
        )
        # The refresh swapped to a new cache name.
        assert cache.current_name() != first_name

    asyncio.run(_scenario())


# ---------------------------------------------------------------------------
# Scenario 4 — Plan 41-04 (LAT-04)
# Streaming pipe: first sentence yields BEFORE the stream completes; the
# LLMToTTSDeltaMeter measures the perceived-latency boundary.
# ---------------------------------------------------------------------------


def test_full_turn_streams_first_sentence_before_completion() -> None:
    """Synthetic streaming accumulator — first sentence boundary fires at
    chunk N (mid-stream), NOT at the end. Validates Plan 41-04's dual-
    phase gate composition with the LLMToTTSDeltaMeter latency record.

    Stream payload (3 sentences):
      "Killer drop hits hard. The next track elevates the groove. Lock in."

    Chunks (deterministic split — Gemini streams token-roughly-similar):
      ['Killer drop hits hard. ',
       'The next track elevates the groove. ',
       'Lock in.']

    Behavior:
      - After chunk 1, find_sentence_end returns a boundary ≥ MIN_HEAD_LEN.
      - passes_head_gate clears (no slop prefix).
      - Meter records first sentence between event-fired and stream end.
    """
    chunks = [
        "Killer drop hits hard. ",
        "The next track elevates the groove. ",
        "Lock in.",
    ]

    # Deterministic clock — start_turn at t=0, each chunk adds 50ms.
    t = [0.0]

    def _clock() -> float:
        return t[0]

    meter = LLMToTTSDeltaMeter(time_fn=_clock)
    meter.start_turn()  # event_fired at t=0

    head_yielded = False
    head_text: str | None = None
    accum = ""
    full_text = ""
    stream_completed_at: float | None = None

    for chunk in chunks:
        t[0] += 0.05  # 50ms per chunk arrival
        full_text += chunk
        if not head_yielded:
            accum += chunk
            end_idx = find_sentence_end(accum)
            if end_idx is not None:
                head = accum[:end_idx]
                if passes_head_gate(head):
                    head_yielded = True
                    head_text = head
                    meter.record_first_sentence()
                    # accum cleared — tail streams below
                    accum = ""
    stream_completed_at = t[0]

    # Head fired mid-stream (after chunk 1, before chunk 3).
    assert head_yielded, "first sentence boundary never fired"
    assert head_text is not None
    assert head_text.startswith("Killer drop hits hard."), (
        f"head text wrong: {head_text!r}"
    )
    # Head fired BEFORE stream completed (the load-bearing assertion).
    delta_ms = meter.delta_ms()
    assert delta_ms is not None
    stream_completed_ms = round(stream_completed_at * 1000)
    assert delta_ms < stream_completed_ms, (
        f"first sentence ({delta_ms}ms) should fire before stream end "
        f"({stream_completed_ms}ms)"
    )
    # Synthetic latency: chunk 1 lands at 50ms → meter records delta ~50ms.
    assert 40 <= delta_ms <= 60, (
        f"meter delta {delta_ms}ms outside synthetic 50ms expected band"
    )


def test_streaming_pipe_rejects_silence_token_head() -> None:
    """Plan 41-04 head gate — `<silence/>` opener short-circuits the
    speculative yield (the whole turn is a suppress)."""
    head = f"{SILENCE_TOKEN} I hear nothing worth saying."
    assert passes_head_gate(head) is False


def test_streaming_pipe_rejects_slop_head() -> None:
    """Plan 41-04 head gate — slop prefix from NEGATIVE_PHRASES rejects
    the speculative yield."""
    # "As an AI" is in the locked NEGATIVE_PHRASES "Generic AI tells"
    # subset — should reject regardless of trailing text.
    head = "As an AI, I'd say that groove is killer."
    assert passes_head_gate(head) is False


def test_streaming_pipe_citation_period_does_not_fire_boundary() -> None:
    """Pitfall 1 lock — period inside `[ev:kick@2.5]` MUST NOT trigger a
    sentence boundary. find_sentence_end's bracket-depth tracker holds."""
    # Citation period at idx=8 is inside depth=1 → no boundary.
    # Trailing period after the bracket close + whitespace is the real
    # boundary, lands past MIN_HEAD_LEN.
    text = "Right [ev:kick@2.5] feeling. More to come."
    end_idx = find_sentence_end(text)
    assert end_idx is not None
    # The boundary must land AFTER the bracket close.
    assert end_idx > text.index("]"), (
        f"boundary {end_idx} fired inside or before the citation bracket"
    )


# ---------------------------------------------------------------------------
# Scenario 5 — Plan 41-05 (LAT-05, LAT-06)
# Embedding-2 probe runs at boot and logs the chosen candidate. Verifies
# A1 (GA model ID) at integration time.
# ---------------------------------------------------------------------------


class _FakeEmbedClient:
    """Minimal genai.Client.models mock for embed_content."""

    def __init__(
        self,
        *,
        succeed_on: str | None = None,
        embeddings_value: list[float] | None = None,
    ) -> None:
        self.succeed_on = succeed_on  # model id that returns a real embedding
        self.embeddings_value = embeddings_value or [0.1] * 768
        self.calls: list[str] = []
        self.models = self  # so client.models.embed_content works

    def embed_content(self, *, model: str, contents: str, config) -> Any:
        self.calls.append(model)
        if self.succeed_on is None or model == self.succeed_on:
            class _R:
                def __init__(self, vals: list[float]) -> None:
                    class _Emb:
                        def __init__(self, v: list[float]) -> None:
                            self.values = v

                    self.embeddings = [_Emb(vals)]

            return _R(self.embeddings_value)
        # Non-target model — return empty embeddings (probe should skip)
        class _Empty:
            def __init__(self) -> None:
                self.embeddings = []

        return _Empty()


def test_embedding_probe_runs_at_boot_and_logs(
    spy_recorder: _SpyRecorder,
) -> None:
    """Plan 41-05 LAT-06 — `_probe_ga_model_id` runs a canary embed_content
    against the candidate tuple and emits `embedding_model_probe` to the
    recorder. The chosen candidate is whichever one returned valid
    embeddings first (in tuple-order).
    """
    from vibemix.library.embed import (
        GEMINI_EMBEDDING_MODEL_GA_CANDIDATES,
        _probe_ga_model_id,
    )

    # Simulate the GA-renamed candidate succeeding (first tuple entry).
    ga_renamed = GEMINI_EMBEDDING_MODEL_GA_CANDIDATES[0]
    client = _FakeEmbedClient(succeed_on=ga_renamed)
    model_id, version = _probe_ga_model_id(client, recorder=spy_recorder)

    assert model_id == ga_renamed
    # Recorder captured exactly one embedding_model_probe event.
    probe_events = [
        e for e in spy_recorder.events if e["type"] == "embedding_model_probe"
    ]
    assert len(probe_events) == 1
    probe = probe_events[0]
    assert probe["chosen"] == ga_renamed
    # Version contract — GA-renamed → bumped version
    assert "ga" in probe["version"].lower() or "v2" in probe["version"]
    assert ga_renamed in probe["candidates_tried"]
    # Probe duration recorded as integer ms
    assert isinstance(probe["duration_ms"], int)
    assert probe["duration_ms"] >= 0


def test_embedding_probe_falls_back_when_ga_renamed_fails(
    spy_recorder: _SpyRecorder,
) -> None:
    """Plan 41-05 LAT-06 — when the GA-renamed id returns empty, the probe
    advances to the legacy candidate and lands on it.
    """
    from vibemix.library.embed import (
        EXCERPT_STRATEGY_VERSION,
        GEMINI_EMBEDDING_MODEL_GA_CANDIDATES,
        _probe_ga_model_id,
    )

    legacy = GEMINI_EMBEDDING_MODEL_GA_CANDIDATES[1]
    # succeed_on=legacy ⇒ GA-renamed call returns empty embeddings, legacy
    # returns the canary vector.
    client = _FakeEmbedClient(succeed_on=legacy)
    model_id, version = _probe_ga_model_id(client, recorder=spy_recorder)

    assert model_id == legacy
    # Legacy fallback → version stays at the v2.1 default (NOT the bumped one).
    assert version == EXCERPT_STRATEGY_VERSION
    probe_events = [
        e for e in spy_recorder.events if e["type"] == "embedding_model_probe"
    ]
    assert len(probe_events) == 1
    probe = probe_events[0]
    assert probe["chosen"] == legacy
    # Both candidates tried (GA-renamed first, then legacy).
    assert probe["candidates_tried"] == list(GEMINI_EMBEDDING_MODEL_GA_CANDIDATES)


# ---------------------------------------------------------------------------
# Scenario 6 — Plan 41-06 (LAT-09)
# Spike scaffold is documentation only — NOT in the runtime path. Catches
# any accidental import of spikes/* from src/vibemix/.
# ---------------------------------------------------------------------------


def test_spike_scaffold_is_not_in_runtime_path() -> None:
    """LAT-09 — spikes/ scaffolding lives outside src/vibemix/. Any import
    from `spikes.` inside `src/vibemix/` is a boundary violation.
    """
    src_root = Path(__file__).resolve().parents[2] / "src" / "vibemix"
    violations: list[Path] = []
    for py_file in src_root.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        # Two forms — `from spikes` / `import spikes` — both forbid.
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("from spikes") or s.startswith("import spikes"):
                violations.append(py_file)
                break
    assert not violations, (
        f"src/vibemix/ contains spikes/* imports — runtime boundary "
        f"violated by: {[str(v) for v in violations]}"
    )


# ---------------------------------------------------------------------------
# Scenario 7 — Plan 40 Phase-3 carry-forward sanity (LookaheadProvider)
# Confirms Phase 40 Part-3 attachment surface still imports cleanly after
# Phase 41 changes (cross-plan import sanity).
# ---------------------------------------------------------------------------


def test_lookahead_provider_imports_cleanly() -> None:
    """Phase 40 carry-forward — LookaheadProvider must still import after
    Phase 41 changes. The Part-3 audio attach is exercised by Phase 40
    tests; this is a pure import-graph sanity check at the integration
    boundary (Pitfall A7 — `vibemix.llm` doesn't break agent.config)."""
    from vibemix.audio.lookahead import LookaheadProvider  # noqa: F401
    from vibemix.agent.config import LLM_MODEL  # noqa: F401

    # No assertion needed beyond the import succeeding — that's the surface.
    assert LookaheadProvider is not None
