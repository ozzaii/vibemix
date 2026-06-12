# SPDX-License-Identifier: Apache-2.0
"""Wreck Room round director — the playable loop behind the Learn front door.

The game: both decks groove LOCKED so the ear learns what right sounds like,
then Sven shoves deck B off (tempo at low difficulty, sneakier phase shoves
higher up), a save window counts down, and the learner drags the pitch fader
until the kicks fuse again. A grazed lock lands the save; only a HELD lock
(16 beats, read from the grade stream) escalates difficulty. A missed window
is loud, honest theater: Sven yanks deck B's fader himself and owns it.

Honesty contract (sandbox lane):
  * This director never writes ``MusicState``/``LearnState``, never writes
    evidence atoms, and never credits skills — the wreck lane is feedback
    only (Invariant #2 stays untouched; credit lives in the lesson lane).
  * Every bark is an authored constant below filled with measured numbers;
    there is no generative path (the fixtures-only AST gate stays honest).
  * Difficulty and the clean-save count ride the existing ``save_*`` wire
    fields. They are measured state for Sven's mouth and plain receipt text,
    never number chips (the anti-gamification law).

The director is pure round logic driven by ``tick(grade, t)`` at the existing
0.15s live-grade cadence. The driver is reached through a getter because
``__main__`` rebinds the practice driver when save-mode own-track sources
load.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Protocol

import random

from vibemix.learn.beatmatch_judge import BeatmatchGrade

_DIFFICULTY_MIN = 1
_DIFFICULTY_MAX = 5
# Save-window rubric — mirrors the lesson lane's floor (14s shrinking 2s per
# level to a 6s floor) so the two lanes feel like one judge.
_WINDOW_BASE_S = 14.0
_WINDOW_STEP_S = 2.0
_WINDOW_MIN_S = 6.0
# Groove shrinks as difficulty rises: the break arrives sooner and sneakier.
_GROOVE_BASE_S = 12.0
_GROOVE_STEP_S = 1.5
_GROOVE_MIN_S = 5.0
_GROOVE_JITTER_S = 2.0
_HOLD_BEATS = 16.0
_VERDICT_REST_S = 2.5
_FALLBACK_BEAT_S = 60.0 / 128.0

# ---- authored bark bank (hand-written; measured slots only) ----------------
_BARKS_GROOVE_OPEN = (
    "two decks, locked. enjoy it while it lasts.",
    "this is what right sounds like. keep it in your ear.",
    "locked and rolling. I will not leave it alone for long.",
)
_BARKS_GROOVE_BACK = (
    "back in. listen to the lock.",
    "rolling again. ears up.",
    "we go again. same pocket.",
)
_BARKS_BREAK_TEMPO = (
    "there it goes. B is running hot. reel it in.",
    "I shoved B. find the pocket.",
    "B just slipped fast. bring the kicks back together.",
)
_BARKS_BREAK_PHASE = (
    "same speed, wrong place. nudge B home.",
    "B is off the one. walk it back.",
    "tempo is fine. the kicks are arguing. fix the phase.",
)
_BARKS_LANDED = (
    "that's the pocket. {time_to_lock}.",
    "locked. clean save in {time_to_lock}.",
    "there it is. {time_to_lock}. now hold it.",
)
_BARK_LANDED_COMPARE = "that's the pocket. last save took {last}. this one {now}."
_BARKS_HELD = (
    "held it. I'm pushing harder next time.",
    "sixteen beats steady. the window gets shorter now.",
    "that lock had roots. next break comes sooner.",
)
# At the difficulty cap nothing escalates, so the bark must not promise it.
_BARKS_HELD_CAP = (
    "held it at the top. I have nothing harder to throw.",
    "sixteen beats on the hardest window I run. that one counts.",
    "you held my worst shove. now make it look boring.",
)
_BARKS_SLIPPED = (
    "slipped. the save counts, the push does not.",
    "you found it, then lost it. hold the next one.",
)
_BARKS_MISSED = (
    "I pulled it. that was a trainwreck.",
    "window's gone. I cut B before it got ugly.",
    "too late. we eat that one and go again.",
)
BARK_BOOTH_BUSY = "your set has the decks. the booth waits until you're off the air."
BARK_NO_DECK = "no deck answered. check your output device, then press it again."

_MARKER_PREFIX = "wreck_round"


class WreckDriverLike(Protocol):
    """The slice of the practice driver the round needs."""

    def wreck(self, kind: str, level: int) -> None: ...

    def lock_b(self) -> None: ...

    def yank_b(self) -> None: ...

    def restore_b(self) -> None: ...

    def waveform_payload(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class WreckBark:
    """One authored Sven line, ready for the tutor-speak channel (uncited)."""

    text: str
    marker: str


@dataclass(frozen=True)
class WreckTick:
    """One director step: live_grade save-field overrides + barks to voice."""

    fields: dict[str, Any]
    barks: tuple[WreckBark, ...] = ()


def _rounds_path() -> Path:
    override = os.environ.get("VIBEMIX_LEARN_ROUNDS_PATH")
    if override:
        return Path(override)
    return Path.home() / ".cache" / "vibemix" / "learn-rounds.jsonl"


def _fmt_seconds(value: float) -> str:
    return f"{max(0.0, value):.0f} seconds" if value >= 1.5 else "under two seconds"


class _VariantPicker:
    """Deterministic anti-repeat: never the same variant twice in a row."""

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng
        self._last: dict[str, int] = {}

    def pick(self, slot: str, bank: tuple[str, ...]) -> str:
        if len(bank) == 1:
            return bank[0]
        last = self._last.get(slot)
        choices = [i for i in range(len(bank)) if i != last]
        index = self._rng.choice(choices)
        self._last[slot] = index
        return bank[index]


class WreckRound:
    """Round FSM: idle → groove → hunt → hold → groove … (stop() → idle)."""

    def __init__(
        self,
        driver_getter: Callable[[], WreckDriverLike | None],
        *,
        rng: random.Random | None = None,
        ledger_path: Path | None = None,
    ) -> None:
        self._driver_getter = driver_getter
        self._rng = rng if rng is not None else random.Random()
        self._picker = _VariantPicker(self._rng)
        self._ledger_path = ledger_path
        self._state = "idle"
        self._difficulty = _DIFFICULTY_MIN
        self._clean_saves = 0
        self._bark_seq = 0
        self._beat_s = _FALLBACK_BEAT_S
        # timers (session-relative seconds, stamped from tick's t)
        self._groove_until: float | None = None
        self._window_until: float | None = None
        self._window_total: float | None = None
        self._hold_until: float | None = None
        self._rest_until: float | None = None
        self._hunt_started: float | None = None
        self._wreck_kind = "tempo"
        self._from_verdict: str | None = None
        self._from_phase: float | None = None
        self._time_to_lock: float | None = None
        self._last_landed_s: float | None = None

    # ---- lifecycle ----------------------------------------------------

    @property
    def active(self) -> bool:
        return self._state != "idle"

    def start(self) -> WreckBark | None:
        """Enter the groove. Returns the opening bark, or None if no driver."""

        driver = self._driver_getter()
        if driver is None:
            return None
        try:
            driver.restore_b()
            driver.lock_b()
            beat = float(driver.waveform_payload().get("beat_interval_s", 0.0))
            self._beat_s = beat if beat > 0.0 else _FALLBACK_BEAT_S
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[learn.wreck] round start failed: {exc!r}", file=sys.stderr)
            return None
        self._state = "groove"
        self._groove_until = None  # stamped on the first tick
        self._last_landed_s = self._read_last_landed_seconds()
        return self._bark("groove_open", _BARKS_GROOVE_OPEN)

    def stop(self) -> None:
        self._state = "idle"
        self._groove_until = None
        self._window_until = None
        self._window_total = None
        self._hold_until = None
        self._rest_until = None
        self._hunt_started = None
        self._from_verdict = None
        self._from_phase = None

    # ---- the 0.15s step -------------------------------------------------

    def tick(self, grade: BeatmatchGrade, t: float) -> WreckTick:
        """Advance the round against one measured grade at session time t."""

        if self._state == "idle":
            return WreckTick(fields=self._fields())
        if grade.abstain and self._state in {"hunt", "hold"}:
            # A stopped deck freezes the judged beats; silence is never a miss.
            # Groove and rest are plain timers and keep moving.
            return WreckTick(fields=self._fields())

        if self._state == "groove":
            return self._tick_groove(t)
        if self._state == "hunt":
            return self._tick_hunt(grade, t)
        if self._state == "hold":
            return self._tick_hold(grade, t)
        if self._state == "rest":
            return self._tick_rest(t)
        return WreckTick(fields=self._fields())

    # ---- states ---------------------------------------------------------

    def _tick_groove(self, t: float) -> WreckTick:
        if self._groove_until is None:
            self._groove_until = t + self._groove_seconds()
        if t < self._groove_until:
            return WreckTick(fields=self._fields())
        driver = self._driver_getter()
        if driver is None:
            return WreckTick(fields=self._fields())
        self._wreck_kind = self._pick_wreck_kind()
        try:
            driver.wreck(self._wreck_kind, self._difficulty)
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[learn.wreck] shove failed: {exc!r}", file=sys.stderr)
            self._groove_until = t + self._groove_seconds()
            return WreckTick(fields=self._fields())
        self._state = "hunt"
        self._hunt_started = t
        self._window_total = self._window_seconds()
        self._window_until = t + self._window_total
        self._from_verdict = None
        self._from_phase = None
        bank = _BARKS_BREAK_TEMPO if self._wreck_kind == "tempo" else _BARKS_BREAK_PHASE
        return WreckTick(
            fields=self._fields(active=True, remaining=self._window_total),
            barks=(self._bark("break", bank),),
        )

    def _tick_hunt(self, grade: BeatmatchGrade, t: float) -> WreckTick:
        assert self._window_until is not None and self._hunt_started is not None
        if grade.verdict == "locked":
            self._time_to_lock = t - self._hunt_started
            self._clean_saves += 1
            recovery = None
            if self._from_phase is not None:
                recovery = max(
                    0.0,
                    min(0.5, abs(self._from_phase) - abs(grade.phase_error_beats)),
                )
            bark = self._landed_bark(self._time_to_lock)
            self._state = "hold"
            self._hold_until = t + _HOLD_BEATS * self._beat_s
            return WreckTick(
                fields=self._fields(
                    landed=True,
                    from_verdict=self._from_verdict,
                    from_phase=self._from_phase,
                    recovery=recovery,
                ),
                barks=(bark,),
            )
        if t >= self._window_until:
            driver = self._driver_getter()
            if driver is not None:
                try:
                    driver.yank_b()
                except Exception as exc:  # pragma: no cover - defensive
                    print(f"[learn.wreck] yank failed: {exc!r}", file=sys.stderr)
            self._append_ledger(landed=False, held=False)
            self._clean_saves = 0
            self._state = "rest"
            self._rest_until = t + _VERDICT_REST_S
            self._window_until = None
            self._hunt_started = None
            return WreckTick(
                fields=self._fields(expired=True),
                barks=(self._bark("missed", _BARKS_MISSED),),
            )
        if grade.verdict in {"drifting", "trainwreck", "tempo_off"}:
            self._from_verdict = grade.verdict
            self._from_phase = float(grade.phase_error_beats)
        return WreckTick(
            fields=self._fields(active=True, remaining=self._window_until - t),
        )

    def _tick_hold(self, grade: BeatmatchGrade, t: float) -> WreckTick:
        assert self._hold_until is not None
        if grade.verdict != "locked":
            self._append_ledger(landed=True, held=False)
            self._enter_groove_rest(t)
            return WreckTick(
                fields=self._fields(),
                barks=(self._bark("slipped", _BARKS_SLIPPED),),
            )
        if t < self._hold_until:
            return WreckTick(fields=self._fields())
        self._append_ledger(landed=True, held=True)
        at_cap = self._difficulty >= _DIFFICULTY_MAX
        self._difficulty = min(_DIFFICULTY_MAX, self._difficulty + 1)
        self._enter_groove_rest(t)
        return WreckTick(
            fields=self._fields(),
            barks=(self._bark("held", _BARKS_HELD_CAP if at_cap else _BARKS_HELD),),
        )

    def _tick_rest(self, t: float) -> WreckTick:
        assert self._rest_until is not None
        if t < self._rest_until:
            return WreckTick(fields=self._fields())
        driver = self._driver_getter()
        if driver is not None:
            try:
                driver.restore_b()
                driver.lock_b()
            except Exception as exc:  # pragma: no cover - defensive
                print(f"[learn.wreck] restore failed: {exc!r}", file=sys.stderr)
        self._state = "groove"
        self._groove_until = t + self._groove_seconds()
        self._rest_until = None
        return WreckTick(
            fields=self._fields(),
            barks=(self._bark("groove_back", _BARKS_GROOVE_BACK),),
        )

    def _enter_groove_rest(self, t: float) -> None:
        self._state = "groove"
        self._groove_until = t + self._groove_seconds()
        self._hold_until = None
        self._window_until = None
        self._window_total = None
        self._hunt_started = None
        self._from_verdict = None
        self._from_phase = None

    # ---- rubric ----------------------------------------------------------

    def _window_seconds(self) -> float:
        return max(
            _WINDOW_MIN_S,
            _WINDOW_BASE_S - (self._difficulty - 1) * _WINDOW_STEP_S,
        )

    def _groove_seconds(self) -> float:
        base = max(
            _GROOVE_MIN_S,
            _GROOVE_BASE_S - (self._difficulty - 1) * _GROOVE_STEP_S,
        )
        return base + self._rng.uniform(0.0, _GROOVE_JITTER_S)

    def _pick_wreck_kind(self) -> str:
        if self._difficulty <= 2:
            return "tempo"
        if self._difficulty >= 4:
            return "phase"
        return "tempo" if self._rng.random() < 0.5 else "phase"

    # ---- wire fields ------------------------------------------------------

    def _fields(
        self,
        *,
        active: bool = False,
        remaining: float | None = None,
        landed: bool = False,
        expired: bool = False,
        from_verdict: str | None = None,
        from_phase: float | None = None,
        recovery: float | None = None,
    ) -> dict[str, Any]:
        return {
            "save_landed": landed,
            "save_from_verdict": from_verdict,
            "save_from_phase_error_beats": from_phase,
            "save_recovery_delta_beats": recovery,
            "save_attempt_active": active,
            "save_floor_seconds_total": self._window_total if active else None,
            "save_floor_seconds_remaining": (
                max(0.0, round(remaining, 2)) if remaining is not None else None
            ),
            "save_floor_expired": expired,
            "save_difficulty_level": self._difficulty,
            "save_streak": self._clean_saves,
        }

    # ---- barks -------------------------------------------------------------

    def _bark(self, slot: str, bank: tuple[str, ...]) -> WreckBark:
        self._bark_seq += 1
        return WreckBark(
            text=self._picker.pick(slot, bank),
            marker=f"{_MARKER_PREFIX}.{slot}.{self._bark_seq}",
        )

    def _landed_bark(self, time_to_lock: float) -> WreckBark:
        now_text = _fmt_seconds(time_to_lock)
        if self._last_landed_s is not None:
            self._bark_seq += 1
            text = _BARK_LANDED_COMPARE.format(
                last=_fmt_seconds(self._last_landed_s),
                now=now_text,
            )
            self._last_landed_s = time_to_lock
            return WreckBark(
                text=text,
                marker=f"{_MARKER_PREFIX}.landed.{self._bark_seq}",
            )
        self._last_landed_s = time_to_lock
        self._bark_seq += 1
        text = self._picker.pick("landed", _BARKS_LANDED).format(
            time_to_lock=now_text
        )
        return WreckBark(text=text, marker=f"{_MARKER_PREFIX}.landed.{self._bark_seq}")

    # ---- ledger (measured receipts, local only) -----------------------------

    def _ledger_file(self) -> Path:
        return self._ledger_path if self._ledger_path is not None else _rounds_path()

    def _append_ledger(self, *, landed: bool, held: bool) -> None:
        record = {
            "ts": datetime.now(UTC).isoformat(),
            "difficulty": self._difficulty,
            "kind": self._wreck_kind,
            "landed": landed,
            "held": held,
            "time_to_lock_s": (
                round(self._time_to_lock, 2) if landed and self._time_to_lock else None
            ),
            "window_s": self._window_total,
        }
        try:
            path = self._ledger_file()
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[learn.wreck] ledger write failed: {exc!r}", file=sys.stderr)

    def _read_last_landed_seconds(self) -> float | None:
        try:
            path = self._ledger_file()
            if not path.exists():
                return None
            last: float | None = None
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    value = row.get("time_to_lock_s")
                    if row.get("landed") and isinstance(value, (int, float)):
                        last = float(value)
            return last
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[learn.wreck] ledger read failed: {exc!r}", file=sys.stderr)
            return None


def wreck_bark_texts() -> tuple[str, ...]:
    """The fixed bark bank, warm-priority order (sequential pre-synth).

    Hunt-critical banks lead: the break bark is needed ~8-15s into round one,
    while groove_open already played live as the warm trigger. Landed lines
    are deliberately absent — they carry MEASURED ``{time_to_lock}`` slots and
    pre-baking a number that has not been measured yet fabricates a receipt.
    """

    ordered = (
        *_BARKS_BREAK_TEMPO,
        *_BARKS_BREAK_PHASE,
        *_BARKS_MISSED,
        *_BARKS_SLIPPED,
        *_BARKS_HELD,
        *_BARKS_HELD_CAP,
        *_BARKS_GROOVE_BACK,
        *_BARKS_GROOVE_OPEN,
        BARK_BOOTH_BUSY,
        BARK_NO_DECK,
    )
    return tuple(dict.fromkeys(ordered))


__all__ = [
    "BARK_BOOTH_BUSY",
    "BARK_NO_DECK",
    "WreckBark",
    "WreckDriverLike",
    "WreckRound",
    "WreckTick",
    "wreck_bark_texts",
]
