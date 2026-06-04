# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from vibemix.agent.dj_cohost import (
    _could_be_finished_line_meta_scaffold,
    repair_finished_headphone_line,
)


def test_final_polish_fragment_after_citation_tail_is_suppressed() -> None:
    raw = "108.0]\n\n4.  **Final Polish (Sven's voice):"

    assert _could_be_finished_line_meta_scaffold(raw) is True
    assert repair_finished_headphone_line(raw) is None


def test_final_polish_wrapper_keeps_quoted_headphone_line() -> None:
    raw = '108.0]\n\n4. **Final Polish (Sven\'s voice): "Hold this until the phrase."'

    assert repair_finished_headphone_line(raw) == "Hold this until the phrase."


def test_orphan_citation_tail_before_clean_line_is_removed() -> None:
    raw = "108.0] Hold this transition until the next phrase."

    assert _could_be_finished_line_meta_scaffold(raw) is True
    assert repair_finished_headphone_line(raw) == "Hold this transition until the next phrase."
