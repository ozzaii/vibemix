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
from types import SimpleNamespace

import pytest

import vibemix.__main__ as main_mod
import vibemix.memory.ingest as ingest_mod
import vibemix.memory.store as store_mod
from vibemix.runtime import session_loop as session_loop_mod
from vibemix.runtime.recordings_index import RetentionSweepResult
from vibemix.runtime.session_loop import SessionLoop

# ---------------------------------------------------------------------------
# Minimal fakes
# ---------------------------------------------------------------------------


class FakeBus:
    """In-memory stand-in for ``WizardBus`` — only what SessionLoop touches."""

    def __init__(self) -> None:
        self.emitted: list[dict] = []

    def register_handler(self, message_type, handler) -> None:
        pass

    async def emit(self, msg: dict) -> None:
        self.emitted.append(msg)


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
    # Memory DB hygiene runs inside that same executor worker, never on the
    # asyncio reaction loop.
    assert "store.reconcile_orphans()" in src
    assert "store.run_retention_sweep()" in src


# ---------------------------------------------------------------------------
# Tier 2 — behavioural: off-loop dispatch, None guard, failure swallow
# ---------------------------------------------------------------------------


@pytest.fixture
def _stub_ingest(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Monkeypatch the ingest entrypoints + the lazy store/embedder builders.

    Records the thread id each entrypoint ran on so the test can assert it was
    an executor thread (off the event loop). Returns a dict the test reads.
    """
    rec: dict = {
        "close_tid": None,
        "boot_tid": None,
        "loop_tid": None,
        "orphan_tids": [],
        "retention_tids": [],
        "stores_closed": 0,
    }

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

    class FakeMemoryStore:
        def reconcile_orphans(self) -> int:
            rec["orphan_tids"].append(threading.get_ident())
            return 0

        def run_retention_sweep(self):
            rec["retention_tids"].append(threading.get_ident())
            return SimpleNamespace(deleted=0, deleted_sessions=[])

        def close(self) -> None:
            rec["stores_closed"] += 1

    monkeypatch.setattr(store_mod, "MemoryStore", lambda *a, **k: FakeMemoryStore())
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
    assert _stub_ingest["orphan_tids"] == []
    assert _stub_ingest["retention_tids"], "memory retention was not swept on close"
    assert _stub_ingest["retention_tids"][0] != _stub_ingest["loop_tid"]
    assert _stub_ingest["stores_closed"] == 1


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
    assert _stub_ingest["orphan_tids"], "memory orphan reconciliation was not swept on boot"
    assert _stub_ingest["retention_tids"], "memory retention was not swept on boot"
    assert _stub_ingest["orphan_tids"][0] != _stub_ingest["loop_tid"]
    assert _stub_ingest["retention_tids"][0] != _stub_ingest["loop_tid"]
    assert _stub_ingest["stores_closed"] == 1


def test_none_recordings_root_skips_ingest(_stub_ingest: dict) -> None:
    """With recordings_root=None neither seam attempts ingest (early-return)."""
    loop = SessionLoop(FakeBus(), recordings_root=None)

    asyncio.run(loop._fire_ingest("boot"))
    asyncio.run(loop._fire_ingest("close", session_dir=Path("/nope")))

    assert _stub_ingest["boot_tid"] is None
    assert _stub_ingest["close_tid"] is None
    assert _stub_ingest["orphan_tids"] == []
    assert _stub_ingest["retention_tids"] == []


def test_disabled_memory_ingest_skips_boot_and_close(
    tmp_path: Path, _stub_ingest: dict
) -> None:
    """Diagnostic session loops can keep retention live without starting CLAP ingest."""
    loop = SessionLoop(
        FakeBus(),
        recordings_root=tmp_path,
        memory_ingest_enabled=False,
    )

    asyncio.run(loop._fire_ingest("boot"))
    asyncio.run(loop._fire_ingest("close", session_dir=tmp_path / "20260531-000000"))

    assert _stub_ingest["boot_tid"] is None
    assert _stub_ingest["close_tid"] is None
    assert _stub_ingest["orphan_tids"] == []
    assert _stub_ingest["retention_tids"] == []


def test_disabled_memory_ingest_keeps_retention_sweep_live(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The diagnostic ``--session`` guard disables CLAP ingest, not retention."""
    calls: list[tuple[Path, int]] = []

    def fake_retention_sweep(root: Path, retention_days: int) -> RetentionSweepResult:
        calls.append((root, retention_days))
        return RetentionSweepResult(deleted_names=[], bytes_pruned=0)

    monkeypatch.setattr(session_loop_mod, "run_retention_sweep", fake_retention_sweep)
    bus = FakeBus()
    loop = SessionLoop(
        bus,
        recordings_root=tmp_path,
        memory_ingest_enabled=False,
    )

    asyncio.run(loop.run_boot_sweeps())

    assert calls == [(tmp_path, loop.config_store.retention_days)]
    assert any(msg.get("type") == "ipc.recordings.usage" for msg in bus.emitted)


def test_ingest_failure_is_swallowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A raising ingest does not propagate — the seam coroutine returns normally."""

    def boom(*a, **k):
        raise RuntimeError("ingest exploded")

    monkeypatch.setattr(ingest_mod, "run_ingest_sweep", boom)
    monkeypatch.setattr(ingest_mod, "ingest_session", boom)
    class FakeMemoryStore:
        def reconcile_orphans(self) -> int:
            return 0

        def run_retention_sweep(self):
            return SimpleNamespace(deleted=0, deleted_sessions=[])

        def close(self) -> None:
            pass

    monkeypatch.setattr(store_mod, "MemoryStore", lambda *a, **k: FakeMemoryStore())
    monkeypatch.setattr(
        SessionLoop, "_build_ingest_embedder", lambda self: FakeEmbedder()
    )

    loop = SessionLoop(FakeBus(), recordings_root=tmp_path)
    session_dir = tmp_path / "s1"
    session_dir.mkdir()

    # Neither seam may raise — the best-effort try/except swallows the failure.
    asyncio.run(loop._fire_ingest("boot"))
    asyncio.run(loop._fire_ingest("close", session_dir=session_dir))


def test_memory_hygiene_failure_is_swallowed_before_ingest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing hygiene pass cannot prevent the boot ingest sweep."""
    calls: dict[str, int] = {"boot": 0, "retention": 0}

    def fake_run_ingest_sweep(recordings_root, store, embedder):
        calls["boot"] += 1
        return []

    class FakeMemoryStore:
        def reconcile_orphans(self) -> int:
            raise RuntimeError("orphan sweep exploded")

        def run_retention_sweep(self):
            calls["retention"] += 1
            raise RuntimeError("retention sweep exploded")

        def close(self) -> None:
            pass

    monkeypatch.setattr(ingest_mod, "run_ingest_sweep", fake_run_ingest_sweep)
    monkeypatch.setattr(store_mod, "MemoryStore", lambda *a, **k: FakeMemoryStore())
    monkeypatch.setattr(
        SessionLoop, "_build_ingest_embedder", lambda self: FakeEmbedder()
    )

    loop = SessionLoop(FakeBus(), recordings_root=tmp_path)

    asyncio.run(loop._fire_ingest("boot"))

    assert calls == {"boot": 1, "retention": 1}


def test_memory_hygiene_dispatches_retention_without_ingest_embedder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Periodic memory hygiene runs retention only, off-loop, with no CLAP build."""
    rec: dict[str, object] = {
        "loop_tid": None,
        "retention_tid": None,
        "closed": 0,
    }

    class FakeMemoryStore:
        def run_retention_sweep(self):
            rec["retention_tid"] = threading.get_ident()
            return SimpleNamespace(deleted=2, deleted_sessions=["old_session"])

        def close(self) -> None:
            rec["closed"] = int(rec["closed"]) + 1

    def embedder_must_not_build(_self):
        raise AssertionError("periodic memory hygiene must not construct CLAP")

    monkeypatch.setattr(store_mod, "MemoryStore", lambda *a, **k: FakeMemoryStore())
    monkeypatch.setattr(SessionLoop, "_build_ingest_embedder", embedder_must_not_build)

    loop = SessionLoop(FakeBus(), recordings_root=tmp_path)

    async def _run() -> None:
        rec["loop_tid"] = threading.get_ident()
        await loop._fire_memory_hygiene("periodic")

    asyncio.run(_run())

    assert rec["retention_tid"] is not None
    assert rec["retention_tid"] != rec["loop_tid"]
    assert rec["closed"] == 1


def test_periodic_recordings_sweep_also_runs_memory_hygiene(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Long-running sessions periodically bound both recordings and memory data."""
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(session_loop_mod, "RETENTION_SWEEP_INTERVAL_S", 0.01)

    async def fake_recordings_sweep(self, trigger: str) -> None:
        calls.append(("recordings", trigger))

    async def fake_memory_hygiene(self, trigger: str) -> None:
        calls.append(("memory", trigger))
        self.request_stop()

    monkeypatch.setattr(SessionLoop, "_fire_one_retention_sweep", fake_recordings_sweep)
    monkeypatch.setattr(SessionLoop, "_fire_memory_hygiene", fake_memory_hygiene)
    loop = SessionLoop(FakeBus(), recordings_root=tmp_path)

    async def _run() -> None:
        await asyncio.wait_for(loop._periodic_retention_sweep_loop(), timeout=1.0)

    asyncio.run(_run())

    assert calls == [("recordings", "periodic"), ("memory", "periodic")]


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


# ---------------------------------------------------------------------------
# Phase 77 Plan 01 (Wave 0) — WIRE-05: ingest fires on the LIVE main() path.
#
# The SessionLoop tests above prove the seam dispatches correctly; but the live
# runtime builds ``_session_ipc = SessionLoop(...)`` and only calls
# ``register_handlers()`` — it NEVER calls ``run()``, so the boot+close ingest
# sweeps never fire on a real session (only the stub SessionLoop.run path did).
# WIRE-05 lifts ``_fire_ingest("boot")`` + ``_fire_ingest("close", ...)`` into
# ``main()`` on that SAME instance, gated behind ``recall_enabled``.
#
# CRITICAL anti-double-retention guard: main() must call ``_fire_ingest`` —
# NOT ``run_boot_sweeps`` / ``on_session_close`` (those fire BOTH retention AND
# ingest, and main() already runs its own retention sweeps → double prune).
#
# This is a SOURCE-TEXT tier (the behavioural wiring lives behind a live
# orchestrator that cannot be driven without audio devices). xfail-strict until
# Plan 04 wires it; flips to a real pass when the executor removes the marker.
# ---------------------------------------------------------------------------


def _main_source() -> str:
    src_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "vibemix"
        / "__main__.py"
    )
    return src_path.read_text(encoding="utf-8")


