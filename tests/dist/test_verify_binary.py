# SPDX-License-Identifier: Apache-2.0
"""Phase 18 Wave 1 — unit tests for scripts.dist.verify_binary.

Every planted byte sequence in this file is an obviously-not-a-real-key
sentinel; see tests/dist/fixtures/README.md for the policy.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

import pytest

from scripts.dist import verify_binary
from scripts.dist.verify_binary import (
    AIZA_PATTERN,
    GENERIC_KEY_PATTERN,
    Hit,
    MsiInspectionUnavailable,
    Pattern,
    VerifyResult,
    _extracted_archive,
    scan_bundle,
    verify,
    write_report,
)

# ---------------------------------------------------------------------------
# Sentinel constants — synthesised, obviously-fake key shapes
# ---------------------------------------------------------------------------

_SENTINEL_AIZA: bytes = b"AIza" + b"A" * 35  # 39 chars total
_SENTINEL_AKIA: bytes = b"AKIA" + b"A" * 16  # 20 chars total
_SENTINEL_YA29: bytes = b"ya29." + b"x" * 40
_SENTINEL_SK: bytes = b"sk-" + b"x" * 40
# Hand-rolled 39-char run that lacks any of the strict prefixes.
_SENTINEL_GENERIC39: bytes = b"A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9T"


# ---------------------------------------------------------------------------
# 1. Clean bundle → ok
# ---------------------------------------------------------------------------


def test_clean_app_passes(
    make_fake_app: Callable[..., Path], tmp_path: Path
) -> None:
    app = make_fake_app()
    result = scan_bundle(app)
    assert result.ok is True
    assert result.hits == ()
    assert result.scanned >= 1

    report_path = tmp_path / "verify-report.json"
    write_report(result, report_path)
    payload = json.loads(report_path.read_text())
    assert payload["status"] == "clean"
    assert payload["hits"] == []
    assert payload["flagged_strings"] == []
    assert payload["scanned"] == result.scanned
    assert payload["binary_count"] == result.scanned


# ---------------------------------------------------------------------------
# 2-5. Planted strict patterns flag with the correct pattern name
# ---------------------------------------------------------------------------


def test_planted_aiza_app_flags(
    make_fake_app: Callable[..., Path],
) -> None:
    app = make_fake_app(planted_bytes=_SENTINEL_AIZA)
    result = scan_bundle(app)
    assert result.ok is False
    aiza_hits = [h for h in result.hits if h.pattern == Pattern.AIZA.value]
    assert aiza_hits, f"expected an aiza hit, got: {result.hits!r}"
    assert aiza_hits[0].source == "Contents/MacOS/vibemix-core"


def test_planted_akia_aws_app_flags(make_fake_app: Callable[..., Path]) -> None:
    app = make_fake_app(planted_bytes=_SENTINEL_AKIA)
    result = scan_bundle(app)
    assert result.ok is False
    assert any(h.pattern == Pattern.AKIA.value for h in result.hits)


def test_planted_ya29_oauth_app_flags(make_fake_app: Callable[..., Path]) -> None:
    app = make_fake_app(planted_bytes=_SENTINEL_YA29)
    result = scan_bundle(app)
    assert result.ok is False
    assert any(h.pattern == Pattern.YA29.value for h in result.hits)


def test_planted_sk_openai_app_flags(make_fake_app: Callable[..., Path]) -> None:
    app = make_fake_app(planted_bytes=_SENTINEL_SK)
    result = scan_bundle(app)
    assert result.ok is False
    assert any(h.pattern == Pattern.SK.value for h in result.hits)


# ---------------------------------------------------------------------------
# 6-7. Generic-39 fires only on non-allowlisted suffixes
# ---------------------------------------------------------------------------


def test_generic_39_char_shape_flags_on_pyc(
    make_fake_app: Callable[..., Path],
) -> None:
    payload = b"\xff\xff" + _SENTINEL_GENERIC39 + b"\xff\xff"
    app = make_fake_app(
        extra_files=(("Contents/Resources/_internal/some.pyc", payload),),
    )
    result = scan_bundle(app)
    assert result.ok is False
    generic_hits = [h for h in result.hits if h.pattern == Pattern.GENERIC39.value]
    assert generic_hits, f"expected generic39 hit, got: {result.hits!r}"
    # Strict patterns should NOT fire on a string that doesn't start
    # with AIza / AKIA / ya29 / sk-.
    strict_hits = [
        h
        for h in result.hits
        if h.pattern in {Pattern.AIZA.value, Pattern.AKIA.value, Pattern.YA29.value, Pattern.SK.value}
    ]
    assert not strict_hits, f"unexpected strict-pattern hit: {strict_hits!r}"


def test_generic_39_char_pattern_skipped_for_allowlisted_suffixes(
    make_fake_app: Callable[..., Path],
) -> None:
    payload = b"\xff\xff" + _SENTINEL_GENERIC39 + b"\xff\xff"
    app = make_fake_app(
        extra_files=(("Contents/Resources/font.woff2", payload),),
    )
    result = scan_bundle(app)
    # generic39 should be suppressed on .woff2; nothing else planted.
    generic_hits = [h for h in result.hits if h.pattern == Pattern.GENERIC39.value]
    assert generic_hits == [], (
        f"generic39 should be suppressed on .woff2, got: {generic_hits!r}"
    )
    assert result.ok is True


# ---------------------------------------------------------------------------
# 8-10. MSI dispatch — Windows / 7z / unavailable
# ---------------------------------------------------------------------------


def test_msi_dispatch_invokes_msiexec_on_windows(
    tmp_path: Path,
) -> None:
    msi = tmp_path / "vibemix-installer.msi"
    msi.write_bytes(b"fake msi bytes")

    calls: list[list[str]] = []

    def fake_runner(cmd: list[str]) -> int:
        calls.append(list(cmd))
        # Simulate msiexec extracting an empty target — caller will scan
        # the empty tree and return ok.
        target_index = next(
            (i for i, a in enumerate(cmd) if str(a).startswith("TARGETDIR=")),
            -1,
        )
        if target_index >= 0:
            target_dir = Path(str(cmd[target_index]).split("=", 1)[1])
            target_dir.mkdir(parents=True, exist_ok=True)
        return 0

    result = scan_bundle(
        msi,
        platform="win32",
        runner=fake_runner,
        which=lambda _name: None,
    )
    assert result.ok is True
    assert calls, "expected at least one runner invocation"
    assert calls[0][0] == "msiexec"
    assert "/a" in calls[0]
    assert "/qb" in calls[0]
    assert any(str(a).startswith("TARGETDIR=") for a in calls[0])


def test_msi_dispatch_falls_back_to_7z_on_non_windows(
    tmp_path: Path,
) -> None:
    msi = tmp_path / "vibemix-installer.msi"
    msi.write_bytes(b"fake msi bytes")

    calls: list[list[str]] = []

    def fake_runner(cmd: list[str]) -> int:
        calls.append(list(cmd))
        target = next(
            (a for a in cmd if str(a).startswith("-o")),
            None,
        )
        if target is not None:
            target_dir = Path(str(target)[2:])
            target_dir.mkdir(parents=True, exist_ok=True)
        return 0

    result = scan_bundle(
        msi,
        platform="darwin",
        runner=fake_runner,
        which=lambda name: "/usr/local/bin/7z" if name == "7z" else None,
    )
    assert result.ok is True
    assert calls and calls[0][0] == "/usr/local/bin/7z"
    assert calls[0][1] == "x"


def test_msi_inspection_raises_when_unavailable(tmp_path: Path) -> None:
    msi = tmp_path / "vibemix-installer.msi"
    msi.write_bytes(b"fake msi bytes")
    with pytest.raises(MsiInspectionUnavailable, match=r"MSI inspection requires"):
        scan_bundle(
            msi,
            platform="darwin",
            runner=lambda _cmd: 0,
            which=lambda _name: None,
        )


# ---------------------------------------------------------------------------
# 11. PyInstaller archive round-trip
# ---------------------------------------------------------------------------


def test_pyinstaller_archive_extraction_round_trip(
    fixture_pyinstaller_archive: Callable[..., Path],
) -> None:
    arc = fixture_pyinstaller_archive(
        entries=[
            ("clean.txt", b"clean payload\n"),
            ("planted.pyc", _SENTINEL_AIZA),
        ]
    )
    seen_paths: list[Path] = []
    with _extracted_archive(arc) as extracted:
        assert extracted is not None, "extractor should accept the synthetic archive"
        for path in extracted.rglob("*"):
            if path.is_file():
                seen_paths.append(path.relative_to(extracted))
        # Verify the planted payload survived the round trip.
        planted = extracted / "planted.pyc"
        assert planted.exists()
        assert _SENTINEL_AIZA in planted.read_bytes()
    # Context manager must clean up the temp dir on exit.
    assert seen_paths, "expected at least one extracted file"


def test_pyinstaller_archive_recursion_flags_embedded_key(
    make_fake_app: Callable[..., Path],
    fixture_pyinstaller_archive: Callable[..., Path],
    tmp_path: Path,
) -> None:
    arc = fixture_pyinstaller_archive(
        entries=[("hidden.pyc", _SENTINEL_AIZA)],
        name="base_library.pyz",
    )
    app = make_fake_app(
        extra_files=(
            ("Contents/Resources/_internal/base_library.pyz", arc.read_bytes()),
        ),
    )
    result = scan_bundle(app)
    assert result.ok is False
    nested_hits = [h for h in result.hits if "!" in h.source]
    assert nested_hits, f"expected a nested-archive hit, got: {result.hits!r}"
    assert nested_hits[0].pattern == Pattern.AIZA.value


# ---------------------------------------------------------------------------
# 12. Report writer redacts matched bytes
# ---------------------------------------------------------------------------


def test_report_redacts_matched_bytes(
    make_fake_app: Callable[..., Path], tmp_path: Path
) -> None:
    app = make_fake_app(planted_bytes=_SENTINEL_AIZA)
    result = scan_bundle(app)
    report_path = tmp_path / "verify-report.json"
    write_report(result, report_path)
    body = report_path.read_text()
    # The literal AIza-prefixed sentinel must never appear in the
    # serialized JSON; only the pattern name should be there.
    assert _SENTINEL_AIZA.decode("ascii") not in body
    payload = json.loads(body)
    assert payload["status"] == "flagged"
    assert Pattern.AIZA.value in payload["flagged_strings"]
    # Every hit dict carries only source + pattern keys; no value-like
    # key.
    for hit in payload["hits"]:
        assert set(hit.keys()) == {"source", "pattern"}


# ---------------------------------------------------------------------------
# 13. CLI exit codes
# ---------------------------------------------------------------------------


def _cli_run(
    bundle: Path, report: Path | None = None, extra: list[str] | None = None
) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", "scripts.dist.verify_binary", str(bundle)]
    if report is not None:
        cmd.extend(["--report", str(report)])
    if extra:
        cmd.extend(extra)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def test_cli_exit_code_clean(make_fake_app: Callable[..., Path], tmp_path: Path) -> None:
    app = make_fake_app()
    report = tmp_path / "clean-report.json"
    proc = _cli_run(app, report=report)
    assert proc.returncode == 0, proc.stderr
    assert report.exists()
    assert json.loads(report.read_text())["status"] == "clean"


def test_cli_exit_code_planted(
    make_fake_app: Callable[..., Path], tmp_path: Path
) -> None:
    app = make_fake_app(planted_bytes=_SENTINEL_AIZA)
    report = tmp_path / "flagged-report.json"
    proc = _cli_run(app, report=report)
    assert proc.returncode == 1, proc.stderr
    assert json.loads(report.read_text())["status"] == "flagged"


def test_cli_exit_code_missing_path(tmp_path: Path) -> None:
    bogus = tmp_path / "does-not-exist.app"
    proc = _cli_run(bogus)
    assert proc.returncode == 2


def test_cli_help_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.dist.verify_binary", "--help"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2])},
    )
    assert proc.returncode == 0
    assert "--report" in proc.stdout
    assert "--allowlist-suffix" in proc.stdout
    assert "bundle" in proc.stdout


# ---------------------------------------------------------------------------
# 14. Log redaction invariant
# ---------------------------------------------------------------------------


def test_log_output_does_not_leak_planted_key(
    make_fake_app: Callable[..., Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = make_fake_app(planted_bytes=_SENTINEL_AIZA)
    with caplog.at_level(logging.DEBUG, logger="scripts.dist.verify_binary"):
        result = scan_bundle(app)
    assert result.ok is False
    sentinel_text = _SENTINEL_AIZA.decode("ascii")
    for record in caplog.records:
        msg = record.getMessage()
        assert sentinel_text not in msg, (
            f"log record leaked the planted AIza sentinel: {msg!r}"
        )


# ---------------------------------------------------------------------------
# 15. Module-level invariants (regression guards)
# ---------------------------------------------------------------------------


def test_patterns_are_compiled_byte_regexes() -> None:
    import re as _re

    assert isinstance(AIZA_PATTERN, _re.Pattern)
    assert isinstance(GENERIC_KEY_PATTERN, _re.Pattern)
    # Bytes mode — the input to .search() is bytes-typed.
    assert AIZA_PATTERN.search(b"AIza" + b"X" * 35) is not None


def test_hit_dataclass_has_no_value_field() -> None:
    from dataclasses import fields

    banned = {"matched", "value", "bytes", "string", "key", "secret", "data"}
    field_names = {f.name for f in fields(Hit)}
    assert not (field_names & banned), (
        f"Hit must not have a field that suggests storing matched bytes; "
        f"got fields={field_names!r}"
    )


def test_verify_is_public_alias_for_scan_bundle(
    make_fake_app: Callable[..., Path],
) -> None:
    app = make_fake_app()
    a = scan_bundle(app)
    b = verify(app)
    assert isinstance(b, VerifyResult)
    assert a.ok == b.ok
    assert a.scanned == b.scanned
