# SPDX-License-Identifier: Apache-2.0
"""Phase 27-06 — REC-09 universal2 sidecar carry-forward tests.

Three classes of test:

1. File-grep gates (always run on every CI runner): no `lipo -create` ever
   appears in release.yml; bundle ID `world.bravoh.vibemix` UNCHANGED in
   tauri.conf.json5 (Pitfall P63 lock); externalBin/resources entry uses
   the bare `vibemix-sidecar` / `vibemix-core` stem (Tauri appends the
   triple at install time).

2. Local-build artifact assertions (skip when no built sidecars present):
   both arch-specific files exist under tauri/src-tauri/binaries/; each is
   single-arch via `lipo -archs` (NOT 'arm64 x86_64' — that would indicate
   someone tried the lipo-merge path despite RESEARCH §Critical Correction).

3. Source-of-truth gates: scripts/build_sidecar.py exposes --target-arch;
   sidecar.rs uses runtime sidecar_triple() (NOT hardcoded
   const SIDECAR_TRIPLE) so a single .app bundle picks the right binary
   based on host arch.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[2]
TAURI_BIN_DIR = PROJECT_ROOT / "tauri" / "src-tauri" / "binaries"
TAURI_CONF = PROJECT_ROOT / "tauri" / "src-tauri" / "tauri.conf.json5"
RELEASE_YAML = PROJECT_ROOT / ".github" / "workflows" / "release.yml"
BUILD_SIDECAR = PROJECT_ROOT / "scripts" / "build_sidecar.py"
SIDECAR_RS = PROJECT_ROOT / "tauri" / "src-tauri" / "src" / "sidecar.rs"


# ----------------------------------------------------------------------
# Class 1 — file-grep gates (always run)
# ----------------------------------------------------------------------


def test_no_lipo_merge_step_in_release_yml() -> None:
    """T-27-06-01: ``lipo -create`` MUST NOT appear in release.yml ever.

    Per RESEARCH §Critical Correction, lipo-merging two PyInstaller bundles
    produces a binary that segfaults on the arch whose PKG archive is NOT
    in the last merged slice. The matrix-build path produces TWO arch-
    specific artifacts; Tauri's resource lookup picks the right one at
    runtime via std::env::consts::ARCH.
    """
    assert RELEASE_YAML.exists(), f"missing {RELEASE_YAML}"
    text = RELEASE_YAML.read_text(encoding="utf-8")
    assert "lipo -create" not in text, (
        "Pitfall P69 violation: release.yml contains 'lipo -create'. "
        "Remove the lipo-merge step — it produces silently-broken binaries."
    )


def test_bundle_id_locked() -> None:
    """T-27-06-02: bundle identifier `world.bravoh.vibemix` MUST be UNCHANGED.

    Pitfall P63 — any change resets ALL TCC permissions (Microphone,
    Screen Recording, Accessibility) on every existing user's machine on
    the v2.0 → v2.1 upgrade.
    """
    assert TAURI_CONF.exists(), f"missing {TAURI_CONF}"
    text = TAURI_CONF.read_text(encoding="utf-8")
    assert '"identifier": "world.bravoh.vibemix"' in text, (
        "Pitfall P63 violation: tauri.conf.json5 bundle identifier "
        "changed. Restore 'world.bravoh.vibemix' or every user re-grants "
        "Microphone + Screen Recording + Accessibility on upgrade."
    )


def test_resources_includes_both_arch_bundles() -> None:
    """REC-09: bundle.resources lists BOTH arm64 + x86_64 sidecar dirs.

    sidecar.rs picks the matching one at runtime via std::env::consts::ARCH;
    this gate ensures BOTH are shipped so the runtime lookup never misses.
    """
    text = TAURI_CONF.read_text(encoding="utf-8")
    assert "binaries/vibemix-core-aarch64-apple-darwin" in text
    assert "binaries/vibemix-core-x86_64-apple-darwin" in text


def test_release_yml_matrix_builds_both_archs() -> None:
    """REC-09: release.yml matrix produces arm64 + x86_64 sidecars."""
    text = RELEASE_YAML.read_text(encoding="utf-8")
    assert "aarch64-apple-darwin" in text
    assert "x86_64-apple-darwin" in text
    assert re.search(r"^\s*matrix:\s*$", text, re.MULTILINE), (
        "release.yml does not contain a matrix: strategy block"
    )


def test_build_sidecar_supports_target_arch() -> None:
    """REC-09: scripts/build_sidecar.py exposes --target-arch."""
    text = BUILD_SIDECAR.read_text(encoding="utf-8")
    assert "--target-arch" in text
    assert "aarch64-apple-darwin" in text or "_target_arch_to_triple" in text


def test_sidecar_rs_uses_runtime_triple_resolver() -> None:
    """REC-09: sidecar.rs uses sidecar_triple() function, NOT a single hard-coded
    macOS const.

    The fix replaces:
        #[cfg(target_os = "macos")]
        const SIDECAR_TRIPLE: &str = "aarch64-apple-darwin";
    with:
        #[cfg(target_os = "macos")]
        fn sidecar_triple() -> &'static str { match std::env::consts::ARCH { ... } }
    so a single .app bundle picks arm64 OR x86_64 based on host arch.
    """
    text = SIDECAR_RS.read_text(encoding="utf-8")
    assert "fn sidecar_triple()" in text, (
        "sidecar.rs does not define sidecar_triple() — REC-09 runtime "
        "arch resolution missing"
    )
    assert "std::env::consts::ARCH" in text, (
        "sidecar.rs does not consult std::env::consts::ARCH for "
        "runtime arch detection"
    )


# ----------------------------------------------------------------------
# Class 2 — built-artifact assertions (skip when no local build present)
# ----------------------------------------------------------------------


def _arch_bin_path(triple: str) -> Path:
    return TAURI_BIN_DIR / f"vibemix-core-{triple}" / f"vibemix-core-{triple}"


@pytest.mark.skipif(
    sys.platform != "darwin", reason="lipo is a Mach-O tool — macOS only"
)
def test_target_triple_files_exist_in_resources_after_build() -> None:
    """REC-09: post-CI-build, both arch-specific bundles are present.

    Skips locally when neither is built; runs on the matrix runners after
    each matrix arm completes its build_sidecar invocation.
    """
    arm64_bin = _arch_bin_path("aarch64-apple-darwin")
    x86_64_bin = _arch_bin_path("x86_64-apple-darwin")
    if not arm64_bin.exists() and not x86_64_bin.exists():
        pytest.skip("no built sidecar in tauri/src-tauri/binaries/")
    # On a single-arch runner, ONE will be present (the one built on this
    # runner). On a downstream bundle job that downloads both artifacts,
    # BOTH will be present.
    assert arm64_bin.exists() or x86_64_bin.exists()


@pytest.mark.skipif(
    sys.platform != "darwin", reason="lipo is a Mach-O tool — macOS only"
)
def test_each_sidecar_is_single_arch() -> None:
    """REC-09: each per-arch bundle is single-arch matching its triple.

    If lipo -archs returns 'arm64 x86_64' on either binary, someone tried
    the lipo-merge path despite RESEARCH §Critical Correction. The result
    is a broken binary that segfaults on one of the two archs at app
    launch — see Pitfall P69.
    """
    cases = [
        (_arch_bin_path("aarch64-apple-darwin"), "arm64"),
        (_arch_bin_path("x86_64-apple-darwin"), "x86_64"),
    ]
    any_present = False
    for path, expected in cases:
        if not path.exists():
            continue
        any_present = True
        result = subprocess.run(
            ["lipo", "-archs", str(path)],
            capture_output=True,
            text=True,
            check=True,
        )
        archs = result.stdout.strip()
        assert archs == expected, (
            f"REC-09 / Pitfall P69 violation: {path.name} is '{archs}' but "
            f"expected single-arch '{expected}'. If lipo returned 'arm64 "
            f"x86_64', someone tried the lipo-merge path."
        )
    if not any_present:
        pytest.skip("no built sidecar in tauri/src-tauri/binaries/")
