# SPDX-License-Identifier: Apache-2.0
"""Progress-path override used by live Learn probes."""

from __future__ import annotations

from pathlib import Path

from vibemix.learn.progress import progress_path


def test_progress_path_honors_live_probe_env_override(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "isolated-learn-progress.json"
    monkeypatch.setenv("VIBEMIX_LEARN_PROGRESS_PATH", str(target))

    assert progress_path() == target
