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
    :meth:`LearnProgress.from_dict`. As of Phase 102 (v11.0) a
    ``schema_version == 1`` file is routed through the explicit
    :func:`_migrate_v1_to_v2` upgrader (seeds the live-portion ``skills``
    block, preserves all lesson history). Any OTHER version
    (``schema_version`` > 2 / garbage / absent) still hits the
    fresh-empty wipe seam. The migration is idempotent — keyed strictly
    on ``schema_version == 1`` — so a v2 file already holding Phase-103
    live data loads untouched (no clobber of ``live_proof_count``).

Phase 102 (v11.0 "Earned"): ``SCHEMA_VERSION`` bumps 1→2. A new
``skills`` live-portion block carries, per skill, the count of grounded
live demos, a mastered flag, and the first-mastered timestamp. ONLY the
live-portion is stored here — the learn-portion (lesson fill + competent
bool) is DERIVED by ``skill_tree.SkillTree.compute`` on every load, so
there is zero dual-write drift. Phase 103 writes the live-portion; Phase
102 seeds it with safe defaults (count 0, mastered False, ts None).

REQ-ID: LESSON-03 (progress persistence + corruption recovery + reset CLI);
DATA-01/02/03 (Phase 102 skills block + v1→v2 migration + reset).
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2

# The 6 REQ-locked DJ skills, in CONTEXT GA1 order. The live-portion
# ``skills`` block on ``learn-progress.json`` is keyed by these ids; the
# learn-portion (lesson fill + competent bool) is NEVER stored here — it is
# DERIVED by ``skill_tree.SkillTree.compute`` from the lesson/recital history.
_SKILL_IDS: tuple[str, ...] = (
    "deck_control",
    "beatmatching",
    "eq_mixing",
    "harmonic_mixing",
    "transitions",
    "phrasing_performance",
)
_PRACTICE_SOURCE_KEYS: tuple[str, ...] = ("hardware", "screen")


def _practice_source_key(source: str | None) -> str | None:
    """Normalize wire action sources into learner-facing practice surfaces."""
    raw = str(source or "midi").strip().lower()
    if raw in {"midi", "hardware", "controller"}:
        return "hardware"
    if raw in {"click", "screen", "onscreen", "on_screen"}:
        return "screen"
    return None


def _practice_source_counts(raw: Any) -> dict[str, int]:
    """Return a bounded hardware/screen count map from an arbitrary row value."""
    counts = {key: 0 for key in _PRACTICE_SOURCE_KEYS}
    if not isinstance(raw, dict):
        return counts
    for key in _PRACTICE_SOURCE_KEYS:
        try:
            counts[key] = max(0, int(raw.get(key, 0)))
        except (TypeError, ValueError):
            counts[key] = 0
    return counts


def _carry_practice_source_fields(
    target: dict[str, Any],
    existing: dict[str, Any] | None,
) -> None:
    """Preserve optional per-lesson practice-source memory across row rewrites."""
    if not isinstance(existing, dict):
        return
    counts = _practice_source_counts(existing.get("practice_sources"))
    if any(counts.values()):
        target["practice_sources"] = counts
    last_source = _practice_source_key(existing.get("last_practice_source"))
    if last_source is not None:
        target["last_practice_source"] = last_source


def _fresh_skills_block() -> dict[str, dict[str, Any]]:
    """Live-portion defaults for all 6 skills (Phase 103 fills these).

    Returns a fresh nested dict on every call (used as the dataclass
    ``default_factory`` for :attr:`LearnProgress.skills` and the seed for
    both the v1→v2 migration and corrupt-recovery). A shared mutable default
    would leak Phase-103 ``live_proof_count`` writes across instances — hence
    a factory, not a module constant.

    Stores ONLY the live-portion (count / mastered / first_mastered_at). It
    deliberately carries NO ``learn_fill`` / ``competent`` keys — those are
    DERIVED by the engine on every load (storing them would re-introduce the
    dual-write drift this split exists to avoid).
    """
    return {
        sid: {
            "live_proof_count": 0,
            "mastered": False,
            "first_mastered_at": None,
        }
        for sid in _SKILL_IDS
    }


