# SPDX-License-Identifier: Apache-2.0
"""Wreck bark PCM cache: the <500ms-bark ship gate.

The fixed bark bank pre-synthesizes once per session so verdict-window barks
play from cache instead of waiting on a fresh MLX synth. Landed barks carry
MEASURED time slots and are deliberately absent — pre-baking a number that
has not been measured yet would fabricate a receipt.
"""
from __future__ import annotations

from vibemix.learn import wreck_round as wreck_round_module
from vibemix.learn.bark_cache import BarkPcmCache
from vibemix.learn.wreck_round import wreck_bark_texts


def test_wreck_bark_texts_cover_every_fixed_bank_line() -> None:
    texts = wreck_bark_texts()
    fixed_banks = (
        wreck_round_module._BARKS_GROOVE_OPEN,
        wreck_round_module._BARKS_GROOVE_BACK,
        wreck_round_module._BARKS_BREAK_TEMPO,
        wreck_round_module._BARKS_BREAK_PHASE,
        wreck_round_module._BARKS_HELD,
        wreck_round_module._BARKS_HELD_CAP,
        wreck_round_module._BARKS_SLIPPED,
        wreck_round_module._BARKS_MISSED,
    )
    for bank in fixed_banks:
        for line in bank:
            assert line in texts, f"fixed bark missing from warm list: {line!r}"
    assert wreck_round_module.BARK_BOOTH_BUSY in texts
    assert wreck_round_module.BARK_NO_DECK in texts
    assert len(texts) == len(set(texts))


def test_wreck_bark_texts_exclude_measured_slot_lines() -> None:
    """Landed lines hold {time_to_lock}; a warm synth would bake a fake number."""

    texts = wreck_bark_texts()
    for line in wreck_round_module._BARKS_LANDED:
        assert line not in texts
    assert wreck_round_module._BARK_LANDED_COMPARE not in texts
    for line in texts:
        assert "{" not in line, f"format slot leaked into the warm list: {line!r}"


def test_wreck_bark_texts_put_hunt_critical_banks_first() -> None:
    """Warm is sequential; the break bark is needed ~8-15s into round one."""

    texts = wreck_bark_texts()
    first_break = texts.index(wreck_round_module._BARKS_BREAK_TEMPO[0])
    first_groove_open = texts.index(wreck_round_module._BARKS_GROOVE_OPEN[0])
    assert first_break < first_groove_open


def test_cache_round_trips_with_whitespace_normalized_keys() -> None:
    cache = BarkPcmCache()
    cache.put("I shoved B.  find the pocket.", b"\x01\x02")
    assert cache.get("I shoved B. find the pocket.") == b"\x01\x02"
    assert cache.get("never spoken") is None


def test_cache_ignores_empty_text_and_empty_pcm() -> None:
    cache = BarkPcmCache()
    cache.put("", b"\x01")
    cache.put("   ", b"\x01")
    cache.put("a real line", b"")
    assert cache.get("") is None
    assert cache.get("a real line") is None


def test_cache_evicts_oldest_unpinned_beyond_byte_cap() -> None:
    cache = BarkPcmCache(max_unpinned_bytes=8)
    cache.put("first", b"\x00" * 4)
    cache.put("second", b"\x00" * 4)
    cache.put("third", b"\x00" * 4)  # cap blown -> "first" goes
    assert cache.get("first") is None
    assert cache.get("second") is not None
    assert cache.get("third") is not None


def test_cache_never_evicts_pinned_warm_entries() -> None:
    cache = BarkPcmCache(max_unpinned_bytes=4)
    cache.put("warm bark", b"\x00" * 64, pinned=True)
    cache.put("live one", b"\x00" * 4)
    cache.put("live two", b"\x00" * 4)  # evicts "live one", never the pin
    assert cache.get("warm bark") == b"\x00" * 64
    assert cache.get("live one") is None
    assert cache.get("live two") is not None


def test_cache_get_refreshes_unpinned_lru_order() -> None:
    cache = BarkPcmCache(max_unpinned_bytes=8)
    cache.put("first", b"\x00" * 4)
    cache.put("second", b"\x00" * 4)
    assert cache.get("first") is not None  # touch -> "second" is now oldest
    cache.put("third", b"\x00" * 4)
    assert cache.get("first") is not None
    assert cache.get("second") is None
