# SPDX-License-Identifier: Apache-2.0
"""Phase 81 BENCH — shared offline fixtures.

Two pillars of honest-green for the bench harness:

1. **Offline clients** — ``_FakeClient`` returns canned text + a synthetic
   ``usage_metadata`` namespace with ZERO network (no ``genai.Client``, no
   ``GEMINI_API_KEY``, no socket). ``_RaisingClient`` raises a fake 429 so
   Plan 02's per-cell fail-safe (Pitfall 2: a 429 must NOT abort the sweep)
   can be driven offline. The call shape mirrors
   ``/tmp/truthtest/run_test.py`` + ``library/agent.py:_gemini_call``:
   ``client.models.generate_content(model=, contents=, config=)`` where
   ``.models`` is the client itself.

2. **Real fixtures** — ``bench_data_dir`` resolves the ``.mp3`` excerpts
   (env-overridable via ``VIBEMIX_BENCH_DATA_DIR``); the ``MusicState``
   builders below construct a REAL ``MusicState`` + a populated
   ``EvidenceRegistry`` snapshot so the bench's groundedness path exercises
   the product's actual additive-grounding gating, not ad-hoc dicts
   (81-PATTERNS "bench/fixtures.py").

No file under ``src/vibemix/`` is touched by this plan — the bench source
lands in Plans 02/03/04.
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from vibemix.state.evidence_registry import EvidenceRegistry
from vibemix.state.music_state import MusicState

# The canned offline reaction. A cited DJ line whose ``[aud:bpm@0.0]`` atom
# resolves against a snapshot carrying ``aud/bpm@0.0`` (see _grounded_snapshot)
# — so a groundedness scorer reusing CitationLinter scores it "valid".
_DEFAULT_CANNED = "that 303 line opened up [aud:bpm@0.0]"


class _FakeClient:
    """Offline stand-in for ``genai.Client`` — returns canned text + synthetic
    ``usage_metadata``, never touches the network.

    ``.models`` is ``self`` (mirrors the real client where the call is
    ``client.models.generate_content(...)``). ``generate_content`` keys the
    reply text by ``model`` so a study sweep can hand different aliases
    distinct canned outputs; the default is a cited DJ line.

    NOTE: deliberately NO ``import socket`` / ``http`` / network anywhere on
    this path — the whole point is a zero-API honest-green gate.
    """

    def __init__(self, canned: dict[str, str] | None = None) -> None:
        self.models = self
        self._canned = dict(canned or {})
        self.calls: list[dict[str, object]] = []  # spy: every call recorded

    def generate_content(
        self,
        *,
        model: str,
        contents: object,
        config: object = None,
    ) -> SimpleNamespace:
        self.calls.append({"model": model, "contents": contents, "config": config})
        text = self._canned.get(model, _DEFAULT_CANNED)
        return SimpleNamespace(
            text=text,
            usage_metadata=SimpleNamespace(
                prompt_token_count=1900,
                candidates_token_count=40,
                total_token_count=1940,
                cached_content_token_count=0,
            ),
        )


class _RaisingClient:
    """Offline client whose ``generate_content`` always raises a fake 429.

    Drives Plan 02's per-cell fail-safe: a rate-limited / errored cell must
    record ``result.error`` (non-None) and the sweep must CONTINUE to the next
    cell — never abort, never fabricate output (81-RESEARCH Pitfall 2; the
    floor study's real 429 billing block is the documented reason).
    """

    def __init__(self) -> None:
        self.models = self
        self.calls: list[dict[str, object]] = []

    def generate_content(
        self,
        *,
        model: str,
        contents: object,
        config: object = None,
    ) -> SimpleNamespace:  # pragma: no cover - always raises before returning
        self.calls.append({"model": model, "contents": contents, "config": config})
        # Mimic a google-genai 429 surface without importing the SDK error type.
        raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded (fake)")


# --------------------------------------------------------------------------- #
# Client fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def fake_client() -> _FakeClient:
    """A zero-network client returning the default canned cited DJ line."""
    return _FakeClient()


@pytest.fixture
def raising_client() -> _RaisingClient:
    """A zero-network client that always raises a fake 429 — the fail-safe driver."""
    return _RaisingClient()


# --------------------------------------------------------------------------- #
# Data-dir fixture (env-overridable)
# --------------------------------------------------------------------------- #


def _resolve_bench_data_dir() -> Path:
    """The .mp3 excerpt dir. ``VIBEMIX_BENCH_DATA_DIR`` overrides the default
    (in-repo ``tests/bench/data/``) so CI / other machines can point elsewhere.
    """
    override = os.environ.get("VIBEMIX_BENCH_DATA_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent / "data"


@pytest.fixture
def bench_data_dir() -> Path:
    """Resolved path to the bench .mp3 excerpts, honoring VIBEMIX_BENCH_DATA_DIR."""
    return _resolve_bench_data_dir()


# --------------------------------------------------------------------------- #
# MusicState + snapshot builders — REAL dataclass, not ad-hoc dicts
# --------------------------------------------------------------------------- #


def _grounded_snapshot() -> dict[str, dict[str, tuple[float, ...]]]:
    """A populated EvidenceRegistry snapshot carrying ``aud/bpm@0.0``.

    The default canned line cites ``[aud:bpm@0.0]``; this snapshot makes that
    citation RESOLVE (CitationLinter ±tol), so a grounded cell scores high and
    a fabricated atom absent from the snapshot scores 0. Built via the real
    registry (not a hand-rolled dict) so the snapshot shape is the exact one
    the linter consumes.
    """
    reg = EvidenceRegistry()
    reg.write("aud", "bpm", 0.0)
    reg.write("aud", "sub", 0.0)
    return reg.snapshot()


def build_snapshot_state() -> tuple[MusicState, dict[str, dict[str, tuple[float, ...]]]]:
    """The ``snapshot`` contexting axis — a COLD audible MusicState (no
    trajectory fields) + its grounded snapshot.

    ``trajectory_narrative=""`` / empty ``phase_history`` / empty ``long_arc``
    means the coach's additive trajectory branch stays OFF — the byte-identical
    v8.0 cold path. Returned alongside the snapshot the cell is scored against.
    """
    state = MusicState(
        audible=True,
        rms=0.32,
        bpm=150.0,
        onset_density=0.55,
        phase="groove",
        detected_genre="hardtechno",
        genre_confidence=0.82,
    )
    return state, _grounded_snapshot()


def build_trajectory_state() -> tuple[MusicState, dict[str, dict[str, tuple[float, ...]]]]:
    """The ``trajectory`` contexting axis — the same audible state with the
    multi-scale PERCEIVE-02 fields populated (trajectory narrative + history +
    long-arc), so the coach's additive trajectory branch fires.
    """
    state = MusicState(
        audible=True,
        rms=0.32,
        bpm=150.0,
        onset_density=0.55,
        phase="build",
        detected_genre="hardtechno",
        genre_confidence=0.82,
        trajectory_narrative="build->drop->groove; building; last move: bass-swap 20s ago",
        phase_history=[(10.0, "groove", "build"), (30.0, "build", "drop")],
        long_arc=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
    )
    return state, _grounded_snapshot()


@pytest.fixture
def snapshot_state() -> tuple[MusicState, dict[str, dict[str, tuple[float, ...]]]]:
    """Cold-contexting MusicState + grounded snapshot (the ``snapshot`` axis)."""
    return build_snapshot_state()


@pytest.fixture
def trajectory_state() -> tuple[MusicState, dict[str, dict[str, tuple[float, ...]]]]:
    """Warm-contexting MusicState + grounded snapshot (the ``trajectory`` axis)."""
    return build_trajectory_state()