def test_main_fires_boot_and_close_ingest() -> None:
    """main() calls _fire_ingest for boot AND close on the live _session_ipc."""
    src = _main_source()
    # Boot + close ingest triggers appear on the live path.
    assert '_fire_ingest("boot"' in src or "_fire_ingest('boot'" in src
    assert '_fire_ingest("close"' in src or "_fire_ingest('close'" in src
    # The close call carries the just-finished session dir.
    assert "session_dir=" in src


def test_memory_ingest_resolver_follows_profile_consent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Memory accrual is profile-consent gated, separate from recall."""
    monkeypatch.delenv("VIBEMIX_MEMORY_INGEST_ENABLED", raising=False)
    monkeypatch.setattr(main_mod, "load_consent", lambda: True)
    assert main_mod._resolve_memory_ingest_enabled() is True
    monkeypatch.setattr(main_mod, "load_consent", lambda: False)
    assert main_mod._resolve_memory_ingest_enabled() is False


def test_memory_ingest_resolver_honors_dev_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dev/CI may override ingest without flipping recall."""
    monkeypatch.setattr(main_mod, "load_consent", lambda: False)
    monkeypatch.setenv("VIBEMIX_MEMORY_INGEST_ENABLED", "yes")
    assert main_mod._resolve_memory_ingest_enabled() is True
    monkeypatch.setattr(main_mod, "load_consent", lambda: True)
    monkeypatch.setenv("VIBEMIX_MEMORY_INGEST_ENABLED", "0")
    assert main_mod._resolve_memory_ingest_enabled() is False


