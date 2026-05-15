# SPDX-License-Identifier: Apache-2.0
"""Plan 29-07 Task 1: stripper wired into tldr.py.

Sentences without ≥1 citation never reach the renderer. Empty-after-strip
→ typed DebriefGenerationError(reason="tldr_generation_failed").
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vibemix.debrief.tldr import DebriefGenerationError, generate_tldr_text


def _resp(text: str):
    return SimpleNamespace(text=text)


def test_three_cited_three_uncited_keeps_three():
    client = MagicMock()
    text = (
        "Cited one [ev:M@1]. "
        "Uncited one. "
        "Cited two [track:t1]. "
        "Uncited two. "
        "Cited three [ev:P@2]. "
        "Uncited three."
    )
    client.models.generate_content.return_value = _resp(text)
    out = generate_tldr_text(client, ["c"], "cited")
    assert "Cited one" in out
    assert "Cited two" in out
    assert "Cited three" in out
    assert "Uncited" not in out


def test_zero_cited_raises_typed_error():
    client = MagicMock()
    client.models.generate_content.return_value = _resp(
        "Random one. Random two. Random three."
    )
    with pytest.raises(DebriefGenerationError) as ei:
        generate_tldr_text(client, ["c"], "cited")
    assert ei.value.reason == "tldr_generation_failed"


def test_stripper_logs_to_stderr(caplog):
    import logging

    caplog.set_level(logging.INFO, logger="vibemix.debrief.stripper")
    client = MagicMock()
    client.models.generate_content.return_value = _resp(
        "Cited [ev:M@1]. Uncited filler."
    )
    generate_tldr_text(client, ["c"], "cited")
    assert any("stripped uncited" in r.message for r in caplog.records)
