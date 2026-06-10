# SPDX-License-Identifier: Apache-2.0
"""Phase 27-05 — invocation tests proving register_library is wired into __main__.py.

The grep gate (Test 6) is the Pitfall P48 CI invariant. Tests 1-5 use
mocker.spy on the EvidenceRegistry.register_library bound method to assert
the wire-in actually fires when a synthetic ~/.cache/vibemix/library.pkl
exists, and does NOT fire when the cache is absent or fails to load.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[2]


def _run_wire_in_block(monkeypatch: pytest.MonkeyPatch | None = None):
    """Re-execute the 5-line wire-in block from __main__.py in test isolation.

    This is the EXACT block inserted at __main__.py:670-680. Tests assert
    the spy records the call when the block runs against the synthetic
    library cache fixture.
    """
    from vibemix.library.rekordbox import RekordboxLibrary
    from vibemix.state.evidence_registry import EvidenceRegistry

    evidence_registry = EvidenceRegistry()

    library_cache = Path.home() / ".cache" / "vibemix" / "library.pkl"
    if library_cache.exists():
        lib = RekordboxLibrary()
        if lib.try_load_cache():
            evidence_registry.register_library(lib)
            return ("registered", evidence_registry, lib)
        return ("cache_failed", evidence_registry, lib)
    return ("no_cache", evidence_registry, None)


def test_register_library_invoked_when_cache_exists(
    synthetic_library_cache: Path,
    synthetic_library,
    mocker,
) -> None:
    """Test 1: synthetic cache present + try_load_cache → True → spy records call."""
    from vibemix.library.rekordbox import RekordboxLibrary
    from vibemix.state.evidence_registry import EvidenceRegistry

    spy = mocker.spy(EvidenceRegistry, "register_library")

    # Mock try_load_cache to return True deterministically and seed tracks
    # so the library has a non-empty mapping for register_library.
    def fake_load(self) -> bool:
        self.tracks = synthetic_library.tracks
        return True

    mocker.patch.object(RekordboxLibrary, "try_load_cache", new=fake_load)

    status, _registry, _lib = _run_wire_in_block()
    assert status == "registered"
    assert spy.call_count == 1, (
        f"register_library not invoked when cache exists; spy={spy.call_args_list}"
    )


def test_register_library_not_invoked_when_cache_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mocker,
) -> None:
    """Test 2: cache absent → register_library NOT called."""
    from vibemix.state.evidence_registry import EvidenceRegistry

    # Re-root home but DO NOT create the cache file.
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    spy = mocker.spy(EvidenceRegistry, "register_library")
    status, _registry, _lib = _run_wire_in_block()
    assert status == "no_cache"
    assert spy.call_count == 0


def test_register_library_not_invoked_when_cache_corrupt(
    synthetic_library_cache: Path,
    mocker,
) -> None:
    """Test 3: cache exists but try_load_cache returns False → no register_library."""
    from vibemix.library.rekordbox import RekordboxLibrary
    from vibemix.state.evidence_registry import EvidenceRegistry

    mocker.patch.object(RekordboxLibrary, "try_load_cache", return_value=False)
    spy = mocker.spy(EvidenceRegistry, "register_library")

    status, _registry, _lib = _run_wire_in_block()
    assert status == "cache_failed"
    assert spy.call_count == 0


def test_grep_gate_register_library_in_main() -> None:
    """Test 6 (Pitfall P48 CI gate): grep proves the wire-in line exists in __main__.py."""
    r = subprocess.run(
        ["grep", "-q", "evidence_registry.register_library", "src/vibemix/__main__.py"],
        cwd=str(PROJECT_ROOT),
    )
    assert r.returncode == 0, (
        "P48 grep gate failed: register_library not called from __main__.py — "
        "the orphan ships AGAIN. Restore the wire-in patch."
    )


def test_grep_gate_marker_comment_present() -> None:
    """The wire-in stays findable at BOTH live surfaces.

    The original "Plan 27-05 final-mile wiring" marker comment was dropped in
    the 364c55ba restructure, which split the wiring in two: live-session
    start registers the library in ``__main__.py`` (guarded by the
    ``library.pkl`` existence check), and post-import refresh re-registers it
    via ``SessionLoop._refresh_library_registry`` in
    ``src/vibemix/runtime/session_loop.py``. Pin both anchors so a future
    refactor can't orphan either half silently.
    """
    main_src = (PROJECT_ROOT / "src/vibemix/__main__.py").read_text()
    assert 'library_cache = Path.home() / ".cache" / "vibemix" / "library.pkl"' in main_src
    assert "evidence_registry.register_library(deck_library)" in main_src

    loop_src = (PROJECT_ROOT / "src/vibemix/runtime/session_loop.py").read_text()
    assert "async def _refresh_library_registry(self) -> None:" in loop_src
    assert "self.evidence_registry.register_library(lib)" in loop_src


def test_rekordbox_library_import_present_in_main() -> None:
    """Import statement is in __main__.py so the wire-in can use the symbol."""
    r = subprocess.run(
        [
            "grep",
            "-q",
            "from vibemix.library.rekordbox import RekordboxLibrary",
            "src/vibemix/__main__.py",
        ],
        cwd=str(PROJECT_ROOT),
    )
    assert r.returncode == 0


def test_library_import_routes_directories_to_folder_ingest_before_xml_import() -> None:
    """Dropping a folder must not fall through to Rekordbox XML parsing.

    364c55ba moved the import routing (alive, same precedence) from
    ``__main__.py`` onto ``SessionLoop._run_library_import`` in
    ``src/vibemix/runtime/session_loop.py``; the XML tail is now the
    ``_start_xml_import`` helper (``import_library_async``), not an inline
    ``LibraryImporter`` block.
    """
    source = (PROJECT_ROOT / "src/vibemix/runtime/session_loop.py").read_text()
    branch_idx = source.index("if source_path.is_dir():")
    folder_idx = source.index("await self._start_folder_import(source_path)", branch_idx)
    return_idx = source.index("return", folder_idx)
    xml_idx = source.index("await self._start_xml_import(source_path)", return_idx)

    assert branch_idx < folder_idx < return_idx < xml_idx


def test_library_import_routes_traktor_and_virtualdj_catalogs_before_xml_import() -> None:
    """Discovered non-Rekordbox catalogs must not be parsed as Rekordbox XML.

    Routing lives on ``SessionLoop`` since 364c55ba. The catalog sniffing
    helper also grew Engine DJ + Serato support — pin all four so a source
    class can't silently drop out of the import path.
    """
    source = (PROJECT_ROOT / "src/vibemix/runtime/session_loop.py").read_text()

    helper_idx = source.index("def _catalog_source_for_import_path(source_path: Path)")
    assert "TraktorSource(nml_path=str(source_path))" in source[helper_idx:]
    assert "VirtualDJSource(database_path=str(source_path))" in source[helper_idx:]
    assert "EngineDJSource(database_path=str(source_path))" in source[helper_idx:]
    assert "SeratoSource(library_path=str(source_path))" in source[helper_idx:]

    branch_idx = source.index(
        "catalog_source = self._catalog_source_for_import_path(source_path)"
    )
    catalog_import_idx = source.index("await self._start_catalog_source_import(", branch_idx)
    return_idx = source.index("return", catalog_import_idx)
    xml_idx = source.index("await self._start_xml_import(source_path)", return_idx)

    assert branch_idx < catalog_import_idx < return_idx < xml_idx


def test_library_import_generic_catalog_path_uses_ingest_source() -> None:
    """The non-Rekordbox path must use the source-ingest orchestrator.

    Since 364c55ba the helper is ``SessionLoop._start_catalog_source_import``:
    it runs ``ingest_source`` off-loop with ``persist_library=True``, then
    re-registers the library (``_refresh_library_registry``) and emits a
    final import-progress frame — the old per-file ``_on_source_progress``
    callback is gone from the catalog lane.
    """
    source = (PROJECT_ROOT / "src/vibemix/runtime/session_loop.py").read_text()
    helper_idx = source.index("async def _start_catalog_source_import(")
    helper = source[helper_idx : source.index("async def _start_xml_import", helper_idx)]

    assert "from vibemix.library.ingest import ingest_source" in helper
    assert "return ingest_source(" in helper
    assert "persist_library=True" in helper
    assert "await self._refresh_library_registry()" in helper
    assert "await self._emit_library_import_progress(" in helper


def test_stale_folder_reindex_uses_recorded_source_not_renderer_path() -> None:
    """Folder re-index keeps the Package 5J consent boundary.

    Re-pinned 2026-06-10: the 364c55ba restructure DROPPED the staleness
    wiring (handler + reindex + boot nudge were one-ended for a while); it
    was restored into SessionLoop, so the pins now read session_loop.py —
    the recorded source is the only reindex target, never a renderer path.
    """
    source = (PROJECT_ROOT / "src/vibemix/runtime/session_loop.py").read_text()

    assert '"ipc.library.staleness_action", self._on_library_staleness_action' in source
    assert "async def _start_folder_reindex(" in source
    assert "source_path, source_kind = refreshable_source(status)" in source
    assert 'source_kind != "folder" or not source_path' in source
    # Behavior-level consent boundary + boot nudge are pinned in
    # tests/runtime/test_session_loop.py (staleness suite).
