# SPDX-License-Identifier: Apache-2.0
"""Producer-level tests for the master-mix energy receipt.

Iter5 of the 2026-06-09/10 bench campaign: the judge scored every spoken
steady-read line as filler — iter3 (audio-only corpus, n=1): "Generic filler
telling the DJ to do nothing; should stay silent."; iter4 (synth-MIDI corpus):
the one steady line was the only friend=0 / should_speak=False line in an
otherwise passing set. The steady/no-information forward bodies therefore no
longer EARN a voice receipt: a receipt exists to carry a point, and "keep
doing what you're doing" is not a point. Change reads (lifting, breathing
space, delta-driven bodies) and scorer-transition receipts are untouched —
those are the lines the judge marked should_speak=True.
"""

from __future__ import annotations

from vibemix.intel.transition_scorer import LIVE_SELECT_CONFIDENCE_FLOOR
from vibemix.runtime.energy_read_voice import build_energy_read_voice_line
from vibemix.state import MusicState
from vibemix.state.evidence_registry import EvidenceRegistry


def _state(
    *,
    curve: list[float] | None = None,
    phase: str = "groove",
    buildup: float = 0.0,
    bands: dict[str, float] | None = None,
) -> MusicState:
    state = MusicState()
    state.audible = True
    state.phase = phase
    state.buildup_score = buildup
    if curve is not None:
        state.energy_curve = curve
    if bands is not None:
        state.bands = dict(bands)
    return state


def _suggestion(confidence: float) -> dict:
    return {
        "title": "Neon Tide",
        "artist": "Velvet Mirage",
        "track_id": "velvet-mirage-neon-tide",
        "transition": {
            "confidence": confidence,
            "score": 0.81,
            "to_track_id": "velvet-mirage-neon-tide",
            "candidate_id": "cand_neon_tide_01",
            "reasons": ["camelot adjacent"],
            "risk_flags": [],
        },
    }


def test_settled_read_without_transition_yields_no_receipt() -> None:
    """The measured-filler body ('holding the groove steady') no longer earns
    a receipt on its own — judged friend 0 / should_speak False on both
    corpora. No receipt → the speak gate's describe-bank rule holds the event
    silent, which is the product-correct outcome for 'keep doing nothing'."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(curve=[0.50, 0.50, 0.40, 0.40]),  # settling arc
    )
    assert line is None


def test_pure_fallback_reads_yield_no_receipt() -> None:
    """The two pure-fallback bodies ('the current phrase direction' / 'the
    current master-mix energy') carry zero information by construction —
    same hold."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase="peak"),  # no arc, no deltas → phrase fallback only
    )
    assert line is None


def test_lifting_read_with_delta_witness_still_yields_receipt() -> None:
    """A CHANGE read keeps its receipt when ANY measured delta rides the
    window — the witness can be slight (it never picks the body, but it
    anchors the arc in something the ear saw). This is the measured surviving
    keeper shape: lever audio-r3 'lifting' read with 'low rose 14% (slight)'
    at low=0.16, judged friend 3 (2026-06-11 filler-cut panel)."""
    reg = EvidenceRegistry()
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=reg,
        state=_state(curve=[0.30, 0.30, 0.45, 0.50], bands={"low": 0.16}),
        audio_delta_items=["low energy rose 14% (slight)"],
    )
    assert isinstance(line, str)
    assert "lifting the next phrase without rushing it" in line
    assert "energy" in reg.snapshot()  # citation key registered at build time


def test_zero_delta_lifting_arc_yields_no_receipt() -> None:
    """Documented contract change (2026-06-11 filler-cut panel): the arc-only
    lifting mint — zero deltas, nothing the ear can anchor — measured 2 NOT
    ('Generic energy coaching', friend 1-2: lever audio-r1 0003, midi-r1
    0004) against 1 friend-2 keeper (midi-r3 0004). The windowed slope alone
    no longer earns a voice receipt; with no phase read either, the receipt
    falls to the no-info bodies and stays silent."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(curve=[0.30, 0.30, 0.45, 0.50], phase=""),
    )
    assert line is None


def test_zero_delta_lifting_arc_morphs_to_phase_body_at_groove() -> None:
    """The zero-delta arc cut is a body veto, not a receipt abort: at a
    phase the producer can still read (groove), the receipt morphs to the
    phase body instead of going silent — the conscious fall-through pinned
    by the 2026-06-11 panel (an iter7 friend-3 keeper survives via exactly
    this morph)."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(curve=[0.30, 0.30, 0.45, 0.50], phase="groove"),
    )
    assert isinstance(line, str)
    assert "letting the current space breathe" in line
    assert "lifting the next phrase" not in line


