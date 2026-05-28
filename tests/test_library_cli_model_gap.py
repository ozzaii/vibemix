# SPDX-License-Identifier: Apache-2.0
"""Library-CLI model-gap UX (2026-05-29 robustification).

A brand-new user with an empty ``~/.cache/vibemix/`` who runs ``library search``
used to get a raw Python traceback (FileNotFoundError / ImportError from the CLAP
embedder). These tests pin the friendly-hint contract:

  1. The ONNX-dependency gap (onnxruntime/tokenizers not installed) → install hint.
  2. The model-files-absent gap (FileNotFoundError while the model is reported
     NOT installed) → install hint.
  3. An UNRELATED error (model present, or a non-model error) → None, so the CLI
     re-raises and never masks a real failure.
"""

from __future__ import annotations

from vibemix.__main__ import _library_model_gap_hint, _run_library_cli


def _status(installed: bool):
    return lambda: {"installed": installed, "missing": [] if installed else ["onnx/audio_model.onnx"]}


def test_dep_gap_returns_install_hint() -> None:
    hint = _library_model_gap_hint(ImportError("No module named 'onnxruntime'"))
    assert hint is not None
    assert "library models --install clap" in hint


def test_model_files_absent_returns_install_hint() -> None:
    exc = FileNotFoundError("onnx/audio_model.onnx")
    hint = _library_model_gap_hint(exc, status_loader=_status(installed=False))
    assert hint is not None
    assert "isn't installed" in hint


def test_filenotfound_with_model_installed_is_not_translated() -> None:
    # The model IS installed → this FileNotFoundError is something else (e.g. a
    # user-supplied missing playlist path). Must NOT be masked.
    exc = FileNotFoundError("/Users/dj/sets/missing.json")
    assert _library_model_gap_hint(exc, status_loader=_status(installed=True)) is None


def test_unrelated_error_returns_none() -> None:
    assert _library_model_gap_hint(ValueError("bad arg")) is None
    assert _library_model_gap_hint(RuntimeError("boom")) is None


def test_run_library_cli_translates_model_gap_to_exit_2(monkeypatch, capsys) -> None:
    # Drive the real dispatch: a command whose handler raises the model gap
    # returns 2 (not a traceback) and prints the hint to stderr.
    import vibemix.__main__ as main_mod

    def _boom(_args):
        raise FileNotFoundError("onnx/audio_model.onnx")

    monkeypatch.setattr(
        main_mod, "_library_model_gap_hint", lambda e, **k: "INSTALL_HINT"
    )

    def _fake_build(parser):
        sub = parser.add_subparsers(dest="cmd")
        p = sub.add_parser("search")
        p.add_argument("query")
        p.set_defaults(func=_boom)

    monkeypatch.setattr(main_mod, "_build_library_subparsers", _fake_build)
    rc = _run_library_cli(["search", "techno"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "INSTALL_HINT" in err


def test_run_library_cli_reraises_unrelated_error(monkeypatch) -> None:
    import vibemix.__main__ as main_mod

    def _boom(_args):
        raise FileNotFoundError("/some/user/path.json")

    monkeypatch.setattr(main_mod, "_library_model_gap_hint", lambda e, **k: None)

    def _fake_build(parser):
        sub = parser.add_subparsers(dest="cmd")
        p = sub.add_parser("export-set")
        p.add_argument("path")
        p.set_defaults(func=_boom)

    monkeypatch.setattr(main_mod, "_build_library_subparsers", _fake_build)
    import pytest

    with pytest.raises(FileNotFoundError):
        _run_library_cli(["export-set", "/some/user/path.json"])
