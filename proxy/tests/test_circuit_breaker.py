# SPDX-License-Identifier: Apache-2.0
"""CB-01..05 — CircuitBreaker lifecycle."""

from __future__ import annotations

import app.upstream as up_mod
from app.upstream import CircuitBreaker


def test_cb_01_initial_allow_true():
    cb = CircuitBreaker(threshold=3, cooldown_sec=1)
    assert cb.allow() is True
    assert cb.retry_after() == 0


def test_cb_02_opens_after_threshold():
    cb = CircuitBreaker(threshold=3, cooldown_sec=60)
    cb.record_failure()
    cb.record_failure()
    assert cb.allow() is True
    cb.record_failure()
    assert cb.allow() is False
    assert 1 <= cb.retry_after() <= 60


def test_cb_03_closes_after_cooldown(monkeypatch):
    cb = CircuitBreaker(threshold=2, cooldown_sec=10)
    cb.record_failure()
    cb.record_failure()
    assert cb.allow() is False
    # advance time past cooldown
    real_time = up_mod.time.time()
    monkeypatch.setattr(up_mod.time, "time", lambda: real_time + 11)
    assert cb.allow() is True
    assert cb.retry_after() == 0


def test_cb_04_success_resets_streak():
    cb = CircuitBreaker(threshold=3, cooldown_sec=60)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    cb.record_failure()
    cb.record_failure()
    assert cb.allow() is True  # streak is 2 < threshold


def test_cb_05_failures_after_open_dont_re_extend():
    cb = CircuitBreaker(threshold=2, cooldown_sec=30)
    cb.record_failure()
    cb.record_failure()
    assert cb.allow() is False
    open_until_1 = cb._open_until
    cb.record_failure()
    cb.record_failure()
    # _open_until is unchanged because the breaker was already open
    assert cb._open_until == open_until_1