def test_breathing_space_read_still_yields_receipt() -> None:
    """'Letting the current space breathe' carries a directive (add nothing)
    — kept, distinct from the steady family."""
    # buildup 0.3 keeps the arc clause neutral (a default-0.0 buildup on a
    # groove/low/breakdown phase reads as a SETTLED arc — the steady family).
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase="breakdown", buildup=0.3),
    )
    assert isinstance(line, str)
    assert "letting the current space breathe" in line


def test_settling_arc_with_sub_fell_delta_yields_earned_receipt() -> None:
    """Deltas outrank arcs: a settling arc + a live 'sub fell' delta is NOT a
    steady read — the delta carries the point ('leave low-end space'). Before
    the iter6a reorder this combination hit the settled branch first and was
    silenced as filler, shadowing an EARNED line (auditor follow-up a)."""
    reg = EvidenceRegistry()
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=reg,
        # Canonical render_delta format (2026-06-11 re-fixture: the old
        # "fell 0.21 -> 0.09" string is a shape render_delta never emits and
        # bypassed the fell-audibility parse): sub fell 57% from an audible
        # level — pre reconstructs to 0.09/(1-0.57)=0.21 >= the floor.
        state=_state(curve=[0.50, 0.50, 0.40, 0.40], bands={"sub": 0.09}),  # settling arc
        audio_delta_items=["sub energy fell 57% (strong)"],
    )
    assert isinstance(line, str)
    assert "leaving low-end space before the next push" in line
    assert "energy" in reg.snapshot()


def test_lifting_arc_with_sub_rose_delta_prefers_delta_body() -> None:
    """Same precedence on the lifting side: the measured delta is fresher and
    more specific than the windowed arc, so its body leads the nudge."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(
            curve=[0.30, 0.30, 0.45, 0.50],  # lifting arc
            bands={"sub": 0.24, "low": 0.20, "mid": 0.10, "high": 0.05},
        ),
        audio_delta_items=["sub energy rose 0.10 -> 0.24"],
    )
    assert isinstance(line, str)
    assert "controlling the added weight in the next phrase" in line


def test_slight_deltas_do_not_select_a_body() -> None:
    """Iter7 (n=3 replication, 2026-06-10): 4 of 5 should_NOT lines across the
    replication pool fired brightness vocabulary from slight-magnitude deltas
    ("That brightness share just ticked up…") — a relative blip stated as an
    audible claim the judge's ears refute. Slight deltas stay in the receipt's
    evidence clause but no longer pick the forward body; with nothing else to
    say, the read is a no-info body and stays silent."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase=""),
        audio_delta_items=["brightness share rose 17% (slight)"],
    )
    assert line is None


def test_slight_delta_skipped_in_favor_of_clear_delta() -> None:
    """A slight sub blip must not shadow a clear mid move — body selection
    reads the first NON-slight match."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase="", bands={"sub": 0.20, "low": 0.18, "mid": 0.22, "high": 0.31}),
        audio_delta_items=[
            "sub energy fell 4% (slight)",
            "brightness share rose 31% (clear)",
        ],
    )
    assert isinstance(line, str)
    assert "using the added brightness as the forward cue" in line


def test_mid_rise_speaks_mid_language_not_brightness() -> None:
    """Iter7 vocab honesty: the 6a dumps caught a receipt saying "the added
    brightness" when the clear delta was MID (+25%) — the judge ruled the
    brightness claim fabricated against low actual highs. A mid rise now gets
    mid-true language; brightness vocabulary fires only on brightness/high
    deltas."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase="", bands={"sub": 0.18, "low": 0.20, "mid": 0.16, "high": 0.04}),
        audio_delta_items=["mid energy rose 25% (clear)"],
    )
    assert isinstance(line, str)
    assert "letting the new mids sit before adding anything on top" in line
    assert "brightness" not in line.split("Live deltas:")[0]


