# SPDX-License-Identifier: Apache-2.0
"""Phase 34 / SEC-09 — Tauri capability snapshot drift detection.

The committed SNAPSHOT.json must match what
scripts/dist/snapshot_capabilities.py produces from default.json. Any
edit to default.json that doesn't update SNAPSHOT.json must fail this
test (and CI).
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts/dist/snapshot_capabilities.py"
SNAPSHOT = REPO_ROOT / "tauri/src-tauri/capabilities-snapshot/SNAPSHOT.json"
DEFAULT = REPO_ROOT / "tauri/src-tauri/capabilities/default.json"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("snapshot_capabilities", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["snapshot_capabilities"] = m
    spec.loader.exec_module(m)  # type: ignore[union-attr]
    return m


def test_snapshot_exists():
    assert SNAPSHOT.exists()
    assert DEFAULT.exists()


def test_committed_snapshot_matches_current_default(mod):
    """The committed SNAPSHOT.json must equal the canonicalised default.json."""
    raw = json.loads(DEFAULT.read_text(encoding="utf-8"))
    rendered = mod.render(raw)
    committed = SNAPSHOT.read_text(encoding="utf-8")
    assert committed == rendered, (
        "Tauri capability snapshot drift — run "
        "`python scripts/dist/snapshot_capabilities.py --write` and commit."
    )


def test_check_mode_passes_on_current_state(mod, capsys):
    rc = mod.main(["--check"])
    assert rc == 0


def test_drift_detected_via_synthetic_mutation(mod, tmp_path, monkeypatch, capsys):
    """Simulate a default.json edit without snapshot update — must fail."""
    # Stage tmp copies.
    tmp_default = tmp_path / "default.json"
    tmp_snapshot = tmp_path / "SNAPSHOT.json"
    shutil.copy(DEFAULT, tmp_default)
    shutil.copy(SNAPSHOT, tmp_snapshot)

    # Mutate default.json: add an extra permission.
    raw = json.loads(tmp_default.read_text(encoding="utf-8"))
    raw["permissions"].append("core:tray:default")  # synthetic addition
    tmp_default.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    # Point the module's globals at the tmp paths.
    monkeypatch.setattr(mod, "DEFAULT_CAP", tmp_default)
    monkeypatch.setattr(mod, "SNAPSHOT", tmp_snapshot)

    rc = mod.main(["--check"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "drift detected" in out.lower()


def test_canonicalise_strips_description(mod):
    """Prose drift in `description` must not affect the snapshot."""
    a = {
        "identifier": "default",
        "description": "first version",
        "windows": ["main"],
        "permissions": ["core:default"],
    }
    b = {
        "identifier": "default",
        "description": "second version",
        "windows": ["main"],
        "permissions": ["core:default"],
    }
    assert mod.canonicalise(a) == mod.canonicalise(b)


def test_canonicalise_sorts_windows_and_permissions(mod):
    """The output must be deterministic regardless of input ordering."""
    a = {
        "identifier": "default",
        "windows": ["mascot", "main", "debrief"],
        "permissions": ["b:default", "a:default"],
    }
    b = {
        "identifier": "default",
        "windows": ["debrief", "main", "mascot"],
        "permissions": ["a:default", "b:default"],
    }
    assert mod.render(a) == mod.render(b)


def test_render_ends_with_newline(mod):
    rendered = mod.render({"identifier": "x", "windows": [], "permissions": []})
    assert rendered.endswith("\n")


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
