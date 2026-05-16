# SPDX-License-Identifier: Apache-2.0
"""Phase 31 Plan 04 — Emote-tag parser tests."""

from __future__ import annotations

import pytest

from vibemix.agent.emote_parser import (
    REACTION_WHITELIST,
    parse_emote_tags,
    strip_emote_tags,
)


class TestParseEmoteTags:
    def test_empty_text_returns_empty(self) -> None:
        assert parse_emote_tags("") == []

    def test_no_tags_returns_empty(self) -> None:
        assert parse_emote_tags("Just commentary, no markers.") == []

    def test_single_whitelisted_tag(self) -> None:
        assert parse_emote_tags("nice drop [emote:fist_pump]") == ["fist_pump"]

    def test_multiple_tags_in_order(self) -> None:
        text = "[emote:wave] welcome — keep it rolling [emote:nod]"
        assert parse_emote_tags(text) == ["wave", "nod"]

    def test_duplicate_tags_preserved(self) -> None:
        text = "double up [emote:fist_pump] [emote:fist_pump]"
        assert parse_emote_tags(text) == ["fist_pump", "fist_pump"]

    def test_unknown_tag_dropped_silently(self) -> None:
        # `wink` is NOT whitelisted (anti-slop guard).
        assert parse_emote_tags("[emote:wink] hey") == []

    def test_mixed_known_and_unknown(self) -> None:
        text = "[emote:nod] then [emote:wink] then [emote:headbang]"
        assert parse_emote_tags(text) == ["nod", "headbang"]

    def test_malformed_brackets_ignored(self) -> None:
        # Missing closing bracket — regex requires `]` so this is dropped.
        assert parse_emote_tags("[emote:wave whoops") == []

    def test_case_sensitive_rejects_uppercase(self) -> None:
        # `[Emote:Wave]` is intentionally rejected — prompt template
        # pins the exact lowercase form.
        assert parse_emote_tags("[Emote:Wave]") == []

    def test_all_whitelisted_tags_round_trip(self) -> None:
        text = " ".join(f"[emote:{name}]" for name in sorted(REACTION_WHITELIST))
        intents = parse_emote_tags(text)
        assert set(intents) == REACTION_WHITELIST
        assert len(intents) == len(REACTION_WHITELIST)


class TestStripEmoteTags:
    def test_strip_removes_tags_returns_clean_text(self) -> None:
        clean, intents = strip_emote_tags("Hello [emote:wave] world")
        assert clean == "Hello world"
        assert intents == ["wave"]

    def test_strip_collapses_whitespace_around_removed_tag(self) -> None:
        clean, _ = strip_emote_tags("a   [emote:nod]   b")
        assert clean == "a b"

    def test_strip_unknown_tag_removes_from_text_but_not_in_intents(self) -> None:
        clean, intents = strip_emote_tags("hello [emote:wink] there")
        # Unknown tag stripped from output (so TTS doesn't read it)…
        assert "[emote:" not in clean
        # …but absent from intent list.
        assert intents == []

    def test_strip_no_tags_returns_text_unchanged_after_trim(self) -> None:
        clean, intents = strip_emote_tags("  just words  ")
        assert clean == "just words"
        assert intents == []

    def test_strip_only_tags_yields_empty_text(self) -> None:
        clean, intents = strip_emote_tags("[emote:wave] [emote:nod]")
        assert clean == ""
        assert intents == ["wave", "nod"]


class TestWhitelistContract:
    def test_whitelist_has_seven_reactions(self) -> None:
        # Locked size — adding/removing reactions requires a separate
        # phase plan touching frontend types AND prompt template AND
        # this whitelist together.
        assert len(REACTION_WHITELIST) == 7

    @pytest.mark.parametrize(
        "name",
        [
            "wave",
            "point_left",
            "point_right",
            "fist_pump",
            "nod",
            "headbang",
            "surprised",
        ],
    )
    def test_each_reaction_in_whitelist(self, name: str) -> None:
        assert name in REACTION_WHITELIST
