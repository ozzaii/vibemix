"""Tests for the Tauri package preparation script."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from scripts.dist import prepare_tauri_build as prep
from scripts.dist.check_sidecar_bundle_ready import SidecarBundleStatus


def test_check_only_raises_when_sidecar_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prep, "detect_host_triple", lambda: "aarch64-apple-darwin")
    monkeypatch.setattr(
        prep,
        "check_sidecar_bundle_ready",
        lambda **_: SidecarBundleStatus(False, "placeholder-only", Path("missing")),
    )

    with pytest.raises(RuntimeError, match="placeholder-only"):
        prep.prepare_tauri_build(skip_frontend=True, check_only=True)


def test_ready_inputs_skip_sidecar_rebuild(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    require_moss_source_calls: list[bool] = []
    monkeypatch.delenv("VIBEMIX_FORCE_SIDECAR", raising=False)
    monkeypatch.delenv("VIBEMIX_REQUIRE_MOSS_SOURCE", raising=False)
    monkeypatch.setattr(prep, "detect_host_triple", lambda: "aarch64-apple-darwin")

    def ready_status(**kwargs) -> SidecarBundleStatus:
        require_moss_source_calls.append(kwargs["require_moss_source"])
        return SidecarBundleStatus(True, "ready", Path("vibemix-core"))

    monkeypatch.setattr(prep, "check_sidecar_bundle_ready", ready_status)
    monkeypatch.setattr(prep, "_run", lambda cmd, **_: calls.append(cmd))

    prep.prepare_tauri_build(skip_frontend=True)

    assert calls == []
    assert require_moss_source_calls == [False, False]


def test_require_moss_source_flag_threads_to_readiness_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    require_moss_source_calls: list[bool] = []
    monkeypatch.setattr(prep, "detect_host_triple", lambda: "aarch64-apple-darwin")

    def ready_status(**kwargs) -> SidecarBundleStatus:
        require_moss_source_calls.append(kwargs["require_moss_source"])
        return SidecarBundleStatus(True, "ready", Path("vibemix-core"))

    monkeypatch.setattr(prep, "check_sidecar_bundle_ready", ready_status)
    monkeypatch.setattr(prep, "_run", lambda cmd, **_: calls.append(cmd))

    prep.prepare_tauri_build(skip_frontend=True, require_moss_source=True)

    assert calls == []
    assert require_moss_source_calls == [True, True]


def test_require_moss_source_env_threads_to_check_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    require_moss_source_calls: list[bool] = []
    monkeypatch.setenv("VIBEMIX_REQUIRE_MOSS_SOURCE", "1")
    monkeypatch.setattr(prep, "detect_host_triple", lambda: "aarch64-apple-darwin")

    def missing_moss_status(**kwargs) -> SidecarBundleStatus:
        require_moss_source_calls.append(kwargs["require_moss_source"])
        return SidecarBundleStatus(False, "missing moss source", Path("vibemix-core"))

    monkeypatch.setattr(prep, "check_sidecar_bundle_ready", missing_moss_status)

    with pytest.raises(RuntimeError, match="missing moss source"):
        prep.prepare_tauri_build(skip_frontend=True, check_only=True)

    assert require_moss_source_calls == [True]


def test_force_sidecar_env_rebuilds_ready_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    statuses = iter(
        [
            SidecarBundleStatus(True, "ready", Path("vibemix-core")),
            SidecarBundleStatus(True, "ready", Path("vibemix-core")),
        ]
    )
    monkeypatch.setenv("VIBEMIX_FORCE_SIDECAR", "1")
    monkeypatch.setattr(prep, "detect_host_triple", lambda: "aarch64-apple-darwin")
    monkeypatch.setattr(prep, "check_sidecar_bundle_ready", lambda **_: next(statuses))
    monkeypatch.setattr(prep, "_run", lambda cmd, **_: calls.append(cmd))

    prep.prepare_tauri_build(skip_frontend=True)

    assert len(calls) == 1
    assert calls[0][-2:] == ["--spec", "vibemix-core.macos.spec"]


def test_missing_sidecar_triggers_platform_build_then_recheck(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    statuses = iter(
        [
            SidecarBundleStatus(False, "placeholder-only", Path("missing")),
            SidecarBundleStatus(True, "ready", Path("vibemix-core")),
        ]
    )
    monkeypatch.setattr(prep, "detect_host_triple", lambda: "aarch64-apple-darwin")
    monkeypatch.setattr(prep, "check_sidecar_bundle_ready", lambda **_: next(statuses))
    monkeypatch.setattr(prep, "_run", lambda cmd, **_: calls.append(cmd))

    prep.prepare_tauri_build(skip_frontend=True)

    assert len(calls) == 1
    assert calls[0][-2:] == ["--spec", "vibemix-core.macos.spec"]


def test_windows_triple_uses_windows_spec(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    statuses = iter(
        [
            SidecarBundleStatus(False, "missing", Path("missing")),
            SidecarBundleStatus(True, "ready", Path("vibemix-core.exe")),
        ]
    )
    monkeypatch.setattr(prep, "check_sidecar_bundle_ready", lambda **_: next(statuses))
    monkeypatch.setattr(prep, "_run", lambda cmd, **_: calls.append(cmd))

    prep.prepare_tauri_build(triple="x86_64-pc-windows-msvc", skip_frontend=True)

    assert calls[0][-2:] == ["--spec", "vibemix-core.windows.spec"]


def test_frontend_build_runs_before_sidecar_check(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(prep, "detect_host_triple", lambda: "aarch64-apple-darwin")
    monkeypatch.setattr(
        prep,
        "check_sidecar_bundle_ready",
        lambda **_: SidecarBundleStatus(True, "ready", Path("vibemix-core")),
    )
    monkeypatch.setattr(prep, "_run", lambda cmd, **_: calls.append(cmd))

    prep.prepare_tauri_build()

    assert calls == [["npm", "--prefix", str(prep.REPO_ROOT / "tauri" / "ui"), "run", "build"]]


def test_main_returns_one_on_failed_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        prep,
        "prepare_tauri_build",
        lambda **_: (_ for _ in ()).throw(RuntimeError("not ready")),
    )

    assert prep.main(["--skip-frontend", "--check-only"]) == 1


def test_main_returns_one_on_failed_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        prep,
        "prepare_tauri_build",
        lambda **_: (_ for _ in ()).throw(
            subprocess.CalledProcessError(7, ["npm", "run", "build"])
        ),
    )

    assert prep.main([]) == 1


def test_main_threads_require_moss_source_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(prep, "prepare_tauri_build", lambda **kwargs: captured.update(kwargs))

    assert prep.main(["--skip-frontend", "--require-moss-source"]) == 0
    assert captured["skip_frontend"] is True
    assert captured["require_moss_source"] is True
