"""Tests for the local Tauri sidecar bundle readiness gate."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from scripts.dist import check_sidecar_bundle_ready as gate

MAC_TRIPLE = "aarch64-apple-darwin"
WIN_TRIPLE = "x86_64-pc-windows-msvc"


def _bundle_dir(root: Path, triple: str) -> Path:
    return root / gate.BINARIES_REL / f"vibemix-core-{triple}"


def _write_learn_exemplar_wavs(bundle: Path) -> None:
    for rel in gate.LEARN_EXEMPLAR_WAVS:
        path = bundle / "_internal" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"wav")


def _write_bundle(
    root: Path,
    triple: str,
    *,
    size: int = 8192,
    executable: bool = True,
    bundled_schema: str | None = None,
    learn_wavs: bool = True,
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
    return binary


def _write_source_schema(root: Path, body: str = '{"oneOf": []}\n') -> None:
    schema = root / gate.IPC_SCHEMA_REL
    schema.parent.mkdir(parents=True, exist_ok=True)
    schema.write_text(body, encoding="utf-8")


def _write_bundled_moss_model(root: Path, triple: str) -> Path:
    base = _bundle_dir(root, triple) / "_internal" / "models" / "moss-tts-onnx"
    model_dir = base / gate.MOSS_MODEL_DIRNAME
    codec_dir = base / "MOSS-Audio-Tokenizer-Nano-ONNX"
    model_dir.mkdir(parents=True)
    codec_dir.mkdir(parents=True)
    (model_dir / gate.MOSS_MANIFEST).write_text(
        json.dumps(
            {
                "model_files": {
                    "tts_meta": "tts_browser_onnx_meta.json",
                    "codec_meta": "../MOSS-Audio-Tokenizer-Nano-ONNX/codec_browser_onnx_meta.json",
                    "tokenizer_model": "tokenizer.model",
                }
            }
        ),
        encoding="utf-8",
    )
    (model_dir / "tts_browser_onnx_meta.json").write_text(
        json.dumps(
            {
                "files": {"prefill": "moss_tts_prefill.onnx"},
                "external_data_files": {"moss_tts_prefill.onnx": ["moss_tts_global_shared.data"]},
            }
        ),
        encoding="utf-8",
    )
    (codec_dir / "codec_browser_onnx_meta.json").write_text(
        json.dumps(
            {
                "files": {"decode": "moss_audio_tokenizer_decode_step.onnx"},
                "external_data_files": {
                    "moss_audio_tokenizer_decode_step.onnx": [
                        "moss_audio_tokenizer_decode_shared.data"
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    for path in (
        model_dir / "tokenizer.model",
        model_dir / "moss_tts_prefill.onnx",
        model_dir / "moss_tts_global_shared.data",
        codec_dir / "moss_audio_tokenizer_decode_step.onnx",
        codec_dir / "moss_audio_tokenizer_decode_shared.data",
    ):
        path.write_bytes(b"x")
    return model_dir


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


def test_require_moss_source_fails_without_bundle_or_archive(
    tmp_path: Path, monkeypatch
) -> None:
    _write_bundle(tmp_path, MAC_TRIPLE)
    monkeypatch.delenv(gate.MOSS_ARCHIVE_URL_ENV, raising=False)
    monkeypatch.delenv(gate.MOSS_ARCHIVE_SHA_ENV, raising=False)
    monkeypatch.delenv(gate.MOSS_ARCHIVE_SIZE_ENV, raising=False)

    status = gate.check_sidecar_bundle_ready(
        root=tmp_path,
        triple=MAC_TRIPLE,
        require_moss_source=True,
    )

    assert status.ok is False
    assert "MOSS-only release has no model source" in status.message
    assert gate.MOSS_ARCHIVE_URL_ENV in status.message


def test_require_moss_source_accepts_release_archive_pins(
    tmp_path: Path, monkeypatch
) -> None:
    binary = _write_bundle(tmp_path, MAC_TRIPLE)
    monkeypatch.setenv(gate.MOSS_ARCHIVE_URL_ENV, "https://models.example/moss.zip")
    monkeypatch.setenv(gate.MOSS_ARCHIVE_SHA_ENV, "a" * 64)
    monkeypatch.setenv(gate.MOSS_ARCHIVE_SIZE_ENV, "123")

    status = gate.check_sidecar_bundle_ready(
        root=tmp_path,
        triple=MAC_TRIPLE,
        require_moss_source=True,
    )

    assert status.ok is True
    assert status.binary == binary


def test_require_moss_source_rejects_unverified_archive_pins(
    tmp_path: Path, monkeypatch
) -> None:
    _write_bundle(tmp_path, MAC_TRIPLE)
    monkeypatch.setenv(gate.MOSS_ARCHIVE_URL_ENV, "http://models.example/moss.zip")
    monkeypatch.setenv(gate.MOSS_ARCHIVE_SHA_ENV, "not-a-sha")
    monkeypatch.setenv(gate.MOSS_ARCHIVE_SIZE_ENV, "0")

    status = gate.check_sidecar_bundle_ready(
        root=tmp_path,
        triple=MAC_TRIPLE,
        require_moss_source=True,
    )

    assert status.ok is False
    assert "https:// URL" in status.message
    assert "64-character lowercase SHA-256" in status.message
    assert "positive byte count" in status.message


def test_require_moss_source_accepts_complete_bundled_model(
    tmp_path: Path, monkeypatch
) -> None:
    binary = _write_bundle(tmp_path, MAC_TRIPLE)
    model_dir = _write_bundled_moss_model(tmp_path, MAC_TRIPLE)
    monkeypatch.delenv("VIBEMIX_MOSS_TTS_DIR", raising=False)
    monkeypatch.delenv(gate.MOSS_ARCHIVE_URL_ENV, raising=False)
    monkeypatch.delenv(gate.MOSS_ARCHIVE_SHA_ENV, raising=False)
    monkeypatch.delenv(gate.MOSS_ARCHIVE_SIZE_ENV, raising=False)

    status = gate.check_sidecar_bundle_ready(
        root=tmp_path,
        triple=MAC_TRIPLE,
        require_moss_source=True,
    )

    assert status.ok is True
    assert status.binary == binary
    assert os.environ.get("VIBEMIX_MOSS_TTS_DIR") is None
    assert str(model_dir) in gate._bundled_moss_model_status(binary.parent)[1]


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
