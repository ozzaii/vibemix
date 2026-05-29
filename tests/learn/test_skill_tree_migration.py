# SPDX-License-Identifier: Apache-2.0
"""DATA-01/02/03 — skill-tree schema v2 migration + persistence tests.

Phase 102 (DATA-01/02/03). Pins the v1→v2 ``learn-progress.json`` migration
that seeds the live-portion ``skills`` block, the corrupt-recovery seeding,
migration idempotency (Phase 103 live data is never clobbered), and the
reset path that clears the live-portion ledger.

The single highest-risk edit in Phase 102 is the ``from_dict`` migration:
a v1 file MUST route through ``_migrate_v1_to_v2`` (preserving lesson
history), NOT through the fresh-empty wipe seam. The wipe seam stays alive
for v3+/garbage (RESEARCH finding #1, Pitfall 1 / Pitfall 5).

All tests monkeypatch ``progress_path()`` to a tmp file — MANDATORY, never
touch the real ``~/.cache/vibemix/learn-progress.json``.

REQ-ID: DATA-01 (skills block persists + round-trips),
DATA-02 (v1→v2 back-fill + corrupt recovery + idempotency),
DATA-03 (reset clears the live-portion ledger).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    from vibemix.learn.progress import (
        _SKILL_IDS,
        SCHEMA_VERSION,
        LearnProgress,
        _fresh_skills_block,
        load_progress,
        reset_progress,
        save_progress,
    )
except ImportError:
    pytest.skip(
        "Learn progress persistence is unavailable in this partial Learn build.",
        allow_module_level=True,
    )


@pytest.fixture
def progress_path_in_tmp(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Path:
    """Redirect ``progress_path()`` to a tmp dir so each test starts with a
    clean canvas. Mirrors the fixture in ``test_progress_persistence.py`` —
    MANDATORY so a test never overwrites the real learn-progress.json."""
    target = tmp_path / "learn-progress.json"
    monkeypatch.setattr(
        "vibemix.learn.progress.progress_path",
        lambda: target,
    )
    return target


_DEFAULT_SKILL = {"live_proof_count": 0, "mastered": False, "first_mastered_at": None}


def test_schema_version_is_two() -> None:
    """The schema bumped 1→2 to carry the live-portion ``skills`` block."""
    assert SCHEMA_VERSION == 2, (
        f"SCHEMA_VERSION must be 2 in v11.0; got {SCHEMA_VERSION!r}"
    )


def test_fresh_progress_has_seeded_skills_block() -> None:
    """A fresh ``LearnProgress()`` carries all 6 skills with live-portion
    defaults (count 0 / mastered False / first_mastered_at None)."""
    progress = LearnProgress()
    assert set(progress.skills.keys()) == set(_SKILL_IDS), (
        f"fresh skills block must hold exactly the 6 skill ids; "
        f"got {sorted(progress.skills.keys())!r}"
    )
    for skill_id in _SKILL_IDS:
        assert progress.skills[skill_id] == _DEFAULT_SKILL, (
            f"skill {skill_id!r} must default to {_DEFAULT_SKILL!r}; "
            f"got {progress.skills[skill_id]!r}"
        )


def test_skill_ids_are_the_six_locked_ids_in_order() -> None:
    """The 6 skill ids are REQ-locked, in the CONTEXT GA1 order."""
    assert _SKILL_IDS == (
        "deck_control",
        "beatmatching",
        "eq_mixing",
        "harmonic_mixing",
        "transitions",
        "phrasing_performance",
    )


def test_migrate_v1_to_v2_seeds_skills(progress_path_in_tmp: Path) -> None:
    """A v1 file with real lesson history migrates to v2: schema bumped,
    lessons + unlock flags preserved, a 6-skill live-portion block seeded
    (DATA-02 deterministic back-fill)."""
    progress_path_in_tmp.parent.mkdir(parents=True, exist_ok=True)
    progress_path_in_tmp.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "courses": {},
                "lessons": {
                    "L1.01": {
                        "completed": True,
                        "completed_at": "2026-05-27T00:00:00Z",
                        "strikes_used": 0,
                    },
                    "L1.03": {
                        "completed": True,
                        "completed_at": "2026-05-27T01:00:00Z",
                        "strikes_used": 2,
                    },
                },
                "course_2_unlocked": True,
            }
        ),
        encoding="utf-8",
    )

    progress, was_corrupt = load_progress()

    assert was_corrupt is False, "a v1 migration is NOT a corruption event"
    assert progress.schema_version == 2, (
        f"migrated object must report schema_version 2; "
        f"got {progress.schema_version!r}"
    )
    # Lesson history preserved verbatim (deterministic back-fill).
    assert progress.lessons["L1.01"]["completed"] is True
    assert progress.lessons["L1.03"]["strikes_used"] == 2
    assert progress.course_2_unlocked is True, (
        "the migration must preserve the C1-recital unlock flag"
    )
    # Live-portion seeded with safe defaults for all 6 skills.
    assert set(progress.skills.keys()) == set(_SKILL_IDS)
    for skill_id in _SKILL_IDS:
        assert progress.skills[skill_id] == _DEFAULT_SKILL


def test_v1_dict_routes_through_upgrader_not_wipe_seam() -> None:
    """``from_dict`` on a v1 dict keeps lessons — it must NOT hit the
    fresh-empty wipe seam (RESEARCH finding #1 / Pitfall 5)."""
    legacy_raw = {
        "schema_version": 1,
        "courses": {},
        "lessons": {
            "L0.00-press-play": {
                "completed": True,
                "completed_at": "2026-05-27T00:00:00Z",
                "strikes_used": 0,
            },
        },
        "course_3_unlocked": True,
    }
    progress = LearnProgress.from_dict(legacy_raw)
    assert progress.schema_version == 2
    assert "L0.00-press-play" in progress.lessons, (
        "v1 dict must migrate (preserve lessons), not wipe to fresh-empty"
    )
    assert progress.course_3_unlocked is True
    assert set(progress.skills.keys()) == set(_SKILL_IDS)


def test_future_schema_version_returns_fresh_empty(
    progress_path_in_tmp: Path,
) -> None:
    """A schema_version=3 (future/garbage) file still hits the wipe seam:
    fresh-empty v2 with a seeded skills block, lessons cleared."""
    progress_path_in_tmp.parent.mkdir(parents=True, exist_ok=True)
    progress_path_in_tmp.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "courses": {},
                "lessons": {"L1.01": {"completed": True}},
            }
        ),
        encoding="utf-8",
    )
    progress, _was_corrupt = load_progress()
    assert progress.lessons == {} and progress.courses == {}, (
        "a v3+ schema must surface as fresh empty (the wipe seam preserved)"
    )
    # Even the wiped fresh-empty carries a seeded skills block.
    assert set(progress.skills.keys()) == set(_SKILL_IDS)


