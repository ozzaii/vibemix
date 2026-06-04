# SPDX-License-Identifier: Apache-2.0
"""Curriculum metadata: course frames + lesson dispatch.

Phase 92 (LESSON-05). Ships ONLY Course 0 (the "hello world" 1-step demo)
for the press-play proof-of-life. Courses 1 / 2 / 3 add their entries in
P94 (anatomy) / P95 (transitions) / P96 (play mode) respectively.

Two top-level tables:

* :data:`COURSE_FRAMES`: short course-context paragraphs appended to the
  tutor system instruction so the LLM has the course frame in mind for
  every beat. Keyed by ``course_id`` (e.g. ``"course_0"``).

* :data:`CURRICULUM`: per-lesson :class:`LessonMeta` records. Keyed by
  ``lesson_id`` (e.g. ``"L0.00-press-play"``). Each :class:`LessonMeta`
  carries the lesson title, course pointer, ≤200-char system instruction
  addendum, and a ``transcript_path`` pointing at the hand-authored JSON
  fixture under ``src/vibemix/learn/transcripts/``.

The :class:`LessonMeta.script` ``@property`` lazy-loads the JSON fixture
on demand. Since :class:`LessonMeta` is ``frozen=True``, the property
re-reads from disk each access: fine for P92 (1 read per lesson start);
P94+ can layer ``functools.lru_cache`` on the property if needed.

TONE-02 binding: the lesson script JSON files are the SOLE source of
``tutor_speak[].text`` content; the AST gate
``tests/learn/test_scripts_are_fixtures.py`` rejects any code path that
writes that field from a generative API call.

# P94 adds L1.01..L1.16 (Course 1: Anatomy), P95 adds L2.01..L2.14
# (Course 2: Transitions), P96 adds L3.01..L3.07 (Course 3: Play Mode).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, get_args

CourseFrontstageMode = Literal[
    "legacy_demo",
    "practice_booth",
    "live_play_mode",
]

CourseCapability = Literal[
    "controller_state",
    "cue_section_lookahead",
    "debrief",
    "dj_profile",
    "evidence_registry",
    "library_exemplars",
    "library_suggestions",
    "live_audio",
    "on_screen_deck",
    "prepared_pool",
    "recital_observer",
    "recovery_drill",
    "session_recording",
    "session_state",
]

COURSE_FRONTSTAGE_MODES: frozenset[CourseFrontstageMode] = frozenset(
    get_args(CourseFrontstageMode)
)
COURSE_CAPABILITIES: frozenset[CourseCapability] = frozenset(
    get_args(CourseCapability)
)


@dataclass(frozen=True)
class CourseMeta:
    """Per-course navigation and unlock metadata.

    ``CURRICULUM`` remains the source of lesson rows. This registry is the
    source for chooser labels and course gates so adding a course is not a
    Python+TypeScript scavenger hunt. ``capabilities`` is the backstage
    integration contract: the coded systems the course is allowed to depend
    on while the frontstage still shows one calm prompt and one action.
    """

    label: str
    hud_label: str
    unlock_gate: str | None = None
    lock_reason: str | None = None
    beginner: bool = True
    frontstage_mode: CourseFrontstageMode = "practice_booth"
    capabilities: tuple[CourseCapability, ...] = (
        "evidence_registry",
        "controller_state",
        "on_screen_deck",
    )


COURSE_REGISTRY: dict[str, CourseMeta] = {
    "course_0": CourseMeta(
        label="Course 0 · Press Play",
        hud_label="COURSE 0 · PRESS PLAY",
        beginner=False,
        frontstage_mode="legacy_demo",
    ),
    "course_1_anatomy": CourseMeta(
        label="Course 1 · Anatomy",
        hud_label="COURSE 1 · ANATOMY",
        capabilities=(
            "evidence_registry",
            "controller_state",
            "on_screen_deck",
            "library_exemplars",
            "recital_observer",
        ),
    ),
    "course_2_transitions": CourseMeta(
        label="Course 2 · Transitions",
        hud_label="COURSE 2 · TRANSITIONS",
        unlock_gate="course_2_unlocked",
        lock_reason="finish the course 1 check to unlock transitions",
        capabilities=(
            "evidence_registry",
            "controller_state",
            "on_screen_deck",
            "library_suggestions",
            "recital_observer",
        ),
    ),
    "course_3_play_mode": CourseMeta(
        label="Course 3 · Play Mode",
        hud_label="COURSE 3 · PLAY-MODE",
        unlock_gate="course_3_unlocked",
        lock_reason="finish the course 2 check to unlock play mode",
        frontstage_mode="live_play_mode",
        capabilities=(
            "evidence_registry",
            "controller_state",
            "on_screen_deck",
            "live_audio",
            "cue_section_lookahead",
            "prepared_pool",
            "library_suggestions",
            "session_state",
            "session_recording",
            "debrief",
            "dj_profile",
            "recovery_drill",
        ),
    ),
}


# ---------------------------------------------------------------------------
# Course frames: appended into the tutor system instruction
# ---------------------------------------------------------------------------

COURSE_FRAMES: dict[str, str] = {
    "course_0": (
        "Course 0 is the hello-world tutorial: a one-lesson demo proving "
        "the runtime end-to-end."
    ),
    "course_1_anatomy": (
        "Course 1 is the anatomy walkthrough: a beginner meets their "
        "controller, names every section (decks / mixer / transport / EQ), "
        "then hears the EQ bands demonstrated on a track from their own "
        "library. The user has no DJ vocabulary yet; ground every "
        "observation in what their hands and ears are doing right now."
    ),
    "course_2_transitions": (
        "Course 2 walks the user through beatmatching (ear and sync) then "
        "the five canonical transitions: long blend, eq swap, bassline "
        "swap, filter fade, echo-out. Add hot cues, the camelot wheel, "
        "phrase matching, and train-wreck diagnosis. When library keys "
        "exist, teach melody through the user's own tracks. Ground every "
        "observation in what the two decks are doing right now."
    ),
    "course_3_play_mode": (
        "Course 3 is the play mode: the beginner runs a real set with "
        "vibemix coaching live. Forward calls land only when [cue:] "
        "anchors back the prediction; otherwise narration stays "
        "retrospective. No exemplar playback while a deck is audible "
        "(verbal coaching only). The user has finished anatomy and "
        "transitions; the floor is muscle memory, the work here is "
        "judgment under live conditions."
    ),
}


# ---------------------------------------------------------------------------
# Per-lesson metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LessonMeta:
    """Per-lesson metadata record.

    Fields:
        title: HUD title: lowercase, period-free (UI-SPEC).
        course_id: Key into :data:`COURSE_FRAMES`.
        system_instruction_addendum: ≤200 char suffix appended to the
            tutor system instruction by
            :func:`vibemix.learn.prompts.build_tutor_system_instruction`.
            Tested against the 200-char cap at composition time:
            ``build_tutor_system_instruction`` raises ``ValueError`` when
            an entry exceeds the cap.
        transcript_path: Relative path under
            ``src/vibemix/learn/transcripts/`` pointing at the hand-
            authored JSON fixture for this lesson. The ``script`` property
            reads + json-decodes the file lazily.
    """

    title: str
    course_id: str
    system_instruction_addendum: str
    transcript_path: str

    @property
    def script(self) -> dict[str, Any]:
        """Lazy-load the JSON fixture from disk.

        Re-reads on every access (frozen dataclass = no instance cache).
        For P92 this is called at most once per lesson start; the I/O is
        a single small read. If the load pattern broadens in P94+, layer
        a ``functools.lru_cache`` on a free function that the property
        delegates to.

        Raises:
            FileNotFoundError: ``transcript_path`` resolves outside the
                ``transcripts/`` directory or the file is missing.
            json.JSONDecodeError: The fixture is not valid JSON.
        """
        base = Path(__file__).parent / "transcripts"
        return json.loads(
            (base / self.transcript_path).read_text(encoding="utf-8")
        )


# ---------------------------------------------------------------------------
# Curriculum dispatch table: keyed by lesson_id
# ---------------------------------------------------------------------------

CURRICULUM: dict[str, LessonMeta] = {
    "L0.00-press-play": LessonMeta(
        title="press play",
        course_id="course_0",
        system_instruction_addendum=(
            "HELLO WORLD ADDENDUM: Wait for the user to press deck A's play "
            "button. Do not narrate over them. Stay quiet between beats."
        ),
        transcript_path="hello_world/01_press_play.json",
    ),
    # ------------------------------------------------------------------
    # P94: Course 1 (Anatomy of a Deck): 16 lessons L1.01..L1.16.
    # Every addendum is byte-equal to the corresponding fixture's
    # ``system_instruction_addendum`` field (drift gate pinned by
    # Plan 94-02's test). Titles are lowercase + period-free per UI-SPEC.
    # ------------------------------------------------------------------
    "L1.01": LessonMeta(
        title="opening dialog",
        course_id="course_1_anatomy",
        system_instruction_addendum=(
            "OPENING DIALOG ADDENDUM: Read the four scripted lines verbatim. "
            "Do not improvise, paraphrase, or add an extra line."
        ),
        transcript_path="course_1_anatomy/01_welcome.json",
    ),
    "L1.02": LessonMeta(
        title="meet your controller",
        course_id="course_1_anatomy",
        system_instruction_addendum=(
            "MEET CONTROLLER ADDENDUM: Name the rendered controller's three "
            "sections: left deck, mixer, right deck. Do not narrate "
            "features beyond the three sections."
        ),
        transcript_path="course_1_anatomy/02_meet_your_controller.json",
    ),
    "L1.03": LessonMeta(
        title="channel strip",
        course_id="course_1_anatomy",
        system_instruction_addendum=(
            "CHANNEL STRIP ADDENDUM: A channel strip is one deck's tone "
            "column: gain, three EQ knobs, fader. Name the parts as the "
            "user sweeps them. Stay quiet during the sweep."
        ),
        transcript_path="course_1_anatomy/03_channel_strip.json",
    ),
    "L1.04": LessonMeta(
        title="crossfader",
        course_id="course_1_anatomy",
        system_instruction_addendum=(
            "CROSSFADER ADDENDUM: The crossfader is the horizontal slider "
            "between decks. Left equals deck A only, right equals deck B "
            "only, center equals both. State only the mechanical behavior."
        ),
        transcript_path="course_1_anatomy/04_crossfader.json",
    ),
    "L1.05": LessonMeta(
        title="pitch fader",
        course_id="course_1_anatomy",
        system_instruction_addendum=(
            "PITCH FADER ADDENDUM: The pitch fader is a percentage "
            "adjustment to the BPM. Reference the tempo display on the "
            "user's deck. Sync is a separate lesson."
        ),
        transcript_path="course_1_anatomy/05_pitch_fader.json",
    ),
    "L1.06": LessonMeta(
        title="transport buttons",
        course_id="course_1_anatomy",
        system_instruction_addendum=(
            "TRANSPORT BUTTONS ADDENDUM: Play, cue, and sync are deck "
            "transport. Cue plays from the cue point while held. Do not "
            "pre-empt the sync explanation; Course 2 owns sync."
        ),
        transcript_path="course_1_anatomy/06_transport_buttons.json",
    ),
    "L1.07": LessonMeta(
        title="jog wheel",
        course_id="course_1_anatomy",
        system_instruction_addendum=(
            "JOG WHEEL ADDENDUM: The jog wheel is the round platter used "
            "to nudge a track forward or back. Scratching is a separate "
            "art form, deferred to a later course. Do not narrate "
            "scratching."
        ),
        transcript_path="course_1_anatomy/07_jog_wheel.json",
    ),
    "L1.08": LessonMeta(
        title="headphone cueing",
        course_id="course_1_anatomy",
        system_instruction_addendum=(
            "HEADPHONE CUEING ADDENDUM: The cue button routes a deck to "
            "the headphones only. Master and headphone cue can differ: "
            "that is the point."
        ),
        transcript_path="course_1_anatomy/08_headphone_cueing.json",
    ),
    "L1.09": LessonMeta(
        title="master · booth · headphones",
        course_id="course_1_anatomy",
        system_instruction_addendum=(
            "MASTER VOL ADDENDUM: Master sets venue volume, booth is the "
            "monitor send, headphones is the cue send. Red zone above "
            "-6 dBFS clips. Do not move master mid-set."
        ),
        transcript_path="course_1_anatomy/09_master_booth_headphones.json",
    ),
    "L1.10": LessonMeta(
        title="anatomy of a song",
        course_id="course_1_anatomy",
        system_instruction_addendum=(
            "SONG ANATOMY ADDENDUM: Walk through intro, build, drop, "
            "breakdown, outro on the playing track. Reference the audio "
            "you both hear, not music-theory jargon."
        ),
        transcript_path="course_1_anatomy/10_anatomy_of_a_song.json",
    ),
    "L1.11": LessonMeta(
        title="counting bars",
        course_id="course_1_anatomy",
        system_instruction_addendum=(
            "COUNTING BARS ADDENDUM: Count one-two-three-four across four "
            "bars (sixteen beats). The user taps on the one each bar. Do "
            "not narrate microtiming."
        ),
        transcript_path="course_1_anatomy/11_counting_bars.json",
    ),
    "L1.12": LessonMeta(
        title="spot breakdown by ear",
        course_id="course_1_anatomy",
        system_instruction_addendum=(
            "SPOT BREAKDOWN EAR ADDENDUM: The breakdown is the energy "
            "drop: usually the kick steps out and a sustained chord or "
            "vocal carries through. State the audible cue, not the bar "
            "number."
        ),
        transcript_path="course_1_anatomy/12_spot_breakdown_by_ear.json",
    ),
    "L1.13": LessonMeta(
        title="spot breakdown by eye",
        course_id="course_1_anatomy",
        system_instruction_addendum=(
            "SPOT BREAKDOWN EYE ADDENDUM: The breakdown on the waveform "
            "is a thinner section: less low end, taller mids. Point to "
            "the waveform, not the audio."
        ),
        transcript_path="course_1_anatomy/13_spot_breakdown_by_eye.json",
    ),
    "L1.14": LessonMeta(
        title="eq as tutor",
        course_id="course_1_anatomy",
        system_instruction_addendum=(
            "EQ AS TUTOR ADDENDUM: Cycle three EQ bands: low, mid, high. "
            "Cite the exemplar track once per band. Stay quiet while the "
            "user is sweeping the knob."
        ),
        transcript_path="course_1_anatomy/14_eq_as_tutor.json",
    ),
    "L1.15": LessonMeta(
        title="load two tracks",
        course_id="course_1_anatomy",
        system_instruction_addendum=(
            "LOAD TWO TRACKS ADDENDUM: The user loads a track to deck A, "
            "then a track to deck B. Reference the load button on the "
            "controller, not the laptop keyboard."
        ),
        transcript_path="course_1_anatomy/15_load_two_tracks.json",
    ),
    "L1.16": LessonMeta(
        title="course 1 recital",
        course_id="course_1_anatomy",
        system_instruction_addendum=(
            "COURSE 1 RECITAL ADDENDUM: Five mixed prompts from prior "
            "lessons. State the score honestly. Do not soften a fail; do "
            "not embellish a pass."
        ),
        transcript_path="course_1_anatomy/16_course_1_recital.json",
    ),
    # ------------------------------------------------------------------
    # P95: Course 2 (Transitions): 14 lessons L2.01..L2.14.
    # Every addendum is byte-equal to the corresponding fixture's
    # ``system_instruction_addendum`` field. Titles are lowercase + period-
    # free per UI-SPEC. Mirror of the P94 Course 1 extension pattern.
    # ------------------------------------------------------------------
    "L2.01": LessonMeta(
        title="beatmatching by ear",
        course_id="course_2_transitions",
        system_instruction_addendum=(
            "BEATMATCH EAR ADDENDUM: Sync stays off. The user lines up "
            "deck B's tempo against deck A by listening for the drift "
            "between the two kicks. State the drift direction, never the "
            "percentage."
        ),
        transcript_path="course_2_transitions/01_beatmatching_ear.json",
    ),
    "L2.02": LessonMeta(
        title="beatmatching with sync",
        course_id="course_2_transitions",
        system_instruction_addendum=(
            "BEATMATCH SYNC ADDENDUM: Sync is the modern fast-path: "
            "press it and the BPMs match. Frame it as a tool, not a "
            "shortcut. The ear-version still matters for hardware without "
            "sync."
        ),
        transcript_path="course_2_transitions/02_beatmatching_sync.json",
    ),
    "L2.03": LessonMeta(
        title="long blend",
        course_id="course_2_transitions",
        system_instruction_addendum=(
            "LONG BLEND ADDENDUM: A 32-bar crossfader fade from deck a to "
            "deck b. State the bar count. Do not narrate the EQ swap: "
            "that is the next lesson."
        ),
        transcript_path="course_2_transitions/03_long_blend.json",
    ),
    "L2.04": LessonMeta(
        title="eq swap",
        course_id="course_2_transitions",
        system_instruction_addendum=(
            "EQ SWAP ADDENDUM: Crossfade with EQs, not the crossfader. "
            "Cut deck a's lows as you raise deck b's lows. Frame it as a "
            "band-by-band hand-off."
        ),
        transcript_path="course_2_transitions/04_eq_swap.json",
    ),
    "L2.05": LessonMeta(
        title="bassline swap",
        course_id="course_2_transitions",
        system_instruction_addendum=(
            "BASSLINE SWAP ADDENDUM: The kick belongs to one deck at a "
            "time. Cut deck a's lows then raise deck b's lows on the "
            "beat-1 of a phrase. Two basslines stacking is the train "
            "wreck this lesson prevents."
        ),
        transcript_path="course_2_transitions/05_bassline_swap.json",
    ),
    "L2.06": LessonMeta(
        title="filter fade",
        course_id="course_2_transitions",
        system_instruction_addendum=(
            "FILTER FADE ADDENDUM: The color filter sweeps both extremes. "
            "Pulling left thins to high-pass; pushing right narrows to "
            "low-pass. The filter sounds like rising water."
        ),
        transcript_path="course_2_transitions/06_filter_fade.json",
    ),
    "L2.07": LessonMeta(
        title="echo-out",
        course_id="course_2_transitions",
        system_instruction_addendum=(
            "ECHO-OUT ADDENDUM: The echo-out is a bail. Hit echo on deck "
            "a, kill its channel, deck b takes over. Frame it as a safety "
            "net, not a featured move."
        ),
        transcript_path="course_2_transitions/07_echo_out.json",
    ),
    "L2.08": LessonMeta(
        title="drop swap",
        course_id="course_2_transitions",
        system_instruction_addendum=(
            "DROP SWAP ADDENDUM: A hard crossfader cut at the drop of "
            "deck b. Time it to the bar: early or late kills the drop."
        ),
        transcript_path="course_2_transitions/08_drop_swap.json",
    ),
    "L2.09": LessonMeta(
        title="loop transition",
        course_id="course_2_transitions",
        system_instruction_addendum=(
            "LOOP TRANSITION ADDENDUM: A loop on deck a buys time while "
            "deck b enters. Loop in, crossfade across, loop out. State "
            "the bar length of the loop."
        ),
        transcript_path="course_2_transitions/09_loop_transition.json",
    ),
    "L2.10": LessonMeta(
        title="hot cues and memory cues",
        course_id="course_2_transitions",
        system_instruction_addendum=(
            "HOT CUES ADDENDUM: Hot cues are jump points. If the user "
            "has rekordbox cues, use them; otherwise frame cue 2 as the "
            "breakdown entry. Do not narrate scratching."
        ),
        transcript_path="course_2_transitions/10_hot_cues_memory_cues.json",
    ),
    "L2.11": LessonMeta(
        title="camelot wheel",
        course_id="course_2_transitions",
        system_instruction_addendum=(
            "CAMELOT WHEEL ADDENDUM: The camelot wheel labels keys 1a "
            "through 12a and 1b through 12b. If a library pair is "
            "provided, teach the wheel through those two real tracks."
        ),
        transcript_path="course_2_transitions/11_camelot_wheel.json",
    ),
    "L2.12": LessonMeta(
        title="phrase matching",
        course_id="course_2_transitions",
        system_instruction_addendum=(
            "PHRASE MATCHING ADDENDUM: A phrase is four bars. Bringing "
            "deck b in on deck a's phrase-one keeps the structure intact. "
            "Frame it as bars, not seconds."
        ),
        transcript_path="course_2_transitions/12_phrase_matching.json",
    ),
    "L2.13": LessonMeta(
        title="diagnosing a train wreck",
        course_id="course_2_transitions",
        system_instruction_addendum=(
            "TRAIN WRECK ADDENDUM: A train wreck has three named causes: "
            "off-phrase, off-key, off-bpm. State the cause you hear; "
            "do not soften it. Listening-only lesson."
        ),
        transcript_path="course_2_transitions/13_diagnosing_train_wreck.json",
    ),
    "L2.14": LessonMeta(
        title="course 2 recital",
        course_id="course_2_transitions",
        system_instruction_addendum=(
            "COURSE 2 RECITAL ADDENDUM: Five transitions drawn from "
            "prior lessons. At least three different transition types "
            "are required to pass. State the score honestly."
        ),
        transcript_path="course_2_transitions/14_course_2_recital.json",
    ),
    # ------------------------------------------------------------------
    # P96: Course 3 (Play Mode): 6 lessons L3.01..L3.06.
    # Every addendum is byte-equal to the corresponding fixture's
    # ``system_instruction_addendum`` field (drift gate pinned by
    # Plan 96-03's test). Titles are lowercase + period-free per UI-SPEC.
    # L3.01-L3.05 carry proactive_lens_active=true + exemplar_audio_forbidden=true;
    # L3.06 (post-set review) carries both false.
    # ------------------------------------------------------------------
    "L3.01": LessonMeta(
        title="first 5-minute mix",
        course_id="course_3_play_mode",
        system_instruction_addendum=(
            "FIRST 5-MIN MIX ADDENDUM: User picks tracks freely. Suggest "
            "one grounded move per minute. Count-ins require [cue:] "
            "evidence; otherwise narrate retrospectively."
        ),
        transcript_path="course_3_play_mode/01_first_5_minute_mix.json",
    ),
    "L3.02": LessonMeta(
        title="first 15-minute set",
        course_id="course_3_play_mode",
        system_instruction_addendum=(
            "FIRST 15-MIN SET ADDENDUM: User brings a prepared five-track "
            "pool from build-a-set or their own queue. Coach each "
            "transition. Cite [cue:] when forward calls are grounded."
        ),
        transcript_path="course_3_play_mode/02_first_15_minute_set.json",
    ),
    "L3.03": LessonMeta(
        title="reading the room",
        course_id="course_3_play_mode",
        system_instruction_addendum=(
            "READING THE ROOM ADDENDUM: Walk through reading the energy "
            "curve mid-set. Suggest next-track adjustments grounded in "
            "what just played."
        ),
        transcript_path="course_3_play_mode/03_reading_the_room.json",
    ),
    "L3.04": LessonMeta(
        title="first 30-minute set capstone",
        course_id="course_3_play_mode",
        system_instruction_addendum=(
            "30-MIN CAPSTONE ADDENDUM: Full proactive co-pilot. Forward "
            "calls ONLY on [cue:] evidence. Save session evidence for a "
            "post-set debrief; do not promise auto-open."
        ),
        transcript_path="course_3_play_mode/04_first_30_minute_capstone.json",
    ),
    "L3.05": LessonMeta(
        title="recovery drills",
        course_id="course_3_play_mode",
        system_instruction_addendum=(
            "RECOVERY DRILLS ADDENDUM: Synthetic train-wreck on deck B "
            "(key clash OR misaligned phrase). User bails out via "
            "echo-out, filter, or cut within 4 bars."
        ),
        transcript_path="course_3_play_mode/05_recovery_drills.json",
    ),
    "L3.06": LessonMeta(
        title="dj profile graduation",
        course_id="course_3_play_mode",
        system_instruction_addendum=(
            "DJ PROFILE GRADUATION ADDENDUM: Review the long-term DJ "
            "profile from v8.1. Summarize lesson completion. No active "
            "session; the debrief is the surface."
        ),
        transcript_path="course_3_play_mode/06_dj_profile_graduation.json",
    ),
}


def course_lesson_ids(course_id: str) -> tuple[str, ...]:
    """Return lesson ids for ``course_id`` in authored curriculum order."""
    return tuple(
        lesson_id
        for lesson_id, meta in CURRICULUM.items()
        if meta.course_id == course_id
    )


def beginner_course_ids() -> tuple[str, ...]:
    """Return course ids that belong to the shipped beginner module."""
    return tuple(
        course_id
        for course_id, meta in COURSE_REGISTRY.items()
        if meta.beginner
    )


def beginner_lesson_ids() -> tuple[str, ...]:
    """Return the beginner lesson ids in authored module order."""
    beginner_courses = set(beginner_course_ids())
    return tuple(
        lesson_id
        for lesson_id, meta in CURRICULUM.items()
        if meta.course_id in beginner_courses
    )