def test_inaudible_mid_rise_yields_no_receipt() -> None:
    """Cadence lever U1 (2026-06-10): deltas are RELATIVE, so a 0.02→0.05 mid
    move renders "rose 25% (clear)" while the mids are still inaudible — the
    measured 0-for-3 cold-start class ("new mids" voiced at mid=0.05, judged
    perceptual-overclaim every run). A ROSE band delta selects a body only
    when its band's post level clears BAND_AUDIBILITY_FLOOR; with nothing else
    to say the read falls to a no-info body and stays silent. Fell reads are
    exempt — a low post level IS the read."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase="", bands={"sub": 0.30, "low": 0.25, "mid": 0.05, "high": 0.02}),
        audio_delta_items=["mid energy rose 25% (clear)", "onset density rose 100% (strong)"],
    )
    assert line is None


def test_inaudible_rose_delta_dropped_from_voiced_clause() -> None:
    """The +151 class (midi-r2/r3, 2026-06-10): the receipt minted on an
    audible delta, but the brain voiced the CO-RIDING "high energy rose 100%
    (strong)" at high=0.02 from the evidence clause. Inaudible-rose deltas no
    longer enter the voiceable clause at all (they stay in the digest)."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase="", bands={"sub": 0.28, "low": 0.24, "mid": 0.08, "high": 0.02}),
        audio_delta_items=[
            "sub energy fell 40% (clear)",
            "high energy rose 100% (strong)",
        ],
    )
    assert isinstance(line, str)
    assert "leaving low-end space before the next push" in line
    assert "high energy rose" not in line


def test_slight_deltas_dropped_from_voiced_clause_when_non_slight_rides() -> None:
    """Slight blips stay out of the brain's voiceable material whenever a real
    delta co-rides — the measured generation-variance path voiced them
    downstream of body selection ("That brightness share just ticked up")."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase="", bands={"sub": 0.28, "low": 0.24, "mid": 0.12, "high": 0.06}),
        audio_delta_items=[
            "sub energy fell 40% (clear)",
            "brightness share rose 17% (slight)",
        ],
    )
    assert isinstance(line, str)
    assert "(slight)" not in line


def test_mid_fell_speaks_mid_language_not_top_end() -> None:
    """The rise-bug's twin (auditor residual, 2026-06-10): "mid energy fell"
    rendered "keeping the top-end space intentional" — top-end vocabulary for
    a mid move. Each band speaks its own vocabulary on the fall side too.
    (2026-06-11 re-fixture: bands carry an audible mid — the fall is from
    pre=0.14/(1-0.30)=0.20. The pin's intent is per-band VOCABULARY; the
    audibility of the fall is the separate fell-floor contract below.)"""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase="", bands={"mid": 0.14}),
        audio_delta_items=["mid energy fell 30% (clear)"],
    )
    assert isinstance(line, str)
    assert "leaving the mids open before the next layer" in line
    assert "top-end" not in line.split("Live deltas:")[0]


def test_high_fell_keeps_top_end_vocabulary() -> None:
    """A genuine high/brightness fall keeps the top-end body — the vocabulary
    split is per-band, not a ban. (2026-06-11 re-fixture: high=0.15 makes
    the fall audible, pre=0.23 — see the fell-floor pins below for the
    inaudible twin.)"""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase="", bands={"high": 0.15}),
        audio_delta_items=["high energy fell 35% (clear)"],
    )
    assert isinstance(line, str)
    assert "keeping the top-end space intentional" in line


def test_inaudible_fell_yields_no_receipt() -> None:
    """Fell-audibility floor (2026-06-11 filler-cut panel, D1): "high energy
    fell 50% (strong)" at high=0.01 reconstructs pre=0.02 — a relative fall
    on a band that was never audible. That exact receipt minted "keeping the
    top-end space intentional" 7 times across lever+baseline runs and was
    judged should_NOT 6 of 7 ("filler; silence was better"). The 7th was a
    friend-3 keeper on byte-identical evidence — the judge is inconsistent on
    this shape, a deterministic rule cannot split it, and the cut buys 6 NOT
    for 1 OK (acknowledged trade). With nothing else to say the read falls to
    the no-info bodies and stays silent."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase="", bands={"sub": 0.74, "low": 0.17, "mid": 0.08, "high": 0.01}),
        audio_delta_items=["high energy fell 50% (strong)"],
    )
    assert line is None


