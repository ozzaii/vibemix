"""Phase 58 / REL-02 — pin the 50a recording rig's resolved paths.

Regression guard for the latent ``REPO_ROOT`` bug: the script lives in
``scripts/e2e/`` so it must resolve the repo root two levels up (``../..``),
not one (``..``). The ``OUT_WEBM`` target must land at the EXACT Gate-6b /
README / CONTEXT location ``<repo>/docs/e2e/2026-05-walk.webm`` regardless of
the cwd the script is invoked from.

These tests would FAIL against the old single-``..`` form (REPO_ROOT would
resolve to ``scripts/`` and OUT_WEBM would be a cwd-relative path).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "e2e" / "record_50a_walk.sh"
EXPECTED_WEBM = REPO_ROOT / "docs" / "e2e" / "2026-05-walk.webm"
EXPECTED_OUT_DIR = REPO_ROOT / "docs" / "e2e"


def _print_paths(cwd: Path) -> dict[str, str]:
    """Invoke the script's --print-paths harness from ``cwd``; parse KEY=VALUE."""
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--print-paths"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
    )
    out: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            out[key.strip()] = value.strip()
    return out


def test_script_exists_and_executable() -> None:
    assert SCRIPT.exists(), f"missing recording rig at {SCRIPT}"


def test_repo_root_resolves_two_levels_up_from_repo_root() -> None:
    paths = _print_paths(REPO_ROOT)
    assert Path(paths["REPO_ROOT"]).resolve() == REPO_ROOT
    assert Path(paths["OUT_DIR"]).resolve() == EXPECTED_OUT_DIR
    assert Path(paths["OUT_WEBM"]).resolve() == EXPECTED_WEBM


def test_out_webm_is_cwd_independent(tmp_path: Path) -> None:
    """The resolved target must be identical when invoked from an arbitrary cwd.

    Under the old single-``..`` bug, REPO_ROOT pointed at ``scripts/`` and
    OUT_WEBM was the cwd-relative literal ``docs/e2e/2026-05-walk.webm`` — so
    invoking from /tmp would resolve to ``/tmp/docs/e2e/...``. This pins the fix.
    """
    from_repo = _print_paths(REPO_ROOT)
    from_tmp = _print_paths(tmp_path)
    assert from_repo == from_tmp, "resolved paths leaked the invoking cwd"
    assert Path(from_tmp["OUT_WEBM"]).resolve() == EXPECTED_WEBM
    assert Path(from_tmp["OUT_WEBM"]).is_absolute()


def test_out_webm_target_is_exact_gate6b_location() -> None:
    """Final target path is exactly repo-root/docs/e2e/2026-05-walk.webm."""
    paths = _print_paths(REPO_ROOT)
    assert Path(paths["OUT_WEBM"]).resolve() == EXPECTED_WEBM


def test_source_pins_double_dotdot_and_absolute_out_webm() -> None:
    """Belt-and-braces literal-shape pin against the old single-``..`` regression."""
    src = SCRIPT.read_text(encoding="utf-8")
    assert '/../.." && pwd)"' in src, "REPO_ROOT must resolve two levels up (../..)"
    assert 'OUT_DIR="${REPO_ROOT}/docs/e2e"' in src
    assert 'OUT_WEBM="${OUT_DIR}/2026-05-walk.webm"' in src
    # The old buggy forms must be gone.
    assert 'OUT_DIR="${REPO_ROOT}/../docs/e2e"' not in src
    assert 'OUT_WEBM="docs/e2e/2026-05-walk.webm"' not in src


def test_ffmpeg_guard_precedes_transcode() -> None:
    """The ffmpeg-presence guard stays before the transcode call (unchanged)."""
    src = SCRIPT.read_text(encoding="utf-8")
    guard_idx = src.find("command -v ffmpeg")
    transcode_idx = src.find("libvpx-vp9")
    assert guard_idx != -1, "ffmpeg presence guard missing"
    assert transcode_idx != -1, "ffmpeg transcode call missing"
    assert guard_idx < transcode_idx, "ffmpeg guard must precede the transcode"
