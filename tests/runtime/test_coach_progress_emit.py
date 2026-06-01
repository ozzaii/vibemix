# SPDX-License-Identifier: Apache-2.0
"""Earned-Wall live-refresh emit (§EARNED-LIVE fix).

After ``_credit_live_skill_demo`` advances the wall on a live cited demo,
``coach_loop`` must push an ``ipc.learn.progress_state`` so the shell SkillWall
repaints WITHOUT a reload (the periodic session snapshot does not carry learn
progress). These guard ``_emit_earned_wall_refresh``.

Kept in its own file — NOT ``test_coach_skill_credit.py`` — to avoid colliding
with concurrent work on that suite.
"""

from __future__ import annotations

import asyncio

from vibemix.runtime import coach


class _FakeBus:
    def __init__(self) -> None:
        self.emitted: list[dict] = []

    async def emit(self, payload: dict) -> None:
        self.emitted.append(payload)


class _FakeProgress:
    def __init__(self, snap: dict | None = None, *, raises: bool = False) -> None:
        self._snap = snap if snap is not None else {"skills": {}, "lessons": {}}
        self._raises = raises

    def snapshot(self) -> dict:
        if self._raises:
            raise RuntimeError("boom")
        return self._snap


class _FakeEnvelope:
    def __init__(self, **kw: object) -> None:
        self._kw = kw

    def to_dict(self) -> dict:
        return {"type": "ipc.learn.progress_state", **self._kw}


def _patch_lps(monkeypatch) -> list[dict]:
    """Stub LearnProgressState so the test is independent of its envelope
    schema — we only assert the helper's wiring (make args + emit)."""
    calls: list[dict] = []

    class _LPS:
        @staticmethod
        def make(**kw: object):
            calls.append(dict(kw))
            return _FakeEnvelope(**kw)

    monkeypatch.setattr("vibemix.ui_bus.learn_messages.LearnProgressState", _LPS)
    return calls


def test_emits_progress_state_on_credit(monkeypatch):
    calls = _patch_lps(monkeypatch)
    bus = _FakeBus()
    snap = {"skills": {"beatmatch": {"mastered": True}}}
    asyncio.run(coach._emit_earned_wall_refresh(["beatmatch"], _FakeProgress(snap), bus))
    assert len(bus.emitted) == 1
    assert bus.emitted[0]["type"] == "ipc.learn.progress_state"
    assert calls and calls[0]["action"] == "snapshot"
    assert calls[0]["progress"] == snap


def test_no_emit_when_nothing_credited(monkeypatch):
    _patch_lps(monkeypatch)
    bus = _FakeBus()
    asyncio.run(coach._emit_earned_wall_refresh([], _FakeProgress(), bus))
    assert bus.emitted == []


def test_no_emit_and_no_crash_without_bus(monkeypatch):
    _patch_lps(monkeypatch)
    # ipc_bus None → silently returns, no exception.
    asyncio.run(coach._emit_earned_wall_refresh(["x"], _FakeProgress(), None))


def test_fail_soft_on_snapshot_error(monkeypatch):
    _patch_lps(monkeypatch)
    bus = _FakeBus()
    # A snapshot failure must NEVER raise — refresh failure != credit failure.
    asyncio.run(coach._emit_earned_wall_refresh(["x"], _FakeProgress(raises=True), bus))
    assert bus.emitted == []
