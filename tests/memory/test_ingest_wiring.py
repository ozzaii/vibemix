# SPDX-License-Identifier: Apache-2.0
"""Phase 64 Plan 03 (Wave 3) — runtime-wiring gate for the memory ingest.

Proves the two seams in ``vibemix.runtime.session_loop`` dispatch the ingest
OFF the asyncio reaction loop and honour the contract:

  * ``on_session_close`` enqueues ``ingest_session`` for the just-finished
    session via ``loop.run_in_executor`` (NOT inline on the loop thread).
  * ``run_boot_sweeps`` enqueues ``run_ingest_sweep`` over the recordings tree
    via ``loop.run_in_executor``.
  * Both early-return when ``recordings_root`` is None (mirror the existing
    retention-sweep guard) — no ingest attempted.
  * A raising ingest is swallowed — the seam coroutine returns normally
    (best-effort / never-raise, T-64-09).

Two enforcement tiers (mirrors the no-live-path gate's static + behavioural
split):

  * a source-text assertion that the wiring imports ``memory.ingest`` and the
    ingest calls appear as ``run_in_executor`` arguments;
  * behavioural tests that monkeypatch the ingest entrypoints + the lazy
    embedder/store builders to fakes, drive the seam coroutines under asyncio,
    and assert the recorded executor-thread id != the event-loop thread id
    (the off-loop proof) plus the None-guard + failure-swallow.

No network: a fake embedder/store stands in; the lazy ``_build_ingest_embedder``
is monkeypatched so no ``genai.Client`` is ever constructed.
"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path

import pytest

import vibemix.memory.ingest as ingest_mod
import vibemix.memory.store as store_mod
from vibemix.runtime.session_loop import SessionLoop


# ---------------------------------------------------------------------------
# Minimal fakes
# ---------------------------------------------------------------------------


class FakeBus:
    """In-memory stand-in for ``WizardBus`` — only what SessionLoop touches."""

    def register_handler(self, message_type, handler) -> None:  # noqa: D401
        pass

    async def emit(self, msg: dict) -> None:
        pass


class FakeRecorder:
    """Duck-typed VoiceRecorder — exposes only ``session_dir`` (recorder.py:211)."""

    def __init__(self, session_dir: Path) -> None:
        self.session_dir = session_dir


class FakeEmbedder:
    """Stand-in embedder — never called in these tests (ingest is monkeypatched)."""

    _model = ""

    def embed_query(self, text: str):  # pragma: no cover - never reached
        raise AssertionError("embed_query must not be called in wiring tests")


# ---------------------------------------------------------------------------
# Tier 1 — source-text gate (wiring shape)
# ---------------------------------------------------------------------------


def _session_loop_source() -> str:
    src_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "vibemix"
        / "runtime"
        / "session_loop.py"
    )
    return src_path.read_text(encoding="utf-8")


def test_wiring_imports_memory_ingest() -> None:
    """The runtime imports ``memory.ingest`` (the gate-safe one-way arrow)."""
    src = _session_loop_source()
    assert "from vibemix.memory.ingest import" in src


def test_wiring_dispatches_through_run_in_executor() -> None:
    """The ingest worker is dispatched via ``run_in_executor`` (not inline).

    Source-text proof that ALL heavy FS+embed work is pushed off the loop: the
    seam awaits ``run_in_executor(None, _worker)`` and the ingest entrypoints
    (``ingest_session`` / ``run_ingest_sweep``) are called INSIDE that off-loop
    worker — never on the event-loop thread.
    """
    src = _session_loop_source()
    assert "run_in_executor" in src
    # The synchronous worker (heavy imports + embedder build + ingest) is the
    # run_in_executor target — the seam coroutine returns to the loop at once.
    assert "await loop.run_in_executor(None, _worker)" in src
    # The ingest entrypoints are imported + invoked INSIDE the off-loop worker
    # (function-local import = the gate-safe one-way arrow), never on the loop.
    assert "from vibemix.memory.ingest import ingest_session, run_ingest_sweep" in src
    assert "ingest_session(session_dir, store, embedder)" in src
    assert "run_ingest_sweep(recordings_root, store, embedder)" in src


# ---------------------------------------------------------------------------
# Tier 2 — behavioural: off-loop dispatch, None guard, failure swallow
# ---------------------------------------------------------------------------


@pytest.fixture
def _stub_ingest(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Monkeypatch the ingest entrypoints + the lazy store/embedder builders.

    Records the thread id each entrypoint ran on so the test can assert it was
    an executor thread (off the event loop). Returns a dict the test reads.
    """
    rec: dict = {"close_tid": None, "boot_tid": None, "loop_tid": None}

    def fake_ingest_session(session_dir, store, embedder):
        rec["close_tid"] = threading.get_ident()
        rec["close_session_dir"] = session_dir
        return ingest_mod.IngestResult(session_id=Path(session_dir).name)

    def fake_run_ingest_sweep(recordings_root, store, embedder):
        rec["boot_tid"] = threading.get_ident()
        rec["boot_root"] = recordings_root
        return []

    monkeypatch.setattr(ingest_mod, "ingest_session", fake_ingest_session)
    monkeypatch.setattr(ingest_mod, "run_ingest_sweep", fake_run_ingest_sweep)
    # The lazy store/embedder builders must never touch sqlite-vec or genai.
    monkeypatch.setattr(store_mod, "MemoryStore", lambda *a, **k: object())
    monkeypatch.setattr(
        SessionLoop, "_build_ingest_embedder", lambda self: FakeEmbedder()
    )
    return rec