def test_non_dict_returns_fresh_empty() -> None:
    """A non-dict ``raw`` (e.g. a JSON list) returns fresh-empty v2."""
    progress = LearnProgress.from_dict(["not", "a", "dict"])  # type: ignore[arg-type]
    assert progress.lessons == {}
    assert set(progress.skills.keys()) == set(_SKILL_IDS)


def test_v2_with_missing_skills_block_seeds_defaults() -> None:
    """A v2 dict with NO ``skills`` key (or a corrupt non-dict block) loads
    with the seeded defaults — idempotent on v2, never raises."""
    raw_missing = {"schema_version": 2, "courses": {}, "lessons": {}}
    progress = LearnProgress.from_dict(raw_missing)
    assert set(progress.skills.keys()) == set(_SKILL_IDS)

    raw_corrupt_block = {
        "schema_version": 2,
        "courses": {},
        "lessons": {},
        "skills": "not-a-dict",
    }
    progress2 = LearnProgress.from_dict(raw_corrupt_block)
    assert set(progress2.skills.keys()) == set(_SKILL_IDS)


def test_to_dict_includes_skills_and_round_trips() -> None:
    """``to_dict`` serialises a ``skills`` key; ``to_dict → from_dict`` is
    stable (DATA-01 round-trip)."""
    progress = LearnProgress()
    progress.skills["transitions"]["live_proof_count"] = 4
    progress.skills["transitions"]["mastered"] = True
    progress.skills["transitions"]["first_mastered_at"] = "2026-05-29T00:00:00Z"

    raw = progress.to_dict()
    assert "skills" in raw, "to_dict must serialise the skills block"
    assert raw["skills"]["transitions"]["live_proof_count"] == 4

    reloaded = LearnProgress.from_dict(raw)
    assert reloaded.skills["transitions"]["live_proof_count"] == 4
    assert reloaded.skills["transitions"]["mastered"] is True
    assert (
        reloaded.skills["transitions"]["first_mastered_at"]
        == "2026-05-29T00:00:00Z"
    )


