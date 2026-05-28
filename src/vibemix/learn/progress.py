# SPDX-License-Identifier: Apache-2.0
"""LearnProgress — atomic JSON persistence for lesson completion.

Phase 92 (LESSON-03). Mirrors the ``runtime/config_store.py:266-278``
atomic-write pattern (``tmp.write_text`` → ``os.replace``) so a crash
mid-write doesn't leave a half-truncated ``learn-progress.json``.

On corrupt-read, the file is silently deleted + a fresh empty progress
is returned + a one-line ``progress_state`` toast is queued for next
emit by the caller (the live wire-in in ``__main__.main()``).

Path: ``~/.cache/vibemix/learn-progress.json`` (resolved by
:func:`progress_path` — function, not constant, so tests can monkeypatch).

Schema::

    {
      "schema_version": 1,
      "courses": {
        "course_0": { "completed": false, "completed_at": null },
        ...
      },
      "lessons": {
        "L0.00-press-play": {
          "completed": true,
          "completed_at": "2026-05-28T01:23:45Z",
          "strikes_used": 1
        },
        ...
      }
    }

Threat model bindings:

  * T-92-04-01 (Tampering: half-truncated write) — mitigated by
    ``os.replace(tmp, target)``. POSIX rename is atomic; Windows
    ``ReplaceFileW`` is atomic. A crash between ``tmp.write_text`` and
    ``os.replace`` leaves a stale ``<file>.json.tmp`` but never a
    half-truncated final file.
  * T-92-04-02 (DoS: corrupt file wedges runtime) — mitigated by
    :func:`load_progress` catching ``OSError | json.JSONDecodeError`` →
    silently ``unlink`` + fresh empty + ``was_corrupt=True`` flag for the
    caller to surface a one-line toast.
  * T-92-04-03 (Tampering: schema version drift) — mitigated by
    :meth:`LearnProgress.from_dict` returning fresh ``cls()`` when
    ``schema_version != SCHEMA_VERSION``. Future migrations land in a
    v2-to-v1 explicit upgrader (not in v9.0).

REQ-ID: LESSON-03 (progress persistence + corruption recovery + reset CLI).
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1


def progress_path() -> Path:
    """Location of ``learn-progress.json`` under ``~/.cache/vibemix/``.

    Module-level FUNCTION (not constant) so tests can monkeypatch via
    ``monkeypatch.setattr("vibemix.learn.progress.progress_path", ...)``.
    """
    return Path.home() / ".cache" / "vibemix" / "learn-progress.json"


@dataclass
class LearnProgress:
    """In-memory model of the on-disk progress JSON.

    Mutable (NOT ``frozen=True``) — :meth:`mark_completed` updates the
    ``lessons`` dict in place. The whole object is re-serialised on
    every :func:`save_progress` call.
    """

    schema_version: int = SCHEMA_VERSION
    courses: dict[str, dict[str, Any]] = field(default_factory=dict)
    lessons: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Plan 94-03 (CURR-1.16 binding): RecitalRuntime flips this to True
    # on a 5/5 Course 1 Recital pass; the HUD reads it to unlock the
    # Course 2 lesson selector. Additive default-False extension to
    # schema_version 1 — a legacy JSON file WITHOUT this field loads as
    # False (forward-compat); the migration seam (schema_version != 1)
    # is untouched.
    course_2_unlocked: bool = False

    def mark_completed(
        self,
        course_id: str,
        lesson_id: str,
        strikes_used: int = 0,
    ) -> None:
        """Record a lesson completion.

        Args:
            course_id: The owning course's identifier (currently
                ``"course_0"`` for the hello-world demo; P94+ add
                ``"course_1"`` / ``"course_2"`` / ``"course_3"``).
            lesson_id: The lesson identifier (e.g. ``"L0.00-press-play"``).
            strikes_used: Number of hint strikes the user took to
                complete the lesson (0 = first try, 3 = max hints).
        """
        # ISO-8601 UTC timestamp with seconds precision (``Z`` suffix
        # marker = UTC; matches the timestamp shape elsewhere in the
        # project, e.g. ``recordings/storage.py``).
        iso = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.lessons[lesson_id] = {
            "completed": True,
            "completed_at": iso,
            "strikes_used": int(strikes_used),
        }

    def snapshot(self) -> dict[str, Any]:
        """Alias of :meth:`to_dict` — the name the runtime + envelope
        emitters use when shipping the current state as a
        ``LearnProgressState`` envelope payload."""
        return self.to_dict()

    def dots_for_course(
        self, course_id: str | None
    ) -> tuple[dict[str, str], ...]:
        """Derive the ``LearnLessonLoaded.payload.progress_dots`` array
        from completed-lesson status.

        Returns a tuple of dicts shaped
        ``{"lesson_id": <id>, "status": "pending" | "completed"}``;
        :meth:`vibemix.ui_bus.learn_messages.LearnLessonLoaded.make`
        accepts this raw-dict form and normalises it into
        :class:`LearnProgressDot` tuples.

        Filters by ``course_id`` via the
        :data:`vibemix.learn.curriculum.CURRICULUM` lookup —
        ``CURRICULUM[lesson_id].course_id`` is the authoritative owner of
        each lesson. Lessons not present in CURRICULUM (e.g. stale
        entries from a prior CURRICULUM that have been pruned) are
        silently skipped — they cannot be displayed anyway. ``None``
        course_id returns an empty tuple (no course loaded).

        For v9.0 ("Lesson One") only ``course_0`` ships with the
        hello-world single-lesson curriculum; the filter is a no-op
        because every lesson belongs to ``course_0``. CR-03 (P92 REVIEW)
        regression — when P94 lands Course 1 (16 lessons) the unfiltered
        walk would have returned 30+ dots, busting the HUD.

        Rule 2 (auto-add missing critical functionality): the
        :class:`LessonRuntime`'s ``on_enter_loaded`` callback calls
        ``progress_store.dots_for_course(course_id)`` (runtime.py:346).
        Without this method the call would throw ``AttributeError`` and
        the defensive try/except would spam stderr on every lesson load.
        """
        if course_id is None:
            return ()
        # Local import — CURRICULUM lives in a sibling module; importing
        # at module-load time would create a circular reference (the
        # curriculum module pulls in transcript JSON paths but not this
        # module today; the lazy local import keeps the import graph
        # one-way regardless of future refactors).
        from vibemix.learn.curriculum import CURRICULUM

        dots: list[dict[str, str]] = []
        for lesson_id, entry in self.lessons.items():
            meta = CURRICULUM.get(lesson_id)
            if meta is None:
                # Lesson id is not in the current CURRICULUM; cannot be
                # attributed to a course → silently skip. This preserves
                # forward-compat with progress rows from a prior
                # CURRICULUM (e.g. test/debug rows that drift out of the
                # ship table); the HUD doesn't paint dots for unknown
                # lessons anyway.
                continue
            if meta.course_id != course_id:
                continue
            if entry.get("completed") is True:
                dots.append({"lesson_id": lesson_id, "status": "completed"})
        return tuple(dots)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict — the JSON-file shape."""
        return {
            "schema_version": self.schema_version,
            "courses": self.courses,
            "lessons": self.lessons,
            "course_2_unlocked": self.course_2_unlocked,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> LearnProgress:
        """Build from a raw dict (the JSON-decoded file contents).

        Returns fresh ``cls()`` if ``raw`` isn't a dict OR if
        ``raw["schema_version"] != SCHEMA_VERSION`` — the migration seam.
        Future v2 schemas land an explicit ``_migrate_v2_to_v1`` upgrader
        instead of attempting a garbled merge here.

        Plan 94-03: ``course_2_unlocked`` reads with a safe default
        (False) — legacy schema_version=1 JSON predating the field loads
        without raising. Additive default-False extension.
        """
        if not isinstance(raw, dict):
            return cls()
        if raw.get("schema_version") != SCHEMA_VERSION:
            return cls()
        return cls(
            schema_version=SCHEMA_VERSION,
            courses=raw.get("courses", {}) or {},
            lessons=raw.get("lessons", {}) or {},
            course_2_unlocked=bool(raw.get("course_2_unlocked", False)),
        )


def load_progress() -> tuple[LearnProgress, bool]:
    """Read ``learn-progress.json``.

    Returns ``(progress, was_corrupt)``:

      * ``was_corrupt=False`` on missing file → ``(LearnProgress(), False)``.
      * ``was_corrupt=False`` on schema-version mismatch → fresh empty;
        the migration seam, NOT corruption.
      * ``was_corrupt=True`` ONLY when ``OSError | json.JSONDecodeError``
        fires; the corrupt file is ``unlink``ed silently and a fresh
        empty is returned. The caller emits a one-line
        ``LearnProgressState { was_recovered: True }`` toast.
    """
    p = progress_path()
    if not p.exists():
        return LearnProgress(), False
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # Corrupt — print a bracket-tagged stderr line (the project's
        # logging convention) so the live log captures what happened,
        # then silently nuke + fresh empty + flag the caller.
        print(
            f"[learn.progress] corrupt {p}; resetting to fresh empty",
            file=sys.stderr,
        )
        try:
            p.unlink()
        except OSError:  # pragma: no cover — defensive (rm-permission edge case)
            pass
        return LearnProgress(), True
    return LearnProgress.from_dict(raw), False


def save_progress(progress: LearnProgress) -> Path:
    """Atomic write via tmp + ``os.replace``. Returns the path written.

    Mirrors :meth:`vibemix.runtime.config_store.ConfigStore.save`
    (config_store.py:266-278) verbatim. POSIX rename is atomic; Windows
    ``ReplaceFileW`` is atomic. A crash between the ``tmp.write_text``
    and the ``os.replace`` leaves a stale ``.json.tmp`` file in the
    cache dir — the next ``load_progress`` ignores it because it only
    reads the final path. (A future ``health-check`` sweep could nuke
    stale tmps; not required for v9.0.)
    """
    p = progress_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    # Use ``.with_suffix(".json.tmp")`` to land the tmp NEXT TO the
    # target in the same filesystem — required for ``os.replace`` to be
    # atomic (cross-FS rename falls back to copy+unlink which is NOT
    # atomic on POSIX). Same approach as ConfigStore.save().
    tmp = p.with_suffix(".json.tmp")
    payload = json.dumps(progress.to_dict(), indent=2, sort_keys=True)
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, p)
    return p


def reset_progress() -> None:
    """Wipe ``learn-progress.json``. Idempotent — calling on an absent
    file is a no-op.

    Used by:
      * The CLI ``vibemix learn reset`` subcommand (P92-04 Task 2).
      * The "Reset Learn Progress" settings drawer button (P92-06).
      * The corruption-recovery path in :func:`load_progress` (above).
    """
    p = progress_path()
    if p.exists():
        try:
            p.unlink()
        except OSError:  # pragma: no cover — defensive (rm-permission edge case)
            pass
