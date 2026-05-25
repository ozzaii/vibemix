# SPDX-License-Identifier: Apache-2.0
"""Phase 77 Plan 01 (Wave 0) — WIRE-01 failing scaffold: Grounding → live agent.

The ``Grounding`` engine ("what's playing") is built + armed at boot
(``__main__.py:1147``) but ``DJCoHostAgent.__init__`` has no ``grounding``
kwarg, so it is fully orphaned. This file is the AUTOMATED PROOF that the wire
exists once Plan 04 lands — written FIRST so the cold-path byte-identity
guarantee is captured as an assertion, not a hope.

Three enforcement tiers (mirrors ``tests/memory/test_ingest_wiring.py``):

  * SOURCE-TEXT GATE — static proof the grounding consult is dispatched
    OFF the reaction loop (a ``run_in_executor`` argument), never inline-
    awaited (the TTFT regression the recall seam exists to avoid). xfail-
    strict until Plan 04 wires it.
  * BEHAVIOURAL — construct ``DJCoHostAgent`` with a duck-typed fake
    ``Grounding`` (records the thread id its ``on_event`` ran on; returns a
    fake CITED ``Citation``). Drive ``set_next_event`` with a TRACK_CHANGE
    under a running loop; assert the dispatch ran on an executor thread
    (id != loop thread). Plus the cold path: ``grounding`` omitted →
    byte-identical (no dispatch attempted, no attribute required). The
    dispatch-fires assertions are xfail-strict until Plan 04.
  * CITATION-GATE — the existing registry contract: a ``[track:<id>]`` for an
    id seeded via ``register_library`` resolves in ``EvidenceRegistry.has``.
    This is GREEN now — it proves the injection target survives the linter.

No network: fakes stand in; no ``genai.Client`` is ever constructed; runs
with NO ``GEMINI_API_KEY``.
"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any

import pytest
from livekit.agents import Agent

from vibemix.agent import DJCoHostAgent
from vibemix.library.grounding import Citation, Grounding
from vibemix.state import Event, MusicState
from vibemix.state.evidence_registry import EvidenceRegistry

DJ_COHOST_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "vibemix"
    / "agent"
    / "dj_cohost.py"
)


def _dj_cohost_source() -> str:
    return DJ_COHOST_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeRecorder:
    def __init__(self, session_dir: Path) -> None:
        self.session_dir = session_dir
        self.events: list[tuple[str, dict]] = []

    def log_event(self, kind: str, **fields: Any) -> None:
        self.events.append((kind, fields))

    def push_voice(self, pcm: bytes) -> None:  # pragma: no cover
        pass


class _FakeGrounding:
    """Duck-typed stand-in for ``library.grounding.Grounding``.

    Records the thread id its ``on_event`` ran on (so a test can assert it was
    an executor thread, OFF the event loop) and returns a fake CITED Citation
    with a known ``track_id`` from ``get_latest_citation``.
    """

    def __init__(self, track_id: str = "track-77") -> None:
        self.on_event_tid: int | None = None
        self.on_event_calls: list[tuple[str, Any]] = []
        self.cleared = 0
        self._track_id = track_id

    def on_event(
        self,
        event_type: str,
        audio_bytes: bytes | None,
        *,
        event_id: str | None = None,
        mime_type: str = "audio/wav",
    ) -> Citation | None:
        self.on_event_tid = threading.get_ident()
        self.on_event_calls.append((event_type, audio_bytes))
        return self.get_latest_citation()

    def get_latest_citation(self) -> Citation:
        return Citation(
            event_id="ev-fake",
            decision="cited",
            track_id=self._track_id,
            cosine=0.91,
            ts=0.0,
        )

    def clear(self) -> None:
        self.cleared += 1


def _build_state() -> MusicState:
    s = MusicState()
    s.audible = True
    s.audible_deck = "A"
    s.phase = "peak"
    s.bpm = 128.0
    return s


def _kwargs(mocker, tmp_path: Path) -> dict[str, Any]:
    return {
        "genai_client": mocker.MagicMock(),
        "clean_audio_buf": mocker.MagicMock(),
        "screen_buf": mocker.MagicMock(),
        "state": _build_state(),
        "recorder": _FakeRecorder(tmp_path),
        "llm_inst": mocker.MagicMock(),
        "tts_inst": mocker.MagicMock(),
    }


# ---------------------------------------------------------------------------
# Tier 1 — SOURCE-TEXT GATE (off-loop wiring shape). xfail-strict until Plan 04.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="WIRE-01 not yet wired (Plan 04)", strict=True)
def test_agent_references_grounding_engine() -> None:
    """dj_cohost.py consults the grounding engine (kwarg + latest-citation pull)."""
    src = _dj_cohost_source()
    assert "grounding" in src
    assert "get_latest_citation" in src


@pytest.mark.xfail(reason="WIRE-01 not yet wired (Plan 04)", strict=True)
def test_grounding_dispatch_is_off_loop_run_in_executor() -> None:
    """The grounding consult is dispatched OFF the loop (run_in_executor arg).

    Static proof that the embed is pre-dispatched (mirrors the recall seam),
    NEVER inline-awaited inside ``llm_node`` — that is the entire reason the
    pre-dispatch+latch+pull pattern exists (TTFT non-regression).
    """
    src = _dj_cohost_source()
    # The grounding service's on_event is handed to run_in_executor (off-loop).
    assert "run_in_executor" in src
    # A sibling dispatcher to _maybe_dispatch_recall — the off-loop seam.
    assert "_maybe_dispatch_grounding" in src
    # The track-aware event gate is imported from the grounding module.
    assert "TRACK_AWARE_EVENTS" in src


# ---------------------------------------------------------------------------
# Tier 2 — BEHAVIOURAL: off-loop dispatch + cold-path byte-identity
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="WIRE-01 dispatch not yet wired (Plan 04)", strict=True
)
def test_track_change_dispatches_grounding_off_loop(
    mocker, tmp_path: Path
) -> None:
    """A TRACK_CHANGE event pre-dispatches grounding.on_event on an executor thread."""
    mocker.patch.object(Agent, "__init__", return_value=None)
    fake = _FakeGrounding()
    agent = DJCoHostAgent(**_kwargs(mocker, tmp_path), grounding=fake)

    loop_tid: dict[str, int | None] = {"tid": None}

    async def _run() -> None:
        loop_tid["tid"] = threading.get_ident()
        state = _build_state()
        agent.set_next_event(Event("TRACK_CHANGE", state, {}))
        # Let the pre-dispatched executor task complete.
        await asyncio.sleep(0.05)

    asyncio.run(_run())

    assert fake.on_event_tid is not None, "grounding.on_event was never called"
    assert fake.on_event_tid != loop_tid["tid"], (
        "grounding.on_event ran on the event-loop thread — must be off-loop "
        "via run_in_executor (TTFT non-regression)"
    )


def test_cold_path_no_grounding_is_byte_identical(mocker, tmp_path: Path) -> None:
    """grounding omitted → no dispatch attempted; set_next_event is a no-op seam.

    This is the v8.0-baseline cold-path guarantee: a TRACK_CHANGE with no
    grounding service wired behaves exactly as today (no crash, no dispatch).
    GREEN now AND after Plan 04 (the gate is ``grounding is None``).
    """
    mocker.patch.object(Agent, "__init__", return_value=None)
    agent = DJCoHostAgent(**_kwargs(mocker, tmp_path))

    async def _run() -> None:
        state = _build_state()
        # Must not raise — the cold path attempts no grounding work.
        agent.set_next_event(Event("TRACK_CHANGE", state, {}))
        await asyncio.sleep(0.01)

    asyncio.run(_run())
    # No grounding attribute is required on the cold path; if one exists it is
    # None. (getattr default keeps this green pre- and post-Plan-04.)
    assert getattr(agent, "_grounding", None) is None


# ---------------------------------------------------------------------------
# Tier 3 — CITATION-GATE: the injected [track:<id>] resolves in the registry.
# GREEN NOW — proves the injection target survives the CitationLinter.
# ---------------------------------------------------------------------------


class _FakeLib:
    """Duck-typed RekordboxLibrary — register_library only reads ``.tracks``."""

    def __init__(self, track_ids: list[str]) -> None:
        self.tracks = {tid: object() for tid in track_ids}


def test_cited_track_id_resolves_in_evidence_registry() -> None:
    """A [track:<id>] for a register_library-seeded id resolves via has().

    The grounding injection writes ``[track:<id>]`` into the prompt; the
    CitationLinter (invariant #2) keeps the turn iff
    ``EvidenceRegistry.has("track", id, t)`` is True. register_library seeds
    every library track id at t_session=0.0 — so a live lookup at t≈0 resolves.
    """
    reg = EvidenceRegistry()
    lib = _FakeLib(["track-77", "track-99"])
    registered = reg.register_library(lib, t_session=0.0)
    assert registered == 2

    cit = _FakeGrounding(track_id="track-77").get_latest_citation()
    assert cit.is_cited
    # The linter resolves the cited id against the registry (tol default 1.0).
    assert reg.has("track", cit.track_id, 0.0) is True
    # A non-seeded id does NOT resolve → the linter would strip that turn.
    assert reg.has("track", "track-not-in-library", 0.0) is False


def test_grounding_module_contract_is_stable() -> None:
    """The real Grounding exposes the seam the agent will consume (smoke).

    No genai.Client is constructed — we only assert the public surface the
    WIRE-01 injection depends on exists and is callable shape-wise.
    """
    assert hasattr(Grounding, "on_event")
    assert hasattr(Grounding, "get_latest_citation")
    assert hasattr(Grounding, "clear")