def test_main_ingest_is_gated_behind_memory_ingest_enabled() -> None:
    """The main-path ingest is gated on profile-consent accrual, not recall."""
    src = _main_source()
    assert "recall_enabled" in src
    assert "recall_enabled = _resolve_recall_enabled" in src
    assert "memory_ingest_enabled = _resolve_memory_ingest_enabled()" in src
    assert "memory_ingest_enabled=memory_ingest_enabled" in src
    assert "memory_ingest_enabled=recall_enabled" not in src
    # Heuristic proximity gate: a memory_ingest_enabled guard appears in the
    # same source region as the _fire_ingest call (additive-gated cold path).
    idx = src.find("_fire_ingest")
    assert idx != -1, "_fire_ingest not present in main() yet"
    window = src[max(0, idx - 1200) : idx + 1200]
    assert "memory_ingest_enabled" in window, (
        "_fire_ingest on the main() path must be gated behind memory_ingest_enabled"
    )


def test_diagnostic_run_session_disables_memory_ingest() -> None:
    """The sidecar-only ``--session`` probe must not launch CLAP memory indexing."""
    src = _session_loop_source()
    idx = src.find("async def run_session")
    assert idx != -1, "run_session not found"
    window = src[idx : idx + 1800]
    assert "memory_ingest_enabled=False" in window


def test_main_does_not_call_combined_retention_methods() -> None:
    """main() must NOT call run_boot_sweeps / on_session_close (double-retention).

    GREEN now AND after Plan 04 — main() owns its own retention sweeps, so the
    WIRE-05 lift uses the ingest-only ``_fire_ingest``, never the combined
    SessionLoop methods that also re-run retention.
    """
    src = _main_source()
    assert "run_boot_sweeps(" not in src, (
        "main() must not call run_boot_sweeps — it double-runs retention"
    )
    assert "on_session_close(" not in src, (
        "main() must not call on_session_close — it double-runs retention"
    )