def test_audible_fell_keeps_low_space_keeper() -> None:
    """The fell-floor keeper twin: "sub energy fell 43% (strong)" at
    sub=0.25 reconstructs pre=0.44 — a real drop from an audible level, the
    corpus's 3-for-4 TRUE low-space family (lever audio-r1/midi-r1/midi-r3,
    friend 2-3)."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase="", bands={"sub": 0.25, "low": 0.32, "mid": 0.41, "high": 0.01}),
        audio_delta_items=["sub energy fell 43% (strong)"],
    )
    assert isinstance(line, str)
    assert "leaving low-end space before the next push" in line


def test_brightness_fell_reconstructs_from_mid_plus_high_sum() -> None:
    """Brightness is the mid+high SUM (deck_context._render_brightness_delta)
    — reconstructing a brightness fall from the high band alone would falsely
    kill every brightness read in a dark-topped mix (high 0.01, mid 0.30:
    an order of magnitude wrong, 2026-06-11 panel). Sum pre = 0.31/0.70 =
    0.44 — audible, the top-end body mints."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase="", bands={"sub": 0.50, "low": 0.19, "mid": 0.30, "high": 0.01}),
        audio_delta_items=["brightness share fell 30% (clear)"],
    )
    assert isinstance(line, str)
    assert "keeping the top-end space intentional" in line


def test_fell_to_near_zero_abstains_from_the_floor() -> None:
    """pct >= 90 makes the pre reconstruction meaningless (post ~ 0 divides
    away the true pre-level) — and a full band kill is the most audible fell
    gesture in DJing (EQ kill / breakdown drop), so the floor ABSTAINS and
    the read stays voiceable."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase="", bands={"sub": 0.0, "low": 0.2, "mid": 0.3, "high": 0.02}),
        audio_delta_items=["sub energy fell 100% (strong)"],
    )
    assert isinstance(line, str)
    assert "leaving low-end space before the next push" in line


def test_non_canonical_fell_string_abstains() -> None:
    """A fell string without the canonical "fell NN% " magnitude cannot
    reconstruct its pre-level — the floor abstains (mirrors the rose-side
    None path) instead of guessing."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase="", bands={"sub": 0.01}),
        audio_delta_items=["sub energy fell 0.21 -> 0.09"],
    )
    assert isinstance(line, str)
    assert "leaving low-end space before the next push" in line


def test_inaudible_fell_dropped_from_voiced_clause() -> None:
    """The voiced-clause mirror of the fell floor: an inaudible high-fall
    co-riding an audible sub-fall stays in the digest but leaves the
    "Live deltas:" clause — the brain must not be offered it as sayable
    material (same mechanism as the inaudible-rose cut, 16b1e1b4)."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase="", bands={"sub": 0.25, "low": 0.32, "mid": 0.41, "high": 0.01}),
        audio_delta_items=[
            "sub energy fell 43% (strong)",
            "high energy fell 50% (strong)",
        ],
    )
    assert isinstance(line, str)
    assert "leaving low-end space before the next push" in line
    assert "sub energy fell 43%" in line
    assert "high energy fell" not in line


def test_unmatched_deltas_fall_to_no_info_body_and_stay_silent() -> None:
    """Auditor follow-up (b): pin the third no-info body. Deltas that match no
    rule ('stereo width rose'), no arc, no phase read → 'the current
    master-mix energy' → held silent like the other no-info bodies."""
    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=_state(phase=""),
        audio_delta_items=["stereo width rose 0.40 -> 0.55"],
    )
    assert line is None


def test_settled_read_with_transition_context_keeps_receipt() -> None:
    """A scorer-transition receipt survives a settled arc — the point is the
    suggested track, not the steady read."""
    reg = EvidenceRegistry()
    line = build_energy_read_voice_line(
        _suggestion(confidence=max(0.9, LIVE_SELECT_CONFIDENCE_FLOOR)),
        event_type="PHASE",
        evidence_registry=reg,
        state=_state(curve=[0.50, 0.50, 0.40, 0.40]),  # settling arc
    )
    assert isinstance(line, str)
    assert "Neon Tide" in line
    assert "track" in reg.snapshot()
