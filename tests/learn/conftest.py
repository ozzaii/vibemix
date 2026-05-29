# SPDX-License-Identifier: Apache-2.0
"""Shared Learn test isolation."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_learn_progress_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Keep runtime save_progress calls inside each test's temp dir."""
    target = tmp_path / "learn-progress.json"
    monkeypatch.setattr("vibemix.learn.progress.progress_path", lambda: target)

