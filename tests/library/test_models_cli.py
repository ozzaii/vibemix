# SPDX-License-Identifier: Apache-2.0
"""Offline `library models --json` CLI status for setup UX."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import tomllib
from pathlib import Path

import pytest

import vibemix.__main__ as m


def test_local_ai_optional_extras_are_declared() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    extras = data["project"]["optional-dependencies"]

    expected = {
        "onnxruntime>=1.20",
    }
    chatterbox_dep = {
        "mlx-audio>=0.3; sys_platform == 'darwin' and platform_machine == 'arm64'"
    }
    assert set(extras["clap"]) == expected | {"tokenizers>=0.22"}
    assert set(extras["cue"]) == expected
    assert set(extras["tts-local"]) == chatterbox_dep
    assert set(extras["ai-local"]) == expected | {"tokenizers>=0.22"} | chatterbox_dep


@pytest.fixture(autouse=True)
def _fake_model_status(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("real_model_status"):
        return

    import vibemix.agent.chatterbox_tts as chatterbox_tts
    import vibemix.library.clap_engine as clap_engine
    import vibemix.library.cue_detr as cue_detr

    monkeypatch.setattr(
        clap_engine,
        "onnx_model_status",
        lambda: {
            "installed": True,
            "path": "/tmp/vibemix-test/clap-onnx",
            "missing": [],
        },
    )
    monkeypatch.setattr(
        chatterbox_tts,
        "resolve_ref_path",
        lambda: Path("/tmp/vibemix-test/cohost_voice_ref.wav"),
    )
    monkeypatch.setattr(
        chatterbox_tts,
        "default_ref_path",
        lambda: Path("/tmp/vibemix-test/cohost_voice_ref.wav"),
    )
    monkeypatch.setattr(chatterbox_tts, "chatterbox_available", lambda: True)
    monkeypatch.setattr(chatterbox_tts, "chatterbox_unavailable_reason", lambda: "unknown")
    monkeypatch.setattr(
        cue_detr,
        "model_status",
        lambda: {
            "installed": False,
            "path": "/tmp/vibemix-test/cue-detr-onnx/cuedetr.fp32.onnx",
            "missing": ["cuedetr.fp32.onnx"],
        },
    )


def _run_handler(monkeypatch: pytest.MonkeyPatch) -> dict:
    buf = io.StringIO()
    monkeypatch.setattr(m.sys, "stdout", buf)
    rc = m._cmd_library_models(argparse.Namespace(json=True))
    assert rc == 0
    return json.loads(buf.getvalue())


def test_models_json_reports_required_and_optional_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _run_handler(monkeypatch)

    assert payload["required_ready"] is True
    assert payload["all_ready"] is False

    clap, voice, cue = payload["models"]
    assert clap == {
        "id": "clap",
        "label": "CLAP ONNX",
        "role": "library embeddings/search/similarity",
        "required": True,
        "env": "VIBEMIX_CLAP_ONNX_DIR",
        "installed": True,
        "installable": True,
        "path": "/tmp/vibemix-test/clap-onnx",
        "missing": [],
        "mismatched": [],
    }
    assert voice == {
        "id": "chatterbox-voice",
        "label": "Chatterbox voice",
        "role": "local co-host voice",
        "required": True,
        "env": "VIBEMIX_CHATTERBOX_REF",
        "installed": True,
        "installable": False,
        "path": "/tmp/vibemix-test/cohost_voice_ref.wav",
        "missing": [],
        "mismatched": [],
    }
    assert cue["id"] == "cue-detr"
    assert cue["required"] is False
    assert cue["installed"] is False
    assert cue["installable"] is False
    assert cue["missing"] == ["cuedetr.fp32.onnx"]
    assert cue["mismatched"] == []
    assert cue["env"] == "VIBEMIX_CUE_ONNX_PATH"


def test_models_json_marks_cue_installable_when_hosted_url_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VIBEMIX_CUE_ONNX_URL", "https://models.example/cuedetr.onnx")

    payload = _run_handler(monkeypatch)

    cue = next(model for model in payload["models"] if model["id"] == "cue-detr")
    assert cue["id"] == "cue-detr"
    assert cue["installable"] is True


def test_models_json_marks_missing_chatterbox_ref_as_required_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vibemix.agent.chatterbox_tts as chatterbox_tts

    monkeypatch.setattr(chatterbox_tts, "resolve_ref_path", lambda: None)
    monkeypatch.setattr(chatterbox_tts, "chatterbox_available", lambda: False)
    monkeypatch.setattr(
        chatterbox_tts,
        "chatterbox_unavailable_reason",
        lambda: "mlx-audio not installed (Chatterbox voice is Apple-only)",
    )

    payload = _run_handler(monkeypatch)

    voice = next(model for model in payload["models"] if model["id"] == "chatterbox-voice")
    assert payload["required_ready"] is False
    assert voice["required"] is True
    assert voice["missing"] == [
        "cohost_voice_ref.wav",
        "mlx-audio not installed (Chatterbox voice is Apple-only)",
    ]


def test_models_subcommand_routes_through_cli(
    capsys: pytest.CaptureFixture,
) -> None:
    rc = m._run_library_cli(["models", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert [model["id"] for model in payload["models"]] == [
        "clap",
        "chatterbox-voice",
        "cue-detr",
    ]


def test_models_install_payload_is_included(monkeypatch: pytest.MonkeyPatch) -> None:
    import vibemix.library.model_assets as model_assets

    monkeypatch.setattr(
        model_assets,
        "install_models",
        lambda target, force=False: {
            "target": target,
            "ok": True,
            "results": [
                {
                    "id": "clap",
                    "installed": True,
                    "path": "/tmp/vibemix-test/clap-onnx",
                    "files": [],
                    "errors": [],
                    "force": force,
                }
            ],
        },
    )

    buf = io.StringIO()
    monkeypatch.setattr(m.sys, "stdout", buf)
    rc = m._cmd_library_models(argparse.Namespace(json=True, install="clap", force=True))
    assert rc == 0
    payload = json.loads(buf.getvalue())
    assert payload["install"]["target"] == "clap"
    assert payload["install"]["results"][0]["force"] is True


def test_models_install_clap_target_routes_through_cli(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    import vibemix.library.model_assets as model_assets

    monkeypatch.setattr(
        model_assets,
        "install_models",
        lambda target, force=False: {
            "target": target,
            "ok": True,
            "results": [
                {
                    "id": "clap",
                    "installed": True,
                    "path": "/tmp/vibemix-test/clap-onnx",
                    "files": [],
                    "errors": [],
                }
            ],
        },
    )

    rc = m._run_library_cli(["models", "--install", "clap", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["install"]["target"] == "clap"
    assert payload["install"]["results"][0]["id"] == "clap"


def test_models_install_chatterbox_target_routes_through_cli(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    import vibemix.library.model_assets as model_assets

    monkeypatch.setattr(
        model_assets,
        "install_models",
        lambda target, force=False: {
            "target": target,
            "ok": True,
            "results": [
                {
                    "id": "chatterbox",
                    "installed": True,
                    "path": "/tmp/vibemix-test/chatterbox",
                    "files": [],
                    "errors": [],
                }
            ],
        },
    )

    rc = m._run_library_cli(["models", "--install", "chatterbox", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["install"]["target"] == "chatterbox"
    assert payload["install"]["results"][0]["id"] == "chatterbox"


def test_models_install_moss_alias_is_still_accepted_by_cli(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    import vibemix.library.model_assets as model_assets

    monkeypatch.setattr(
        model_assets,
        "install_models",
        lambda target, force=False: {
            "target": target,
            "ok": True,
            "results": [
                {
                    "id": "chatterbox",
                    "installed": True,
                    "path": "/tmp/vibemix-test/chatterbox",
                    "files": [],
                    "errors": [],
                }
            ],
        },
    )

    rc = m._run_library_cli(["models", "--install", "moss", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["install"]["target"] == "moss"
    assert payload["install"]["results"][0]["id"] == "chatterbox"


def test_models_install_progress_keeps_stdout_json_pure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    import vibemix.library.model_assets as model_assets

    def _install(target, force=False, progress=None):
        assert target == "clap"
        assert force is False
        assert progress is not None
        progress(
            {
                "target": target,
                "id": "clap",
                "n": 2,
                "total": 6,
                "status": "downloading",
                "rel_path": "onnx/text_model.onnx",
                "downloaded": 1048576,
                "size": 501513769,
            }
        )
        return {
            "target": target,
            "ok": True,
            "results": [
                {
                    "id": "clap",
                    "installed": True,
                    "path": "/tmp/vibemix-test/clap-onnx",
                    "files": [],
                    "errors": [],
                }
            ],
        }

    monkeypatch.setattr(model_assets, "install_models", _install)

    rc = m._run_library_cli(["models", "--install", "clap", "--json", "--progress"])
    captured = capsys.readouterr()

    assert rc == 0
    assert json.loads(captured.out)["install"]["target"] == "clap"
    prefix, raw = captured.err.strip().split(" ", 1)
    assert prefix == "VIBEMIX_MODEL_PROGRESS"
    progress = json.loads(raw)
    assert progress["target"] == "clap"
    assert progress["id"] == "clap"
    assert progress["status"] == "downloading"


def test_models_install_cue_target_routes_through_cli(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    import vibemix.library.model_assets as model_assets

    monkeypatch.setattr(
        model_assets,
        "install_models",
        lambda target, force=False: {
            "target": target,
            "ok": True,
            "results": [
                {
                    "id": "cue-detr",
                    "installed": True,
                    "path": "/tmp/vibemix-test/cue-detr-onnx/cuedetr.fp32.onnx",
                    "files": [],
                    "errors": [],
                }
            ],
        },
    )

    rc = m._run_library_cli(["models", "--install", "cue", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["install"]["target"] == "cue"
    assert payload["install"]["results"][0]["id"] == "cue-detr"


def test_install_models_chatterbox_target_routes_to_prefetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vibemix.library.model_assets as model_assets

    monkeypatch.setattr(
        model_assets,
        "install_chatterbox_model",
        lambda force=False: {
            "id": "chatterbox",
            "installed": True,
            "path": "/tmp/vibemix-test/chatterbox",
            "repo": model_assets.CHATTERBOX_MODEL_REPO,
            "revision": model_assets.CHATTERBOX_MODEL_REVISION,
            "files": [],
            "errors": [],
            "force": force,
        },
    )

    payload = model_assets.install_models("chatterbox", force=True)

    assert payload["target"] == "chatterbox"
    assert payload["ok"] is True
    assert payload["results"][0]["id"] == "chatterbox"
    assert payload["results"][0]["force"] is True


def test_install_models_moss_alias_routes_to_chatterbox_prefetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vibemix.library.model_assets as model_assets

    monkeypatch.setattr(
        model_assets,
        "install_chatterbox_model",
        lambda force=False: {
            "id": "chatterbox",
            "installed": True,
            "path": "/tmp/vibemix-test/chatterbox",
            "repo": model_assets.CHATTERBOX_MODEL_REPO,
            "revision": model_assets.CHATTERBOX_MODEL_REVISION,
            "files": [],
            "errors": [],
            "force": force,
        },
    )

    payload = model_assets.install_models("moss", force=True)

    assert payload["target"] == "chatterbox"
    assert payload["ok"] is True
    assert payload["results"][0]["id"] == "chatterbox"
    assert payload["results"][0]["force"] is True


def test_models_install_failure_exits_nonzero_with_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vibemix.library.model_assets as model_assets

    monkeypatch.setattr(
        model_assets,
        "install_models",
        lambda target, force=False: {
            "target": target,
            "ok": False,
            "results": [
                {
                    "id": "clap",
                    "installed": False,
                    "path": "/tmp/vibemix-test/clap-onnx",
                    "files": [],
                    "errors": ["download failed"],
                }
            ],
        },
    )

    buf = io.StringIO()
    monkeypatch.setattr(m.sys, "stdout", buf)
    rc = m._cmd_library_models(argparse.Namespace(json=True, install="clap", force=False))
    assert rc == 1
    payload = json.loads(buf.getvalue())
    assert payload["install"]["ok"] is False
    assert payload["install"]["results"][0]["errors"] == ["download failed"]


def test_models_install_cue_reports_manual_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    import vibemix.library.model_assets as model_assets

    monkeypatch.delenv("VIBEMIX_CUE_ONNX_URL", raising=False)

    payload = model_assets.install_models("cue")
    assert payload["target"] == "cue"
    assert payload["ok"] is False
    assert payload["results"][0]["id"] == "cue-detr"
    assert "VIBEMIX_CUE_ONNX_URL" in payload["results"][0]["errors"][0]


def test_models_install_required_does_not_require_optional_cue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vibemix.library.model_assets as model_assets

    monkeypatch.setattr(
        model_assets,
        "install_clap_model",
        lambda force=False: {
            "id": "clap",
            "installed": True,
            "path": "/tmp/vibemix-test/clap-onnx",
            "files": [],
            "errors": [],
        },
    )
    monkeypatch.setattr(
        model_assets,
        "install_chatterbox_model",
        lambda force=False: {
            "id": "chatterbox",
            "installed": True,
            "path": "/tmp/vibemix-test/chatterbox",
            "files": [],
            "errors": [],
        },
    )

    def _unexpected_cue(*, force=False):
        raise AssertionError("required install must not touch optional CUE")

    monkeypatch.setattr(model_assets, "install_cue_model", _unexpected_cue)

    payload = model_assets.install_models("required")
    assert payload["target"] == "required"
    assert payload["ok"] is True
    assert [result["id"] for result in payload["results"]] == ["clap", "chatterbox"]


def test_install_cue_model_rejects_unverified_hosted_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vibemix.library.model_assets as model_assets

    monkeypatch.setenv("VIBEMIX_CUE_ONNX_URL", "https://models.example/cuedetr.onnx")
    monkeypatch.delenv("VIBEMIX_CUE_ONNX_SHA256", raising=False)
    monkeypatch.delenv("VIBEMIX_CUE_ONNX_SIZE", raising=False)

    payload = model_assets.install_cue_model()

    assert payload["installed"] is False
    assert any("VIBEMIX_CUE_ONNX_SHA256" in e for e in payload["errors"])
    assert any("VIBEMIX_CUE_ONNX_SIZE" in e for e in payload["errors"])


def test_install_cue_model_downloads_env_hosted_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vibemix.library.cue_detr as cue_detr
    import vibemix.library.model_assets as model_assets

    data = b"tiny-cue-onnx"
    digest = hashlib.sha256(data).hexdigest()
    target = tmp_path / "cuedetr.fp32.onnx"
    monkeypatch.setenv("VIBEMIX_CUE_ONNX_URL", "https://models.example/cuedetr.onnx")
    monkeypatch.setenv("VIBEMIX_CUE_ONNX_SHA256", digest)
    monkeypatch.setenv("VIBEMIX_CUE_ONNX_SIZE", str(len(data)))
    monkeypatch.setattr(cue_detr, "model_path", lambda: target)

    def _status():
        missing = [] if target.is_file() else [target.name]
        return {
            "installed": not missing,
            "path": str(target),
            "missing": missing,
            "mismatched": [],
        }

    def _fake_download(*, url, dest, expected_size, expected_sha256, rel_path):
        assert url == "https://models.example/cuedetr.onnx"
        assert expected_size == len(data)
        assert expected_sha256 == digest
        dest.write_bytes(data)
        return {
            "rel_path": rel_path,
            "path": str(dest),
            "status": "downloaded",
            "size": len(data),
            "sha256": digest,
            "url": url,
        }

    monkeypatch.setattr(cue_detr, "model_status", _status)
    monkeypatch.setattr(model_assets, "_download_url_to_file", _fake_download)

    payload = model_assets.install_cue_model()

    assert payload["installed"] is True
    assert payload["errors"] == []
    assert payload["files"][0]["status"] == "downloaded"
    assert target.read_bytes() == data


def test_models_install_all_requires_cue_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vibemix.library.model_assets as model_assets

    monkeypatch.setattr(
        model_assets,
        "install_clap_model",
        lambda force=False: {
            "id": "clap",
            "installed": True,
            "path": "/tmp/vibemix-test/clap-onnx",
            "files": [],
            "errors": [],
        },
    )
    monkeypatch.setattr(
        model_assets,
        "install_chatterbox_model",
        lambda force=False: {
            "id": "chatterbox",
            "installed": True,
            "path": "/tmp/vibemix-test/chatterbox",
            "files": [],
            "errors": [],
        },
    )
    monkeypatch.setattr(
        model_assets,
        "install_cue_model",
        lambda force=False: {
            "id": "cue-detr",
            "installed": False,
            "path": "/tmp/vibemix-test/cue-detr-onnx/cuedetr.fp32.onnx",
            "files": [],
            "errors": ["manual cue model missing"],
        },
    )

    payload = model_assets.install_models("all")
    assert payload["ok"] is False
    assert [result["id"] for result in payload["results"]] == [
        "clap",
        "chatterbox",
        "cue-detr",
    ]


@pytest.mark.real_model_status
def test_cue_model_status_marks_env_pinned_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vibemix.library.cue_detr as cue_detr

    good = b"expected"
    bad = b"bad"
    target = tmp_path / "cuedetr.fp32.onnx"
    target.write_bytes(bad)
    monkeypatch.setenv("VIBEMIX_CUE_ONNX_PATH", str(target))
    monkeypatch.setenv("VIBEMIX_CUE_ONNX_SHA256", hashlib.sha256(good).hexdigest())
    monkeypatch.setenv("VIBEMIX_CUE_ONNX_SIZE", str(len(good)))

    payload = cue_detr.model_status()

    assert payload["installed"] is False
    assert payload["missing"] == []
    assert payload["mismatched"] == ["cuedetr.fp32.onnx"]


def test_install_clap_model_skips_verified_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import vibemix.library.model_assets as model_assets

    data = b"tiny-model"
    digest = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(
        model_assets,
        "_CLAP_FILES",
        (model_assets.ModelFile("tiny.bin", len(data), digest),),
    )
    monkeypatch.setenv("VIBEMIX_CLAP_ONNX_DIR", str(tmp_path))
    (tmp_path / "tiny.bin").write_bytes(data)

    payload = model_assets.install_clap_model()
    assert payload["installed"] is True
    assert payload["files"][0]["status"] == "skipped"
    assert payload["files"][0]["sha256"] == digest


def test_install_models_progress_reports_target_and_verified_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import vibemix.library.model_assets as model_assets

    data = b"tiny-model"
    digest = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(
        model_assets,
        "_CLAP_FILES",
        (model_assets.ModelFile("tiny.bin", len(data), digest),),
    )
    monkeypatch.setenv("VIBEMIX_CLAP_ONNX_DIR", str(tmp_path))
    (tmp_path / "tiny.bin").write_bytes(data)
    frames: list[dict[str, object]] = []

    payload = model_assets.install_models("clap", progress=frames.append)

    assert payload["ok"] is True
    assert frames == [
        {
            "target": "clap",
            "id": "clap",
            "n": 1,
            "total": 1,
            "status": "verified",
            "rel_path": "tiny.bin",
            "downloaded": len(data),
            "size": len(data),
        }
    ]


def test_install_clap_model_downloads_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import vibemix.library.model_assets as model_assets

    data = b"tiny-model"
    digest = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(
        model_assets,
        "_CLAP_FILES",
        (model_assets.ModelFile("nested/tiny.bin", len(data), digest),),
    )
    monkeypatch.setenv("VIBEMIX_CLAP_ONNX_DIR", str(tmp_path))

    def _fake_download(spec, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return {
            "rel_path": spec.rel_path,
            "path": str(dest),
            "status": "downloaded",
            "size": len(data),
            "sha256": digest,
            "url": spec.url,
        }

    monkeypatch.setattr(model_assets, "_download_file", _fake_download)
    payload = model_assets.install_clap_model()
    assert payload["installed"] is True
    assert payload["files"][0]["status"] == "downloaded"
    assert (tmp_path / "nested" / "tiny.bin").read_bytes() == data


def test_install_clap_model_repairs_broken_cache_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import vibemix.library.model_assets as model_assets

    data = b"tiny-model"
    digest = hashlib.sha256(data).hexdigest()
    root = tmp_path / "clap-onnx"
    root.symlink_to(tmp_path / "missing-target")
    monkeypatch.setenv("VIBEMIX_CLAP_ONNX_DIR", str(root))
    monkeypatch.setattr(
        model_assets,
        "_CLAP_FILES",
        (model_assets.ModelFile("onnx/tiny.onnx", len(data), digest),),
    )

    def _fake_download(spec, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return {
            "rel_path": spec.rel_path,
            "path": str(dest),
            "status": "downloaded",
            "size": len(data),
            "sha256": digest,
            "url": spec.url,
        }

    monkeypatch.setattr(model_assets, "_download_file", _fake_download)

    payload = model_assets.install_clap_model()

    assert payload["installed"] is True
    assert root.is_dir()
    assert not root.is_symlink()
    assert (tmp_path / "clap-onnx.invalid").is_symlink()
    assert (root / "onnx" / "tiny.onnx").read_bytes() == data


def test_clap_manifest_defaults_to_full_precision_runtime_models() -> None:
    import vibemix.library.model_assets as model_assets

    specs = {spec.rel_path: spec for spec in model_assets.clap_model_files()}

    audio = specs["onnx/audio_model.onnx"]
    text = specs["onnx/text_model.onnx"]
    assert audio.source_rel_path is None
    assert audio.size == 281_749_092
    assert audio.sha256 == "3ecc72d27740e2a09ced20cf22fd6244122e5e506008763a0f368b3b4ff6eac8"
    assert audio.url.endswith("/onnx/audio_model.onnx")

    assert text.source_rel_path is None
    assert text.size == 501_513_769
    assert text.sha256 == "96c0f248bfaabe5d467958245beb0243e387ed628251e3b407b856848379e89c"
    assert text.url.endswith("/onnx/text_model.onnx")


def test_onnx_model_status_marks_wrong_sized_cache_for_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib

    import vibemix.library.clap_engine as clap_engine
    import vibemix.library.model_assets as model_assets

    clap_engine = importlib.reload(clap_engine)
    data = b"q8"
    digest = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(clap_engine, "_ONNX_REQUIRED_RELS", ("onnx/tiny.onnx",))
    monkeypatch.setattr(
        model_assets,
        "_CLAP_FILES",
        (model_assets.ModelFile("onnx/tiny.onnx", len(data), digest),),
    )
    monkeypatch.setenv("VIBEMIX_CLAP_ONNX_DIR", str(tmp_path))
    (tmp_path / "onnx").mkdir()
    (tmp_path / "onnx" / "tiny.onnx").write_bytes(b"fp32-sized")

    payload = clap_engine.onnx_model_status()
    assert payload["installed"] is False
    assert payload["missing"] == []
    assert payload["mismatched"] == ["onnx/tiny.onnx"]
