# SPDX-License-Identifier: Apache-2.0
"""PROMPT-03: TurnHistory ring — N=12 capacity, alternating user/model push,
oldest-drop overflow, <recent_turns> as_text() format.

Format (per Phase 10 plan):

    <recent_turns>
    <user>...</user>
    <model>...</model>
    ...
    </recent_turns>

In-memory only (no disk persistence v1). Empty ring → empty string (NOT a
bare wrapper) so the dj_cohost prompt can drop it cleanly when there's no
history yet.
"""

from __future__ import annotations

import pytest

from vibemix.prompts.turn_history import TurnHistory

# ---------------------------------------------------------------------------
# Construction + defaults
# ---------------------------------------------------------------------------


def test_turn_history_01_starts_empty() -> None:
    """Fresh ring is empty; as_text() returns empty string."""
    th = TurnHistory()
    assert th.as_text() == ""


def test_turn_history_02_default_max_pairs_is_12() -> None:
    """Default capacity is 12 pairs (CONTEXT §TurnHistory)."""
    th = TurnHistory()
    assert th.max_pairs == 12


def test_turn_history_03_custom_max_pairs() -> None:
    """Capacity is configurable via constructor."""
    th = TurnHistory(max_pairs=4)
    assert th.max_pairs == 4


# ---------------------------------------------------------------------------
# Push semantics
# ---------------------------------------------------------------------------


def test_turn_history_04_push_user_then_model_alternates() -> None:
    """User+model alternation produces the expected as_text shape."""
    th = TurnHistory()
    th.push_user("kaan asks: how's the mix?")
    th.push_model("the kicks landed clean")
    out = th.as_text()
    assert out.startswith("<recent_turns>\n")
    assert out.endswith("\n</recent_turns>")
    assert "<user>kaan asks: how's the mix?</user>" in out
    assert "<model>the kicks landed clean</model>" in out


def test_turn_history_05_push_user_only() -> None:
    """Pushing only user turns still renders correctly."""
    th = TurnHistory()
    th.push_user("first")
    th.push_user("second")
    out = th.as_text()
    assert "<user>first</user>" in out
    assert "<user>second</user>" in out
    assert "<model>" not in out


def test_turn_history_06_push_model_only() -> None:
    """Pushing only model turns still renders correctly."""
    th = TurnHistory()
    th.push_model("first reply")
    th.push_model("second reply")
    out = th.as_text()
    assert "<model>first reply</model>" in out
    assert "<model>second reply</model>" in out
    assert "<user>" not in out


def test_turn_history_07_chronological_order_preserved() -> None:
    """as_text emits entries in push-order (oldest first)."""
    th = TurnHistory()
    th.push_user("u1")
    th.push_model("m1")
    th.push_user("u2")
    th.push_model("m2")
    out = th.as_text()
    # Find positions
    p_u1 = out.index("u1")
    p_m1 = out.index("m1")
    p_u2 = out.index("u2")
    p_m2 = out.index("m2")
    assert p_u1 < p_m1 < p_u2 < p_m2


# ---------------------------------------------------------------------------
# Ring overflow
# ---------------------------------------------------------------------------


def test_turn_history_08_overflow_drops_oldest_pair() -> None:
    """At max_pairs=2 capacity, push 3 pairs → oldest pair gone."""
    th = TurnHistory(max_pairs=2)
    for i in range(3):
        th.push_user(f"u{i}")
        th.push_model(f"m{i}")
    out = th.as_text()
    assert "u0" not in out
    assert "m0" not in out
    assert "u1" in out and "m1" in out
    assert "u2" in out and "m2" in out


def test_turn_history_09_overflow_at_default_12() -> None:
    """Push 14 pairs → only the last 12 remain (default cap).

    Use full <user>uN</user> framing for substring checks so 'u1' doesn't
    spuriously match 'u10' / 'u11' / etc.
    """
    th = TurnHistory()
    for i in range(14):
        th.push_user(f"u{i}")
        th.push_model(f"m{i}")
    out = th.as_text()
    # u0, u1 evicted; u2..u13 retained (12 pairs).
    assert "<user>u0</user>" not in out
    assert "<user>u1</user>" not in out
    assert "<user>u2</user>" in out
    assert "<user>u13</user>" in out
    # Sanity: ring contents are exactly 12 pairs (24 entries).
    assert out.count("<user>") == 12
    assert out.count("<model>") == 12


# ---------------------------------------------------------------------------
# Format
# ---------------------------------------------------------------------------


def test_turn_history_10_format_byte_match() -> None:
    """Exact byte format match against the canonical shape."""
    th = TurnHistory()
    th.push_user("hi")
    th.push_model("ok")
    expected = "<recent_turns>\n<user>hi</user>\n<model>ok</model>\n</recent_turns>"
    assert th.as_text() == expected


def test_turn_history_11_clear_resets() -> None:
    """clear() empties the ring; as_text returns empty string after."""
    th = TurnHistory()
    th.push_user("u")
    th.push_model("m")
    assert th.as_text() != ""
    th.clear()
    assert th.as_text() == ""


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_turn_history_12_empty_string_push_skipped_or_kept() -> None:
    """Empty-string push doesn't crash; behavior is well-defined.
    Spec: empty strings are kept as-is (the cascade may emit them via
    streaming chunks; we don't re-decide what's content-worthy here)."""
    th = TurnHistory()
    th.push_user("")
    th.push_model("real")
    # No crash. The 'real' entry is present.
    assert "<model>real</model>" in th.as_text()


@pytest.mark.parametrize("special", ["<weird/>", "&amp;", "<user>nested</user>"])
def test_turn_history_13_no_xml_escaping_done(special: str) -> None:
    """We do NOT XML-escape — the prompt is plain text consumed by an LLM,
    not parsed as strict XML. Format stays simple; LLM tolerates inner tags."""
    th = TurnHistory()
    th.push_user(special)
    out = th.as_text()
    # The special chars appear verbatim (no escape).
    assert special in out
