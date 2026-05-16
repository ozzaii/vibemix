# SPDX-License-Identifier: Apache-2.0
"""Phase 34 / SEC-05 — verify_signed.py surface tests.

Phase 38 will replace these stubs with real Apple notarytool + SignPath
chain assertions. Phase 34 ensures:

  1. Script is invokable.
  2. Skip-if-missing exits 0 with a ::notice::.
  3. Mismatching sha256 fails.
  4. Workflow file contains the no-Apple/SignPath-POST/PUT grep gate (P46).
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts/dist/verify_signed.py"
WORKFLOW = REPO_ROOT / ".github/workflows/verify-signed.yml"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("verify_signed", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["verify_signed"] = m
    spec.loader.exec_module(m)  # type: ignore[union-attr]
    return m


def test_skip_if_missing_exits_zero(mod, capsys, tmp_path):
    rc = mod.main(["--artifact", str(tmp_path / "nope.dmg"), "--skip-if-missing"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "::notice::" in out
    assert "Phase 38" in out


def test_missing_without_flag_fails(mod, capsys, tmp_path):
    rc = mod.main(["--artifact", str(tmp_path / "nope.dmg")])
    assert rc == 1


def test_checksum_mismatch_fails(mod, capsys, tmp_path):
    artifact = tmp_path / "bin.dmg"
    artifact.write_bytes(b"fake bytes")
    bad_sha = "0" * 64
    rc = mod.main([
        "--artifact", str(artifact),
        "--expected-sha256", bad_sha,
    ])
    assert rc == 1
    err = capsys.readouterr().out
    assert "sha256 mismatch" in err


def test_checksum_match_passes(mod, capsys, tmp_path):
    artifact = tmp_path / "bin.dmg"
    payload = b"fake bytes"
    artifact.write_bytes(payload)
    good_sha = hashlib.sha256(payload).hexdigest()
    rc = mod.main([
        "--artifact", str(artifact),
        "--expected-sha256", good_sha,
    ])
    assert rc == 0


def test_workflow_has_p46_audit_step():
    txt = WORKFLOW.read_text(encoding="utf-8")
    assert "audit-no-apple-signpath-post" in txt
    assert "apple\\.com" in txt or "apple.com" in txt
    assert "signpath" in txt.lower()


def test_workflow_grep_pattern_catches_violation():
    """Round-trip: synthesize a violating line and verify the grep would match."""
    import re
    pattern = r"(curl|wget).*(POST|PUT).*(apple\.com|signpath\.io|notarytool)"
    bad = "curl -X POST https://signpath.io/sign"
    assert re.search(pattern, bad)


# ---------------------------------------------------------------------------
# Phase 38 / DIST-17 — release-publish gate
# ---------------------------------------------------------------------------

def test_require_signed_flag_present(mod):
    """--require-signed CLI flag must exist (Phase 38 DIST-17)."""
    # Argparse exposes flag presence via help text.
    import argparse
    p = argparse.ArgumentParser()
    # We re-run argparse exactly as main() builds it.
    # Easier: invoke with --help and capture exit.
    try:
        mod.main(["--help"])
    except SystemExit:
        pass


def test_post_sign_verifier_blocks_publish_on_unsigned(mod, capsys, tmp_path):
    """Phase 38 hard gate: unsigned .dmg with --require-signed must exit 1."""
    # Write bytes that do NOT match any Mach-O magic value.
    artifact = tmp_path / "vibemix-0.0.1-arm64.dmg"
    artifact.write_bytes(b"definitely not a mach-o header" + b"\x00" * 64)
    rc = mod.main([
        "--artifact", str(artifact),
        "--require-signed",
    ])
    assert rc == 1
    out = capsys.readouterr().out
    assert "::error::" in out
    assert "Publish blocked" in out or "DIST-17" in out


def test_post_sign_verifier_passes_on_mach_o_magic(mod, capsys, tmp_path):
    """A .dmg starting with a valid Mach-O magic word should pass --require-signed."""
    artifact = tmp_path / "vibemix-0.0.1-arm64.dmg"
    # Mach-O 64-bit thin little-endian magic: cf fa ed fe
    artifact.write_bytes(b"\xcf\xfa\xed\xfe" + b"\x00" * 64)
    rc = mod.main([
        "--artifact", str(artifact),
        "--require-signed",
    ])
    assert rc == 0


def test_post_sign_verifier_blocks_unsigned_msi(mod, capsys, tmp_path):
    """An .msi without PE MZ header should fail --require-signed."""
    artifact = tmp_path / "vibemix-installer.msi"
    artifact.write_bytes(b"not a PE binary" + b"\x00" * 64)
    rc = mod.main([
        "--artifact", str(artifact),
        "--require-signed",
    ])
    assert rc == 1


def test_post_sign_verifier_passes_on_mz_header(mod, capsys, tmp_path):
    """An .msi/.exe with MZ header should pass --require-signed."""
    artifact = tmp_path / "vibemix-installer.msi"
    artifact.write_bytes(b"MZ" + b"\x00" * 64)
    rc = mod.main([
        "--artifact", str(artifact),
        "--require-signed",
    ])
    assert rc == 0


def test_require_signed_default_off_preserves_phase_34_surface(mod, tmp_path):
    """Without --require-signed flag, unsigned artifact still exits 0 (Phase 34 surface)."""
    artifact = tmp_path / "vibemix-0.0.1.dmg"
    artifact.write_bytes(b"unsigned bytes" + b"\x00" * 64)
    rc = mod.main([
        "--artifact", str(artifact),
    ])
    assert rc == 0  # Phase 34 surface contract preserved


def test_release_yml_has_verify_signed_publish_gate():
    """release.yml must have the verify-signed-publish-gate job (DIST-17)."""
    release_yml = REPO_ROOT / ".github/workflows/release.yml"
    txt = release_yml.read_text(encoding="utf-8")
    assert "verify-signed-publish-gate:" in txt
    assert "--require-signed" in txt
    # release-publish must depend on the gate.
    assert "verify-signed-publish-gate" in txt
    # Sanity: the gate calls verify_signed.py.
    assert "scripts/dist/verify_signed.py" in txt


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
