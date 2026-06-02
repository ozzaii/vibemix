# SPDX-License-Identifier: Apache-2.0
"""PyInstaller data collection for bundled local MOSS voice assets."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.dist import moss_bundle


def _write_fake_moss_tree(root: Path) -> Path:
    model_dir = root / moss_bundle.MOSS_MODEL_DIRNAME
    codec_dir = root / moss_bundle.MOSS_CODEC_DIRNAME
    model_dir.mkdir(parents=True)
    codec_dir.mkdir(parents=True)
    (model_dir / moss_bundle.MOSS_MANIFEST).write_text(
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
    (model_dir / "tts_browser_onnx_meta.json").write_text("{}", encoding="utf-8")
    (model_dir / "tokenizer.model").write_bytes(b"tok")
    (model_dir / ".cache" / "huggingface").mkdir(parents=True)
    (model_dir / ".cache" / "huggingface" / ".gitignore").write_text("*\n", encoding="utf-8")
    (codec_dir / "codec_browser_onnx_meta.json").write_text("{}", encoding="utf-8")
    (codec_dir / "moss_audio_tokenizer_decode_step.onnx").write_bytes(b"onnx")
    return model_dir


def test_collect_moss_model_datas_preserves_runtime_bundle_layout(
    monkeypatch, tmp_path: Path
) -> None:
    root = tmp_path / "moss-tts-onnx"
    model_dir = _write_fake_moss_tree(root)
    monkeypatch.setenv(moss_bundle.MOSS_MODEL_DIR_ENV, str(model_dir))

    datas = moss_bundle.collect_moss_model_datas()

    pairs = {(Path(src).name, dest) for src, dest in datas}
    assert (
        moss_bundle.MOSS_MANIFEST,
        "models/moss-tts-onnx/MOSS-TTS-Nano-100M-ONNX",
    ) in pairs
    assert (
        "codec_browser_onnx_meta.json",
        "models/moss-tts-onnx/MOSS-Audio-Tokenizer-Nano-ONNX",
    ) in pairs
    assert not any(".cache" in src or ".cache" in dest for src, dest in datas)


def test_collect_moss_model_datas_is_empty_when_model_missing(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(moss_bundle.MOSS_MODEL_DIR_ENV, str(tmp_path / "missing"))

    assert moss_bundle.collect_moss_model_datas() == []