def test_migration_idempotent_preserves_live_portion(
    progress_path_in_tmp: Path,
) -> None:
    """Loading a v2 file that already holds Phase-103 live data does NOT
    clobber it back to defaults — the migration is keyed strictly on
    ``schema_version == 1`` (Pitfall 5)."""
    progress = LearnProgress()
    progress.skills["transitions"]["live_proof_count"] = 3
    progress.skills["transitions"]["first_mastered_at"] = "2026-05-29T12:00:00Z"
    save_progress(progress)

    # First reload — must preserve the P103 live-portion verbatim.
    reloaded, was_corrupt = load_progress()
    assert was_corrupt is False
    assert reloaded.schema_version == 2
    assert reloaded.skills["transitions"]["live_proof_count"] == 3, (
        "a v2 reload must NOT reset live_proof_count to 0 (idempotency)"
    )
    assert (
        reloaded.skills["transitions"]["first_mastered_at"]
        == "2026-05-29T12:00:00Z"
    )

    # Second round-trip — the file is byte-stable (no re-seed drift).
    first_bytes = progress_path_in_tmp.read_bytes()
    save_progress(reloaded)
    second_bytes = progress_path_in_tmp.read_bytes()
    assert first_bytes == second_bytes, (
        "a v2 save→load→save round-trip must be byte-identical (no migration "
        "re-run on an already-v2 file)"
    )


def test_corrupt_recovers_with_empty_skills_block(
    progress_path_in_tmp: Path,
) -> None:
    """Garbage bytes → ``was_corrupt=True`` AND a fresh-empty v2 object whose
    ``skills`` block is the seeded 6-skill default (DATA-02 corrupt-recovery)."""
    progress_path_in_tmp.parent.mkdir(parents=True, exist_ok=True)
    progress_path_in_tmp.write_bytes(b"not json{{{")
    progress, was_corrupt = load_progress()
    assert was_corrupt is True, "garbage bytes must set was_corrupt=True"
    assert progress.lessons == {} and progress.courses == {}
    assert set(progress.skills.keys()) == set(_SKILL_IDS), (
        "corrupt recovery must seed an empty v2 skills block"
    )
    for skill_id in _SKILL_IDS:
        assert progress.skills[skill_id] == _DEFAULT_SKILL


def test_reset_clears_live_portion(progress_path_in_tmp: Path) -> None:
    """Reset (file unlink) returns the live-portion to defaults: after a
    reset, the next load re-seeds an empty v2 skills block (DATA-03)."""
    progress = LearnProgress()
    progress.skills["beatmatching"]["live_proof_count"] = 5
    progress.skills["beatmatching"]["mastered"] = True
    progress.skills["beatmatching"]["first_mastered_at"] = "2026-05-29T00:00:00Z"
    save_progress(progress)

    reset_progress()
    assert not progress_path_in_tmp.exists(), "reset must unlink the file"

    reloaded, was_corrupt = load_progress()
    assert was_corrupt is False
    assert reloaded.skills["beatmatching"] == _DEFAULT_SKILL, (
        "after reset, the live-portion ledger must be back to defaults"
    )


def test_fresh_skills_block_returns_independent_dicts() -> None:
    """``_fresh_skills_block`` must return fresh nested dicts each call —
    a shared mutable default would leak P103 writes across instances."""
    a = _fresh_skills_block()
    b = _fresh_skills_block()
    a["deck_control"]["live_proof_count"] = 99
    assert b["deck_control"]["live_proof_count"] == 0, (
        "_fresh_skills_block must not share nested dict references between calls"
    )
