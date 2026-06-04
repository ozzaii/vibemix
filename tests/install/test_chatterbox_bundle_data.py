# SPDX-License-Identifier: Apache-2.0
"""PyInstaller data collection for the bundled Chatterbox reference voice."""

from __future__ import annotations

from pathlib import Path

from scripts.dist import chatterbox_bundle


def test_collect_chatterbox_ref_datas_preserves_runtime_bundle_layout(
    monkeypatch, tmp_path: Path
) -> None:
    ref = tmp_path / chatterbox_bundle.CHATTERBOX_REF_NAME
    ref.write_bytes(b"RIFF$\x00\x00\x00WAVEfmt ")
    monkeypatch.setenv(chatterbox_bundle.CHATTERBOX_REF_ENV, str(ref))

    datas = chatterbox_bundle.collect_chatterbox_ref_datas()

    assert datas == [(str(ref), "models/chatterbox")]


def test_collect_chatterbox_ref_datas_is_empty_when_ref_missing(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(chatterbox_bundle.CHATTERBOX_REF_ENV, str(tmp_path / "missing.wav"))

    assert chatterbox_bundle.collect_chatterbox_ref_datas() == []
