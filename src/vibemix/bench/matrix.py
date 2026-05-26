# SPDX-License-Identifier: Apache-2.0
"""Study definitions — the two focused sweeps + the decisive no-audio cell.

The harness can EXPRESS the full 4×2×2×3×2 = 96-cell-per-model matrix, but the
documented RUNS are the charter's two focused studies (RESEARCH §Matrix scope,
Anti-Pattern "Cartesian explosion"):

- :data:`STUDY_A` — architecture-axis at ONE fixed model alias (``library_auto_tag``):
  sweep grounding × prompting × contexting × lens (a representative arch slice).
- :data:`STUDY_B` — model-axis: the best-arch placeholder cell swept over the
  plausible reaction-model router ALIASES (``live_coach`` / ``library_auto_tag``).
- :data:`NO_AUDIO_CELL` — the single decisive ``dsp_only`` cell (the empirical
  heart: can Gemini ground a sharp reaction on the DSP snapshot ALONE?).

NO MODEL LITERAL lives here — ``STUDY_*`` stores router ALIAS strings only; the
assembler resolves each via ``model_router.resolve(alias)``
(``test_no_model_literal.py`` + ``scripts/release/check_no_hardcoded_model.sh``
enforce). :data:`TASTE_RUBRIC` + :data:`LENS_ANCHORS` are FIXED module constants,
never user input (anti-prompt-injection — mirrors ``MOOD_PERSONAS`` /
``LENS_TO_MODE_MOOD``; T-81-03).
"""

from __future__ import annotations

from vibemix.bench.cell import BenchCell

# --------------------------------------------------------------------------- #
# The taste axis — the one genuinely-new authored string.
# --------------------------------------------------------------------------- #
# KAAN-ACTION: placeholder taste rubric — final wording is Kaan's IP (Open Q1).
# Do NOT author the real reward-signal wording here. This tiny FIXED fragment
# exists only so the `taste=with_rubric` axis assembles a distinct prompt; the
# real "what 'clicked' means" rubric (Kaan's lived-experience reward signal) is
# parked as a KAAN-ACTION and supplied at the live verdict run.
TASTE_RUBRIC: str = (
    "\n\n[TASTE — PLACEHOLDER, KAAN-ACTION] A reaction 'clicks' when it names "
    "the real moment and sounds like a DJ friend in the ear, not a voice "
    "assistant. (Final rubric wording is Kaan's IP — this is a stand-in.)"
)

# --------------------------------------------------------------------------- #
# Lens vocabulary anchors — FIXED constants for the BENCH-02 lens-fidelity
# heuristic (RESEARCH §271). Keyed to the LENS_TO_MODE_MOOD lens enum
# (hype / critique / tutor). Never user input.
# --------------------------------------------------------------------------- #
LENS_ANCHORS: dict[str, tuple[str, ...]] = {
    "hype": ("drop", "sick", "cooking", "energy"),
    "critique": ("try", "muddied", "tighten", "clashing", "kill"),
    "tutor": ("because", "technique", "phrase", "structure", "that's why"),
}

# --------------------------------------------------------------------------- #
# STUDY_A — architecture-axis at ONE fixed model alias.
# --------------------------------------------------------------------------- #
# A representative slice of the arch matrix (grounding × prompting × contexting
# × lens) at the fixed `library_auto_tag` reaction-model alias. NOT the full
# cartesian product (Anti-Pattern: explosion) — a focused, readable sweep that
# answers "which architecture clicks?" across the three lenses + the no-audio
# vs audio+dsp grounding contrast + the generic-vs-structured prompting knob.
_ARCH_MODEL = "library_auto_tag"  # alias, NOT a literal — resolved by the router

STUDY_A: tuple[BenchCell, ...] = (
    # dsp_only (no-audio) × structured × snapshot, across the 3 lenses — the
    # empirical-heart grounding contrasted per lens.
    BenchCell(_ARCH_MODEL, "dsp_only", "structured", "snapshot", "hype", "without_rubric"),
    BenchCell(_ARCH_MODEL, "dsp_only", "structured", "snapshot", "critique", "without_rubric"),
    BenchCell(_ARCH_MODEL, "dsp_only", "structured", "snapshot", "tutor", "without_rubric"),
    # audio+dsp × structured × snapshot, across the 3 lenses — the full secondary-ear stack.
    BenchCell(_ARCH_MODEL, "audio+dsp", "structured", "snapshot", "hype", "without_rubric", track="t1"),
    BenchCell(_ARCH_MODEL, "audio+dsp", "structured", "snapshot", "critique", "without_rubric", track="t1"),
    BenchCell(_ARCH_MODEL, "audio+dsp", "structured", "snapshot", "tutor", "without_rubric", track="t1"),
    # The contexting axis — trajectory vs snapshot at audio+dsp+traj+genre, hype lens.
    BenchCell(_ARCH_MODEL, "audio+dsp+traj+genre", "structured", "trajectory", "hype", "without_rubric", track="t1"),
    # The prompting axis — the generic (no-structure) control vs structured, dsp_only hype.
    BenchCell(_ARCH_MODEL, "dsp_only", "generic", "snapshot", "hype", "without_rubric"),
    # The taste axis — with_rubric vs the without_rubric default, dsp_only hype.
    BenchCell(_ARCH_MODEL, "dsp_only", "structured", "snapshot", "hype", "with_rubric"),
    # The raw-audio control — audio Part only, generic prompt, no structured evidence.
    BenchCell(_ARCH_MODEL, "raw_audio", "generic", "snapshot", "hype", "without_rubric", track="t1"),
)

# --------------------------------------------------------------------------- #
# STUDY_B — model-axis: the best-arch placeholder cell swept over the plausible
# reaction-model aliases. Until Kaan's STUDY_A verdict picks the winning arch,
# the placeholder best-arch is the full secondary-ear stack (audio+dsp,
# structured, snapshot, hype).
# --------------------------------------------------------------------------- #
# The router aliases that are plausible reaction-model candidates (RESEARCH
# Open Q2: sweep the EXISTING aliases; add a router alias, never a bench literal,
# for any model not yet in the router).
_MODEL_AXIS_ALIASES: tuple[str, ...] = ("live_coach", "library_auto_tag")

STUDY_B: tuple[BenchCell, ...] = tuple(
    BenchCell(
        alias,
        "audio+dsp",
        "structured",
        "snapshot",
        "hype",
        "without_rubric",
        track="t1",
    )
    for alias in _MODEL_AXIS_ALIASES
)

# --------------------------------------------------------------------------- #
# NO_AUDIO_CELL — the single decisive dsp_only cell (the milestone's empirical
# heart). ZERO audio Parts, a fully-populated evidence body. If Gemini grounds a
# sharp reaction on the DSP snapshot alone, the intelligence resided in the EAR,
# not the raw ear.
# --------------------------------------------------------------------------- #
NO_AUDIO_CELL: BenchCell = BenchCell(
    _ARCH_MODEL,
    "dsp_only",
    "structured",
    "snapshot",
    "hype",
    "without_rubric",
)

# Named-study lookup for the CLI (`bench run --study {A|B|no-audio}`).
STUDIES: dict[str, tuple[BenchCell, ...]] = {
    "A": STUDY_A,
    "B": STUDY_B,
    "no-audio": (NO_AUDIO_CELL,),
}
