# SPDX-License-Identifier: Apache-2.0
"""Shared cache/model path helpers stay in sync across runtime modules."""

from __future__ import annotations

from pathlib import Path


def test_cache_paths_use_vibemix_cache_suffixes() -> None:
    from vibemix.library import cache_paths

    assert cache_paths.VIBEMIX_CACHE_DIR.name == "vibemix"
    assert cache_paths.EMBED_CACHE_DB_PATH == cache_paths.VIBEMIX_CACHE_DIR / "embeddings.db"
    assert (
        cache_paths.CLAP_EMBED_CACHE_DB_PATH == cache_paths.VIBEMIX_CACHE_DIR / "clap_embeddings.db"
    )
    assert (
        cache_paths.SECTION_VECTOR_CACHE_DB_PATH
        == cache_paths.VIBEMIX_CACHE_DIR / "section_vectors.db"
    )
    assert cache_paths.DEFAULT_CLAP_ONNX_DIR == cache_paths.VIBEMIX_CACHE_DIR / "clap-onnx"
    assert (
        cache_paths.DEFAULT_CUE_ONNX_PATH
        == cache_paths.VIBEMIX_CACHE_DIR / "cue-detr-onnx" / "cuedetr.fp32.onnx"
    )


def test_model_path_helpers_expand_env_overrides(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from vibemix.library.cache_paths import (
        CLAP_ONNX_ENV,
        CUE_ONNX_ENV,
        clap_onnx_dir,
        cue_onnx_path,
    )

    clap_dir = tmp_path / "models" / "clap"
    cue_path = tmp_path / "models" / "cue.onnx"
    monkeypatch.setenv(CLAP_ONNX_ENV, str(clap_dir))
    monkeypatch.setenv(CUE_ONNX_ENV, str(cue_path))

    assert clap_onnx_dir() == clap_dir
    assert cue_onnx_path() == cue_path


def test_runtime_modules_resolve_shared_model_paths(
    monkeypatch,
    tmp_path: Path,
) -> None:
    import vibemix.library.clap_engine as clap_engine
    import vibemix.library.cue_detr as cue_detr
    import vibemix.library.model_assets as model_assets
    from vibemix.library.cache_paths import CLAP_ONNX_ENV, CUE_ONNX_ENV

    clap_dir = tmp_path / "clap-onnx"
    cue_path = tmp_path / "cue-detr-onnx" / "cuedetr.fp32.onnx"
    monkeypatch.setenv(CLAP_ONNX_ENV, str(clap_dir))
    monkeypatch.setenv(CUE_ONNX_ENV, str(cue_path))

    assert model_assets._clap_model_dir() == clap_dir
    assert clap_engine.onnx_model_status()["path"] == str(clap_dir)
    assert cue_detr.model_path() == cue_path
    assert cue_detr.model_status()["path"] == str(cue_path)