def _migrate_v1_to_v2(raw: dict[str, Any]) -> dict[str, Any]:
    """Upgrade a ``schema_version == 1`` dict to v2 (DATA-02).

    Seeds the live-portion ``skills`` block with safe defaults for all 6
    skills and bumps ``schema_version`` to 2, while preserving the v1
    lesson/course history verbatim (the deterministic learn-history
    back-fill — the learn-portion is recomputed by the engine, never
    stored). Returns a COPY; the caller's ``raw`` is left untouched.

    NOT a wipe: a v1 file with real lesson rows migrates in place rather
    than nuking the user's progress (RESEARCH finding #1). Routed ONLY on
    ``schema_version == 1`` so it can never re-run on a v2 file and clobber
    Phase-103 live data (idempotency — Pitfall 5).
    """
    upgraded = dict(raw)
    upgraded["schema_version"] = 2
    upgraded["skills"] = _fresh_skills_block()
    return upgraded


def progress_path() -> Path:
    """Location of ``learn-progress.json`` under ``~/.cache/vibemix/``.

    Module-level FUNCTION (not constant) so tests can monkeypatch via
    ``monkeypatch.setattr("vibemix.learn.progress.progress_path", ...)``.
    """
    override = os.environ.get("VIBEMIX_LEARN_PROGRESS_PATH")
    if override:
        return Path(override).expanduser()
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
    # Plan 95 (CURR-2.14 binding): RecitalRuntime flips this to True on
    # a 5/5 Course 2 Recital pass with >= 3 distinct transition types.
    # Same additive-default-False extension pattern as course_2_unlocked
    # — legacy schema_version=1 JSON predating the field loads as False
    # (forward-compat). When Course 3 lands in P96, this is the gate the
    # HUD reads to unlock the play-mode lesson selector.
    course_3_unlocked: bool = False
    # Phase 102 (DATA-01): the live-portion skill ledger. Per skill id
    # ``{"live_proof_count": int, "mastered": bool, "first_mastered_at":
    # str | None}``. STORED here (it cannot be recomputed — Phase 103
    # writes it from grounded live demos); the learn-portion (fill +
    # competent bool) is DERIVED by ``skill_tree.SkillTree.compute`` and is
    # never persisted. ``default_factory=_fresh_skills_block`` seeds the
    # 6-skill defaults on a fresh object — which is also the corrupt-recovery
    # seed (``load_progress`` returns ``LearnProgress()`` on garbage bytes).
    skills: dict[str, dict[str, Any]] = field(
        default_factory=_fresh_skills_block
    )

    def mark_completed(
        self,
        course_id: str,
        lesson_id: str,
        strikes_used: int = 0,
        demonstrated: bool = True,
    ) -> None:
        """Record a lesson completion.

        Args:
            course_id: The owning course's identifier (currently
                ``"course_0"`` for the hello-world demo; P94+ add
                ``"course_1"`` / ``"course_2"`` / ``"course_3"``).
            lesson_id: The lesson identifier (e.g. ``"L0.00-press-play"``).
            strikes_used: Number of hint strikes the user took to
                complete the lesson (0 = first try, 3 = max hints).
            demonstrated: True only when the learner completed the lesson by
                performing the expected action, not by timing out and skipping.
        """
        # ISO-8601 UTC timestamp with seconds precision (``Z`` suffix
        # marker = UTC; matches the timestamp shape elsewhere in the
        # project, e.g. ``recordings/storage.py``).
        iso = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        existing = self.lessons.get(lesson_id)
        row = {
            "completed": True,
            "completed_at": iso,
            "strikes_used": int(strikes_used),
            "demonstrated": bool(demonstrated),
        }
        _carry_practice_source_fields(
            row,
            existing if isinstance(existing, dict) else None,
        )
        self.lessons[lesson_id] = row

    def mark_started(self, course_id: str, lesson_id: str) -> None:
        """Record that a lesson attempt has begun.

        This intentionally uses only the existing schema-v1 row fields so
        progress snapshots stay wire-compatible with older Learn windows:
        an incomplete row is ``completed=False`` + ``completed_at=None``.
        Completed rows are left completed so replaying a lesson never erases
        prior progress.
        """
        self.courses.setdefault(course_id, {})
        existing = self.lessons.get(lesson_id)
        if isinstance(existing, dict) and existing.get("completed") is True:
            return
        strikes = 0
        if isinstance(existing, dict):
            try:
                strikes = max(0, min(3, int(existing.get("strikes_used", 0))))
            except (TypeError, ValueError):
                strikes = 0
        row = {
            "completed": False,
            "completed_at": None,
            "strikes_used": strikes,
        }
        _carry_practice_source_fields(
            row,
            existing if isinstance(existing, dict) else None,
        )
        self.lessons[lesson_id] = row

    def mark_practice_source(
        self,
        course_id: str,
        lesson_id: str,
        source: str | None,
    ) -> None:
        """Remember whether the learner practiced on hardware or screen.

        The Learn frontstage stays one prompt / one action. This data is
        backstage: future debrief/profile/course logic can tell whether the
        user is learning on a physical controller or using the on-screen deck,
        without adding a new dashboard to the booth.
        """
        source_key = _practice_source_key(source)
        if source_key is None:
            return
        self.mark_started(course_id, lesson_id)
        row = self.lessons.get(lesson_id)
        if not isinstance(row, dict):
            return
        counts = _practice_source_counts(row.get("practice_sources"))
        counts[source_key] += 1
        row["practice_sources"] = counts
        row["last_practice_source"] = source_key

    def mark_hint_strike(
        self,
        course_id: str,
        lesson_id: str,
        strikes_used: int,
    ) -> None:
        """Persist the latest hint strike for an unfinished attempt."""
        self.mark_started(course_id, lesson_id)
        row = self.lessons.get(lesson_id)
        if not isinstance(row, dict) or row.get("completed") is True:
            return
        row["strikes_used"] = max(0, min(3, int(strikes_used)))

    def snapshot(self) -> dict[str, Any]:
        """The ``LearnProgressState`` envelope payload — the file shape PLUS the
        derived Earned-Wall block.

        The runtime + envelope emitters ship this (not :meth:`to_dict`) over
        ``ipc.learn.progress_state``. It is :meth:`to_dict` (the persisted
        fields) with one ADDITIVE IPC-only key, ``skill_wall``: the per-skill
        Competent/Mastered stage derived by ``SkillTree.compute`` so the webview
        paints the wall without re-deriving the stage rule. ``skill_wall`` is
        NEVER persisted — :meth:`to_dict` (the file + ``from_dict`` round-trip)
        stays the pure stored shape. The import is local to keep the module
        import graph one-way (``skill_tree`` reads ``progress`` structurally).
        """
        from vibemix.learn.skill_tree import skill_wall_payload

        return {**self.to_dict(), "skill_wall": skill_wall_payload(self)}

    def dots_for_course(
        self,
        course_id: str | None,
        *,
        current_lesson_id: str | None = None,
    ) -> tuple[dict[str, str], ...]:
        """Derive the ``LearnLessonLoaded.payload.progress_dots`` array
        from curriculum order + completed/current lesson status.

        Returns a tuple of dicts shaped
        ``{"lesson_id": <id>, "status": "pending" | "current" | "completed"}``;
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

        Course 1-3 now ship as a real 36-lesson curriculum, so this
        must render every lesson in the active course, not only completed
        rows from the persisted progress dict. Otherwise a fresh lesson
        opens with ``OF 0`` in the HUD and no visible current/pending
        progression.

        Rule 2 (auto-add missing critical functionality): the
        :class:`LessonRuntime`'s ``on_enter_loaded`` callback calls
        ``progress_store.dots_for_course(course_id, current_lesson_id=...)``
        (runtime.py). Without this method the call would throw
        ``AttributeError`` and the defensive try/except would spam
        stderr on every lesson load.
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
        for lesson_id, meta in CURRICULUM.items():
            if meta.course_id != course_id:
                continue
            completed = self.lessons.get(lesson_id, {}).get("completed") is True
            if lesson_id == current_lesson_id:
                status = "current"
            elif completed:
                status = "completed"
            else:
                status = "pending"
            dots.append({"lesson_id": lesson_id, "status": status})
        return tuple(dots)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict — the JSON-file shape."""
        return {
            "schema_version": self.schema_version,
            "courses": self.courses,
            "lessons": self.lessons,
            "course_2_unlocked": self.course_2_unlocked,
            "course_3_unlocked": self.course_3_unlocked,
            "skills": self.skills,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> LearnProgress:
        """Build from a raw dict (the JSON-decoded file contents).

        Migration routing (DATA-02):

          * ``raw`` not a dict → fresh ``cls()``.
          * ``schema_version == 1`` → routed through
            :func:`_migrate_v1_to_v2` (seed the live-portion ``skills``
            block, preserve lesson history) then loaded as v2 — NOT the
            wipe seam.
          * ``schema_version`` is any OTHER value (> 2 / garbage / absent)
            → fresh ``cls()`` (the wipe seam preserved for forward-incompat
            files).
          * ``schema_version == 2`` → loaded as-is. The ``skills`` block is
            read with an ``isinstance`` guard; a missing or non-dict block
            falls back to the seeded defaults. Because migration is keyed
            strictly on ``schema_version == 1``, a v2 file already carrying
            Phase-103 live data loads UNTOUCHED (idempotency — Pitfall 5).

        Plan 94-03: ``course_2_unlocked`` reads with a safe default
        (False) — legacy schema_version=1 JSON predating the field loads
        without raising. Additive default-False extension.

        Plan 95: ``course_3_unlocked`` follows the same additive default-
        False pattern (legacy JSON loads as locked, freshly persisted
        course_3_unlocked round-trips through to_dict).
        """
        if not isinstance(raw, dict):
            return cls()
        version = raw.get("schema_version")
        if version == 1:
            raw = _migrate_v1_to_v2(raw)  # migrate v1 in place, don't wipe
        elif version != SCHEMA_VERSION:
            return cls()  # v3+/garbage/absent → fresh empty (wipe seam)
        skills = raw.get("skills")
        if not isinstance(skills, dict):
            # Missing or corrupt block → seed defaults. Idempotent on v2.
            skills = _fresh_skills_block()
        return cls(
            schema_version=SCHEMA_VERSION,
            courses=raw.get("courses", {}) or {},
            lessons=raw.get("lessons", {}) or {},
            course_2_unlocked=bool(raw.get("course_2_unlocked", False)),
            course_3_unlocked=bool(raw.get("course_3_unlocked", False)),
            skills=skills,
        )


def load_progress() -> tuple[LearnProgress, bool]:
    """Read ``learn-progress.json``.

    Returns ``(progress, was_corrupt)``:

      * ``was_corrupt=False`` on missing file → ``(LearnProgress(), False)``.
      * ``was_corrupt=False`` on a ``schema_version == 1`` file → migrated
        in place to v2 (lesson history preserved, ``skills`` block seeded);
        NOT corruption.
      * ``was_corrupt=False`` on a forward-incompatible version
        (``schema_version`` > 2 / garbage) → fresh empty; the wipe seam,
        NOT corruption. The fresh ``LearnProgress()`` carries a seeded
        empty v2 ``skills`` block (via ``default_factory``).
      * ``was_corrupt=True`` ONLY when ``OSError | json.JSONDecodeError``
        fires; the corrupt file is ``unlink``ed silently and a fresh
        empty (with a seeded v2 skills block) is returned. The caller emits
        a one-line ``LearnProgressState { was_recovered: True }`` toast.
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
