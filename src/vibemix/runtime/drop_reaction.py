# SPDX-License-Identifier: Apache-2.0
"""Persona line layer — turn the deterministic reaction reel into spoken lines.

``runtime.automix_demo`` emits semantic cue KEYS (``drop_incoming`` …); this is the
"the persona turns each cue key into a line" step its docstring names. The lines are
short DJ-friend interjections the co-host SPEAKS on the drop, kept tight so TTS lands
them inside the ~2 s phrase window. The selector passes each chosen line through the
same anti-slop wall the live co-host's reactions clear
(``prompts.filter.filter_for_slop``) and fails closed if a future bank edit trips it.

The layer is pure + deterministic: a reel narrates to the same lines every run for a
given ``variant_seed`` (the "lands every time" guarantee), and the seed walks each
cue's bank so a multi-beat run sounds alive instead of stuck on one phrase.
"""
from __future__ import annotations

from dataclasses import dataclass

from vibemix.prompts.filter import SILENCE_TOKEN, filter_for_slop
from vibemix.runtime.automix_demo import AutomixReel

# One bank of lines per cue key. Tight, spoken, no empty hype ("amazing"/"awesome"
# are slop-filtered) and no AI tells — a real DJ leaning into your ear, not a
# narrator. ``slam_in`` = mode-4 center-start full-volume slam; ``slammed_cut`` =
# hard cut (no blend ever fires for it), so its lines never imply a smooth blend.
REACTION_LINES: dict[str, tuple[str, ...]] = {
    "drop_incoming": (
        "here it comes",
        "ok, watch this",
        "build's peaking, hold up",
        "wait for it",
    ),
    "mixing_in": (
        "and there it is",
        "blend's locked",
        "rolling into the next one",
        "right on the phrase",
    ),
    "slam_in": (
        "full send",
        "slammed it straight in",
        "no easing, just dropped it",
    ),
    "landed_clean": (
        "clean, fully over now",
        "landed it, dead on",
        "all the way across",
    ),
    "slammed_cut": (
        "boom, cut straight to it",
        "hard cut, no warning",
        "straight swap, done",
    ),
}

# The closed set of keys the reel can emit — mirrors automix_demo.reaction_cue.
REACTION_CUES = frozenset(REACTION_LINES)


@dataclass(frozen=True)
class SpokenBeat:
    """One reaction beat with the line the co-host speaks at it."""

    t_sec: float  # fromDeck wall-time of the beat (from the DemoBeat)
    cue: str  # the reaction_cue key
    text: str  # the spoken line


def reaction_line(cue: str, *, variant: int = 0) -> str:
    """The spoken line for a cue key. ``variant`` wraps modulo the bank size.

    Raises ``KeyError`` on an unknown cue — the cue keys come from the closed
    ``reaction_cue`` set, so an unknown key is a programming error, not user input;
    fail loud rather than speak a wrong-or-empty line over the drop.

    Raises ``ValueError`` when a fixed bank line hits the anti-slop filter. The
    live call-site catches exceptions and skips the call, so a bad bank edit
    mutes the DROP line instead of bypassing the release speech guard.
    """
    bank = REACTION_LINES[cue]
    line = bank[variant % len(bank)]
    clean, matched = filter_for_slop(line)
    if matched or clean == SILENCE_TOKEN:
        raise ValueError(f"slop-filtered reaction line for {cue!r}: {matched!r}")
    return clean


def narrate_reel(reel: AutomixReel, *, variant_seed: int = 0) -> tuple[SpokenBeat, ...]:
    """Map every :class:`DemoBeat` to a :class:`SpokenBeat` with its line.

    Deterministic: same reel + seed → same lines. The seed walks the bank per beat
    index so consecutive beats of one cue don't repeat the same phrase.
    """
    return tuple(
        SpokenBeat(
            t_sec=beat.t_sec,
            cue=beat.cue,
            text=reaction_line(beat.cue, variant=variant_seed + i),
        )
        for i, beat in enumerate(reel.beats)
    )
