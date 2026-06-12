# SPDX-License-Identifier: Apache-2.0
"""Grounded master-mix energy receipts for Sven's audio-only coaching.

The transition scorer and next-suggestion engine can produce useful forward
context even when the live rig exposes only the master mix. This module binds
that library/scorer context to current master-mix DSP deltas, then emits one
citable receipt the prompt may turn into a short coaching nudge.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from vibemix.intel.transition_scorer import LIVE_SELECT_CONFIDENCE_FLOOR
from vibemix.state.deck_context import (
    SPECTRAL_CLAIM_BAND_FLOOR,
    render_audio_delta_items,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from vibemix.state import MusicState
    from vibemix.state.evidence_registry import EvidenceRegistry

_CITATION_BODY_RE = re.compile(r"^[^\s,\]]+$")

# The measured-filler forward bodies (iter3/iter4 judge runs, 2026-06-09/10):
# "holding the groove steady" produced every friend-0 filler line; the two
# fallbacks carry zero information by construction. Kept in lock-step with
# the _forward_body rule table below.
_STEADY_NO_INFO_BODIES = frozenset(
    {
        "holding the groove steady",
        "the current phrase direction",
        "the current master-mix energy",
    }
)
_VOICE_EVENT_TYPES = frozenset(
    {"HEARTBEAT", "PHASE", "TRACK_CHANGE", "TRANSITION_OPPORTUNITY"}
)
_TEXT_ESCAPE = str.maketrans({"[": "(", "]": ")", "\n": " ", "\r": " ", "|": "/"})

# Deltas are RELATIVE (|cur-prev|/prev), so a 0.02→0.05 mid move renders
# "rose 25% (clear)" while the mids are still inaudible — the judge refuted
# every such line ("new mids" voiced at mid=0.05: the 0-for-3 cold-start
# class, 2026-06-10 cadence lever). A ROSE band delta is voiceable only when
# its band's post level clears this floor. A FELL band delta (2026-06-11
# filler-cut panel) is voiceable only when its reconstructed PRE level
# clears it: "high energy fell 50%" at 0.02→0.01 is a relative fall on a
# band that was never audible — that one receipt minted "keeping the
# top-end space intentional" 7 times across lever+baseline runs, judged
# should_NOT 6 of 7. Keeper calibration: killers at band 0.01-0.05,
# survivors at 0.10-0.16 (rose post) / pre 0.15-0.44 (fell).
# Bound by reference to the guard layer (C.6, free Sven): the producer, the
# spectral guard, and the evidence-license block must agree on what
# "audible" means — a drifted local copy would voice reads the guard then
# refuses to license.
BAND_AUDIBILITY_FLOOR = SPECTRAL_CLAIM_BAND_FLOOR

# Delta-string keyword → the state.bands key(s) backing the claim. ROSE
# "brightness" keys on the HIGH band alone: the brightness share sums
# mid+high, so a mid-driven rise must not voice top-end vocabulary (the
# measured "added brightness" fabrication). FELL "brightness" reconstructs
# the mid+high SUM brightness actually measures — high alone would falsely
# kill every brightness read in a dark-topped mix (high 0.01 / mid 0.30: an
# order of magnitude wrong, 2026-06-11 panel).
_ROSE_BAND_KEYWORDS = (
    ("sub energy", ("sub",)),
    ("low energy", ("low",)),
    ("mid energy", ("mid",)),
    ("high energy", ("high",)),
    ("brightness", ("high",)),
)
_FELL_BAND_KEYWORDS = (
    ("sub energy", ("sub",)),
    ("low energy", ("low",)),
    ("mid energy", ("mid",)),
    ("high energy", ("high",)),
    ("brightness", ("mid", "high")),
)
_FELL_PCT_RE = re.compile(r"fell (\d+)% ")


def _band_claim_level(text: str, state: MusicState) -> float | None:
    """Audibility level backing a band-delta claim; None = abstain.

    ROSE → the named band's POST level (a rise must be audible NOW).
    FELL → the PRE level reconstructed as post/(1 - pct): a fall must have
    been audible BEFORE. Abstains (None) on non-band deltas (onset/LUFS/RMS),
    a non-canonical fell string (no "fell NN% " magnitude to reconstruct
    from), and pct >= 90 — post ~ 0 divides the true pre-level away, and a
    full band kill (EQ kill / breakdown drop) is the most audible fell
    gesture there is, so it stays voiceable."""
    bands = getattr(state, "bands", {}) or {}
    if not isinstance(bands, dict):
        return None

    def _level(keys: tuple[str, ...]) -> float:
        total = 0.0
        for key in keys:
            try:
                total += float(bands.get(key, 0.0) or 0.0)
            except (TypeError, ValueError):
                pass
        return total

    if "rose" in text:
        for keyword, keys in _ROSE_BAND_KEYWORDS:
            if keyword in text:
                return _level(keys)
        return None
    if "fell" in text:
        m = _FELL_PCT_RE.search(text)
        if m is None:
            return None
        pct = int(m.group(1))
        if pct >= 90:
            return None
        for keyword, keys in _FELL_BAND_KEYWORDS:
            if keyword in text:
                return _level(keys) / (1.0 - pct / 100.0)
        return None
    return None


def _voiced_deltas(deltas: Sequence[str], state: MusicState) -> list[str]:
    """The deltas the receipt offers the brain as voiceable material.

    The full window still feeds the receipt digest; this clause is what the
    prompt presents as sayable. Two measured cuts (2026-06-10): slight blips
    drop whenever a non-slight delta co-rides (the brain voiced co-riding
    blips as audible claims), and inaudible-rose band deltas drop always
    (the "high energy rose 100% (strong)" at high=0.02 class)."""
    has_non_slight = any("(slight)" not in str(d).casefold() for d in deltas)
    out: list[str] = []
    for raw in deltas:
        text = str(raw).casefold()
        if has_non_slight and "(slight)" in text:
            continue
        level = _band_claim_level(text, state)
        if level is not None and level < BAND_AUDIBILITY_FLOOR:
            continue
        out.append(raw)
    return out


def build_energy_read_voice_line(
    suggestion: Mapping[str, Any] | None,
    *,
    event_type: str,
    evidence_registry: EvidenceRegistry | None,
    state: MusicState | None,
    audio_delta_items: Sequence[str] | None = None,
) -> str | None:
    """Return a citable master-mix coaching receipt for audio-only turns."""

    if event_type not in _VOICE_EVENT_TYPES:
        return None
    if evidence_registry is None or state is None:
        return None
    if not bool(getattr(state, "audible", False)):
        return None

    deltas = _bounded_audio_deltas(state, audio_delta_items)
    arc_clause = _energy_arc_clause(state)
    phrase_clause = _phrase_clause(state)
    if not deltas and arc_clause is None and phrase_clause is None:
        return None

    transition = _transition_context(suggestion)
    candidate_id = (
        str(transition["candidate_id"]) if transition is not None else _audio_only_candidate_id(state)
    )
    forward_body = _forward_body(deltas, arc_clause, phrase_clause, state)
    # Iter5 (2026-06-10 bench campaign): the steady/no-information bodies no
    # longer earn a VOICE receipt on their own. Judge-measured on both corpora:
    # every spoken steady line scored friend 0 / should_speak False ("generic
    # filler telling the DJ to do nothing"). A receipt exists to carry a point;
    # "keep doing what you're doing" is not one. Change reads (lifting /
    # breathing space / delta-driven) and scorer-transition receipts — the
    # lines the judge marked should_speak=True — pass through unchanged.
    if transition is None and forward_body in _STEADY_NO_INFO_BODIES:
        return None
    digest = _receipt_digest(
        candidate_id=candidate_id,
        deltas=deltas,
        arc_clause=arc_clause,
        phrase_clause=phrase_clause,
        forward_body=forward_body,
    )
    energy_key = f"master_read={candidate_id}_{digest}"

    evidence_registry.write("energy", energy_key, _set_seconds(state))
    cite_tail = f"[energy:{energy_key}]"
    scorer_clause = f"The master-mix read points toward {forward_body}. "
    reasons_clause = ""
    risks_clause = ""
    scope_clause = "master-mix energy, brightness, loudness, and phrase direction"

    if transition is not None:
        track_id = str(transition["track_id"])
        mix_key = f"transition_verdict={candidate_id}"
        evidence_registry.write("track", track_id, 0.0)
        evidence_registry.write("mix", mix_key, 0.0)

        risk_cite = _register_first_risk_citation(transition["transition"], evidence_registry)
        cite_tail = f"{cite_tail} [track:{track_id}] [mix:{mix_key}]"
        if risk_cite is not None:
            cite_tail = f"{cite_tail} {risk_cite}"

        title = str(transition["title"])
        artist = str(transition["artist"])
        artist_clause = f" by {artist}" if artist else ""
        score = transition["score"]
        score_clause = f"score {score:.2f}, " if score is not None else ""
        confidence = float(transition["confidence"])
        scorer_clause = (
            f"The next-suggestion scorer points toward {title}{artist_clause} with "
            f"{score_clause}confidence {confidence:.2f}. "
        )
        reasons_clause = _list_clause("Scorer reasons", transition["transition"].get("reasons"))
        risks_clause = _list_clause("Risk flags", transition["transition"].get("risk_flags"))
        scope_clause = f"{scope_clause}, and library fit"

    voiced = _voiced_deltas(deltas, state)
    delta_clause = f"Live deltas: {'; '.join(voiced)}. " if voiced else ""
    arc_text = f"{arc_clause}. " if arc_clause is not None else ""
    phrase_text = f"{phrase_clause}. " if phrase_clause is not None else ""

    return (
        "Energy-read receipt: source=master_mix. "
        f"{scorer_clause}"
        f"{delta_clause}{arc_text}{phrase_text}{reasons_clause}{risks_clause}"
        f"Use this as one forward coaching nudge scoped to {scope_clause}. "
        f"Copy these citations exactly: {cite_tail}."
    )


def _transition_context(suggestion: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if suggestion is None:
        return None
    transition = suggestion.get("transition")
    if not isinstance(transition, Mapping):
        return None

    confidence = _finite_float(transition.get("confidence"))
    if confidence is None or confidence < LIVE_SELECT_CONFIDENCE_FLOOR:
        return None

    track_id = _clean_citation_body(transition.get("to_track_id")) or _clean_citation_body(
        suggestion.get("track_id")
    )
    candidate_id = _clean_citation_body(transition.get("candidate_id"))
    if track_id is None or candidate_id is None:
        return None

    return {
        "transition": transition,
        "confidence": confidence,
        "score": _finite_float(transition.get("score")),
        "track_id": track_id,
        "candidate_id": candidate_id,
        "title": _clean_text(suggestion.get("title"), fallback="the next library option"),
        "artist": _clean_text(suggestion.get("artist"), fallback=""),
    }


def _bounded_audio_deltas(
    state: MusicState,
    audio_delta_items: Sequence[str] | None,
    *,
    cap: int = 4,
) -> list[str]:
    items = audio_delta_items if audio_delta_items is not None else render_audio_delta_items(state)
    out: list[str] = []
    for raw in items or ():
        text = _clean_text(raw, fallback="", cap=96)
        if text:
            out.append(text)
        if len(out) >= cap:
            break
    return out


def _energy_arc_clause(state: MusicState) -> str | None:
    curve = [
        float(value)
        for value in getattr(state, "energy_curve", []) or []
        if isinstance(value, (int, float))
    ]
    if len(curve) >= 4:
        first = sum(curve[:2]) / 2.0
        last = sum(curve[-2:]) / 2.0
        delta = last - first
        if abs(delta) >= 0.015:
            direction = "lifting" if delta > 0.0 else "settling"
            return f"Energy arc over the recent master window is {direction}"

    buildup = _finite_float(getattr(state, "buildup_score", None))
    if buildup is not None and buildup >= 0.5:
        return "Energy arc is building"
    if buildup is not None and buildup <= 0.1 and getattr(state, "phase", "") in {
        "low",
        "groove",
        "breakdown",
    }:
        return "Energy arc is settled"
    return None


def _phrase_clause(state: MusicState) -> str | None:
    phase = _clean_text(getattr(state, "phase", None), fallback="", cap=24)
    if not phase or phase == "silent":
        return None
    bpm = _finite_float(getattr(state, "bpm", None))
    bpm_conf = _finite_float(getattr(state, "bpm_confidence", None)) or 0.0
    if bpm is not None and bpm > 0.0 and bpm_conf >= 0.6:
        return f"Phrase read: current section feels like {phase} at {bpm:.0f} BPM"
    return f"Phrase read: current section feels like {phase}"


def _register_first_risk_citation(
    transition: Mapping[str, Any],
    evidence_registry: EvidenceRegistry,
) -> str | None:
    risk_flags = transition.get("risk_flags")
    if not isinstance(risk_flags, Sequence) or isinstance(risk_flags, str):
        return None
    for raw in risk_flags:
        risk = _clean_citation_body(raw)
        if risk is None:
            continue
        key = f"energy_risk={risk}"
        evidence_registry.write("energy", key, 0.0)
        return f"[energy:{key}]"
    return None


def _list_clause(label: str, value: object) -> str:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ""
    cleaned = [
        _clean_text(item, fallback="", cap=96)
        for item in value
        if _clean_text(item, fallback="", cap=96)
    ]
    if not cleaned:
        return ""
    return f"{label}: {'; '.join(cleaned[:2])}. "


def _receipt_digest(
    *,
    candidate_id: str,
    deltas: Sequence[str],
    arc_clause: str | None,
    phrase_clause: str | None,
    forward_body: str,
) -> str:
    raw = "|".join(
        [candidate_id, forward_body, *(deltas or ()), arc_clause or "", phrase_clause or ""]
    )
    return hashlib.blake2s(raw.encode("utf-8"), digest_size=4).hexdigest()


def _audio_only_candidate_id(state: MusicState) -> str:
    bucket = int(_set_seconds(state) // 4.0)
    phase = _clean_citation_body(str(getattr(state, "phase", "") or "mix")) or "mix"
    return f"audio_{phase}_{bucket}"


def _forward_body(
    deltas: Sequence[str],
    arc_clause: str | None,
    phrase_clause: str | None,
    state: MusicState,
) -> str:
    arc = (arc_clause or "").casefold()
    phase = str(getattr(state, "phase", "") or "").strip().casefold()
    # Deltas first (iter6a): a measured live delta is fresher and more specific
    # than the windowed arc or the phase label — a settling arc + "sub fell"
    # is an earned "leave low-end space" nudge, not a steady read.
    for raw in deltas:
        text = str(raw).casefold()
        # Iter7 (n=3 replication, 2026-06-10): slight-magnitude deltas stay in
        # the receipt's evidence clause but never pick the body — 4/5 judged
        # should_NOT lines were relative blips voiced as audible claims
        # ("That brightness share just ticked up…") the judge's ears refuted.
        if "(slight)" in text:
            continue
        # Band claims must be audible (BAND_AUDIBILITY_FLOOR): a rose claim
        # checks its POST level (a relative rise from near-silence is a blip,
        # not a read — the measured cold-start "new mids at mid=0.05" class),
        # a fell claim checks its reconstructed PRE level (a relative fall on
        # a never-audible band minted the "top-end space intentional" filler
        # family, 6-of-7 should_NOT, 2026-06-11).
        level = _band_claim_level(text, state)
        if level is not None and level < BAND_AUDIBILITY_FLOOR:
            continue
        if ("sub energy" in text or "low energy" in text or "rms" in text) and "fell" in text:
            return "leaving low-end space before the next push"
        if ("sub energy" in text or "low energy" in text or "rms" in text) and "rose" in text:
            return "controlling the added weight in the next phrase"
        # Mid is split from brightness (iter7): a clear mid rise rendered as
        # "the added brightness" was judged fabricated against low actual
        # highs — each band speaks its own vocabulary. Same split on the fall
        # side (the rise-bug's twin): a mid fall is a mid read, not top-end.
        if "mid energy" in text and "rose" in text:
            return "letting the new mids sit before adding anything on top"
        if ("high energy" in text or "brightness" in text) and "rose" in text:
            return "using the added brightness as the forward cue"
        if "mid energy" in text and "fell" in text:
            return "leaving the mids open before the next layer"
        if ("high energy" in text or "brightness" in text) and "fell" in text:
            return "keeping the top-end space intentional"
    # The arc-only mint needs a delta witness (2026-06-11 filler-cut panel):
    # a lifting slope with NOTHING measured in the window — no band move, no
    # onset change — measured 2 should_NOT ("Generic energy coaching",
    # friend 1-2) against 1 friend-2 keeper. Any delta qualifies, slight
    # included: it never picks the body (skipped above), it just anchors the
    # arc in something the ear saw. Zero-delta lifting falls through to the
    # phase bodies — a conscious morph, not a receipt abort (an iter7
    # friend-3 keeper survives at phase=groove via exactly this path).
    if ("lifting" in arc or "building" in arc) and deltas:
        return "lifting the next phrase without rushing it"
    if "settling" in arc or "settled" in arc:
        return "holding the groove steady"
    if phase in {"build", "buildup", "rise"}:
        return "setting up the next lift"
    if phase in {"breakdown", "low", "groove"}:
        return "letting the current space breathe"
    if phrase_clause is not None:
        return "the current phrase direction"
    return "the current master-mix energy"


def _clean_citation_body(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or _CITATION_BODY_RE.fullmatch(value) is None:
        return None
    return value


def _clean_text(value: object, *, fallback: str, cap: int = 72) -> str:
    if not isinstance(value, str):
        return fallback
    text = " ".join(value.translate(_TEXT_ESCAPE).split())
    if not text:
        return fallback
    if len(text) <= cap:
        return text
    return text[: cap - 1].rstrip() + "..."


def _finite_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed or parsed in {float("inf"), float("-inf")}:
        return None
    return parsed


def _set_seconds(state: MusicState) -> float:
    try:
        return max(0.0, float(getattr(state, "set_seconds", 0.0) or 0.0))
    except (TypeError, ValueError):
        return 0.0


__all__ = ["build_energy_read_voice_line"]
