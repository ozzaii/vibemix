"""Tests for the local Tauri sidecar bundle readiness gate."""

from __future__ import annotations

import builtins
import json
import os
import stat
import wave
from pathlib import Path

import pytest
from scripts.dist import check_sidecar_bundle_ready as gate

MAC_TRIPLE = "aarch64-apple-darwin"
WIN_TRIPLE = "x86_64-pc-windows-msvc"
SOURCE_HEAD = "abc123"
SOURCE_FINGERPRINT = "f" * 64


@pytest.fixture(autouse=True)
def _stable_source_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gate, "git_head", lambda *, root=gate.REPO_ROOT: SOURCE_HEAD)
    monkeypatch.setattr(
        gate,
        "source_fingerprint",
        lambda *, root=gate.REPO_ROOT: SOURCE_FINGERPRINT,
    )
    monkeypatch.setattr(gate, "source_dirty_paths", lambda *, root=gate.REPO_ROOT: [])


def _bundle_dir(root: Path, triple: str) -> Path:
    return root / gate.BINARIES_REL / f"vibemix-core-{triple}"


def _write_learn_exemplar_wavs(bundle: Path) -> None:
    for rel in gate.LEARN_EXEMPLAR_WAVS:
        path = bundle / "_internal" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"wav")


def _write_source_manifest(
    bundle: Path,
    triple: str,
    *,
    git_head: str = SOURCE_HEAD,
    source_fingerprint: str = SOURCE_FINGERPRINT,
    source_dirty: list[str] | None = None,
    schema: str = gate.BUILD_MANIFEST_SCHEMA,
) -> None:
    (bundle / gate.BUILD_MANIFEST_NAME).write_text(
        json.dumps(
            {
                "schema": schema,
                "git_head": git_head,
                "source_fingerprint": source_fingerprint,
                "source_dirty": source_dirty or [],
                "source_fingerprint_paths": ["src/vibemix"],
                "triple": triple,
                "built_at": "2026-06-04T00:00:00Z",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_bundle(
    root: Path,
    triple: str,
    *,
    size: int = 8192,
    executable: bool = True,
    bundled_schema: str | None = None,
    learn_wavs: bool = True,
    source_manifest: bool = True,
) -> Path:
    bundle = _bundle_dir(root, triple)
    bundle.mkdir(parents=True)
    (bundle / "_internal").mkdir()
    if learn_wavs:
        _write_learn_exemplar_wavs(bundle)
    if bundled_schema is not None:
        schema = bundle / "_internal" / gate.IPC_SCHEMA_REL
        schema.parent.mkdir(parents=True, exist_ok=True)
        schema.write_text(bundled_schema, encoding="utf-8")
    suffix = gate.exe_suffix_for_triple(triple)
    binary = bundle / f"vibemix-core-{triple}{suffix}"
    binary.write_bytes(b"x" * size)
    if suffix == "":
        mode = binary.stat().st_mode
        if executable:
            binary.chmod(mode | stat.S_IXUSR)
        else:
            binary.chmod(mode & ~stat.S_IXUSR & ~stat.S_IXGRP & ~stat.S_IXOTH)
    if source_manifest:
        _write_source_manifest(bundle, triple)
    return binary


def _write_source_schema(root: Path, body: str = '{"oneOf": []}\n') -> None:
    schema = root / gate.IPC_SCHEMA_REL
    schema.parent.mkdir(parents=True, exist_ok=True)
    schema.write_text(body, encoding="utf-8")


def _write_bundled_chatterbox_ref(
    root: Path,
    triple: str,
    *,
    channels: int = gate.CHATTERBOX_REF_CHANNELS,
    sample_width: int = gate.CHATTERBOX_REF_SAMPLE_WIDTH,
    sample_rate: int = gate.CHATTERBOX_REF_SAMPLE_RATE,
) -> Path:
    ref_path = _bundle_dir(root, triple) / gate.CHATTERBOX_REF_REL
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(ref_path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00" * channels * sample_width * 24)
    return ref_path


def test_ready_macos_bundle_passes(tmp_path: Path) -> None:
    binary = _write_bundle(tmp_path, MAC_TRIPLE)

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is True
    assert status.binary == binary


def test_ready_bundle_passes_when_embedded_ipc_schema_matches(tmp_path: Path) -> None:
    schema = '{"oneOf": [{"properties": {"type": {"const": "ipc.status.tick"}}}]}\n'
    _write_source_schema(tmp_path, schema)
    binary = _write_bundle(tmp_path, MAC_TRIPLE, bundled_schema=schema)

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is True
    assert status.binary == binary


def test_stale_embedded_ipc_schema_fails_with_rebuild_action(tmp_path: Path) -> None:
    _write_source_schema(tmp_path, '{"oneOf": [{"type": "current"}]}\n')
    _write_bundle(tmp_path, MAC_TRIPLE, bundled_schema='{"oneOf": [{"type": "old"}]}\n')

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is False
    assert "IPC schema is stale" in status.message
    assert "scripts/build_sidecar.py" in status.message


def test_missing_source_manifest_fails_with_rebuild_action(tmp_path: Path) -> None:
    _write_bundle(tmp_path, MAC_TRIPLE, source_manifest=False)

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is False
    assert "source manifest missing" in status.message
    assert "scripts/build_sidecar.py" in status.message


def test_stale_source_manifest_fingerprint_fails(tmp_path: Path) -> None:
    binary = _write_bundle(tmp_path, MAC_TRIPLE)
    _write_source_manifest(binary.parent, MAC_TRIPLE, source_fingerprint="0" * 64)

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is False
    assert "fingerprint is stale" in status.message


def test_dirty_runtime_source_after_freeze_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_bundle(tmp_path, MAC_TRIPLE)
    monkeypatch.setattr(
        gate,
        "source_dirty_paths",
        lambda *, root=gate.REPO_ROOT: [" M src/vibemix/library/codex_curate.py"],
    )

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is False
    assert "runtime-package source is dirty" in status.message
    assert "codex_curate.py" in status.message


def test_source_manifest_built_from_dirty_source_fails(tmp_path: Path) -> None:
    binary = _write_bundle(tmp_path, MAC_TRIPLE)
    _write_source_manifest(
        binary.parent,
        MAC_TRIPLE,
        source_dirty=[" M scripts/build_sidecar.py"],
    )

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is False
    assert "built from dirty runtime-package source" in status.message


def test_missing_embedded_ipc_schema_fails_when_source_schema_exists(tmp_path: Path) -> None:
    _write_source_schema(tmp_path)
    _write_bundle(tmp_path, MAC_TRIPLE)

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is False
    assert "IPC schema missing" in status.message


def test_placeholder_only_bundle_fails_with_action(tmp_path: Path) -> None:
    bundle = _bundle_dir(tmp_path, MAC_TRIPLE)
    bundle.mkdir(parents=True)
    (bundle / ".placeholder").write_text("build the sidecar first\n", encoding="utf-8")

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is False
    assert "placeholder-only" in status.message
    assert "scripts/build_sidecar.py" in status.message


def test_missing_binary_fails(tmp_path: Path) -> None:
    bundle = _bundle_dir(tmp_path, MAC_TRIPLE)
    bundle.mkdir(parents=True)
    (bundle / "_internal").mkdir()

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is False
    assert "binary missing" in status.message


def test_tiny_binary_fails(tmp_path: Path) -> None:
    _write_bundle(tmp_path, MAC_TRIPLE, size=16)

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is False
    assert "too small" in status.message


def test_posix_binary_must_be_executable(tmp_path: Path) -> None:
    _write_bundle(tmp_path, MAC_TRIPLE, executable=False)

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is False
    assert "not executable" in status.message


def test_windows_bundle_does_not_require_posix_execute_bit(tmp_path: Path) -> None:
    binary = _write_bundle(tmp_path, WIN_TRIPLE, executable=False)

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=WIN_TRIPLE)

    assert status.ok is True
    assert status.binary == binary
    assert not os.access(binary, os.X_OK)


def test_missing_pyinstaller_internal_dir_fails(tmp_path: Path) -> None:
    binary = _write_bundle(tmp_path, MAC_TRIPLE, learn_wavs=False)
    (binary.parent / "_internal").rmdir()

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is False
    assert "_internal" in status.message


def test_missing_learn_exemplar_wavs_fail_with_rebuild_action(tmp_path: Path) -> None:
    _write_bundle(tmp_path, MAC_TRIPLE, learn_wavs=False)

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is False
    assert "Learn exemplar WAV bank missing" in status.message
    assert "scripts/build_sidecar.py" in status.message


def test_bundled_test_fixture_payloads_fail(tmp_path: Path) -> None:
    _write_bundle(tmp_path, MAC_TRIPLE)
    fixture = (
        _bundle_dir(tmp_path, MAC_TRIPLE)
        / "_internal"
        / "tests"
        / "library"
        / "fixtures"
        / "synthetic_collection.xml"
    )
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text("<DJ_PLAYLISTS />\n", encoding="utf-8")

    status = gate.check_sidecar_bundle_ready(root=tmp_path, triple=MAC_TRIPLE)

    assert status.ok is False
    assert "test fixture payloads bundled in sidecar" in status.message
    assert "tests/library/fixtures/synthetic_collection.xml" in status.message


def test_require_chatterbox_ref_fails_without_bundled_ref(tmp_path: Path) -> None:
    _write_bundle(tmp_path, MAC_TRIPLE)

    status = gate.check_sidecar_bundle_ready(
        root=tmp_path,
        triple=MAC_TRIPLE,
        require_chatterbox_ref=True,
    )

    assert status.ok is False
    assert "Chatterbox release has no bundled voice reference" in status.message
    assert str(gate.CHATTERBOX_REF_REL) in status.message


def test_require_chatterbox_ref_accepts_complete_bundled_ref(tmp_path: Path) -> None:
    binary = _write_bundle(tmp_path, MAC_TRIPLE)
    ref_path = _write_bundled_chatterbox_ref(tmp_path, MAC_TRIPLE)

    status = gate.check_sidecar_bundle_ready(
        root=tmp_path,
        triple=MAC_TRIPLE,
        require_chatterbox_ref=True,
    )

    assert status.ok is True
    assert status.binary == binary
    assert str(ref_path) in gate.chatterbox_release_ref_ready(binary.parent)[1]


def test_require_chatterbox_ref_rejects_wrong_sample_rate(
    tmp_path: Path,
) -> None:
    _write_bundle(tmp_path, MAC_TRIPLE)
    _write_bundled_chatterbox_ref(tmp_path, MAC_TRIPLE, sample_rate=16_000)

    status = gate.check_sidecar_bundle_ready(
        root=tmp_path,
        triple=MAC_TRIPLE,
        require_chatterbox_ref=True,
    )

    assert status.ok is False
    assert "expected 24000 Hz Chatterbox ref" in status.message


def test_require_chatterbox_ref_rejects_unreadable_wav(tmp_path: Path) -> None:
    _write_bundle(tmp_path, MAC_TRIPLE)
    ref_path = _bundle_dir(tmp_path, MAC_TRIPLE) / gate.CHATTERBOX_REF_REL
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    ref_path.write_text("nope", encoding="utf-8")

    status = gate.check_sidecar_bundle_ready(
        root=tmp_path,
        triple=MAC_TRIPLE,
        require_chatterbox_ref=True,
    )

    assert status.ok is False
    assert "unreadable WAV" in status.message


def test_bundled_chatterbox_ref_check_does_not_import_tts_runtime(
    tmp_path: Path, monkeypatch
) -> None:
    binary = _write_bundle(tmp_path, MAC_TRIPLE)
    _write_bundled_chatterbox_ref(tmp_path, MAC_TRIPLE)
    real_import = builtins.__import__

    def guard_import(name, *args, **kwargs):
        if name.startswith("vibemix.agent") or name.startswith("mlx_audio"):
            raise AssertionError(f"release verifier imported runtime-only module: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guard_import)

    ok, detail = gate.chatterbox_release_ref_ready(binary.parent)

    assert ok is True
    assert "bundled Chatterbox ref ready" in detail


def test_main_returns_zero_for_ready_explicit_triple(tmp_path: Path, capsys) -> None:
    _write_bundle(tmp_path, MAC_TRIPLE)

    rc = gate.main(["--root", str(tmp_path), "--triple", MAC_TRIPLE])

    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_main_returns_one_for_placeholder_bundle(tmp_path: Path, capsys) -> None:
    bundle = _bundle_dir(tmp_path, MAC_TRIPLE)
    bundle.mkdir(parents=True)
    (bundle / ".placeholder").write_text("placeholder\n", encoding="utf-8")

    rc = gate.main(["--root", str(tmp_path), "--triple", MAC_TRIPLE])

    assert rc == 1
    assert "placeholder-only" in capsys.readouterr().err