def test_close_seam_dispatches_off_loop_thread(
    tmp_path: Path, _stub_ingest: dict
) -> None:
    """on_session_close runs ingest_session on an executor thread, not the loop."""
    session_dir = tmp_path / "2026-05-22_0900"
    session_dir.mkdir()
    recorder = FakeRecorder(session_dir)
    loop = SessionLoop(
        FakeBus(), recordings_root=tmp_path, active_recorder=recorder
    )

    async def _run() -> None:
        _stub_ingest["loop_tid"] = threading.get_ident()
        await loop._fire_ingest("close", session_dir=session_dir)

    asyncio.run(_run())

    assert _stub_ingest["close_tid"] is not None, "ingest_session was never called"
    assert _stub_ingest["close_tid"] != _stub_ingest["loop_tid"], (
        "ingest_session ran on the event-loop thread — must be off-loop via "
        "run_in_executor"
    )
    assert _stub_ingest["close_session_dir"] == session_dir


def test_boot_seam_dispatches_off_loop_thread(
    tmp_path: Path, _stub_ingest: dict
) -> None:
    """run_boot_sweeps runs run_ingest_sweep on an executor thread, not the loop."""
    loop = SessionLoop(FakeBus(), recordings_root=tmp_path)

    async def _run() -> None:
        _stub_ingest["loop_tid"] = threading.get_ident()
        await loop._fire_ingest("boot")

    asyncio.run(_run())

    assert _stub_ingest["boot_tid"] is not None, "run_ingest_sweep was never called"
    assert _stub_ingest["boot_tid"] != _stub_ingest["loop_tid"], (
        "run_ingest_sweep ran on the event-loop thread — must be off-loop via "
        "run_in_executor"
    )
    assert _stub_ingest["boot_root"] == tmp_path


def test_none_recordings_root_skips_ingest(_stub_ingest: dict) -> None:
    """With recordings_root=None neither seam attempts ingest (early-return)."""
    loop = SessionLoop(FakeBus(), recordings_root=None)

    asyncio.run(loop._fire_ingest("boot"))
    asyncio.run(loop._fire_ingest("close", session_dir=Path("/nope")))

    assert _stub_ingest["boot_tid"] is None
    assert _stub_ingest["close_tid"] is None


def test_ingest_failure_is_swallowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A raising ingest does not propagate — the seam coroutine returns normally."""

    def boom(*a, **k):
        raise RuntimeError("ingest exploded")

    monkeypatch.setattr(ingest_mod, "run_ingest_sweep", boom)
    monkeypatch.setattr(ingest_mod, "ingest_session", boom)
    monkeypatch.setattr(store_mod, "MemoryStore", lambda *a, **k: object())
    monkeypatch.setattr(
        SessionLoop, "_build_ingest_embedder", lambda self: FakeEmbedder()
    )

    loop = SessionLoop(FakeBus(), recordings_root=tmp_path)
    session_dir = tmp_path / "s1"
    session_dir.mkdir()

    # Neither seam may raise — the best-effort try/except swallows the failure.
    asyncio.run(loop._fire_ingest("boot"))
    asyncio.run(loop._fire_ingest("close", session_dir=session_dir))


def test_close_seam_falls_back_to_sweep_without_recorder(
    tmp_path: Path, _stub_ingest: dict
) -> None:
    """on_session_close with no live recorder falls back to the boot-style sweep.

    The marker makes the sweep a near no-op; here we only assert the fallback
    path dispatches run_ingest_sweep (not ingest_session) when session_dir is
    None.
    """
    loop = SessionLoop(FakeBus(), recordings_root=tmp_path, active_recorder=None)

    asyncio.run(loop._fire_ingest("close", session_dir=None))

    assert _stub_ingest["boot_tid"] is not None, (
        "close with no session_dir should fall back to run_ingest_sweep"
    )
    assert _stub_ingest["close_tid"] is None
