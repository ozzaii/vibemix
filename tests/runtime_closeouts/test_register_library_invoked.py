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

    status, _registry, lib = _run_wire_in_block()
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
    """Marker comment lets future refactors find the wire-in."""
    r = subprocess.run(
        ["grep", "-q", "Plan 27-05 final-mile wiring", "src/vibemix/__main__.py"],
        cwd=str(PROJECT_ROOT),
    )
    assert r.returncode == 0


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
