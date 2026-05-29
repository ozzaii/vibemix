# SPDX-License-Identifier: Apache-2.0
"""Compact prompt context for per-deck grounding.

This module is deliberately pure/read-only. It turns the existing
``MusicState.deck_state`` snapshot into a bounded string that helps the coach
separate "one deck changed" from "two decks are actually in play" without
adding another model call or touching the Rekordbox live database.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from vibemix.state.deck_state import DeckTrack
from vibemix.state.deltas import DELTA_FLOOR, render_delta

if TYPE_CHECKING:  # pragma: no cover - typing-only import
    from vibemix.state.music_state import MusicState


DECK_CONTEXT_MIN_CONF: float = 0.3
_MOVE_SIDE_RE = re.compile(r"\b([ABCD])_(?:low|mid|hi|filter|volume|play)")
_MULTI_DECK_OUTCOME_RE = re.compile(
    r"\b("
    r"transition(?:ed|ing)?|blend(?:ed|ing)?|mix(?:ed|ing)?|crossfade(?:d|s|ing)?|"
    r"swap(?:ped|ping)?|switch(?:ed|ing)?|segue(?:d|ing)?|drop(?:ped|ping)?|"
    r"handoff|bridge(?:d|ing)?|layer(?:ed|ing)?"
    r")\b",
    re.IGNORECASE,
)
_MULTI_DECK_PHRASE_RE = re.compile(
    r"\b("
    r"other deck|second deck|incoming deck|incoming track|new track came in|"
    r"came in clean|brought (?:the )?(?:other|second|incoming) deck in"
    r")\b",
    re.IGNORECASE,
)
_MULTI_DECK_DISCLAIMER_RE = re.compile(
    r"\b("
    r"not a transition|no transition|single[- ]deck|one[- ]deck|only one deck|"
    r"cannot call|can't call|won't call|wouldn't call|do not have evidence|"
    r"don't have evidence"
    r")\b",
    re.IGNORECASE,
)
_MULTI_DECK_VERDICT_RE = re.compile(
    r"\b("
    r"great|nice|good|clean|smooth|solid|perfect|successful|tight|seamless|"
    r"nailed|worked|landed|bad|rough|messy|weak"
    r")\b",
    re.IGNORECASE,
)
_MOVE_EFFECT_CONTROL_RE = re.compile(
    r"\b("
    r"eq|low|mid|high|bass|sub|filter|fader|knob|kill(?:ed)?|cut|boost(?:ed)?|"
    r"volume|xfader|crossfader"
    r")\b",
    re.IGNORECASE,
)
_MOVE_EFFECT_CAUSAL_VERDICT_RE = re.compile(
    r"\b("
    r"because|caused|made|fixed|cleaned|cleared|tightened|improved|saved|"
    r"worked|landed|nailed|opened|resolved|sorted"
    r")\b",
    re.IGNORECASE,
)
_MOVE_EFFECT_BARE_VERDICT_RE = re.compile(
    r"\b(?:that|it|this|move)\b.{0,32}\b(?:landed|worked|nailed|fixed|saved|improved)\b",
    re.IGNORECASE,
)
_MOVE_EFFECT_DISCLAIMER_RE = re.compile(
    r"\b("
    r"not causal proof|not proof|cannot say it caused|can't say it caused|"
    r"won't claim it caused|correlated|around the move|same window"
    r")\b",
    re.IGNORECASE,
)
_EVIDENCE_TOKEN_RE = re.compile(r"[^A-Za-z0-9_.:+-]+")
_AUDIO_WINDOW_CONTEXT_REQUIRED_ATOMS: tuple[str, ...] = (
    "P1=master_global_mix",
    "P1_heard=true",
    "timeline=past_action_future",
    "deckA_audio=not_attached",
    "deckB_audio=not_attached",
    "per_deck_audio=structured_text_only",
    "duplicate_audio=same_master_not_deck_split",
    "deck_separation=deck_lanes_context",
    "lane_aliases=deck1:A,deck2:B",
    "action=-1.0..0.0",
    "rule=time_alignment_not_outcome_verdict",
)
_AUDIO_WINDOW_CONTEXT_FORBIDDEN_ATOMS: tuple[str, ...] = (
    "deckA_audio=attached",
    "deckB_audio=attached",
    "deckA_audio=stem",
    "deckB_audio=stem",
    "per_deck_audio=attached",
    "isolated_decks=true",
)
_AUDIO_PART_CONTEXT_REQUIRED_ATOMS: tuple[str, ...] = (
    "P1=live_global_mix",
    "P1_runtime_observed=true",
    "P1_audience_heard=true",
    "P1_deck_audio=global_mix_not_stems",
    "deck1=A",
    "deck2=B",
    "together_audio=P1",
    "per_deck_audio=not_attached",
    "duplicate_audio=same_master_not_deck_split",
    "rule=part_labels_not_outcome_verdict",
)
_AUDIO_PART_CONTEXT_FORBIDDEN_ATOMS: tuple[str, ...] = (
    "deckA_audio=attached",
    "deckB_audio=attached",
    "deckA_audio=stem",
    "deckB_audio=stem",
    "per_deck_audio=attached",
    "isolated_decks=true",
    "P1_deck_audio=stems",
    "P2_deck_audio=stems",
    "P3_deck_audio=stems",
)
_DECK_AUDIO_SEPARATION_CONTEXT_REQUIRED_ATOMS: tuple[str, ...] = (
    "deckA_audio=not_captured",
    "deckB_audio=not_captured",
    "current_capture=P1_global_mix",
    "per_deck_audio=not_attached",
    "rule=separation_capability_not_outcome",
)
_DECK_AUDIO_SEPARATION_CONTEXT_FORBIDDEN_ATOMS: tuple[str, ...] = (
    "deckA_audio=attached",
    "deckB_audio=attached",
    "deckA_audio=stem",
    "deckB_audio=stem",
    "per_deck_audio=attached",
    "isolated_decks=true",
)
_HISTORICAL_CITATION_RE = re.compile(
    r"\[(?:ev|aud|midi|track|screen|mix|tend|key|recall|exemplar|cue):[^\]]+\]"
)
_HISTORICAL_AUDIO_WINDOW_RE = re.compile(r"audio_window=(audio_window_context\[[^\]]*\])")
_HISTORICAL_SAID_FIELD_RE = re.compile(
    r"said:\s*([^/]+?)(?=(?:\s*/\s*)|$)",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class LiveClaimGuardResult:
    """Post-model correction result for deck-scoped live outcome claims."""

    text: str
    corrected: bool = False
    policy: str = "requires_more_evidence"
    reason: str | None = None
    summary: str = ""


LIVE_TRANSITION_HELD_REPLY = "I'll hold the transition verdict until live deck proof is stronger."
LIVE_CANDIDATE_HELD_REPLY = (
    "I see a transition candidate; I'll hold the quality grade until stronger "
    "two-deck proof is available."
)
LIVE_MOVE_EFFECT_HELD_REPLY = (
    "I see the control move and audio change; I'll hold the cause/quality "
    "verdict until live proof is stronger."
)


def normalize_audio_window_context_text(raw: object, *, max_len: int = 900) -> str | None:
    """Return trusted ``audio_window_context[...]`` text, or ``None``.

    This validator is shared by Viber preview/proof paths. A raw frame must not
    be allowed to claim isolated deck audio or omit the deck-split limitation.
    If validation fails, callers should recompute a safe packet from state and
    recent moves.
    """
    if raw is None:
        return None
    text = " ".join(str(raw).split())
    if not text:
        return None
    text = text[:max_len]
    if not text.startswith("audio_window_context["):
        return None
    if not all(atom in text for atom in _AUDIO_WINDOW_CONTEXT_REQUIRED_ATOMS):
        return None
    if any(atom in text for atom in _AUDIO_WINDOW_CONTEXT_FORBIDDEN_ATOMS):
        return None
    return text


def normalize_audio_part_context_text(raw: object, *, max_len: int = 900) -> str | None:
    """Return trusted ``audio_part_context[...]`` text, or ``None``."""
    return _normalize_live_context_text(
        raw,
        prefix="audio_part_context",
        required_atoms=_AUDIO_PART_CONTEXT_REQUIRED_ATOMS,
        forbidden_atoms=_AUDIO_PART_CONTEXT_FORBIDDEN_ATOMS,
        max_len=max_len,
    )


def normalize_deck_lanes_context_text(raw: object, *, max_len: int = 900) -> str | None:
    """Return trusted ``deck_lanes_context[...]`` text, or ``None``."""
    return _normalize_live_context_text(
        raw,
        prefix="deck_lanes_context",
        required_atoms=(
            "lane_aliases=deck1:A,deck2:B",
            "rule=per_lane_identity_route_control_not_outcome",
        ),
        forbidden_atoms=("isolated_decks=true", "per_deck_audio=attached"),
        max_len=max_len,
    )


def normalize_deck_reference_context_text(raw: object, *, max_len: int = 900) -> str | None:
    """Return trusted ``deck_reference_context[...]`` text, or ``None``."""
    return _normalize_live_context_text(
        raw,
        prefix="deck_reference_context",
        required_atoms=(
            "deck1=A",
            "deck2=B",
            "audio=P1_global_mix",
            "per_deck_audio=not_attached",
            "isolated_decks=false",
            "rule=deck1_deck2_reference_not_outcome",
        ),
        forbidden_atoms=(
            "isolated_decks=true",
            "per_deck_audio=attached",
            "deckA_audio=attached",
            "deckB_audio=attached",
            "deckA_audio=stem",
            "deckB_audio=stem",
        ),
        max_len=max_len,
    )


def normalize_deck_source_context_text(raw: object, *, max_len: int = 900) -> str | None:
    """Return trusted ``deck_source_context[...]`` text, or ``None``."""
    return _normalize_live_context_text(
        raw,
        prefix="deck_source_context",
        required_atoms=(
            "identity_state=MusicState.deck_state",
            "second_deck=independent_source_required",
            "rule=unresolved_deck_is_not_transition_evidence",
        ),
        forbidden_atoms=(
            "live_db=read",
            "second_deck=inferred",
            "unresolved_deck_is_transition_evidence",
        ),
        max_len=max_len,
    )


def normalize_deck_audio_context_text(raw: object, *, max_len: int = 900) -> str | None:
    """Return trusted ``deck_audio_context[...]`` text, or ``None``."""
    return _normalize_live_context_text(
        raw,
        prefix="deck_audio_context",
        required_atoms=(
            "source=global_mix",
            "isolated_decks=false",
            "rule=audio_heard_must_be_mapped_through_deck_context",
        ),
        forbidden_atoms=(
            "isolated_decks=true",
            "source=deckA",
            "source=deckB",
            "per_deck_audio=attached",
            "deckA_audio=attached",
            "deckB_audio=attached",
            "deckA_audio=stem",
            "deckB_audio=stem",
        ),
        max_len=max_len,
    )


def normalize_deck_audio_separation_context_text(raw: object, *, max_len: int = 900) -> str | None:
    """Return trusted ``deck_audio_separation_context[...]`` text, or ``None``."""
    return _normalize_live_context_text(
        raw,
        prefix="deck_audio_separation_context",
        required_atoms=_DECK_AUDIO_SEPARATION_CONTEXT_REQUIRED_ATOMS,
        forbidden_atoms=_DECK_AUDIO_SEPARATION_CONTEXT_FORBIDDEN_ATOMS,
        max_len=max_len,
    )


def _normalize_live_context_text(
    raw: object,
    *,
    prefix: str,
    required_atoms: tuple[str, ...],
    max_len: int,
    forbidden_atoms: tuple[str, ...] = (),
) -> str | None:
    if raw is None:
        return None
    text = " ".join(str(raw).split())
    if not text:
        return None
    text = text[:max_len]
    if not text.startswith(f"{prefix}["):
        return None
    if not all(atom in text for atom in required_atoms):
        return None
    if any(atom in text for atom in forbidden_atoms):
        return None
    return text


def sanitize_historical_move_signature_for_prompt(
    signature: object,
    *,
    cap: int = 220,
    strip_citations: bool = True,
) -> str:
    """Return a bounded past-session signature that cannot masquerade as live proof.

    Historical memories are useful comparison material, but stale signatures can
    carry old live verdicts or pre-contract audio-window shapes. Keep the move
    and DSP hints, strip copied evidence refs, and normalize audio-window packets
    to the current "master mix, deck lanes are structured text" contract.
    """
    text = " ".join(str(signature).split()).replace("|", " / ")
    if strip_citations:
        text = _HISTORICAL_CITATION_RE.sub("", text)
    text = _sanitize_historical_audio_windows(text)
    text = _sanitize_historical_spoken_outcome_claims(text)
    text = " ".join(text.split())
    if len(text) <= cap:
        return text
    return text[: cap - 3].rstrip() + "..."


def _sanitize_historical_audio_windows(text: str) -> str:
    """Keep old audio-window memory useful while removing unsafe deck-audio shape."""

    def repl(match: re.Match[str]) -> str:
        packet = match.group(1)
        trusted = normalize_audio_window_context_text(packet)
        if trusted:
            return f"audio_window={trusted}"
        if any(atom in packet for atom in _AUDIO_WINDOW_CONTEXT_FORBIDDEN_ATOMS):
            return "audio_window=omitted_untrusted_audio_window"
        if "P1=master_global_mix" not in packet:
            return "audio_window=omitted_untrusted_audio_window"
        return (
            "audio_window=audio_window_context[P1=master_global_mix P1_heard=true "
            "timeline=past_action_future "
            "deckA_audio=not_attached deckB_audio=not_attached "
            "per_deck_audio=structured_text_only "
            "duplicate_audio=same_master_not_deck_split "
            "deck_separation=deck_lanes_context lane_aliases=deck1:A,deck2:B "
            "action=-1.0..0.0 rule=time_alignment_not_outcome_verdict "
            "legacy_context_upgraded=true]"
        )

    return _HISTORICAL_AUDIO_WINDOW_RE.sub(repl, text)


def _sanitize_historical_spoken_outcome_claims(text: str) -> str:
    """Remove stale spoken outcome verdicts from comparison memory."""

    def repl(match: re.Match[str]) -> str:
        said = match.group(1).strip()
        if not has_multi_deck_outcome_claim(said):
            return match.group(0)
        if has_multi_deck_outcome_disclaimer(said) and not has_unsafe_multi_deck_disclaimer_claim(
            said
        ):
            return match.group(0)
        return "said: omitted_past_live_outcome_claim"

    return _HISTORICAL_SAID_FIELD_RE.sub(repl, text)


def render_deck_context(state: MusicState, *, compact: bool = False) -> str | None:
    """Return a bounded ``deck_context[...]`` packet, or ``None`` when cold.

    The cold/default path is intentionally silent: an empty ``DeckState`` means
    the prompt stays byte-identical to the historical no-deck context.
    """
    if not state.deck_state.decks:
        return None

    resolved = _resolved_decks(state.deck_state.decks)
    status = _transition_status(state, resolved)
    resolved_sides = "+".join(sorted(resolved)) if resolved else "none"

    if compact:
        return (
            "deck_context["
            f"audible={state.audible_deck} "
            f"resolved={resolved_sides} "
            f"{_deck_identity_evidence_status(resolved)} "
            f"{status}]"
        )

    fields = [
        f"audible={state.audible_deck}",
        f"deck_conf={state.deck_confidence:.2f}",
        f"resolved={resolved_sides}",
        *_deck_identity_scope(resolved),
        status,
    ]
    if resolved:
        loaded = " | ".join(_deck_summary(side, dt) for side, dt in sorted(resolved.items()))
        fields.append(f"loaded={loaded}")

    return "deck_context[" + " ".join(fields) + "]"


def render_deck_lane_context(state: MusicState, *, compact: bool = False) -> str | None:
    """Return a per-deck lane map combining identity, route, and controls.

    This is the compact "deck one here / deck two here" packet. It does not
    grade the sound; it only names what each deck lane is known to contain and
    how that lane is routed through the controller.
    """
    decks = getattr(state.deck_state, "decks", {})
    if not decks and not getattr(state, "controller_connected", False):
        return None

    resolved = _resolved_decks(decks)
    scores = dict(_deck_route_scores(state))
    sides: set[str] = set()
    if getattr(state, "controller_connected", False) or any(side in decks for side in ("A", "B")):
        sides.update(("A", "B"))
    sides.update(side for side in decks if side in {"A", "B", "C", "D"})
    if not sides:
        return None

    render_lane = _deck_lane_compact_summary if compact else _deck_lane_summary
    lanes = [
        render_lane(state, side, decks.get(side), resolved.get(side), scores.get(side))
        for side in sorted(sides)
    ]
    return (
        "deck_lanes_context["
        + " | ".join(lanes)
        + " lane_aliases=deck1:A,deck2:B"
        + " rule=per_lane_identity_route_control_not_outcome]"
    )


def render_deck_reference_context(state: MusicState, *, compact: bool = False) -> str | None:
    """Return a direct deck1/deck2 reference map for live-agent prompts.

    ``deck_lanes_context`` is optimized for compact policy checks. This packet
    is optimized for the human/agent mental model: "deck one is A, deck two is
    B, here is what each lane currently contains and how it is routed." It still
    says the only attached audio is the global mix; it is not an outcome grade.
    """
    decks = getattr(state.deck_state, "decks", {})
    has_deck_reference = bool(decks) or bool(getattr(state, "controller_connected", False))
    if not has_deck_reference:
        return None

    resolved = _resolved_decks(decks)
    scores = dict(_deck_route_scores(state))
    lanes: list[str] = []
    for alias, side in (("deck1", "A"), ("deck2", "B")):
        lanes.append(
            _deck_reference_lane(
                state,
                alias,
                side,
                decks.get(side),
                resolved.get(side),
                scores.get(side),
                compact=compact,
            )
        )
    fields = [
        *lanes,
        "audio=P1_global_mix",
        "per_deck_audio=not_attached",
        "isolated_decks=false",
        "rule=deck1_deck2_reference_not_outcome",
    ]
    return "deck_reference_context[" + " ".join(fields) + "]"


def render_deck_source_context(state: MusicState, *, compact: bool = False) -> str | None:
    """Return source-ladder honesty for per-deck identity claims.

    This tells the agent why an unknown deck is unknown. The current robust
    live identity source is ``MusicState.deck_state`` populated by the read-only
    deck poller; it may resolve the attributed now-playing track against the
    library cache, but it must not invent a second deck without an independent
    source.
    """
    decks = getattr(state.deck_state, "decks", {})
    has_reference = bool(decks) or bool(getattr(state, "controller_connected", False))
    if not has_reference:
        return None

    resolved = _resolved_decks(decks)
    observed_sides = sorted(side for side in decks if side in {"A", "B", "C", "D"})
    reference_sides = {"A", "B"} if getattr(state, "controller_connected", False) else set()
    reference_sides.update(observed_sides)
    unresolved_sides = sorted(side for side in reference_sides if side not in resolved)
    source_labels = sorted(
        {str(deck.source) for deck in resolved.values() if getattr(deck, "source", None)}
    )

    fields = [
        "identity_state=MusicState.deck_state",
        "primary=nowplaying_controller_attribution_to_library_cache",
        f"resolved={'+'.join(sorted(resolved)) if resolved else 'none'}",
        f"unresolved={'+'.join(unresolved_sides) if unresolved_sides else 'none'}",
        f"sources={'+'.join(source_labels) if source_labels else 'none'}",
    ]
    fields.extend(_deck_source_status_fields(state, compact=compact))
    if not compact:
        fields.extend(
            [
                "source_ladder=rekordbox_xml_or_folder_cache_then_screen_vision_when_enabled",
                "live_db=not_read",
                "event_xml=diagnostic_only",
            ]
        )
    fields.extend(
        [
            "second_deck=independent_source_required",
            "rule=unresolved_deck_is_not_transition_evidence",
        ]
    )
    return "deck_source_context[" + " ".join(fields) + "]"


def _deck_source_status_fields(state: MusicState, *, compact: bool) -> list[str]:
    status = getattr(getattr(state, "deck_state", None), "source_status", {})
    if not isinstance(status, dict) or not status:
        return []
    keys = (
        ("controller", "controller"),
        ("nowplaying", "nowplaying"),
        ("nowplaying_owner", "nowplaying_owner"),
        ("nowplaying_title", "nowplaying_title"),
        ("audible_deck", "source_audible_deck"),
        ("resolution", "resolution"),
        ("resolved_side", "resolved_side"),
    )
    fields: list[str] = []
    for key, label in keys:
        raw = status.get(key)
        if raw is None:
            continue
        token = _evidence_token(str(raw))
        if token:
            fields.append(f"{label}={token}")
    if fields and not compact:
        fields.append("source_status_rule=diagnostic_not_deck_identity")
    return fields


def render_deck_audio_context(state: MusicState) -> str | None:
    """Return the audio-to-deck routing context Gemini should assume.

    The live audio buffer is the booth/master mix, not isolated per-deck stems.
    This packet makes that limitation explicit while still giving the model the
    cheap controller-derived routing reference: which deck is likely dominant,
    muted, or part of a two-deck route.
    """
    has_deck_reference = bool(getattr(state.deck_state, "decks", {})) or bool(
        getattr(state, "controller_connected", False)
    )
    if not has_deck_reference:
        return None
    if not getattr(state, "audible", False) and not getattr(state, "controller_connected", False):
        return None

    fields = [
        f"audio={'audible' if getattr(state, 'audible', False) else 'silent_or_unknown'}",
        "source=global_mix",
        "isolated_decks=false",
    ]
    scores = _deck_route_scores(state)
    if scores:
        fields.append("routing=" + " ".join(_route_summary(side, score) for side, score in scores))
        fields.append("support=" + _route_support(scores))
    elif getattr(state, "controller_connected", False):
        fields.append("routing=unknown")
        fields.append("support=no_controller_audio_route")
    else:
        fields.append("routing=unknown")
        fields.append("support=controller_disconnected")
    fields.append("rule=audio_heard_must_be_mapped_through_deck_context")
    return "deck_audio_context[" + " ".join(fields) + "]"


def render_deck_audio_separation_context(capture: dict[str, object] | None = None) -> str:
    """Return what the live audio capture can and cannot separate by deck.

    This is the anti-hallucination packet for the user's "deck one here, deck
    two here" goal. Deck identity/control can be structured text, but today the
    Gemini/Viber audio Part is still P1 global mix unless a future multichannel
    capture path explicitly attaches deck pairs.
    """
    capture = capture if isinstance(capture, dict) else {}
    requested = _evidence_token(str(capture.get("requested_device") or "unknown")) or "unknown"
    device = _evidence_token(str(capture.get("device_name") or "unknown")) or "unknown"
    input_channels = _capture_channel_token(capture.get("input_channels"))
    opened_channels = _capture_channel_token(capture.get("opened_channels"))
    sample_rate = _capture_channel_token(capture.get("sample_rate"))
    max_in = _capture_int(capture.get("input_channels"))
    opened = _capture_int(capture.get("opened_channels"))
    capacity = (
        "multichannel_available"
        if max_in is not None and max_in >= 4
        else "stereo_or_less"
        if max_in is not None
        else "unknown"
    )
    if opened is not None and opened >= 4:
        mode = "multichannel_open_but_deck_pairs_not_attached"
    elif max_in is not None and max_in >= 4:
        mode = "multichannel_device_available_but_runtime_opened_stereo"
    elif opened is not None and opened <= 2:
        mode = "global_mix_only"
    else:
        mode = "global_mix_or_unknown"
    fields = [
        f"requested_device={requested}",
        f"capture_device={device}",
        f"input_channels={input_channels}",
        f"opened_channels={opened_channels}",
        f"sample_rate={sample_rate}",
        f"device_capacity={capacity}",
        f"mode={mode}",
        "current_capture=P1_global_mix",
        "gemini_audio=mono_downmix_of_capture",
        "deckA_audio=not_captured",
        "deckB_audio=not_captured",
        "per_deck_audio=not_attached",
        "isolated_decks=false",
        "upgrade_path=multi_channel_deck_pair_capture",
        "rule=separation_capability_not_outcome",
    ]
    return "deck_audio_separation_context[" + " ".join(fields) + "]"


def render_audio_window_context(
    state: MusicState,
    moves: list[str] | tuple[str, ...] | None = None,
    *,
    audio_seconds: float = 6.0,
    lookahead_part_label: str | None = None,
    lookahead_horizon_s: float = 3.0,
    force: bool = False,
) -> str | None:
    """Return a temporal map for the attached master-audio window.

    This is the cheap "old part / current move / +3s forward" bridge. It does
    not add another audio Part and it never pretends Deck A/B stems are present.
    Deck separation still comes from ``deck_lanes_context`` and controller
    routing unless a future capture path attaches real isolated deck audio.
    """
    labels = [_move_label(item).strip() for item in (moves or ())]
    labels = [label for label in labels if label][-3:]
    has_reference = bool(
        force
        or labels
        or getattr(state, "audible", False)
        or getattr(state, "controller_connected", False)
        or getattr(state.deck_state, "decks", {})
        or lookahead_part_label
    )
    if not has_reference:
        return None

    try:
        seconds = float(audio_seconds)
    except (TypeError, ValueError):
        seconds = 6.0
    seconds = max(1.0, min(30.0, seconds))
    pre_end = -1.0 if seconds > 1.0 else 0.0

    fields = [
        "P1=master_global_mix",
        "P1_heard=true",
        "timeline=past_action_future",
        "together_audio=P1_global_mix",
        "decks_together=true",
        "deckA_audio=not_attached",
        "deckB_audio=not_attached",
        "per_deck_audio=structured_text_only",
        "duplicate_audio=same_master_not_deck_split",
        "deck_separation=deck_lanes_context",
        "lane_aliases=deck1:A,deck2:B",
        f"pre=-{seconds:.1f}..{pre_end:.1f}",
        "current=-1.0..0.0",
        "action=-1.0..0.0",
        "rule=time_alignment_not_outcome_verdict",
    ]

    anchors: list[str] = []
    for label in labels:
        token = _evidence_token(label) or "move"
        age = _move_age_for_label(state, label)
        if age is None:
            anchors.append(f"{token}@age_unknown")
            continue
        relation = "inside_P1" if age <= seconds else "before_P1"
        anchors.append(f"{token}@-{age:.1f}s:{relation}")
    fields.append("move_anchor=" + (",".join(anchors) if anchors else "none"))

    part_label = _audio_part_label(lookahead_part_label)
    if part_label:
        try:
            horizon = float(lookahead_horizon_s)
        except (TypeError, ValueError):
            horizon = 3.0
        horizon = max(0.1, min(12.0, horizon))
        fields.extend(
            [
                f"{part_label}=source_file_lookahead",
                "future_heard=false",
                f"future=0.0..+{horizon:.1f}",
                "future_rule=forecast_only_not_audience_evidence",
            ]
        )
    else:
        fields.append("future_heard=false")
        fields.append("future=not_attached")

    return "audio_window_context[" + " ".join(fields) + "]"


def render_audio_part_context(
    *,
    audio_seconds: float = 6.0,
    mic_part_label: str | None = None,
    lookahead_part_label: str | None = None,
    lookahead_horizon_s: float = 3.0,
    surface: str = "gemini_parts",
    p1_model_heard: bool = True,
    p1_runtime_observed: bool = True,
) -> str:
    """Return a strict label contract for Gemini audio Parts.

    This is adjacent prompt metadata, not musical evidence. It tells Gemini how
    to interpret the attached Parts before it reasons: P1 is the current live
    master/global mix, optional mic audio is user speech, optional lookahead is
    future source-file reference, and none of the Parts are isolated deck stems.
    """
    try:
        seconds = float(audio_seconds)
    except (TypeError, ValueError):
        seconds = 6.0
    seconds = max(1.0, min(30.0, seconds))

    surface_label = _evidence_token(surface) or "gemini_parts"
    fields = [
        f"surface={surface_label}",
        "P1=live_global_mix",
        f"P1_model_heard={'true' if p1_model_heard else 'false'}",
        f"P1_runtime_observed={'true' if p1_runtime_observed else 'false'}",
        "P1_audience_heard=true",
        f"P1_span=-{seconds:.1f}..0.0",
        "P1_deck_audio=global_mix_not_stems",
        "deck1=A",
        "deck2=B",
        "together_audio=P1",
        "per_deck_audio=not_attached",
        "duplicate_audio=same_master_not_deck_split",
    ]

    mic_label = _audio_part_label(mic_part_label)
    if mic_label:
        fields.extend(
            [
                f"{mic_label}=user_mic",
                f"{mic_label}_model_heard=true",
                f"{mic_label}_role=user_speech",
                f"{mic_label}_deck_audio=none",
                f"{mic_label}_rule=not_deck_audio",
            ]
        )

    lookahead_label = _audio_part_label(lookahead_part_label)
    if lookahead_label:
        try:
            horizon = float(lookahead_horizon_s)
        except (TypeError, ValueError):
            horizon = 3.0
        horizon = max(0.1, min(12.0, horizon))
        fields.extend(
            [
                f"{lookahead_label}=source_file_lookahead",
                f"{lookahead_label}_model_heard=true",
                f"{lookahead_label}_audience_heard=false",
                f"{lookahead_label}_span=0.0..+{horizon:.1f}",
                f"{lookahead_label}_deck_audio=none",
                f"{lookahead_label}_rule=forecast_only_not_current_live_evidence",
            ]
        )

    fields.append("rule=part_labels_not_outcome_verdict")
    return "audio_part_context[" + " ".join(fields) + "]"


def render_audio_window_map(
    state: MusicState,
    moves: list[str] | tuple[str, ...] | None = None,
    *,
    audio_seconds: float = 6.0,
    lookahead_part_label: str | None = None,
    lookahead_horizon_s: float = 3.0,
    force: bool = False,
) -> dict[str, Any] | None:
    """Return the structured twin of ``audio_window_context[...]``.

    This is a cheap context label map, not another audio upload. It makes the
    old/current/future P1 arrangement explicit for UI/Viber transport while the
    text renderer remains the compact Gemini/Viber prompt grammar.
    """
    labels = [_move_label(item).strip() for item in (moves or ())]
    labels = [label for label in labels if label][-3:]
    has_reference = bool(
        force
        or labels
        or getattr(state, "audible", False)
        or getattr(state, "controller_connected", False)
        or getattr(state.deck_state, "decks", {})
        or lookahead_part_label
    )
    if not has_reference:
        return None

    try:
        seconds = float(audio_seconds)
    except (TypeError, ValueError):
        seconds = 6.0
    seconds = max(1.0, min(30.0, seconds))
    pre_end = -1.0 if seconds > 1.0 else 0.0

    anchors: list[dict[str, Any]] = []
    for label in labels:
        token = _evidence_token(label) or "move"
        age = _move_age_for_label(state, label)
        relation = "age_unknown"
        if age is not None:
            relation = "inside_P1" if age <= seconds else "before_P1"
        anchors.append(
            {
                "label": label[:72],
                "token": token[:96],
                "age_s": round(age, 1) if age is not None else None,
                "relation": relation,
            }
        )

    future: dict[str, Any] = {"heard": False, "span": "not_attached"}
    part_label = _audio_part_label(lookahead_part_label)
    if part_label:
        try:
            horizon = float(lookahead_horizon_s)
        except (TypeError, ValueError):
            horizon = 3.0
        horizon = max(0.1, min(12.0, horizon))
        future = {
            "heard": False,
            "part": part_label,
            "source": "source_file_lookahead",
            "span_s": [0.0, round(horizon, 1)],
            "rule": "forecast_only_not_audience_evidence",
        }

    return {
        "p1": "master_global_mix",
        "p1_heard": True,
        "timeline": "past_action_future",
        "together_audio": "P1_global_mix",
        "decks_together": True,
        "deckA_audio": "not_attached",
        "deckB_audio": "not_attached",
        "per_deck_audio": "structured_text_only",
        "duplicate_audio": "same_master_not_deck_split",
        "deck_separation": "deck_lanes_context",
        "lane_aliases": "deck1:A,deck2:B",
        "pre_s": [-round(seconds, 1), round(pre_end, 1)],
        "current_s": [-1.0, 0.0],
        "action_s": [-1.0, 0.0],
        "move_anchors": anchors,
        "future": future,
        "rule": "time_alignment_not_outcome_verdict",
    }


def render_context_feed_contract(
    state: MusicState,
    moves: list[str] | tuple[str, ...] | None = None,
    *,
    surface: str = "live_prompt",
    audio_seconds: float = 6.0,
    force: bool = False,
) -> str | None:
    """Return LLM-facing labels for freshness, cacheability, and cost shape.

    This is not musical evidence. It tells the model how to read the evidence
    packet: deck/controller/audio-window fields are volatile per-turn labels,
    historical memory is comparison material, and static persona/rules are the
    cacheable part. Keeping this as one compact line makes the feed cheaper and
    less ambiguous than prose scattered across prompt surfaces.
    """
    labels = [_move_label(item).strip() for item in (moves or ())]
    labels = [label for label in labels if label]
    has_live_packet = bool(
        force
        or labels
        or getattr(state, "audible", False)
        or getattr(state, "controller_connected", False)
        or getattr(state.deck_state, "decks", {})
        or getattr(state, "audio_delta", None)
    )
    if not has_live_packet:
        return None

    try:
        seconds = float(audio_seconds)
    except (TypeError, ValueError):
        seconds = 6.0
    seconds = max(1.0, min(30.0, seconds))
    surface_label = _evidence_token(surface) or "live_prompt"
    per_turn = (
        "small_text+single_P1_audio"
        if surface_label.startswith("gemini")
        else "small_text_live_context"
    )
    fields = [
        f"surface={surface_label}",
        "labels=deck1:A,deck2:B",
        "sources=MusicState.deck_state+deck_mixer+EvidenceRegistry+perceive_cache",
        "volatile=deck_state+deck_mixer+recent_moves+audio_delta+audio_window",
        "history=past_comparison_not_live_proof",
        "cache=static_persona_rules_only",
        f"per_turn={per_turn}",
        f"ttl=recent_moves_8s+audio_window_{seconds:.0f}s",
        "speed=no_extra_model_pass",
        "rule=label_provenance_freshness_before_reasoning",
    ]
    return "context_feed_contract[" + " ".join(fields) + "]"


def render_move_context(state: MusicState, moves: list[str] | tuple[str, ...]) -> str | None:
    """Return event-local context for controller moves.

    This is the cheap bridge between "a knob moved" and "what deck did that
    affect?" It never grades the move; it only states the deterministic deck
    scope and whether transition language is allowed.
    """
    if not moves:
        return None

    touched_sides = _move_sides(moves)
    controls = _move_controls(moves)
    resolved = _resolved_decks(state.deck_state.decks)
    scope = _move_scope(touched_sides, controls)
    transition = _move_transition_status(state, resolved, scope, controls)

    fields = [
        f"scope={scope}",
        f"sides={'+'.join(sorted(touched_sides)) if touched_sides else 'unknown'}",
        f"controls={'+'.join(sorted(controls)) if controls else 'unknown'}",
        f"audible={state.audible_deck}",
        f"resolved={'+'.join(sorted(resolved)) if resolved else 'none'}",
        transition,
    ]
    return "move_context[" + " ".join(fields) + "]"


def render_deck_change_context(
    state: MusicState,
    moves: list[str] | tuple[str, ...],
) -> str | None:
    """Return moment-local controller history mapped onto deck routing.

    ``recent_moves`` already says what the human touched. This packet adds the
    small missing DJ-context bridge: after that touch, was the affected deck
    muted, present, dominant, or part of a two-deck route? It is a history hint,
    not a grade.
    """
    labels = [_move_label(raw) for raw in moves][-3:]
    labels = [label for label in labels if label]
    if not labels:
        return None

    scores = _deck_route_scores(state)
    support = _route_support(scores) if scores else "route_unknown"
    fields = [
        "window=recent_moves",
        f"support={support}",
        f"audible={state.audible_deck}",
    ]
    changes = [_change_summary(state, label, scores) for label in labels]
    if changes:
        fields.append("changes=" + " | ".join(changes))
    fields.append("rule=history_hint_not_quality_verdict")
    return "deck_change_context[" + " ".join(fields) + "]"


def render_audio_delta_items(
    state: MusicState,
    *,
    cap: int = 4,
    use_cached: bool = True,
) -> list[str]:
    """Return bounded DSP deltas from the existing perceive snapshot."""
    if use_cached:
        cached = getattr(state, "audio_delta", None)
        if isinstance(cached, (list, tuple)) and cached:
            return [str(item) for item in cached if item][:cap]
    if not getattr(state, "audible", False):
        return []
    prev = getattr(state, "prev_perceive", None)
    if not isinstance(prev, dict) or not prev:
        return []
    bands = getattr(state, "bands", {}) if isinstance(getattr(state, "bands", {}), dict) else {}
    candidates = (
        ("sub energy", float(bands.get("sub", 0.0) or 0.0), "sub"),
        ("low energy", float(bands.get("low", 0.0) or 0.0), "low"),
        ("mid energy", float(bands.get("mid", 0.0) or 0.0), "mid"),
        ("high energy", float(bands.get("high", 0.0) or 0.0), "high"),
        ("RMS", float(getattr(state, "rms", 0.0) or 0.0), "rms"),
        ("onset density", float(getattr(state, "onset_density", 0.0) or 0.0), "onset_density"),
    )
    out: list[str] = []
    for label, cur, key in candidates:
        phr = render_delta(label, cur, prev.get(key), floor=DELTA_FLOOR)
        if phr is not None:
            out.append(phr)
        if len(out) >= cap:
            break
    return out


def midi_evidence_key(label: str) -> str:
    """Return a citation-safe key for a controller move label."""
    return _evidence_token(label) or "unknown_move"


def move_evidence_atoms(
    state: MusicState,
    moves: list[str] | tuple[str, ...] | None = None,
) -> list[tuple[str, float]]:
    """Return ``(midi_key, t_session)`` atoms for recent move citations."""
    requested = [_move_label(item) for item in (moves or [])]
    if not requested:
        requested = [_move_label(item) for item in getattr(state, "recent_moves", [])]
    requested = [label for label in requested if label]
    if not requested:
        return []

    atoms: list[tuple[str, float]] = []
    seen: set[tuple[str, float]] = set()
    for label in requested[-4:]:
        age = _move_age_for_label(state, label)
        if age is None or age > 8.0:
            continue
        key = midi_evidence_key(label)
        t_session = max(0.0, float(getattr(state, "set_seconds", 0.0) or 0.0) - age)
        rounded_t = round(t_session, 1)
        ident = (key, rounded_t)
        if ident in seen:
            continue
        seen.add(ident)
        atoms.append((key, rounded_t))
    return atoms


def live_mix_evidence_keys(
    state: MusicState,
    moves: list[str] | tuple[str, ...] | None = None,
    *,
    audio_delta_items: list[str] | tuple[str, ...] | None = None,
) -> list[str]:
    """Return citation-safe ``mix`` evidence keys for current deck grounding."""
    keys: list[str] = []
    scores = _deck_route_scores(state)
    route_key: str | None = None
    if scores:
        keys.append(f"deck_audio_support={_route_support(scores)}")
        route = "+".join(f"{side}_{_route_tier(score)}" for side, score in scores)
        route_key = f"deck_route={route}"

    resolved = _resolved_decks(state.deck_state.decks)
    has_identity_reference = bool(state.deck_state.decks) or bool(
        getattr(state, "controller_connected", False)
    )
    if has_identity_reference:
        keys.append(_transition_status(state, resolved))
        keys.append(_deck_identity_evidence_status(resolved))
    lane_status = _deck_lane_evidence_status(state)
    if lane_status:
        keys.append(lane_status)
    reference_status = _deck_reference_evidence_status(state)
    if reference_status:
        keys.append(reference_status)
    source_status = _deck_source_evidence_status(state)
    if source_status:
        keys.append(source_status)

    labels = [_move_label(item) for item in (moves or [])]
    labels = [label for label in labels if label]
    move_scope_key: str | None = None
    if labels:
        touched_sides = _move_sides(labels)
        controls = _move_controls(labels)
        scope = _move_scope(touched_sides, controls)
        status = _move_transition_status(state, resolved, scope, controls)
        move_scope_key = f"move_scope={scope}"
        keys.append(status)

    if move_scope_key:
        keys.append(move_scope_key)
    deltas = [str(item) for item in (audio_delta_items or render_audio_delta_items(state)) if item]
    prefix = "move_effect" if labels else "audio_delta"
    for delta in deltas[:4]:
        keys.append(f"{prefix}={_evidence_token(delta)}")
    if route_key:
        keys.append(route_key)

    out: list[str] = []
    seen: set[str] = set()
    for key in keys:
        safe_key = _evidence_key(key)
        if safe_key and safe_key not in seen:
            out.append(safe_key)
            seen.add(safe_key)
    return out[:8]


def live_evidence_packet(
    state: MusicState,
    moves: list[str] | tuple[str, ...] | None = None,
    *,
    audio_delta_items: list[str] | tuple[str, ...] | None = None,
) -> dict[str, object]:
    """Return bounded live evidence categories for prompt/socket transport."""
    move_items = tuple(_recent_move_items(state)) if moves is None else tuple(moves)
    mix_keys = live_mix_evidence_keys(
        state,
        move_items,
        audio_delta_items=audio_delta_items,
    )
    midi_atoms = move_evidence_atoms(state, move_items) if move_items else []

    out: dict[str, object] = {}
    if mix_keys:
        out["mix"] = mix_keys[:8]
    if midi_atoms:
        out["midi"] = [
            {"key": key, "t": round(float(t_session), 1)} for key, t_session in midi_atoms[:4]
        ]

    refs: list[str] = []
    for key, t_session in midi_atoms[:4]:
        refs.append(f"midi:{key}@{float(t_session):.1f}")
    refs.extend(f"mix:{key}" for key in mix_keys)
    if refs:
        out["refs"] = refs[:9]
    return out


def render_live_evidence_context(
    state: MusicState,
    moves: list[str] | tuple[str, ...] | None = None,
    *,
    audio_delta_items: list[str] | tuple[str, ...] | None = None,
) -> str | None:
    """Render prompt-readable evidence categories without implying a verdict."""
    packet = live_evidence_packet(
        state,
        moves,
        audio_delta_items=audio_delta_items,
    )
    if not packet:
        return None

    fields: list[str] = []
    refs = packet.get("refs")
    if isinstance(refs, list) and refs:
        fields.append("refs=" + ",".join(str(item) for item in refs[:9]))
    mix = packet.get("mix")
    if isinstance(mix, list) and mix:
        fields.append("mix=" + ",".join(str(item) for item in mix[:8]))
    midi = packet.get("midi")
    if isinstance(midi, list) and midi:
        midi_refs: list[str] = []
        for item in midi[:4]:
            if not isinstance(item, dict):
                continue
            key = item.get("key")
            t_session = item.get("t")
            if isinstance(key, str) and isinstance(t_session, (int, float)):
                midi_refs.append(f"{key}@{float(t_session):.1f}")
        if midi_refs:
            fields.append("midi=" + ",".join(midi_refs))
    if not fields:
        return None
    fields.append("rule=evidence_categories_not_quality_verdict")
    return "live_evidence[" + " ".join(fields) + "]"


def _recent_move_items(state: MusicState, *, max_age_s: float = 8.0) -> list[object]:
    out: list[object] = []
    for item in getattr(state, "recent_moves", []):
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            try:
                if float(item[0]) > max_age_s:
                    continue
            except (TypeError, ValueError):
                continue
        out.append(item)
    return out


def render_grounding_ref_context(
    state: MusicState,
    *,
    registry_snapshot: dict[str, dict[str, tuple[float, ...]]] | None,
    moves: list[str] | tuple[str, ...] | None = None,
) -> str | None:
    """Render exact citable refs that are already present in the registry."""
    if not registry_snapshot:
        return None

    refs: list[str] = []
    for key, target_t in move_evidence_atoms(state, moves):
        observed_t = _matching_observed_time(registry_snapshot, "midi", key, target_t)
        if observed_t is not None:
            refs.append(f"[midi:{key}@{observed_t:.1f}]")

    for key in live_mix_evidence_keys(state, moves or getattr(state, "recent_moves", [])):
        if key in registry_snapshot.get("mix", {}):
            refs.append(f"[mix:{key}]")

    if not refs:
        return None
    return "grounding_refs[" + " ".join(refs[:9]) + "]"


def render_move_effect_context(
    state: MusicState,
    moves: list[str] | tuple[str, ...],
    *,
    audio_delta_items: list[str] | tuple[str, ...] | None = None,
) -> str | None:
    """Return move-scoped DSP deltas without treating them as proof of skill."""
    if not moves:
        return None
    deltas = [str(item) for item in (audio_delta_items or render_audio_delta_items(state)) if item]
    if not deltas:
        return None
    fields = [
        "window=recent_moves",
        f"moves={min(len(moves), 3)}",
        "deltas=" + "; ".join(deltas[:4]),
        "rule=dsp_delta_not_causal_proof",
    ]
    return "move_effect_context[" + " ".join(fields) + "]"


def render_mixer_context(state: MusicState) -> str | None:
    """Return a bounded per-deck controller posture packet.

    This names what the mixer is doing without pretending that the music result
    is known. It is cheap state, not another model pass: deck volume/EQ/filter,
    play flags, crossfader side, and the audible-deck confidence.
    """
    if not getattr(state, "controller_connected", False):
        return None

    parts = [
        f"connected={str(bool(state.controller_connected)).lower()}",
        f"xfader={_xfader_label(_int_0_127(getattr(state, 'xfader', 64), 64))}",
        f"deck_conf={float(getattr(state, 'deck_confidence', 0.0) or 0.0):.2f}",
    ]
    deck_parts: list[str] = []
    for side, attr in (("A", "deck_a"), ("B", "deck_b")):
        raw = getattr(state, attr, None)
        if not isinstance(raw, dict):
            continue
        deck_parts.append(_mixer_deck_summary(side, raw))
    if deck_parts:
        parts.append("decks=" + " | ".join(deck_parts))
    return "mixer_context[" + " ".join(parts) + "]"


def has_multi_deck_outcome_claim(text: str) -> bool:
    """Return True when text promotes a multi-deck musical outcome."""
    return bool(_MULTI_DECK_OUTCOME_RE.search(text) or _MULTI_DECK_PHRASE_RE.search(text))


def has_multi_deck_outcome_disclaimer(text: str) -> bool:
    """Return True when text explicitly withdraws a multi-deck outcome claim."""
    return bool(_MULTI_DECK_DISCLAIMER_RE.search(text))


def has_unsafe_multi_deck_disclaimer_claim(text: str) -> bool:
    """Return True when a self-correction also sneaks in a fresh outcome claim."""
    clauses = re.split(r"[.;:]|\b(?:but|however|though|still)\b", text, flags=re.IGNORECASE)
    for clause in clauses:
        if has_multi_deck_outcome_claim(clause) and not has_multi_deck_outcome_disclaimer(clause):
            return True
    return False


def live_claim_policy(
    state: MusicState,
    moves: list[str] | tuple[str, ...] = (),
) -> tuple[str, str | None]:
    """Return the allowed multi-deck outcome policy for the current evidence.

    The policy is about claim category, not wording. A single-deck move, one
    resolved deck, or a watch-only crossfader case blocks outcome praise even
    if the model uses a synonym like "blend", "drop", or "handoff".
    """
    if not state.deck_state.decks and not moves:
        return "requires_more_evidence", None

    resolved = _resolved_decks(state.deck_state.decks)
    deck_status = _transition_status(state, resolved)
    move_status = None
    if moves:
        touched_sides = _move_sides(moves)
        controls = _move_controls(moves)
        scope = _move_scope(touched_sides, controls)
        move_status = _move_transition_status(state, resolved, scope, controls)

    if "transition_block=" in deck_status:
        return "blocked", deck_status.split("=", 1)[1]
    if move_status is not None and "transition_block=" in move_status:
        return "blocked", move_status.split("=", 1)[1]
    if move_status is not None and "transition_watch=" in move_status:
        return "watch_not_claim", move_status.split("=", 1)[1]
    if "transition_watch=" in deck_status:
        return "watch_not_claim", deck_status.split("=", 1)[1]
    if "transition_candidate=" in deck_status or (
        move_status is not None and "transition_candidate=" in move_status
    ):
        return "candidate_not_verdict", None
    return "requires_more_evidence", None


def should_defer_live_claim_stream(
    state: MusicState,
    moves: list[str] | tuple[str, ...] = (),
) -> bool:
    """Return True when the response must be post-checked before TTS flush."""
    policy, _reason = live_claim_policy(state, moves)
    return policy in {"blocked", "watch_not_claim", "candidate_not_verdict"} or bool(
        moves and render_audio_delta_items(state)
    )


def apply_live_claim_guard(
    text: str,
    state: MusicState,
    moves: list[str] | tuple[str, ...] = (),
    *,
    audio_delta_items: list[str] | tuple[str, ...] | None = None,
) -> LiveClaimGuardResult:
    """Correct unsupported multi-deck outcome claims from live coach text.

    This is a result-boundary guard. The prompt teaches the rule, but this
    catches failures without depending on a specific phrase such as "great
    transition".
    """
    policy, reason = live_claim_policy(state, moves)
    outcome_claim = has_multi_deck_outcome_claim(text)
    effect_deltas = [str(item) for item in (audio_delta_items or render_audio_delta_items(state))]
    effect_claim = bool(
        moves
        and effect_deltas
        and (
            (_MOVE_EFFECT_CONTROL_RE.search(text) and _MOVE_EFFECT_CAUSAL_VERDICT_RE.search(text))
            or _MOVE_EFFECT_BARE_VERDICT_RE.search(text)
        )
    )
    if effect_claim and not _MOVE_EFFECT_DISCLAIMER_RE.search(text):
        summary = _live_guard_summary(state, moves)
        delta_hint = "; ".join(effect_deltas[:2])
        log_summary = summary + (
            f"; DSP deltas around the move: {delta_hint}" if delta_hint else ""
        )
        return LiveClaimGuardResult(
            text=LIVE_MOVE_EFFECT_HELD_REPLY,
            corrected=True,
            policy="move_effect_not_verdict",
            reason="dsp_delta_not_causal_proof",
            summary=log_summary,
        )
    has_disclaimer = bool(outcome_claim and has_multi_deck_outcome_disclaimer(text))
    if has_disclaimer and not has_unsafe_multi_deck_disclaimer_claim(text):
        return LiveClaimGuardResult(text=text, policy=policy, reason=reason)
    if policy == "candidate_not_verdict" and outcome_claim and _MULTI_DECK_VERDICT_RE.search(text):
        summary = _live_guard_summary(state, moves)
        return LiveClaimGuardResult(
            text=LIVE_CANDIDATE_HELD_REPLY,
            corrected=True,
            policy=policy,
            reason=reason,
            summary=summary,
        )

    if policy not in {"blocked", "watch_not_claim"}:
        return LiveClaimGuardResult(text=text, policy=policy, reason=reason)
    if not text.strip() or not outcome_claim:
        return LiveClaimGuardResult(text=text, policy=policy, reason=reason)

    summary = _live_guard_summary(state, moves)
    return LiveClaimGuardResult(
        text=LIVE_TRANSITION_HELD_REPLY,
        corrected=True,
        policy=policy,
        reason=reason,
        summary=summary,
    )


def _resolved_decks(decks: dict[str, DeckTrack]) -> dict[str, DeckTrack]:
    """Decks with enough source confidence to use as prompt context.

    Title/track id proves identity; a normalized key alone is still useful
    deck-panel evidence, but only above the same low prompt floor used by
    ``AICoach.evidence_line`` for audible track names.
    """
    out: dict[str, DeckTrack] = {}
    for side, deck in decks.items():
        if deck.confidence < DECK_CONTEXT_MIN_CONF:
            continue
        if not (deck.title or deck.track_id or deck.camelot):
            continue
        out[side] = deck
    return out


def _transition_status(state: MusicState, resolved: dict[str, DeckTrack]) -> str:
    """A coarse, prompt-readable transition/blend gate."""
    if not resolved:
        return "transition_block=no_resolved_decks"
    if len(resolved) == 1:
        return "transition_block=single_resolved_deck"
    if state.audible_deck == "mix" or _has_two_deck_route_support(state):
        return "transition_candidate=two_resolved_decks_mixing"
    if state.audible_deck in ("A", "B"):
        return f"transition_watch=two_resolved_decks_single_audible_{state.audible_deck}"
    return "transition_watch=two_resolved_decks_audible_unknown"


def _deck_identity_scope(resolved: dict[str, DeckTrack]) -> list[str]:
    """Return prompt fields that separate observed deck identity from guesses."""
    if not resolved:
        return [
            "identity_scope=no_resolved_decks",
            "known_decks=none",
            "second_deck_identity=blocked",
            "identity_rule=do_not_invent_unresolved_decks",
        ]

    known = "+".join(sorted(resolved))
    if len(resolved) == 1:
        return [
            "identity_scope=single_resolved_deck",
            f"known_decks={known}",
            "second_deck_identity=unknown_or_suppressed",
            "identity_rule=do_not_invent_unresolved_decks",
        ]

    return [
        "identity_scope=two_resolved_decks",
        f"known_decks={known}",
        "second_deck_identity=observed",
        "identity_rule=only_name_observed_decks",
    ]


def _deck_identity_evidence_status(resolved: dict[str, DeckTrack]) -> str:
    if not resolved:
        return "second_deck_identity=blocked"
    if len(resolved) == 1:
        return "second_deck_identity=unknown_or_suppressed"
    return "second_deck_identity=observed"


def _deck_lane_evidence_status(state: MusicState) -> str | None:
    decks = getattr(state.deck_state, "decks", {})
    if not decks and not getattr(state, "controller_connected", False):
        return None
    resolved = _resolved_decks(decks)
    scores = dict(_deck_route_scores(state))
    sides: set[str] = set()
    if getattr(state, "controller_connected", False) or any(side in decks for side in ("A", "B")):
        sides.update(("A", "B"))
    sides.update(side for side in decks if side in {"A", "B", "C", "D"})
    if not sides:
        return None
    atoms: list[str] = []
    for side in sorted(sides):
        if side in resolved:
            ident = "known"
        elif side in decks:
            ident = "unresolved"
        else:
            ident = "unknown"
        route = _route_tier(scores[side]) if side in scores else "unknown"
        atoms.append(f"{side}_{ident}_route_{route}")
    return "deck_lanes=" + "+".join(atoms)


def _deck_reference_evidence_status(state: MusicState) -> str | None:
    decks = getattr(state.deck_state, "decks", {})
    if not decks and not getattr(state, "controller_connected", False):
        return None
    resolved = _resolved_decks(decks)
    scores = dict(_deck_route_scores(state))
    atoms: list[str] = []
    for alias, side in (("deck1", "A"), ("deck2", "B")):
        if side in resolved:
            ident = "known"
        elif side in decks:
            ident = "unresolved"
        else:
            ident = "unknown"
        route = _route_tier(scores[side]) if side in scores else "unknown"
        atoms.append(f"{alias}_{side}_{ident}_route_{route}")
    return "deck_reference=" + "+".join(atoms)


def _deck_source_evidence_status(state: MusicState) -> str | None:
    decks = getattr(state.deck_state, "decks", {})
    if not decks and not getattr(state, "controller_connected", False):
        return None
    resolved = _resolved_decks(decks)
    atoms: list[str] = []
    for alias, side in (("deck1", "A"), ("deck2", "B")):
        deck = decks.get(side)
        if side in resolved:
            ident = "known"
            source = resolved[side].source or "unknown"
        elif deck is not None:
            ident = "unresolved"
            source = deck.source or "unknown"
        else:
            ident = "unknown"
            source = "none"
        atoms.append(f"{alias}_{side}_{ident}_src_{_evidence_token(source) or 'unknown'}")
    return "deck_source=" + "+".join(atoms)


def _move_sides(moves: list[str] | tuple[str, ...]) -> set[str]:
    sides: set[str] = set()
    for label in moves:
        sides.update(_MOVE_SIDE_RE.findall(label))
    return sides


def _move_controls(moves: list[str] | tuple[str, ...]) -> set[str]:
    controls: set[str] = set()
    for label in moves:
        if "xfader" in label:
            controls.add("xfader")
        if "_low:" in label:
            controls.add("low")
        if "_mid:" in label:
            controls.add("mid")
        if "_hi:" in label:
            controls.add("hi")
        if "_filter:" in label:
            controls.add("filter")
        if "_play" in label:
            controls.add("play")
        if "_volume:" in label:
            controls.add("volume")
        if "killed" in label:
            controls.add("eq_kill")
    return controls


def _move_label(raw: object) -> str:
    if isinstance(raw, str):
        return raw
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        return str(raw[1])
    return str(raw) if raw is not None else ""


def _audio_part_label(raw: str | None) -> str | None:
    label = str(raw or "").strip().upper()
    if not label:
        return None
    if not re.fullmatch(r"P[2-9][0-9]?", label):
        return None
    return label


def _capture_int(raw: object) -> int | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = int(float(str(raw)))
    except (TypeError, ValueError, OverflowError):
        return None
    if value < 0:
        return None
    return min(value, 128)


def _capture_channel_token(raw: object) -> str:
    value = _capture_int(raw)
    return str(value) if value is not None else "unknown"


def _move_age_for_label(state: MusicState, label: str) -> float | None:
    for raw in getattr(state, "recent_moves", []):
        if not isinstance(raw, (list, tuple)) or len(raw) < 2:
            continue
        if str(raw[1]) != label:
            continue
        try:
            return max(0.0, float(raw[0]))
        except (TypeError, ValueError):
            return None
    return None


def _evidence_token(text: str) -> str:
    token = text.replace("→", "_to_").replace("%", "pct")
    token = _EVIDENCE_TOKEN_RE.sub("_", token)
    token = re.sub(r"_+", "_", token).strip("_")
    return token[:96]


def _evidence_key(text: str) -> str:
    if "=" not in text:
        return _evidence_token(text)
    left, right = text.split("=", 1)
    return f"{_evidence_token(left)}={_evidence_token(right)}"


def _matching_observed_time(
    registry_snapshot: dict[str, dict[str, tuple[float, ...]]],
    source: str,
    key: str,
    target_t: float,
    *,
    tol: float = 1.0,
) -> float | None:
    times = registry_snapshot.get(source, {}).get(key, ())
    if not times:
        return None
    best = min((float(t) for t in times), key=lambda t: abs(t - target_t))
    return best if abs(best - target_t) <= tol else None


def _move_primary_side(label: str) -> str | None:
    match = _MOVE_SIDE_RE.search(label)
    return match.group(1) if match else None


def _move_primary_control(label: str) -> str:
    if "xfader" in label:
        return "xfader"
    for token, control in (
        ("_low:", "low"),
        ("_mid:", "mid"),
        ("_hi:", "hi"),
        ("_filter:", "filter"),
        ("_volume:", "volume"),
        ("_play", "play"),
    ):
        if token in label:
            return control
    return "unknown"


def _move_scope(touched_sides: set[str], controls: set[str]) -> str:
    if "xfader" in controls or len(touched_sides) >= 2:
        return "cross_deck_move"
    if len(touched_sides) == 1:
        return f"single_deck_move_{next(iter(touched_sides))}"
    return "deck_unknown_move"


def _move_transition_status(
    state: MusicState,
    resolved: dict[str, DeckTrack],
    scope: str,
    controls: set[str],
) -> str:
    if not resolved:
        return "transition_block=no_resolved_decks"
    if len(resolved) < 2:
        return "transition_block=single_resolved_deck"
    if not (scope == "cross_deck_move" or "xfader" in controls):
        return "transition_block=single_deck_move"
    if state.audible_deck == "mix" or _has_two_deck_route_support(state):
        return "transition_candidate=two_deck_move_audible_mix"
    return "transition_watch=two_deck_move_single_audible"


def _deck_summary(side: str, deck: DeckTrack) -> str:
    parts = [f"{side}={deck.title!r}" if deck.title else f"{side}=unknown_title"]
    if deck.camelot:
        parts.append(f"key={deck.camelot}")
    if deck.bpm and deck.bpm > 0:
        parts.append(f"bpm={deck.bpm:.0f}")
    parts.append(f"src={deck.source}")
    parts.append(f"conf={deck.confidence:.2f}")
    return " ".join(parts)


def _deck_lane_summary(
    state: MusicState,
    side: str,
    deck: DeckTrack | None,
    resolved_deck: DeckTrack | None,
    route_score: float | None,
) -> str:
    parts: list[str] = []
    if resolved_deck is not None:
        parts.append("identity=known")
        if resolved_deck.title:
            parts.append(f"title={_prompt_quote(resolved_deck.title)}")
        if resolved_deck.camelot:
            parts.append(f"key={resolved_deck.camelot}")
        if resolved_deck.bpm and resolved_deck.bpm > 0:
            parts.append(f"bpm={resolved_deck.bpm:.0f}")
        parts.append(f"src={resolved_deck.source}")
        parts.append(f"conf={resolved_deck.confidence:.2f}")
    elif deck is not None:
        parts.append("identity=unresolved")
        parts.append(f"src={deck.source}")
        parts.append(f"conf={deck.confidence:.2f}")
    else:
        parts.append("identity=unknown")

    parts.append(f"route={_route_tier(route_score) if route_score is not None else 'unknown'}")
    raw = _deck_raw(state, side)
    if raw:
        parts.extend(
            [
                f"vol={_volume_tier(_int_0_127(raw.get('vol'), 0))}",
                f"low={_knob_tier(_int_0_127(raw.get('eq_low'), 64))}",
                f"mid={_knob_tier(_int_0_127(raw.get('eq_mid'), 64))}",
                f"hi={_knob_tier(_int_0_127(raw.get('eq_hi'), 64))}",
                f"filter={_knob_tier(_int_0_127(raw.get('filter'), 64))}",
                f"play={'on' if bool(raw.get('play', False)) else 'off'}",
            ]
        )
    else:
        parts.append("controls=unobserved")
    return f"{side}(" + " ".join(parts) + ")"


def _deck_lane_compact_summary(
    state: MusicState,
    side: str,
    deck: DeckTrack | None,
    resolved_deck: DeckTrack | None,
    route_score: float | None,
) -> str:
    if resolved_deck is not None:
        ident = "known"
    elif deck is not None:
        ident = "unresolved"
    else:
        ident = "unknown"
    route = _route_tier(route_score) if route_score is not None else "unknown"
    return f"{side}={ident}:{route}"


def _deck_reference_lane(
    state: MusicState,
    alias: str,
    side: str,
    deck: DeckTrack | None,
    resolved_deck: DeckTrack | None,
    route_score: float | None,
    *,
    compact: bool,
) -> str:
    if resolved_deck is not None:
        fields = [f"{alias}={side}", "identity=known"]
        if resolved_deck.title:
            fields.append(f"title={_prompt_quote(resolved_deck.title)}")
        if not compact:
            if resolved_deck.camelot:
                fields.append(f"key={resolved_deck.camelot}")
            if resolved_deck.bpm and resolved_deck.bpm > 0:
                fields.append(f"bpm={resolved_deck.bpm:.0f}")
            fields.append(f"src={resolved_deck.source}")
            fields.append(f"conf={resolved_deck.confidence:.2f}")
    elif deck is not None:
        fields = [f"{alias}={side}", "identity=unresolved", f"src={deck.source}"]
        if not compact:
            fields.append(f"conf={deck.confidence:.2f}")
    else:
        fields = [f"{alias}={side}", "identity=unknown"]

    fields.append(f"route={_route_tier(route_score) if route_score is not None else 'unknown'}")
    raw = _deck_raw(state, side)
    if raw:
        fields.extend(
            [
                f"vol={_volume_tier(_int_0_127(raw.get('vol'), 0))}",
                f"low={_knob_tier(_int_0_127(raw.get('eq_low'), 64))}",
                f"mid={_knob_tier(_int_0_127(raw.get('eq_mid'), 64))}",
                f"hi={_knob_tier(_int_0_127(raw.get('eq_hi'), 64))}",
                f"filter={_knob_tier(_int_0_127(raw.get('filter'), 64))}",
                f"play={'on' if bool(raw.get('play', False)) else 'off'}",
            ]
        )
    elif not compact:
        fields.append("controls=unobserved")
    return "(" + " ".join(fields) + ")"


def _prompt_quote(raw: str, *, max_len: int = 48) -> str:
    text = " ".join(str(raw).replace("|", "/").split())[:max_len]
    return repr(text)


def _int_0_127(raw: object, default: int) -> int:
    try:
        value = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(0, min(127, value))


def _knob_tier(value: int) -> str:
    if value < 8:
        return "killed"
    if value < 30:
        return "deep-cut"
    if value < 55:
        return "cut"
    if value <= 73:
        return "flat"
    if value <= 100:
        return "boost"
    return "max"


def _volume_tier(value: int) -> str:
    if value < 8:
        return "closed"
    if value < 48:
        return "low"
    if value <= 80:
        return "mid"
    if value <= 112:
        return "open"
    return "full"


def _xfader_label(value: int) -> str:
    if value < 16:
        return "full-A"
    if value < 48:
        return "A-side"
    if value <= 80:
        return "center"
    if value <= 112:
        return "B-side"
    return "full-B"


def _xfader_factor(side: str, xfader: int) -> float:
    if side == "A":
        if xfader >= 112:
            return 0.0
        if xfader >= 80:
            return 0.3
        if xfader >= 48:
            return 0.7
        return 1.0
    if xfader < 16:
        return 0.0
    if xfader < 48:
        return 0.3
    if xfader <= 80:
        return 0.7
    return 1.0


def _deck_raw(state: MusicState, side: str | None) -> dict:
    if side == "A":
        raw = getattr(state, "deck_a", None)
    elif side == "B":
        raw = getattr(state, "deck_b", None)
    else:
        raw = None
    return raw if isinstance(raw, dict) else {}


def _deck_route_scores(state: MusicState) -> list[tuple[str, float]]:
    if not getattr(state, "controller_connected", False):
        return []
    xfader = _int_0_127(getattr(state, "xfader", 64), 64)
    scores: list[tuple[str, float]] = []
    for side, attr in (("A", "deck_a"), ("B", "deck_b")):
        raw = getattr(state, attr, None)
        if not isinstance(raw, dict):
            scores.append((side, 0.0))
            continue
        volume = _int_0_127(raw.get("vol"), 0) / 127.0
        score = volume * _xfader_factor(side, xfader)
        if volume < 0.1:
            score = 0.0
        scores.append((side, max(0.0, min(1.0, score))))
    return scores


def _route_tier_for(scores: list[tuple[str, float]], side: str | None) -> str:
    if not side:
        return "unknown"
    return _route_tier(dict(scores).get(side, 0.0)) if scores else "unknown"


def _has_two_deck_route_support(state: MusicState) -> bool:
    scores = dict(_deck_route_scores(state))
    return scores.get("A", 0.0) > 0.2 and scores.get("B", 0.0) > 0.2


def _route_tier(score: float) -> str:
    if score <= 0.04:
        return "muted"
    if score < 0.2:
        return "low"
    if score < 0.45:
        return "present"
    return "dominant"


def _route_summary(side: str, score: float) -> str:
    return f"{side}={_route_tier(score)}({score:.2f})"


def _route_support(scores: list[tuple[str, float]]) -> str:
    lookup = dict(scores)
    a_score = lookup.get("A", 0.0)
    b_score = lookup.get("B", 0.0)
    if a_score <= 0.04 and b_score <= 0.04:
        return "no_deck_route"
    if a_score > 0.2 and b_score > 0.2:
        return "two_deck_route"
    if a_score >= b_score:
        return "single_deck_A"
    return "single_deck_B"


def _control_now_tier(raw: dict, control: str) -> str:
    if control == "low":
        return _knob_tier(_int_0_127(raw.get("eq_low"), 64))
    if control == "mid":
        return _knob_tier(_int_0_127(raw.get("eq_mid"), 64))
    if control == "hi":
        return _knob_tier(_int_0_127(raw.get("eq_hi"), 64))
    if control == "filter":
        return _knob_tier(_int_0_127(raw.get("filter"), 64))
    if control == "volume":
        return _volume_tier(_int_0_127(raw.get("vol"), 0))
    if control == "play":
        return "on" if bool(raw.get("play", False)) else "off"
    return "unknown"


def _change_summary(state: MusicState, label: str, scores: list[tuple[str, float]]) -> str:
    control = _move_primary_control(label)
    if control == "xfader":
        xfader = _xfader_label(_int_0_127(getattr(state, "xfader", 64), 64))
        routes = (
            "+".join(f"{side}:{_route_tier(score)}" for side, score in scores)
            if scores
            else "unknown"
        )
        return f"xfader(now={xfader} routes={routes})"

    side = _move_primary_side(label)
    raw = _deck_raw(state, side)
    now = _control_now_tier(raw, control)
    route = _route_tier_for(scores, side)
    deck = side or "unknown"
    return f"{deck}_{control}(now={now} route={route})"


def _mixer_deck_summary(side: str, raw: dict) -> str:
    vol = _int_0_127(raw.get("vol"), 0)
    low = _int_0_127(raw.get("eq_low"), 64)
    mid = _int_0_127(raw.get("eq_mid"), 64)
    hi = _int_0_127(raw.get("eq_hi"), 64)
    filter_value = _int_0_127(raw.get("filter"), 64)
    play = bool(raw.get("play", False))
    return (
        f"{side}(vol={_volume_tier(vol)} low={_knob_tier(low)} "
        f"mid={_knob_tier(mid)} hi={_knob_tier(hi)} "
        f"filter={_knob_tier(filter_value)} play={'on' if play else 'off'})"
    )


def _live_guard_summary(
    state: MusicState,
    moves: list[str] | tuple[str, ...],
) -> str:
    resolved = _resolved_decks(state.deck_state.decks)
    resolved_sides = "+".join(sorted(resolved)) if resolved else "none"
    parts = [
        f"audible deck {state.audible_deck}",
        f"resolved decks={resolved_sides}",
    ]
    if not resolved:
        parts.append("second deck identity=blocked")
    elif len(resolved) == 1:
        parts.append("second deck identity=unknown_or_suppressed")
    else:
        parts.append("second deck identity=observed")
    source_summary = _live_guard_source_summary(state)
    if source_summary:
        parts.append(f"deck source={source_summary}")
    lane_summary = _live_guard_lane_summary(state)
    if lane_summary:
        parts.append(f"deck lanes={lane_summary}")
    if moves:
        move_hint = " | ".join(str(label) for label in moves[-3:])
        parts.append(f"recent control evidence: {move_hint}")
    return "; ".join(parts)


def _live_guard_source_summary(state: MusicState) -> str | None:
    rendered = render_deck_source_context(state, compact=True)
    if not rendered:
        return None
    inner = rendered.removeprefix("deck_source_context[").removesuffix("]")
    fields = [
        field
        for field in inner.split()
        if field.startswith(
            (
                "resolved=",
                "unresolved=",
                "sources=",
                "second_deck=",
                "rule=",
            )
        )
    ]
    return " ".join(fields) or None


def _live_guard_lane_summary(state: MusicState) -> str | None:
    rendered = render_deck_lane_context(state, compact=True)
    if not rendered:
        return None
    inner = rendered.removeprefix("deck_lanes_context[").removesuffix("]")
    inner = inner.replace(" rule=per_lane_identity_route_control_not_outcome", "")
    return inner.replace(" | ", " / ") or None
