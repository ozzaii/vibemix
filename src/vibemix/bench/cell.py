# SPDX-License-Identifier: Apache-2.0
"""BenchCell + BenchResult — the 6-D matrix point and its recorded output.

Frozen value dataclasses, mirroring the project convention
(``coach/citation_linter.py:56`` ``LintResult`` / ``library/budget.py``
``CostProjection``). A :class:`BenchCell` is ONE point in the
model × grounding × prompting × contexting × lens × taste space; a
:class:`BenchResult` is the recorded output PLUS the DSP-fact snapshot the cell
was assembled against (so the BENCH-02 eval can re-run
``CitationLinter.check`` against the cell's OWN snapshot) PLUS the
``error`` fail-safe field (the cardinal-sin guard: a 429 parks here, the sweep
never fabricates a cell).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The grounding values that attach a live-audio Part. ``dsp_only`` is
# deliberately ABSENT — the no-audio cell sends a fully-populated evidence body
# but ZERO audio Parts (the milestone's empirical heart). ``raw_audio`` is the
# audio-only control (no structured evidence).
AUDIO_GROUNDINGS: frozenset[str] = frozenset(
    {"raw_audio", "audio+dsp", "audio+dsp+traj+genre"}
)

# The grounding values that frame the structured evidence as a secondary-ear
# corroborating signal (Phase-80 / GROUND-01 ``build_parts_description(secondary_ear=)``).
SECONDARY_EAR_GROUNDINGS: frozenset[str] = frozenset(
    {"audio+dsp", "audio+dsp+traj+genre"}
)


@dataclass(frozen=True)
class BenchCell:
    """One point in the 6-D bench matrix.

    Every field is a validated-by-convention string axis value; the assembler
    (:func:`vibemix.bench.assemble.build_cell_prompt`) maps each axis onto a
    real product knob (see 81-RESEARCH §Dimension→Seam Map).
    """

    model_path: str
    # raw_audio | dsp_only | audio+dsp | audio+dsp+traj+genre
    grounding: str
    # generic | structured
    prompting: str
    # snapshot | trajectory
    contexting: str
    # hype | critique | tutor
    lens: str
    # with_rubric | without_rubric
    taste: str
    skill: str = "intermediate"
    # Optional .mp3 basename (under bench_data_dir) for the audio-grounding cells.
    track: str | None = None

    @property
    def uses_audio(self) -> bool:
        """True iff this cell attaches a live-audio Part (NOT the dsp_only cell)."""
        return self.grounding in AUDIO_GROUNDINGS

    @property
    def secondary_ear(self) -> bool:
        """True iff the structured evidence is framed as a secondary-ear signal."""
        return self.grounding in SECONDARY_EAR_GROUNDINGS

    @property
    def structured(self) -> bool:
        """True iff the full anti-slop prompting stack is engaged (vs the generic control)."""
        return self.prompting == "structured"


@dataclass(frozen=True)
class BenchResult:
    """One recorded cell — output + the snapshot it was scored against + usage.

    ``dsp_snapshot`` carries the EXACT ``EvidenceRegistry.snapshot()`` shape
    (``evidence_registry.py:322``) the cell was assembled against, so the eval
    re-runs ``CitationLinter.check(output, dsp_snapshot)`` against the cell's
    own grounded facts. ``error`` is the fail-safe field: on a successful call
    it is ``None``; on a 429/auth/network error it carries ``repr(e)[:160]``,
    ``output`` stays ``""``, and the sweep continues (NEVER fabricated, NEVER
    aborted — RESEARCH Pitfall 2).
    """

    cell: BenchCell
    prompt: str
    output: str
    dsp_snapshot: dict[str, dict[str, tuple[float, ...]]] | None
    usage: dict = field(default_factory=dict)
    error: str | None = None
