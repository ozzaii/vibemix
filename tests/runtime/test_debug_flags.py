# SPDX-License-Identifier: Apache-2.0
"""v8.0 LOG-04 — debug-log verbosity switch + --debug-log flag plumbing."""

from __future__ import annotations

import os

import pytest

from vibemix.runtime import debug_flags


@pytest.fixture(autouse=True)
def _reset_flag():
    """Snapshot + restore the process-global flag around each test."""
    before = debug_flags.debug_log_enabled()
    yield
    debug_flags.set_debug_log(before)


def test_set_debug_log_toggles(monkeypatch) -> None:
    monkeypatch.delenv("VIBEMIX_DEBUG_LOG", raising=False)
    debug_flags.set_debug_log(True)
    assert debug_flags.debug_log_enabled() is True
    debug_flags.set_debug_log(False)
    assert debug_flags.debug_log_enabled() is False


def test_env_is_the_floor_flag_cannot_lower_it(monkeypatch) -> None:
    """A truthy VIBEMIX_DEBUG_LOG keeps logging on even on a default launch."""
    monkeypatch.setenv("VIBEMIX_DEBUG_LOG", "1")
    # set_debug_log(False) must NOT override a truthy env (env is the floor).
    debug_flags.set_debug_log(False)
    assert debug_flags.debug_log_enabled() is True


@pytest.mark.parametrize("val,expected", [("1", True), ("true", True), ("on", True), ("0", False), ("", False), ("nope", False)])
def test_env_default_parsing(monkeypatch, val, expected) -> None:
    monkeypatch.setenv("VIBEMIX_DEBUG_LOG", val)
    assert debug_flags._env_default() is expected


def test_debug_log_flag_parses_and_defaults_off() -> None:
    from vibemix.__main__ import _parse_args

    assert _parse_args([]).debug_log is False
    assert _parse_args(["--debug-log"]).debug_log is True
