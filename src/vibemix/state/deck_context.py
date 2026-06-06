# SPDX-License-Identifier: Apache-2.0
"""Compact prompt context for per-deck grounding.

This module is deliberately pure/read-only. It turns the existing
``MusicState.deck_state`` snapshot into a bounded string that helps the coach
separate "one deck changed" from "two decks are actually in play" without
adding another model call or touching the Rekordbox live database.
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from vibemix.audio.xfade import xfade_gains
from vibemix.intel.eq_move_model import canonical_eq_move, predicted_band_gains
from vibemix.intel.transition_scorer import bpm_folded_delta_pct
from vibemix.state.deck_state import DeckTrack
from vibemix.state.deltas import DELTA_FLOOR, render_delta

if TYPE_CHECKING:  # pragma: no cover - typing-only import
    from vibemix.state.music_state import MusicState


DECK_CONTEXT_MIN_CONF: float = 0.3
DECK_CONTEXT_TRUSTED_SOURCES: frozenset[str] = frozenset(
    {
        "rekordbox_xml",
        "folder_cache",
        "screen_vision",
        "numpy_key",
        "nowplaying",
    }
)
GEMINI_AUDIO_TOKENS_PER_SECOND: int = 32
_MOVE_SIDE_RE = re.compile(r"\b([ABCD])_(?:low|mid|hi|filter|volume|play)")
_XFADER_MOVE_RE = re.compile(
    r"\bxfader\s*(?:→|->)\s*(full-A|A-side|center|B-side|full-B)\b",
    re.IGNORECASE,
)
_XFADER_BUCKET_TO_X: dict[str, float] = {
    "full-A": -1.0,
    "A-side": -0.5,
    "center": 0.0,
    "B-side": 0.5,
    "full-B": 1.0,
}
_XFADER_MIN_SIGNIFICANT_DB = 1.0
_XFADER_MAX_TOKEN_DB = 24
_DECK_RMS_DELTA_RE = re.compile(r"\brms_(rose|fell)_", re.IGNORECASE)
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
    r"came in clean|two separate tracks|two tracks|both tracks|"
    r"brought (?:the )?(?:other|second|incoming) deck in"
    r")\b",
    re.IGNORECASE,
)
_CITATION_ATOM_RE = re.compile(r"\[[a-z][a-z0-9_]*:[^\]]+\]", re.IGNORECASE)
_SINGLE_EVENT_TRANSITION_OUTCOME_RE = re.compile(
    r"\b("
    r"transition(?:ed|ing)?|blend(?:ed|ing)?|mix(?:ed|ing)?|crossfade(?:d|s|ing)?|"
    r"swap(?:ped|ping)?|switch(?:ed|ing)?|segue(?:d|ing)?|handoff|bridge(?:d|ing)?"
    r")\b",
    re.IGNORECASE,
)
_SUB_LAYER_AUDIO_OBSERVATION_RE = re.compile(
    r"\b(sub(?:[- ]?bass)?|low[- ]end|bottom[- ]end|bass|weight|bottom)\b",
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
_LIVE_PUBLIC_DIAGNOSTIC_RE = re.compile(
    r"\b("
    r"i need to correct (?:the|that) live read|resolved decks=|"
    r"live evidence gate:|transition_block=|claim_policy=|"
    r"proof_not_ready|unsupported_live_outcome_claim|guard_violations|"
    r"my bad(?: on| with)? (?:the )?live|"
    r"my mistake(?: on| with)? (?:the )?live|"
    r"bad read on my part|"
    r"i (?:gave|fed) you (?:a )?(?:bad|wrong) (?:live )?read|"
    r"i (?:messed|screwed) up(?: on| with)? (?:the )?live|"
    r"i (?:was|am|'m) wrong(?: about| on| with)? (?:the )?live|"
    r"i (?:got|read) (?:that|this) wrong(?: from| in)? (?:the )?live|"
    r"i (?:overclaimed|over-claimed|falsely claimed)|"
    r"i(?:'m| am| was) (?:being )?(?:stupid|dumb|confused)(?: about| on| with)? "
    r"(?:the )?live|"
    r"i(?:'m| am| was) (?:doing|saying) (?:something )?(?:stupid|dumb|stupidity)"
    r"(?: about| on| with)? (?:the )?live|"
    r"i(?:'m| am) not sure(?: yet)? (?:what happened|from this live read|"
    r"from the live read|about the live read|on the live read)"
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
_JUDGE_BLEND_SCORE_RE = re.compile(
    r"\bblend score\s+([0-9]+(?:\.[0-9]+)?)/1\b",
    re.IGNORECASE,
)
_JUDGE_STRONG_PRAISE_RE = re.compile(
    r"\b("
    r"bomb|lit|huge|massive|insane|perfect|flawless|killer|smashed|nailed|"
    r"seamless|great|amazing|incredible|beautiful|gorgeous|big payoff|peak"
    r")\b",
    re.IGNORECASE,
)
_JUDGE_POSITIVE_PRAISE_RE = re.compile(
    r"\b("
    r"nice|good|clean|smooth|solid|successful|tight|worked|landed"
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
    r"worked|landed|nailed|opened(?:\s+up)?|resolved|sorted|"
    r"cleaner|tighter|muddy|muddier|brighter|darker|wider|widened"
    r")\b",
    re.IGNORECASE,
)
_MOVE_EFFECT_CAUSAL_TEXTURE_RE = re.compile(
    r"\b("
    r"eq|mixer|move|low cut|mid cut|high cut|low boost|mid boost|high boost|"
    r"filter|fader|knob|cut|boost(?:ed)?|kill(?:ed)?|low|lows|mid|high|bass|sub"
    r")\b"
    r"[^.?!]{0,64}\b("
    r"made|caused|turned|left|took|pulled|pushed"
    r")\b"
    r"[^.?!]{0,80}\b("
    r"thin(?:ned|ner|ning)?(?:\s+out)?|boomy|boomier|boom|"
    r"weight(?:ier|y)?|heavy|heavier|lost\s+weight|(?:the\s+)?weight\s+out"
    r")\b",
    re.IGNORECASE,
)
_MOVE_EFFECT_TEXTURE_FELL_RE = re.compile(
    r"\b("
    r"thin(?:ned|ner|ning)?(?:\s+out)?|lost\s+weight|(?:the\s+)?weight\s+out"
    r")\b",
    re.IGNORECASE,
)
_MOVE_EFFECT_TEXTURE_ROSE_RE = re.compile(
    r"\b("
    r"boomy|boomier|boom|weighty|weightier|heavy|heavier"
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
_AUDIO_BAND_DELTA_RE = re.compile(
    r"\b(sub|low|mid|high) energy (rose|fell)\b",
    re.IGNORECASE,
)
_MOVE_EFFECT_MIN_PREDICTED_DB = 1.0
_LIVE_AUDIO_SOURCE_DETAIL_NOUN_RE = re.compile(
    r"\b("
    r"vocal|vocals|voice|lyric|lyrics|kick|kickdrum|kick drum|snare|clap|"
    r"hi[- ]?hat|hat|hats|drum|drums|bassline|lead|synth|pad|stem|stems|"
    r"acapella|instrumental"
    r")\b",
    re.IGNORECASE,
)
_LIVE_AUDIO_SOURCE_DETAIL_CLAIM_RE = re.compile(
    r"\b("
    r"hear|heard|hearing|sounds?|feels?|opened(?:\s+up)?|opening|"
    r"tight(?:ened|er|ening)?|clean(?:ed|er)?|clear(?:ed|er)?|brighter|"
    r"darker|wider|punch(?:y|ier)|muddy|muddier|landed|came in|sits?|"
    r"cut(?:s|ting)? through|present|up front|flood(?:ed|ing)?"
    r")\b",
    re.IGNORECASE,
)
_LIVE_AUDIO_SOURCE_DETAIL_BOUNDARY_RE = re.compile(
    r"\b("
    r"can't tell|cannot tell|can't say|cannot say|not enough proof|not proof|"
    r"don't have proof|do not have proof|won't claim|will not claim|"
    r"not source[- ]level proof|not stem proof|not isolated"
    r")\b",
    re.IGNORECASE,
)
_LIVE_AUDIO_SOURCE_DETAIL_TAIL_RE = re.compile(
    r"\s+\b(?:under|over|behind|around|through|from|against)\b\s+"
    r"[^\[.?!;]*\b("
    r"vocal|vocals|voice|lyric|lyrics|snare|clap|hi[- ]?hat|hat|hats|"
    r"drum|drums|bassline|lead|synth|pad|stem|stems|acapella|instrumental"
    r")\b[^\[.?!;]*",
    re.IGNORECASE,
)
_LIVE_AUDIO_SOURCE_DETAIL_ADVICE_RE = re.compile(
    r"(?:\s*[,;]\s*)?(?:\b(?:now|then|so)\b\s+)?\b"
    r"(?:bring|add|layer|drop|pull|mix|blend|cue)\b"
    r"[^.?!]{0,44}\b(?P<noun>"
    r"vocal|vocals|voice|lyric|lyrics|kick|kickdrum|kick drum|snare|clap|"
    r"hi[- ]?hat|hat|hats|drum|drums|bassline|lead|synth|pad|stem|stems|"
    r"acapella|instrumental"
    r")\b",
    re.IGNORECASE,
)
_LIVE_AUDIO_KICK_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "KICK_SWAP",
        "KICK_DENSITY_SHIFT",
        "BREAKDOWN_KICK_KILL",
        "REENTRY_KICK_LAND",
    }
)
_LIVE_CLAIM_DEFER_AUTO_EVENTS: frozenset[str] = _LIVE_AUDIO_KICK_EVENT_TYPES | frozenset(
    {"PHRASE_BOUNDARY", "SUB_LAYER_ARRIVAL"}
)
_LIVE_AUDIO_VOCAL_NOUNS: frozenset[str] = frozenset(
    {"vocal", "vocals", "voice", "lyric", "lyrics", "acapella"}
)
_LIVE_AUDIO_KICK_NOUNS: frozenset[str] = frozenset({"kick", "kickdrum", "kick drum"})
_NO_MOVE_CONTROL_ACTION_RE = re.compile(
    r"\byou\b[^.?!]{0,32}\b("
    r"brought|pulled|pushed|raised|dropped|cut|killed|boosted|opened|closed|swept"
    r")\b[^.?!]{0,32}\b("
    r"fader|faders|low|lows|mid|mids|high|highs|hi|bass|sub|eq|filter|"
    r"high[- ]?pass|low[- ]?pass|gain|trim|volume|knob|it|that|them"
    r")\b",
    re.IGNORECASE,
)
_NO_MOVE_CONTROL_NOUN_RE = re.compile(
    r"\bthat\b[^.?!]{0,24}\b("
    r"eq|filter|low|high|fader|kill|cut|move|low cut|high cut"
    r")\b[^.?!]{0,32}\b("
    r"cleaned|cleared|fixed|tightened|improved|saved|caused|made|opened|sorted|"
    r"landed|worked|paid\s+off"
    r")\b",
    re.IGNORECASE,
)
_NO_MOVE_CONTROL_INSTRUCTION_RE = re.compile(
    r"\b("
    r"bring|pull|push|take|move|set"
    r")\b[^.?!]{0,32}\b("
    r"high[- ]?pass|low[- ]?pass|filter|fader|eq|low|high|mid|gain"
    r")\b[^.?!]{0,32}\b(back|down|up|to)\b",
    re.IGNORECASE,
)
_NO_MOVE_CONTROL_ABSENCE_RE = re.compile(
    r"\byou\b[^.?!]{0,24}\b("
    r"didn['’]?t|did\s+not|haven['’]?t|have\s+not|never"
    r")\b[^.?!]{0,24}\b("
    r"touch|move|adjust|ride|work|use"
    r")\b[^.?!]{0,32}\b("
    r"controller|controls?|mixer|deck|fader|faders|eq|knob|knobs|filter"
    r")\b",
    re.IGNORECASE,
)
_NO_MOVE_COACHING_ADVICE_RE = re.compile(
    r"\b("
    r"try\b[^.?!]{0,48}\b(?:next time|later|earlier|on the|at the|for the|"
    r"cut|kill|ride|wait|hold|bring|release|tighten|cleaner|one|1|8 bars?)|"
    r"next time|wait\s+\d+\s+bars?|"
    r"tighten(?:\s+(?:it|that|the|your))?|"
    r"ride(?:\s+(?:it|that|the|your|low|lows|bass|sub))?|"
    r"bring\b[^.?!]{0,32}\bback|"
    r"hold\b[^.?!]{0,32}\blonger|"
    r"cut\b[^.?!]{0,32}\bcleaner|"
    r"kill\b[^.?!]{0,32}\bnext time|"
    r"release\b[^.?!]{0,32}\b(?:on|at)\s+(?:the\s+)?(?:1|one)"
    r")\b",
    re.IGNORECASE,
)
_UNSUPPORTED_TRANSITION_COACHING_RE = re.compile(
    r"\b("
    r"kicks?\b[^.?!]{0,56}\b(?:step(?:ped|ping)?|clash(?:ed|ing)?|collid(?:ed|ing)|"
    r"fight(?:ing)?|flam(?:med|ming)?|phase(?:d)?|double(?:d)?)|"
    r"(?:tighten|clean|fix|lock|line)\b[^.?!]{0,48}\b(?:sync|beatmatch|beat match|phase)|"
    r"(?:sync|beatmatch|beat match|phase)\b[^.?!]{0,48}\b(?:before|next time|tighter|"
    r"off|late|early|mismatch|matched|lock)|"
    r"(?:half[- ]?bar|one[- ]?beat|1[- ]?beat|phrase)\b[^.?!]{0,40}\b(?:off|late|early|"
    r"mismatch)"
    r")\b",
    re.IGNORECASE,
)
_HARMONIC_DECK_CLAIM_RE = re.compile(
    r"\b("
    r"harmonic\s+clash|key\s+clash|key\s+compatibility|compatible\s+keys|"
    r"incompatible\s+keys|camelot|semitones?|major\s+harmonic\s+clash|"
    r"keys?\b[^.?!]{0,48}\b(?:clash(?:ed|ing)?|compatible|incompatible|fight(?:ing)?)|"
    r"harmonic\b[^.?!]{0,48}\b(?:clash(?:ed|ing)?|compatible|incompatible)"
    r")\b",
    re.IGNORECASE,
)
_MIXER_LOW_KILL_CLAIM_RE = re.compile(
    r"\b(?:eq|mixer|move|it|that|you)\b[^.?!]{0,80}\bkilled\s+(?:the\s+)?(?:low|lows|bass|sub)\b|"
    r"\b(?:low|lows|bass|sub)\b[^.?!]{0,40}\b(?:was|were|got|is|are)?\s*killed\b",
    re.IGNORECASE,
)
_MIXER_LOW_KILL_NEGATION_RE = re.compile(
    r"\b(?:not|no|never|didn't|didnt|doesn't|doesnt|without)\b[^.?!]{0,32}\bkilled\b",
    re.IGNORECASE,
)
_TRACK_CITATION_RE = re.compile(r"\[track:[^\]]+\]", re.IGNORECASE)
_TRACK_IDENTITY_QUOTED_RE = re.compile(
    r"\b(?:track|song|tune|record|id)\b[^.?!]{0,36}[\"'`]([^\"'`]{3,})[\"'`]",
    re.IGNORECASE,
)
_TRACK_IDENTITY_CALLED_RE = re.compile(
    r"\b(?:track|song|tune|record|id)\b[^.?!]{0,24}\b(?:called|named)\b[^.?!]{0,64}",
    re.IGNORECASE,
)
_TRACK_IDENTITY_BY_RE = re.compile(
    r"\b[A-Z][A-Za-z0-9&'.,:/+-]{1,}(?:\s+[A-Z][A-Za-z0-9&'.,:/+-]{1,}){0,8}"
    r"\s+by\s+[A-Z][A-Za-z0-9&'.,:/+-]{1,}",
)
_TRACK_IDENTITY_NAME_WORD = r"(?:[A-Z0-9][\w&'.,:/+()[\]]{1,}|[A-Z]{2,})"
_TRACK_IDENTITY_NAME_PHRASE = (
    rf"{_TRACK_IDENTITY_NAME_WORD}(?:\s+{_TRACK_IDENTITY_NAME_WORD}){{0,8}}"
)
_TRACK_IDENTITY_DASHED_RE = re.compile(
    rf"(?:"
    rf"(?i:\b(?:this\s+(?:is|was)|that(?:'s|\s+is|\s+was)|sounds?\s+like|"
    rf"hearing|playing|track|song|tune|record|id)\b)"
    rf"[^.?!]{{0,36}}\b{_TRACK_IDENTITY_NAME_PHRASE}\s*(?:-|\u2013|\u2014)\s*"
    rf"{_TRACK_IDENTITY_NAME_PHRASE}"
    rf"|"
    rf"\b{_TRACK_IDENTITY_NAME_PHRASE}\s*(?:-|\u2013|\u2014)\s*"
    rf"{_TRACK_IDENTITY_NAME_PHRASE}\b[^.?!]{{0,32}}"
    rf"(?i:\b(?:is|was|just)?\s*(?:playing|loaded|coming\s+in|running|on\s+now)\b)"
    rf")"
)
_EVIDENCE_TOKEN_RE = re.compile(r"[^A-Za-z0-9_.:+-]+")
_AUDIO_WINDOW_CONTEXT_REQUIRED_ATOMS: tuple[str, ...] = (
    "P1=master_global_mix",
    "P1_heard=",
    "timeline=past_action_future",
    "deck_separation=deck_lanes_context",
    "lane_aliases=deck1:A,deck2:B",
    "action=-1.0..0.0",
    "rule=time_alignment_not_outcome_verdict",
)
_AUDIO_WINDOW_CONTEXT_SHAPES: tuple[tuple[str, ...], ...] = (
    (
        "deckA_audio=not_attached",
        "deckB_audio=not_attached",
        "per_deck_audio=structured_text_only",
        "duplicate_audio=same_master_not_deck_split",
    ),
    (
        "per_deck_audio=deck_pair_parts",
        "duplicate_audio=separate_deck_pair_parts",
        "deck_audio_separation=deck_audio_separation_context",
    ),
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
    "P1_audience_heard=",
    "P1_deck_audio=global_mix_not_stems",
    "deck1=A",
    "deck2=B",
    "together_audio=P1",
    "rule=part_labels_not_outcome_verdict",
)
_AUDIO_PART_CONTEXT_SHAPES: tuple[tuple[str, ...], ...] = (
    (
        "per_deck_audio=not_attached",
        "duplicate_audio=same_master_not_deck_split",
    ),
    (
        "per_deck_audio=deck_pair_parts",
        "duplicate_audio=separate_deck_pair_parts",
    ),
)
_AUDIO_PART_CONTEXT_FORBIDDEN_ATOMS: tuple[str, ...] = (
    "deckA_audio=attached",
    "deckB_audio=attached",
    "deckA_audio=stem",
    "deckB_audio=stem",
    "isolated_decks=true",
    "P1_deck_audio=stems",
    "deck_audio=stems",
)
_DECK_AUDIO_SEPARATION_CONTEXT_REQUIRED_ATOMS: tuple[str, ...] = (
    "rule=separation_capability_not_outcome",
)
_DECK_AUDIO_SEPARATION_CONTEXT_SHAPES: tuple[tuple[str, ...], ...] = (
    (
        "deckA_audio=not_captured",
        "deckB_audio=not_captured",
        "current_capture=P1_global_mix",
        "per_deck_audio=not_attached",
        "isolated_decks=false",
    ),
    (
        "deckA_audio=captured",
        "deckB_audio=captured",
        "current_capture=P1_global_mix_plus_deck_pairs",
        "per_deck_audio=captured_not_attached",
        "isolated_decks=runtime_capture_available",
    ),
    (
        "deckA_audio=captured_unverified",
        "deckB_audio=captured_unverified",
        "current_capture=P1_global_mix_plus_unverified_deck_pairs",
        "per_deck_audio=unverified_not_attached",
        "isolated_decks=false",
    ),
)
_DECK_AUDIO_SEPARATION_CONTEXT_FORBIDDEN_ATOMS: tuple[str, ...] = (
    "deckA_audio=attached",
    "deckB_audio=attached",
    "deckA_audio=stem",
    "deckB_audio=stem",
    "per_deck_audio=attached",
    "isolated_decks=true",
)
_DECK_AUDIO_FEATURES_CONTEXT_REQUIRED_ATOMS: tuple[str, ...] = (
    "source=deck_pair_capture",
    "per_deck_audio=captured_features",
    "rule=deck_audio_features_not_outcome_verdict",
)
_DECK_AUDIO_FEATURES_CONTEXT_FORBIDDEN_ATOMS: tuple[str, ...] = (
    "transition_verdict=",
    "quality_verdict=",
    "great_transition",
    "clean_transition",
)
_DECK_AUDIO_DELTA_CONTEXT_REQUIRED_ATOMS: tuple[str, ...] = (
    "source=deck_pair_capture",
    "per_deck_delta=captured_feature_delta",
    "rule=deck_audio_delta_not_causal_proof",
)
_DECK_AUDIO_DELTA_CONTEXT_FORBIDDEN_ATOMS: tuple[str, ...] = (
    "transition_verdict=",
    "quality_verdict=",
    "caused_by_move=true",
    "great_transition",
    "clean_transition",
)
_DECK_AUDIO_WINDOW_CONTEXT_REQUIRED_ATOMS: tuple[str, ...] = (
    "source=deck_pair_capture",
    "timeline=pre_action_current",
    "per_deck_audio=captured_window_features",
    "rule=deck_audio_window_not_causal_or_quality_verdict",
)
_DECK_AUDIO_WINDOW_CONTEXT_FORBIDDEN_ATOMS: tuple[str, ...] = (
    "transition_verdict=",
    "quality_verdict=",
    "caused_by_move=true",
    "great_transition",
    "clean_transition",
)
_SET_WINDOW_CONTEXT_REQUIRED_ATOMS: tuple[str, ...] = (
    "audio_attached=P1_only_last_60-90s",
    "history=structured_text_only",
    "per_deck_audio=not_attached",
    "isolated_decks=false",
    "rule=long_window_is_structured_history_not_audio_proof",
)
_SET_WINDOW_CONTEXT_FORBIDDEN_ATOMS: tuple[str, ...] = (
    "deckA_audio=attached",
    "deckB_audio=attached",
    "deckA_audio=stem",
    "deckB_audio=stem",
    "deckA_audio=captured",
    "deckB_audio=captured",
    "per_deck_audio=attached",
    "per_deck_audio=deck_pair_parts",
    "isolated_decks=true",
    "transition_verdict=",
    "quality_verdict=",
)
_HISTORICAL_CITATION_RE = re.compile(
    r"\[(?:ev|aud|midi|track|screen|mix|key|recall|exemplar|cue):[^\]]+\]"
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
    emit_corrected: bool = False
    policy: str = "requires_more_evidence"
    reason: str | None = None
    summary: str = ""


@dataclass(frozen=True, slots=True)
class MoveEffectLicense:
    """A narrow proof that a move prediction and measured audio delta agree."""

    move: str
    band: str
    predicted_db: float
    measured_direction: str
    evidence_key: str
    context_token: str


LIVE_TRANSITION_HELD_REPLY = (
    "I can't call that a transition until I have clear two-deck proof."
)
LIVE_CANDIDATE_HELD_REPLY = (
    "That is only a transition candidate; I need clear two-deck proof before I grade it."
)
LIVE_MOVE_EFFECT_HELD_REPLY = (
    "I can't tell from this live proof whether the control caused that."
)
LIVE_COACHING_ADVICE_HELD_REPLY = (
    "I can't give coaching advice from this live proof."
)
LIVE_AUDIO_SOURCE_DETAIL_HELD_REPLY = (
    "I only have a broad listener read from the audio here, not source-level proof."
)
LIVE_TRACK_IDENTITY_HELD_REPLY = (
    "I can hear the sound, but I need a citable track match before naming the tune."
)
LIVE_JUDGE_OVERPRAISE_HELD_REPLY = (
    "The measured Judge read was restrained there. The useful note is the evidence, not a hype grade."
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
    if not any(all(atom in text for atom in shape) for shape in _AUDIO_WINDOW_CONTEXT_SHAPES):
        return None
    if not re.search(r"\bP1_heard=(?:true|false)\b", text):
        return None
    if "per_deck_audio=deck_pair_parts" in text and not _audio_window_deck_labels_are_valid(
        text
    ):
        return None
    if any(atom in text for atom in _AUDIO_WINDOW_CONTEXT_FORBIDDEN_ATOMS):
        return None
    return text


def _audio_window_deck_labels_are_valid(text: str) -> bool:
    deck_a = re.search(r"\bdeckA_audio=(P[2-9][0-9]?)\b", text)
    deck_b = re.search(r"\bdeckB_audio=(P[2-9][0-9]?)\b", text)
    if not deck_a or not deck_b:
        return False
    return deck_a.group(1) != deck_b.group(1)


def normalize_audio_part_context_text(raw: object, *, max_len: int = 1400) -> str | None:
    """Return trusted ``audio_part_context[...]`` text, or ``None``."""
    text = _normalize_live_context_text(
        raw,
        prefix="audio_part_context",
        required_atoms=_AUDIO_PART_CONTEXT_REQUIRED_ATOMS,
        forbidden_atoms=_AUDIO_PART_CONTEXT_FORBIDDEN_ATOMS,
        max_len=max_len,
    )
    if text is None:
        return None
    if not re.search(r"\bP1_audience_heard=(?:true|false)\b", text):
        return None
    if not any(all(atom in text for atom in shape) for shape in _AUDIO_PART_CONTEXT_SHAPES):
        return None
    if "per_deck_audio=not_attached" in text:
        if re.search(r"\bdeck[AB]_part=P[2-9][0-9]?\b", text):
            return None
    if "per_deck_audio=deck_pair_parts" in text and not _audio_part_deck_pair_map_is_valid(
        text
    ):
        return None
    return text


def _audio_part_deck_pair_map_is_valid(text: str) -> bool:
    """Return True when Deck A/B part labels are complete and non-conflicting."""
    deck_labels: dict[str, str] = {}
    for side in ("A", "B"):
        match = re.search(rf"\bdeck{side}_part=(P[2-9][0-9]?)\b", text)
        if not match:
            return False
        deck_labels[side] = match.group(1)
    if deck_labels["A"] == deck_labels["B"]:
        return False

    part_order = _audio_part_order(text)
    if part_order is None:
        return False
    if part_order[0] != "P1" or len(part_order) != len(set(part_order)):
        return False
    if part_order != sorted(part_order, key=lambda label: int(label[1:])):
        return False
    if not all(label in part_order for label in deck_labels.values()):
        return False

    for side, label in deck_labels.items():
        expected_role = f"deck{side}_configured_capture"
        required_atoms = (
            f"deck{side}_part={label}",
            f"{label}={expected_role}",
            f"{label}_model_heard=true",
            f"{label}_audience_heard=false",
            f"{label}_deck_audio={expected_role}",
            f"{label}_rule=deck_pair_capture_reference_not_quality_verdict",
        )
        if not all(_audio_part_has_atom(text, atom) for atom in required_atoms):
            return False
        roles = set(re.findall(rf"\b{re.escape(label)}=([A-Za-z0-9_]+)\b", text))
        if roles != {expected_role}:
            return False
    return True


def _audio_part_order(text: str) -> list[str] | None:
    match = re.search(r"\bpart_order=(P1(?:,P[2-9][0-9]?)*)\b", text)
    if not match:
        return None
    return match.group(1).split(",")


def _audio_part_has_atom(text: str, atom: str) -> bool:
    haystack = " " + text.replace("[", " ").replace("]", " ") + " "
    return f" {atom} " in haystack


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


def normalize_deck_audio_separation_context_text(raw: object, *, max_len: int = 1200) -> str | None:
    """Return trusted ``deck_audio_separation_context[...]`` text, or ``None``."""
    text = _normalize_live_context_text(
        raw,
        prefix="deck_audio_separation_context",
        required_atoms=_DECK_AUDIO_SEPARATION_CONTEXT_REQUIRED_ATOMS,
        forbidden_atoms=_DECK_AUDIO_SEPARATION_CONTEXT_FORBIDDEN_ATOMS,
        max_len=max_len,
    )
    if text is None:
        return None
    if not any(
        all(atom in text for atom in shape) for shape in _DECK_AUDIO_SEPARATION_CONTEXT_SHAPES
    ):
        return None
    return text


def normalize_deck_audio_features_context_text(raw: object, *, max_len: int = 900) -> str | None:
    """Return trusted ``deck_audio_features_context[...]`` text, or ``None``."""
    text = _normalize_live_context_text(
        raw,
        prefix="deck_audio_features_context",
        required_atoms=_DECK_AUDIO_FEATURES_CONTEXT_REQUIRED_ATOMS,
        forbidden_atoms=_DECK_AUDIO_FEATURES_CONTEXT_FORBIDDEN_ATOMS,
        max_len=max_len,
    )
    if text is None:
        return None
    if not any(f"{side}_activity=" in text and f"{side}_rms=" in text for side in ("A", "B")):
        return None
    return text


def normalize_deck_audio_delta_context_text(raw: object, *, max_len: int = 900) -> str | None:
    """Return trusted ``deck_audio_delta_context[...]`` text, or ``None``."""
    text = _normalize_live_context_text(
        raw,
        prefix="deck_audio_delta_context",
        required_atoms=_DECK_AUDIO_DELTA_CONTEXT_REQUIRED_ATOMS,
        forbidden_atoms=_DECK_AUDIO_DELTA_CONTEXT_FORBIDDEN_ATOMS,
        max_len=max_len,
    )
    if text is None:
        return None
    if not any(f"{side}_delta=" in text for side in ("A", "B")):
        return None
    return text


def normalize_set_window_context_text(raw: object, *, max_len: int = 1400) -> str | None:
    """Return trusted ``set_window_context[...]`` text, or ``None``."""
    return _normalize_live_context_text(
        raw,
        prefix="set_window_context",
        required_atoms=_SET_WINDOW_CONTEXT_REQUIRED_ATOMS,
        forbidden_atoms=_SET_WINDOW_CONTEXT_FORBIDDEN_ATOMS,
        max_len=max_len,
    )


def normalize_deck_audio_window_context_text(raw: object, *, max_len: int = 1100) -> str | None:
    """Return trusted ``deck_audio_window_context[...]`` text, or ``None``."""
    text = _normalize_live_context_text(
        raw,
        prefix="deck_audio_window_context",
        required_atoms=_DECK_AUDIO_WINDOW_CONTEXT_REQUIRED_ATOMS,
        forbidden_atoms=_DECK_AUDIO_WINDOW_CONTEXT_FORBIDDEN_ATOMS,
        max_len=max_len,
    )
    if text is None:
        return None
    if not any(f"{side}_current=" in text for side in ("A", "B")):
        return None
    return text


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
        tempo_bridge = _tempo_bridge_context(resolved)
        tempo_field = f" {tempo_bridge}" if tempo_bridge else ""
        return (
            "deck_context["
            f"audible={state.audible_deck} "
            f"resolved={resolved_sides} "
            f"{_deck_identity_evidence_status(resolved)} "
            f"{status}{tempo_field}]"
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
    tempo_bridge = _tempo_bridge_context(resolved)
    if tempo_bridge:
        fields.append(tempo_bridge)

    return "deck_context[" + " ".join(fields) + "]"


def render_deck_lane_context(state: MusicState, *, compact: bool = False) -> str | None:
    """Return a per-deck lane map combining identity, route, and controls.

    This is the compact "deck one here / deck two here" packet. It does not
    grade the sound; it only names what each deck lane is known to contain and
    how that lane is routed through the controller.
    """
    decks = getattr(state.deck_state, "decks", {})
    source_status = getattr(getattr(state, "deck_state", None), "source_status", {})
    if not decks and not getattr(state, "controller_connected", False) and not source_status:
        return None

    resolved = _resolved_decks(decks)
    scores = dict(_deck_route_scores(state))
    sides: set[str] = set()
    if (
        getattr(state, "controller_connected", False)
        or source_status
        or any(side in decks for side in ("A", "B"))
    ):
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
    source_status = getattr(getattr(state, "deck_state", None), "source_status", {})
    has_deck_reference = (
        bool(decks) or bool(getattr(state, "controller_connected", False)) or bool(source_status)
    )
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
    source_status = getattr(getattr(state, "deck_state", None), "source_status", {})
    has_reference = (
        bool(decks)
        or bool(getattr(state, "controller_connected", False))
        or bool(source_status)
    )
    if not has_reference:
        return None

    resolved = _resolved_decks(decks)
    observed_sides = sorted(side for side in decks if side in {"A", "B", "C", "D"})
    source_controller_connected = (
        str(source_status.get("controller_connection") or "").lower() == "connected"
    )
    reference_sides = (
        {"A", "B"}
        if getattr(state, "controller_connected", False) or source_controller_connected
        else set()
    )
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
        ("controller_connection", "controller_connection"),
        ("library", "library"),
        ("library_tracks", "library_tracks"),
        ("library_source", "library_source"),
        ("library_match", "library_match"),
        ("nowplaying", "nowplaying"),
        ("nowplaying_owner", "nowplaying_owner"),
        ("nowplaying_title", "nowplaying_title"),
        ("audible_deck", "source_audible_deck"),
        ("audible_deck_source", "source_audible_deck_source"),
        ("nowplaying_playback", "nowplaying_playback"),
        ("resolution", "resolution"),
        ("resolved_side", "resolved_side"),
        ("resolved_side_rule", "resolved_side_rule"),
        ("second_deck_source", "second_deck_source"),
        ("screen_vision", "screen_vision"),
        ("last_known_sides", "last_known_sides"),
        ("last_known_rule", "last_known_rule"),
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
    sample_rate = _capture_sample_rate_token(capture.get("sample_rate"))
    max_in = _capture_int(capture.get("input_channels"))
    opened = _capture_int(capture.get("opened_channels"))
    required_opened = _capture_int(capture.get("deck_audio_required_opened_channels"))
    capture_reason = _evidence_token(str(capture.get("deck_audio_capture_reason") or "unknown"))
    deck_channels = _capture_deck_channels(capture.get("deck_channels"))
    deck_capture_configured = bool(capture.get("deck_audio_capture_configured")) and all(
        side in deck_channels for side in ("A", "B")
    )
    deck_capture_enabled = bool(capture.get("deck_audio_capture_enabled")) and all(
        side in deck_channels for side in ("A", "B")
    )
    capacity = (
        "multichannel_available"
        if max_in is not None and max_in >= 4
        else "stereo_or_less"
        if max_in is not None
        else "unknown"
    )
    if deck_capture_enabled:
        mode = "deck_pair_capture_configured"
    elif deck_capture_configured and capture.get("deck_audio_capture_verified") is False:
        mode = "deck_pair_capture_unverified"
    elif opened is not None and opened >= 4:
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
    ]
    master_channels = _capture_channel_map_token(capture.get("master_channels"))
    if master_channels:
        fields.append(f"master_channels={master_channels}")
    master_source = _evidence_token(str(capture.get("deck_audio_master_source") or ""))
    if master_source:
        fields.append(f"master_source={master_source}")
    if required_opened and required_opened > 0:
        fields.append(f"required_opened_channels={required_opened}")
    if capture_reason and capture_reason != "unknown":
        fields.append(f"capture_reason={capture_reason}")
    routing_hint = _capture_routing_hint_token(capture.get("deck_audio_routing_hint"))
    if routing_hint:
        fields.append(f"routing_hint={routing_hint}")
        fields.append("routing_hint_rule=output_routing_not_live_audio_proof")
    if (
        not deck_capture_enabled
        and capture_reason in {"capture_device_too_few_channels", "opened_channels_too_few"}
    ):
        fields.append(f"setup_block={capture_reason}")
    route_diagnosis = _deck_audio_route_diagnosis_token(
        capture.get("deck_audio_route_diagnosis")
    )
    if deck_capture_enabled:
        activity = _deck_audio_activity_token(capture.get("deck_audio_rms"))
        fields.extend(
            [
                "current_capture=P1_global_mix_plus_deck_pairs",
                "gemini_audio=mono_downmix_of_master_capture",
                "deckA_audio=captured",
                "deckB_audio=captured",
                "per_deck_audio=captured_not_attached",
                "isolated_decks=runtime_capture_available",
                "deck_pairs=" + _deck_pairs_token(deck_channels),
                "upgrade_path=attach_deck_pair_audio_parts_when_needed",
            ]
        )
        if activity:
            fields.append(f"deck_audio_activity={activity}")
        if route_diagnosis:
            fields.append(f"route_diagnosis={route_diagnosis}")
    elif deck_capture_configured:
        activity = _deck_audio_activity_token(capture.get("deck_audio_rms"))
        active_seen = _evidence_token(str(capture.get("deck_audio_active_sides_seen") or "none"))
        fields.extend(
            [
                "current_capture=P1_global_mix_plus_unverified_deck_pairs",
                "gemini_audio=mono_downmix_of_master_capture",
                "deckA_audio=captured_unverified",
                "deckB_audio=captured_unverified",
                "per_deck_audio=unverified_not_attached",
                "isolated_decks=false",
                "deck_pairs=" + _deck_pairs_token(deck_channels),
                "verification=awaiting_live_audio_on_both_deck_pairs",
                "upgrade_path=verify_rekordbox_deck_routing_or_use_manual_map",
            ]
        )
        if active_seen:
            fields.append(f"active_sides_seen={active_seen}")
        if activity:
            fields.append(f"deck_audio_activity={activity}")
        if route_diagnosis:
            fields.append(f"route_diagnosis={route_diagnosis}")
    else:
        fields.extend(
            [
                "current_capture=P1_global_mix",
                "gemini_audio=mono_downmix_of_capture",
                "deckA_audio=not_captured",
                "deckB_audio=not_captured",
                "per_deck_audio=not_attached",
                "isolated_decks=false",
                "upgrade_path=multi_channel_deck_pair_capture",
            ]
        )
    fields.append("rule=separation_capability_not_outcome")
    return "deck_audio_separation_context[" + " ".join(fields) + "]"


def render_deck_audio_features_context(capture: dict[str, object] | None = None) -> str | None:
    """Return compact per-deck audio measurements from configured deck capture.

    These are descriptors for "what each captured lane is doing", not a
    transition score. They are safe for Viber text context because they are
    small deterministic numbers from the audio callback, not raw audio and not
    another model pass.
    """
    capture = capture if isinstance(capture, dict) else {}
    deck_channels = _capture_deck_channels(capture.get("deck_channels"))
    deck_capture_enabled = bool(capture.get("deck_audio_capture_enabled")) and all(
        side in deck_channels for side in ("A", "B")
    )
    if not deck_capture_enabled:
        return None

    rows = _deck_audio_feature_values(capture.get("deck_audio_features"))
    if not rows:
        rows = {
            side: {"activity": "active" if rms >= 0.003 else "silent", "rms": rms}
            for side, rms in _deck_audio_rms_values(capture.get("deck_audio_rms")).items()
        }
    if not rows:
        return None

    fields = [
        "source=deck_pair_capture",
        "window=latest_callback",
        "per_deck_audio=captured_features",
    ]
    for side in ("A", "B"):
        row = rows.get(side)
        if not row:
            continue
        activity = str(row.get("activity") or "").strip().lower()
        if activity not in {"active", "silent"}:
            rms = _feature_float(row.get("rms"))
            activity = "active" if rms is not None and rms >= 0.003 else "silent"
        fields.append(f"{side}_activity={activity}")
        for key, places in (
            ("rms", 3),
            ("peak", 3),
            ("zcr", 3),
            ("flux", 3),
            ("crest", 1),
        ):
            value = _feature_float(row.get(key))
            if value is not None:
                fields.append(f"{side}_{key}={value:.{places}f}")
    if not any(field.startswith(("A_rms=", "B_rms=")) for field in fields):
        return None
    fields.append("rule=deck_audio_features_not_outcome_verdict")
    return "deck_audio_features_context[" + " ".join(fields) + "]"


def render_deck_audio_delta_context(capture: dict[str, object] | None = None) -> str | None:
    """Return per-deck feature changes from configured deck capture.

    This is the per-lane counterpart of global ``audio_delta``. It says what
    changed on each captured deck lane, while explicitly refusing causal or
    quality claims about the user's move.
    """
    capture = capture if isinstance(capture, dict) else {}
    deck_channels = _capture_deck_channels(capture.get("deck_channels"))
    deck_capture_enabled = bool(capture.get("deck_audio_capture_enabled")) and all(
        side in deck_channels for side in ("A", "B")
    )
    if not deck_capture_enabled:
        return None
    deltas = _deck_audio_delta_values(capture.get("deck_audio_deltas"))
    features = _deck_audio_feature_values(capture.get("deck_audio_features"))
    if not deltas and not any(features.get(side) for side in ("A", "B")):
        return None

    fields = [
        "source=deck_pair_capture",
        "window=latest_callback",
        "per_deck_delta=captured_feature_delta",
    ]
    for side in ("A", "B"):
        items = deltas.get(side)
        if items:
            fields.append(f"{side}_delta={'+'.join(items[:4])}")
        elif features.get(side):
            fields.append(f"{side}_delta=no_clear_delta")
    if not any(field.startswith(("A_delta=", "B_delta=")) for field in fields):
        return None
    fields.append("rule=deck_audio_delta_not_causal_proof")
    return "deck_audio_delta_context[" + " ".join(fields) + "]"


def render_deck_audio_window_context(capture: dict[str, object] | None = None) -> str | None:
    """Return per-deck pre/current audio movement from configured deck capture.

    This is the user's "older part / current part" idea made cheap and explicit:
    deterministic feature summaries from Deck A and Deck B around the current
    action window. It labels what changed on each lane; it is not a transition
    verdict and not proof that a controller move caused the change.
    """
    capture = capture if isinstance(capture, dict) else {}
    deck_channels = _capture_deck_channels(capture.get("deck_channels"))
    deck_capture_enabled = bool(capture.get("deck_audio_capture_enabled")) and all(
        side in deck_channels for side in ("A", "B")
    )
    if not deck_capture_enabled:
        return None
    windows = _deck_audio_window_values(capture.get("deck_audio_windows"))
    if not windows:
        return None

    pre_span = _window_span_token(windows.get("pre_s"), fallback="-6.0..-1.0")
    current_span = _window_span_token(windows.get("current_s"), fallback="-1.0..0.0")
    fields = [
        "source=deck_pair_capture",
        "timeline=pre_action_current",
        f"pre={pre_span}",
        f"current={current_span}",
        "action=-1.0..0.0",
        "per_deck_audio=captured_window_features",
    ]
    for side in ("A", "B"):
        row = windows.get(side)
        if not isinstance(row, dict):
            continue
        pre = _deck_audio_window_feature_row(row.get("pre"))
        current = _deck_audio_window_feature_row(row.get("current"))
        delta = _deck_audio_delta_values({side: row.get("delta")}).get(side, [])
        if pre:
            fields.append(f"{side}_pre={_window_feature_token(pre)}")
        if current:
            fields.append(f"{side}_current={_window_feature_token(current)}")
        if delta:
            fields.append(f"{side}_delta={'+'.join(delta[:4])}")
    if not any(field.startswith(("A_current=", "B_current=")) for field in fields):
        return None
    fields.append("rule=deck_audio_window_not_causal_or_quality_verdict")
    return "deck_audio_window_context[" + " ".join(fields) + "]"


def render_audio_window_context(
    state: MusicState,
    moves: list[str] | tuple[str, ...] | None = None,
    *,
    audio_seconds: float = 6.0,
    mic_part_label: str | None = None,
    lookahead_part_label: str | None = None,
    deck_part_labels: dict[str, str] | None = None,
    deck_part_activity: dict[str, str] | None = None,
    deck_part_seconds: float = 3.0,
    lookahead_horizon_s: float = 3.0,
    force: bool = False,
) -> str | None:
    """Return a temporal map for the attached master-audio window.

    This is the cheap "old part / current move / +3s forward" bridge. It does
    not add another audio Part. Deck separation comes from ``deck_lanes_context``
    and, when optional deck-pair Parts are really attached, from the explicit
    deck Part labels. Those Parts are references, not transition verdicts.
    """
    labels = [_move_label(item).strip() for item in (moves or ())]
    labels = [label for label in labels if label][-3:]
    deck_labels = _deck_audio_part_labels(
        deck_part_labels,
        reserved_labels=(mic_part_label, lookahead_part_label),
    )
    has_reference = bool(
        force
        or labels
        or getattr(state, "audible", False)
        or getattr(state, "controller_connected", False)
        or getattr(state.deck_state, "decks", {})
        or lookahead_part_label
        or deck_labels
    )
    if not has_reference:
        return None

    try:
        seconds = float(audio_seconds)
    except (TypeError, ValueError):
        seconds = 6.0
    seconds = max(1.0, min(30.0, seconds))
    pre_end = -1.0 if seconds > 1.0 else 0.0
    p1_heard = bool(getattr(state, "audible", False))

    fields = [
        "P1=master_global_mix",
        f"P1_heard={'true' if p1_heard else 'false'}",
        "timeline=past_action_future",
        "together_audio=P1_global_mix",
        "decks_together=true",
    ]
    if deck_labels:
        try:
            deck_seconds = float(deck_part_seconds)
        except (TypeError, ValueError):
            deck_seconds = 3.0
        deck_seconds = max(1.0, min(6.0, deck_seconds))
        fields.extend(
            [
                f"deckA_audio={deck_labels.get('A', 'not_attached')}",
                f"deckB_audio={deck_labels.get('B', 'not_attached')}",
                "per_deck_audio=deck_pair_parts",
                "duplicate_audio=separate_deck_pair_parts",
                "deck_separation=deck_lanes_context",
                "deck_audio_separation=deck_audio_separation_context",
                f"deck_part_span=-{deck_seconds:.1f}..0.0",
            ]
        )
        deck_activity = _deck_audio_part_activity(deck_part_activity)
        for side in ("A", "B"):
            if side in deck_activity:
                fields.append(f"deck{side}_activity={deck_activity[side]}")
    else:
        fields.extend(
            [
                "deckA_audio=not_attached",
                "deckB_audio=not_attached",
                "per_deck_audio=structured_text_only",
                "duplicate_audio=same_master_not_deck_split",
                "deck_separation=deck_lanes_context",
            ]
        )
    fields.extend(
        [
            "lane_aliases=deck1:A,deck2:B",
            f"pre=-{seconds:.1f}..{pre_end:.1f}",
            "current=-1.0..0.0",
            "action=-1.0..0.0",
            "rule=time_alignment_not_outcome_verdict",
        ]
    )

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
    mic_part_seconds: float = 8.0,
    lookahead_part_label: str | None = None,
    deck_part_labels: dict[str, str] | None = None,
    deck_part_activity: dict[str, str] | None = None,
    deck_part_seconds: float = 3.0,
    lookahead_horizon_s: float = 3.0,
    surface: str = "gemini_parts",
    p1_model_heard: bool = True,
    p1_runtime_observed: bool = True,
    p1_audience_heard: bool = True,
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
        f"audio_token_rate={GEMINI_AUDIO_TOKENS_PER_SECOND}_per_second",
        "P1=live_global_mix",
        f"P1_model_heard={'true' if p1_model_heard else 'false'}",
        f"P1_runtime_observed={'true' if p1_runtime_observed else 'false'}",
        f"P1_audience_heard={'true' if p1_audience_heard else 'false'}",
        f"P1_span=-{seconds:.1f}..0.0",
        f"P1_tokens_est={round(seconds * GEMINI_AUDIO_TOKENS_PER_SECOND)}",
        "P1_deck_audio=global_mix_not_stems",
        "deck1=A",
        "deck2=B",
        "together_audio=P1",
    ]
    model_audio_tokens_est = (
        round(seconds * GEMINI_AUDIO_TOKENS_PER_SECOND) if p1_model_heard else 0
    )

    mic_label = _audio_part_label(mic_part_label)
    lookahead_label = _audio_part_label(lookahead_part_label)
    deck_labels = _deck_audio_part_labels(
        deck_part_labels,
        reserved_labels=(mic_label, lookahead_label),
    )
    ordered_parts = ["P1"]
    ordered_parts.extend(
        sorted(
            {
                label
                for label in (
                    mic_label,
                    lookahead_label,
                    deck_labels.get("A"),
                    deck_labels.get("B"),
                )
                if label
            },
            key=lambda label: int(label[1:]),
        )
    )
    fields.append("part_order=" + ",".join(ordered_parts))

    deck_activity: dict[str, str] = {}
    if isinstance(deck_part_activity, dict):
        for side in ("A", "B"):
            activity = str(deck_part_activity.get(side) or "").strip().lower()
            if activity in {"active", "silent"}:
                deck_activity[side] = activity
    if deck_labels:
        try:
            deck_seconds = float(deck_part_seconds)
        except (TypeError, ValueError):
            deck_seconds = 3.0
        deck_seconds = max(1.0, min(6.0, deck_seconds))
        fields.extend(
            [
                "per_deck_audio=deck_pair_parts",
                "duplicate_audio=separate_deck_pair_parts",
            ]
        )
        for side in ("A", "B"):
            label = deck_labels.get(side)
            if not label:
                continue
            fields.extend(
                [
                    f"deck{side}_part={label}",
                    f"{label}=deck{side}_configured_capture",
                    f"{label}_model_heard=true",
                    f"{label}_audience_heard=false",
                    f"{label}_span=-{deck_seconds:.1f}..0.0",
                    f"{label}_tokens_est={round(deck_seconds * GEMINI_AUDIO_TOKENS_PER_SECOND)}",
                    f"{label}_deck_audio=deck{side}_configured_capture",
                    f"{label}_rule=deck_pair_capture_reference_not_quality_verdict",
                ]
            )
            model_audio_tokens_est += round(deck_seconds * GEMINI_AUDIO_TOKENS_PER_SECOND)
            activity = deck_activity.get(side)
            if activity:
                fields.append(f"{label}_activity=deck{side}_{activity}")
    else:
        fields.extend(
            [
                "per_deck_audio=not_attached",
                "duplicate_audio=same_master_not_deck_split",
            ]
        )

    if mic_label:
        try:
            mic_seconds = float(mic_part_seconds)
        except (TypeError, ValueError):
            mic_seconds = 8.0
        mic_seconds = max(1.0, min(30.0, mic_seconds))
        fields.extend(
            [
                f"{mic_label}=user_mic",
                f"{mic_label}_model_heard=true",
                f"{mic_label}_span=-{mic_seconds:.1f}..0.0",
                f"{mic_label}_tokens_est={round(mic_seconds * GEMINI_AUDIO_TOKENS_PER_SECOND)}",
                f"{mic_label}_role=user_speech",
                f"{mic_label}_deck_audio=none",
                f"{mic_label}_rule=not_deck_audio",
            ]
        )
        model_audio_tokens_est += round(mic_seconds * GEMINI_AUDIO_TOKENS_PER_SECOND)

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
                f"{lookahead_label}_tokens_est={round(horizon * GEMINI_AUDIO_TOKENS_PER_SECOND)}",
                f"{lookahead_label}_deck_audio=none",
                f"{lookahead_label}_rule=forecast_only_not_current_live_evidence",
            ]
        )
        model_audio_tokens_est += round(horizon * GEMINI_AUDIO_TOKENS_PER_SECOND)

    fields.append(f"model_audio_tokens_est={model_audio_tokens_est}")
    fields.append("rule=part_labels_not_outcome_verdict")
    return "audio_part_context[" + " ".join(fields) + "]"


def _deck_audio_part_labels(
    deck_part_labels: dict[str, str] | None,
    *,
    reserved_labels: tuple[str | None, ...] = (),
) -> dict[str, str]:
    if not isinstance(deck_part_labels, dict):
        return {}
    labels: dict[str, str] = {}
    for side in ("A", "B"):
        label = _audio_part_label(deck_part_labels.get(side))
        if label:
            labels[side] = label
    if set(labels) != {"A", "B"}:
        return {}
    if labels["A"] == labels["B"]:
        return {}
    reserved = {label for label in (_audio_part_label(item) for item in reserved_labels) if label}
    if labels["A"] in reserved or labels["B"] in reserved:
        return {}
    return labels


def _deck_audio_part_activity(deck_part_activity: dict[str, str] | None) -> dict[str, str]:
    activity: dict[str, str] = {}
    if not isinstance(deck_part_activity, dict):
        return activity
    for side in ("A", "B"):
        value = str(deck_part_activity.get(side) or "").strip().lower()
        if value in {"active", "silent"}:
            activity[side] = value
    return activity


def render_audio_window_map(
    state: MusicState,
    moves: list[str] | tuple[str, ...] | None = None,
    *,
    audio_seconds: float = 6.0,
    mic_part_label: str | None = None,
    lookahead_part_label: str | None = None,
    deck_part_labels: dict[str, str] | None = None,
    deck_part_activity: dict[str, str] | None = None,
    deck_part_seconds: float = 3.0,
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
    deck_labels = _deck_audio_part_labels(
        deck_part_labels,
        reserved_labels=(mic_part_label, lookahead_part_label),
    )
    has_reference = bool(
        force
        or labels
        or getattr(state, "audible", False)
        or getattr(state, "controller_connected", False)
        or getattr(state.deck_state, "decks", {})
        or lookahead_part_label
        or deck_labels
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

    deck_activity = _deck_audio_part_activity(deck_part_activity)
    deck_pair_attached = bool(deck_labels)
    deck_part_span: list[float] | None = None
    if deck_pair_attached:
        try:
            deck_seconds = float(deck_part_seconds)
        except (TypeError, ValueError):
            deck_seconds = 3.0
        deck_seconds = max(1.0, min(6.0, deck_seconds))
        deck_part_span = [-round(deck_seconds, 1), 0.0]

    return {
        "p1": "master_global_mix",
        "p1_heard": bool(getattr(state, "audible", False)),
        "timeline": "past_action_future",
        "together_audio": "P1_global_mix",
        "decks_together": True,
        "deckA_audio": deck_labels.get("A", "not_attached"),
        "deckB_audio": deck_labels.get("B", "not_attached"),
        "per_deck_audio": "deck_pair_parts" if deck_pair_attached else "structured_text_only",
        "duplicate_audio": (
            "separate_deck_pair_parts" if deck_pair_attached else "same_master_not_deck_split"
        ),
        "deck_separation": "deck_lanes_context",
        "deck_audio_separation": (
            "deck_audio_separation_context" if deck_pair_attached else "not_attached"
        ),
        "deck_part_span_s": deck_part_span,
        "deck_part_activity": deck_activity,
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


def render_set_window_context(
    state: MusicState,
    *,
    span_seconds: float = 300.0,
    audio_seconds: float = 90.0,
    max_moves: int = 12,
    max_events: int = 8,
    force: bool = False,
) -> str | None:
    """Return the X4 long-window TEXT digest for deep live-coach context.

    The packet summarizes the last few minutes from existing state fields while
    preserving the master-only honesty contract: history is text, P1 is the
    only attached audio, and isolated/per-deck audio is not claimed.
    """
    has_context = bool(
        force
        or getattr(state, "trajectory_narrative", "")
        or getattr(state, "long_arc", None)
        or getattr(state, "recent_moves", None)
        or getattr(state, "phase_history", None)
        or getattr(state, "track_history", None)
        or getattr(getattr(state, "deck_state", None), "decks", None)
        or getattr(state, "audio_delta", None)
        or getattr(state, "move_audio_delta", None)
    )
    if not has_context:
        return None

    span = _bounded_seconds(span_seconds, default=300.0, minimum=60.0, maximum=300.0)
    audio_span = _bounded_seconds(audio_seconds, default=90.0, minimum=30.0, maximum=90.0)
    move_cap = max(0, min(12, int(max_moves)))
    event_cap = max(0, min(8, int(max_events)))
    fields = [
        f"span=-{span:.0f}..0.0",
        "audio_attached=P1_only_last_60-90s",
        f"audio_window_s={audio_span:.0f}",
        "history=structured_text_only",
        _set_window_energy_arc(state),
        _set_window_moves(state, move_cap),
        _set_window_events(state, event_cap),
        f"transitions={_bounded_count(max(0, len(getattr(state, 'track_history', [])) - 1))}",
        f"phase_boundaries={_bounded_count(len(getattr(state, 'phase_history', [])))}",
        _set_window_decks(state),
        _set_window_recent_tracks(state),
        _set_window_audio_delta(state),
        _set_window_trajectory(state),
        "per_deck_audio=not_attached",
        "isolated_decks=false",
        "rule=long_window_is_structured_history_not_audio_proof",
    ]
    text = "set_window_context[" + " ".join(field for field in fields if field) + "]"
    return normalize_set_window_context_text(text)


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
    lufs_delta = _render_lufs_delta(getattr(state, "master_lufs", None), prev.get("master_lufs"))
    if lufs_delta is not None:
        out.append(lufs_delta)
    for label, cur, key in candidates:
        phr = render_delta(label, cur, prev.get(key), floor=DELTA_FLOOR)
        if phr is not None:
            out.append(phr)
        if len(out) >= cap:
            break
    if len(out) < cap:
        brightness_delta = _render_brightness_delta(bands, prev)
        if brightness_delta is not None:
            out.append(brightness_delta)
    return out


def _band_env_tokens(state: MusicState) -> list[str]:
    tokens = []
    for raw in getattr(state, "band_env", []) or []:
        text = str(raw).strip().lower()
        if re.fullmatch(r"(?:sub|low|mid|high)=(?:low|mid|high)_(?:rising|falling|steady)", text):
            tokens.append(text)
    return tokens[:4]


def render_band_env_context(state: MusicState) -> str | None:
    """Return recent per-band level+trend context without making a genre verdict."""
    if not getattr(state, "audible", False):
        return None
    tokens = _band_env_tokens(state)
    if not tokens:
        return None
    fields = [
        "source=master_global_mix",
        "window=recent_feature_history",
        "bands=" + ",".join(tokens),
        "rule=band_envelope_not_genre_or_quality_verdict",
    ]
    return "band_env_context[" + " ".join(fields) + "]"


def _move_effect_audio_delta_items(
    state: MusicState,
    moves: list[str] | tuple[str, ...],
    audio_delta_items: list[str] | tuple[str, ...] | None = None,
    *,
    cap: int = 4,
) -> list[str]:
    labels = [_move_label(item) for item in (moves or ())]
    labels = [label for label in labels if label]
    if labels and any(canonical_eq_move(label) is not None for label in labels):
        move_delta = getattr(state, "move_audio_delta", None)
        if isinstance(move_delta, (list, tuple)) and move_delta:
            return [str(item) for item in move_delta if item][:cap]
    return [str(item) for item in (audio_delta_items or render_audio_delta_items(state)) if item][:cap]


def _render_lufs_delta(cur: object, prev: object, *, floor_lu: float = 1.0) -> str | None:
    if cur is None or prev is None:
        return None
    try:
        cur_f = float(cur)
        prev_f = float(prev)
    except (TypeError, ValueError):
        return None
    if not (-120.0 < cur_f < 20.0 and -120.0 < prev_f < 20.0):
        return None
    delta = cur_f - prev_f
    if abs(delta) < floor_lu:
        return None
    verb = "rose" if delta > 0.0 else "fell"
    magnitude = round(abs(delta))
    if magnitude <= 0:
        return None
    if magnitude >= 6:
        confidence = "strong"
    elif magnitude >= 3:
        confidence = "clear"
    else:
        confidence = "slight"
    return f"master lufs delta {verb} {magnitude} lu ({confidence})"


def _render_brightness_delta(
    bands: dict[str, object],
    prev: dict[str, object],
    *,
    floor: float = 0.15,
) -> str | None:
    """Render a compact mid+high movement receipt.

    This is not a full spectral-centroid claim. It is a prompt-safe receipt
    from the already-cached four-band shares: mids plus highs rose/fell enough
    to be worth citing.
    """
    cur_brightness = _finite_band_sum(bands, "mid", "high")
    prev_brightness = _finite_band_sum(prev, "mid", "high")
    if cur_brightness is None or prev_brightness is None:
        return None
    return render_delta(
        "brightness share",
        cur_brightness,
        prev_brightness,
        floor=floor,
    )


def _finite_band_sum(values: dict[str, object], *keys: str) -> float | None:
    total = 0.0
    for key in keys:
        try:
            value = float(values.get(key, 0.0) or 0.0)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(value) or value < 0.0:
            return None
        total += value
    return total


def _licensed_move_effect(
    state: MusicState,
    moves: list[str] | tuple[str, ...],
    *,
    audio_delta_items: list[str] | tuple[str, ...] | None = None,
    audio_capture_context: dict[str, object] | None = None,
) -> MoveEffectLicense | None:
    """Return a move-effect license when prediction and measurement agree.

    This is intentionally abstain-first: no move, unknown move, flat measured
    bands, or mismatched direction all return ``None`` and the old refusal path
    remains in force.
    """
    labels = [_move_label(item) for item in moves]
    labels = [label for label in labels if label]
    if not labels:
        return None
    measured = _measured_band_directions(
        _move_effect_audio_delta_items(state, labels, audio_delta_items)
    )
    sample_rate = _move_effect_sample_rate(state, audio_capture_context)

    if measured:
        for label in reversed(labels[-3:]):
            canonical = canonical_eq_move(label)
            if canonical is None:
                continue
            if not _eq_move_current_state_supports(state, label, canonical):
                continue
            predicted = predicted_band_gains(canonical, sample_rate)
            if not predicted:
                continue
            for band in ("sub", "low", "mid", "high"):
                measured_direction = measured.get(band)
                if measured_direction is None:
                    continue
                predicted_db = float(predicted.get(band, 0.0) or 0.0)
                if abs(predicted_db) < _MOVE_EFFECT_MIN_PREDICTED_DB:
                    continue
                predicted_direction = "rose" if predicted_db > 0.0 else "fell"
                if predicted_direction != measured_direction:
                    continue
                pred_token = f"pred_{predicted_direction}_{round(abs(predicted_db))}db"
                context_token = f"{canonical}:{band}:{pred_token}:measured_{measured_direction}"
                evidence_key = f"move_effect={context_token}"
                return MoveEffectLicense(
                    move=canonical,
                    band=band,
                    predicted_db=round(predicted_db, 2),
                    measured_direction=measured_direction,
                    evidence_key=evidence_key,
                    context_token=context_token,
                )
    return _licensed_xfade_effect(state, labels, audio_capture_context=audio_capture_context)


def _eq_move_current_state_supports(
    state: MusicState,
    label: str,
    canonical: str,
) -> bool:
    """Return True only when controller state still supports the EQ move.

    The prediction+measurement gate proves a band moved in the expected
    direction. This additional check keeps stale or ambiguous move labels from
    licensing a causal line after the knob has settled somewhere contradictory.
    When no controller snapshot is available, keep the older master-only path:
    abstention still depends on measured audio, not on controller presence.
    """
    side = _move_primary_side(label)
    control = _eq_move_control(canonical)
    direction = _eq_move_direction(canonical)
    if control is None or direction is None:
        return True
    raw = _deck_raw(state, side)
    if not raw:
        return not getattr(state, "controller_connected", False)
    now = _control_now_tier(raw, control)
    if direction == "cut":
        return now in {"killed", "deep-cut", "cut"}
    if direction == "boost":
        return now in {"boost", "max"}
    return False


def _eq_move_control(canonical: str) -> str | None:
    if canonical.startswith("low_"):
        return "low"
    if canonical.startswith("mid_"):
        return "mid"
    if canonical.startswith("high_"):
        return "hi"
    if canonical.startswith("filter_"):
        return "filter"
    return None


def _eq_move_direction(canonical: str) -> str | None:
    if canonical.endswith("_kill") or canonical == "filter_hp":
        return "cut"
    if canonical.endswith("_boost") or canonical == "filter_lp":
        return "boost"
    return None


def _licensed_xfade_effect(
    state: MusicState,
    labels: list[str],
    *,
    audio_capture_context: dict[str, object] | None,
) -> MoveEffectLicense | None:
    transition = _xfader_transition_from_recent_moves(state, labels)
    if transition is None:
        return None
    prev_bucket, current_bucket = transition
    expected = _xfader_expected_directions(prev_bucket, current_bucket)
    if not expected:
        return None
    measured = _deck_audio_rms_delta_directions(audio_capture_context)
    if not measured:
        return None
    matched: list[tuple[str, str, int]] = []
    for side, (direction, delta_db) in expected.items():
        observed = measured.get(side)
        if observed is None:
            continue
        if observed != direction:
            return None
        matched.append((side, direction, round(min(abs(delta_db), _XFADER_MAX_TOKEN_DB))))
    if not matched:
        return None
    from_token = _xfader_bucket_token(prev_bucket)
    to_token = _xfader_bucket_token(current_bucket)
    match_token = "+".join(
        f"{side}_pred_{direction}_{db}db" for side, direction, db in matched
    )
    context_token = f"xfade:{from_token}_to_{to_token}:{match_token}:measured_match"
    evidence_key = f"move_effect={context_token}"
    return MoveEffectLicense(
        move="xfade",
        band="rms",
        predicted_db=max(db for _, _, db in matched),
        measured_direction="matched",
        evidence_key=evidence_key,
        context_token=context_token,
    )


def _xfader_transition_from_recent_moves(
    state: MusicState,
    labels: list[str],
) -> tuple[str, str] | None:
    history = [_move_label(item) for item in getattr(state, "recent_moves", [])]
    sequence: list[str] = []
    for label in [*history, *labels]:
        bucket = _xfader_bucket(label)
        if bucket is None:
            continue
        if sequence and sequence[-1] == bucket:
            continue
        sequence.append(bucket)
    if len(sequence) < 2:
        return None
    return sequence[-2], sequence[-1]


def _xfader_expected_directions(prev_bucket: str, current_bucket: str) -> dict[str, tuple[str, float]]:
    prev_x = _XFADER_BUCKET_TO_X.get(prev_bucket)
    current_x = _XFADER_BUCKET_TO_X.get(current_bucket)
    if prev_x is None or current_x is None or prev_x == current_x:
        return {}
    prev_gains = xfade_gains(prev_x)
    current_gains = xfade_gains(current_x)
    out: dict[str, tuple[str, float]] = {}
    for side, prev_gain, current_gain in (
        ("A", prev_gains[0], current_gains[0]),
        ("B", prev_gains[1], current_gains[1]),
    ):
        delta_db = _gain_delta_db(prev_gain, current_gain)
        if abs(delta_db) < _XFADER_MIN_SIGNIFICANT_DB:
            continue
        out[side] = ("rose" if delta_db > 0.0 else "fell", delta_db)
    return out


def _deck_audio_rms_delta_directions(
    capture: dict[str, object] | None,
) -> dict[str, str]:
    if not isinstance(capture, dict) or not bool(capture.get("deck_audio_capture_enabled")):
        return {}
    out: dict[str, str] = {}
    for side, tokens in _deck_audio_delta_values(capture.get("deck_audio_deltas")).items():
        for token in tokens:
            match = _DECK_RMS_DELTA_RE.search(token)
            if match is not None:
                out[side] = match.group(1).lower()
                break
    return out


def _deck_audio_delta_text_items(capture: dict[str, object] | None) -> list[str]:
    if not isinstance(capture, dict) or not bool(capture.get("deck_audio_capture_enabled")):
        return []
    out: list[str] = []
    for side, tokens in _deck_audio_delta_values(capture.get("deck_audio_deltas")).items():
        for token in tokens[:2]:
            out.append(f"{side} {token}")
    return out[:4]


def _xfader_bucket(label: str) -> str | None:
    match = _XFADER_MOVE_RE.search(str(label))
    if match is None:
        return None
    raw = match.group(1)
    for bucket in _XFADER_BUCKET_TO_X:
        if raw.lower() == bucket.lower():
            return bucket
    return None


def _xfader_bucket_token(bucket: str) -> str:
    return bucket.lower().replace("-", "_")


def _gain_delta_db(prev_gain: float, current_gain: float) -> float:
    floor = 0.001
    prev = max(float(prev_gain), floor)
    current = max(float(current_gain), floor)
    if prev <= 0.0 or current <= 0.0:
        return 0.0
    delta = 20.0 * math.log10(current / prev)
    if not math.isfinite(delta):
        return 0.0
    if delta > _XFADER_MAX_TOKEN_DB:
        return float(_XFADER_MAX_TOKEN_DB)
    if delta < -_XFADER_MAX_TOKEN_DB:
        return float(-_XFADER_MAX_TOKEN_DB)
    return delta


def _measured_band_directions(
    audio_delta_items: list[str] | tuple[str, ...],
) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in audio_delta_items:
        match = _AUDIO_BAND_DELTA_RE.search(str(item))
        if not match:
            continue
        out[match.group(1).lower()] = match.group(2).lower()
    return out


def _move_effect_sample_rate(
    state: MusicState,
    audio_capture_context: dict[str, object] | None,
) -> int:
    candidates = []
    if isinstance(audio_capture_context, dict):
        candidates.extend(
            [
                audio_capture_context.get("sample_rate"),
                audio_capture_context.get("sample_rate_hz"),
                audio_capture_context.get("deck_audio_sample_rate"),
            ]
        )
    candidates.extend([getattr(state, "sample_rate", None), getattr(state, "audio_sample_rate", None)])
    for raw in candidates:
        if raw is None or isinstance(raw, bool):
            continue
        try:
            value = int(float(str(raw)))
        except (TypeError, ValueError, OverflowError):
            continue
        if value > 0:
            return max(8_000, min(value, 384_000))
    return 48_000


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
    audio_capture_context: dict[str, object] | None = None,
) -> list[str]:
    """Return citation-safe ``mix`` evidence keys for current deck grounding."""
    keys: list[str] = []
    labels = [_move_label(item) for item in (moves or [])]
    labels = [label for label in labels if label]
    move_scope_key: str | None = None
    move_transition_key: str | None = None
    scores = _deck_route_scores(state)
    route_key: str | None = None
    if scores:
        keys.append(f"deck_audio_support={_route_support(scores)}")
        route = "+".join(f"{side}_{_route_tier(score)}" for side, score in scores)
        route_key = f"deck_route={route}"

    resolved = _resolved_decks(state.deck_state.decks)
    source_status_map = getattr(getattr(state, "deck_state", None), "source_status", {})
    has_identity_reference = bool(state.deck_state.decks) or bool(
        getattr(state, "controller_connected", False)
    ) or bool(source_status_map)
    if has_identity_reference:
        if labels:
            touched_sides = _move_sides(labels)
            controls = _move_controls(labels)
            scope = _move_scope(touched_sides, controls)
            move_scope_key = f"move_scope={scope}"
            move_transition_key = _move_transition_status(state, resolved, scope, controls)
            keys.append(move_transition_key)
        else:
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
    capture_status = _deck_audio_capture_evidence_status(audio_capture_context)
    if capture_status:
        keys.append(capture_status)
    feature_status = _deck_audio_features_evidence_status(audio_capture_context)
    if feature_status:
        keys.append(feature_status)
    delta_status = _deck_audio_delta_evidence_status(audio_capture_context)
    if delta_status:
        keys.append(delta_status)
    window_status = _deck_audio_window_evidence_status(audio_capture_context)
    if window_status:
        keys.append(window_status)

    if labels:
        if move_transition_key is None:
            touched_sides = _move_sides(labels)
            controls = _move_controls(labels)
            scope = _move_scope(touched_sides, controls)
            move_scope_key = f"move_scope={scope}"
            keys.append(_move_transition_status(state, resolved, scope, controls))
    elif capture_status and _deck_audio_capture_has_two_active(audio_capture_context):
        if len(resolved) >= 2:
            keys.append("transition_candidate=two_resolved_decks_captured_audio")

    if move_scope_key:
        keys.append(move_scope_key)
    deltas = _move_effect_audio_delta_items(state, labels, audio_delta_items)
    license_ = (
        _licensed_move_effect(
            state,
            labels,
            audio_delta_items=deltas,
            audio_capture_context=audio_capture_context,
        )
        if labels
        else None
    )
    if license_ is not None:
        keys.append(license_.evidence_key)
    prefix = "move_effect" if labels else "audio_delta"
    for delta in deltas[:4]:
        keys.append(f"{prefix}={_evidence_token(delta)}")
    band_env = "+".join(_evidence_token(token) for token in _band_env_tokens(state))
    if band_env:
        keys.append(f"band_env={band_env}")
    if route_key:
        keys.append(route_key)

    out: list[str] = []
    seen: set[str] = set()
    for key in keys:
        safe_key = _evidence_key(key)
        if safe_key and safe_key not in seen:
            out.append(safe_key)
            seen.add(safe_key)
    return out[:10]


def live_evidence_packet(
    state: MusicState,
    moves: list[str] | tuple[str, ...] | None = None,
    *,
    audio_delta_items: list[str] | tuple[str, ...] | None = None,
    audio_capture_context: dict[str, object] | None = None,
) -> dict[str, object]:
    """Return bounded live evidence categories for prompt/socket transport."""
    move_items = tuple(_recent_move_items(state)) if moves is None else tuple(moves)
    mix_keys = live_mix_evidence_keys(
        state,
        move_items,
        audio_delta_items=audio_delta_items,
        audio_capture_context=audio_capture_context,
    )
    midi_atoms = move_evidence_atoms(state, move_items) if move_items else []

    out: dict[str, object] = {}
    if mix_keys:
        out["mix"] = mix_keys[:10]
    if midi_atoms:
        out["midi"] = [
            {"key": key, "t": round(float(t_session), 1)} for key, t_session in midi_atoms[:4]
        ]

    refs: list[str] = []
    for key, t_session in midi_atoms[:4]:
        refs.append(f"midi:{key}@{float(t_session):.1f}")
    refs.extend(f"mix:{key}" for key in mix_keys)
    if refs:
        out["refs"] = refs[:14]
    return out


def render_live_evidence_context(
    state: MusicState,
    moves: list[str] | tuple[str, ...] | None = None,
    *,
    audio_delta_items: list[str] | tuple[str, ...] | None = None,
    audio_capture_context: dict[str, object] | None = None,
) -> str | None:
    """Render prompt-readable evidence categories without implying a verdict."""
    packet = live_evidence_packet(
        state,
        moves,
        audio_delta_items=audio_delta_items,
        audio_capture_context=audio_capture_context,
    )
    if not packet:
        return None

    fields: list[str] = []
    refs = packet.get("refs")
    if isinstance(refs, list) and refs:
        fields.append("refs=" + ",".join(str(item) for item in refs[:14]))
    mix = packet.get("mix")
    if isinstance(mix, list) and mix:
        fields.append("mix=" + ",".join(str(item) for item in mix[:10]))
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
    audio_capture_context: dict[str, object] | None = None,
) -> str | None:
    """Render exact citable refs that are already present in the registry."""
    if not registry_snapshot:
        return None

    refs: list[str] = []
    for key, target_t in move_evidence_atoms(state, moves):
        observed_t = _matching_observed_time(registry_snapshot, "midi", key, target_t)
        if observed_t is not None:
            refs.append(f"[midi:{key}@{observed_t:.1f}]")

    for key in live_mix_evidence_keys(
        state,
        moves or getattr(state, "recent_moves", []),
        audio_capture_context=audio_capture_context,
    ):
        if key in registry_snapshot.get("mix", {}):
            refs.append(f"[mix:{key}]")

    if not refs:
        return None
    return "grounding_refs[" + " ".join(refs[:14]) + "]"


def render_move_effect_context(
    state: MusicState,
    moves: list[str] | tuple[str, ...],
    *,
    audio_delta_items: list[str] | tuple[str, ...] | None = None,
    audio_capture_context: dict[str, object] | None = None,
) -> str | None:
    """Return move-scoped DSP deltas without treating them as proof of skill."""
    if not moves:
        return None
    deltas = _move_effect_audio_delta_items(state, moves, audio_delta_items)
    license_ = _licensed_move_effect(
        state,
        moves,
        audio_delta_items=deltas,
        audio_capture_context=audio_capture_context,
    )
    deck_delta = _move_deck_audio_delta_token(audio_capture_context)
    deck_window = _move_deck_audio_window_token(audio_capture_context)
    if not deltas and not deck_delta and not deck_window:
        return None
    fields = [
        "window=recent_moves",
        f"moves={min(len(moves), 3)}",
    ]
    if deltas:
        fields.append("deltas=" + "; ".join(deltas[:4]))
    if deck_delta:
        fields.append(f"deck_deltas={deck_delta}")
    if deck_window:
        fields.append(f"deck_windows={deck_window}")
    if license_ is not None:
        fields.append(f"license={license_.context_token}")
        fields.append("rule=move_effect_prediction_and_measurement_agree")
    elif deck_delta or deck_window:
        fields.append("rule=move_audio_timing_not_causal_or_quality_proof")
    else:
        fields.append("rule=dsp_delta_not_causal_proof")
    return "move_effect_context[" + " ".join(fields) + "]"


def _move_deck_audio_delta_token(capture: dict[str, object] | None) -> str | None:
    if not isinstance(capture, dict) or not bool(capture.get("deck_audio_capture_enabled")):
        return None
    deltas = _deck_audio_delta_values(capture.get("deck_audio_deltas"))
    if not deltas:
        return None
    parts: list[str] = []
    for side in ("A", "B"):
        items = deltas.get(side)
        if items:
            parts.append(f"{side}:{'+'.join(items[:2])}")
    return "+".join(parts) if parts else None


def _move_deck_audio_window_token(capture: dict[str, object] | None) -> str | None:
    if not isinstance(capture, dict) or not bool(capture.get("deck_audio_capture_enabled")):
        return None
    windows = _deck_audio_window_values(capture.get("deck_audio_windows"))
    if not windows:
        return None
    parts: list[str] = []
    for side in ("A", "B"):
        row = windows.get(side)
        if not isinstance(row, dict):
            continue
        pre = row.get("pre")
        current = row.get("current")
        if not isinstance(current, dict):
            continue
        activity = str(current.get("activity") or "unknown")
        pre_rms = _feature_float(pre.get("rms")) if isinstance(pre, dict) else None
        current_rms = _feature_float(current.get("rms"))
        side_parts = [side, activity if activity in {"active", "silent"} else "unknown"]
        if pre_rms is not None:
            side_parts.append(f"pre_{pre_rms:.3f}")
        if current_rms is not None:
            side_parts.append(f"current_{current_rms:.3f}")
        delta = row.get("delta")
        if isinstance(delta, list) and delta:
            side_parts.append("delta_" + "+".join(str(item) for item in delta[:2]))
        parts.append(":".join(side_parts))
    return "+".join(parts) if parts else None


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
    public_text = _CITATION_ATOM_RE.sub(" ", str(text or ""))
    return bool(
        _MULTI_DECK_OUTCOME_RE.search(public_text)
        or _MULTI_DECK_PHRASE_RE.search(public_text)
    )


def _is_grounded_single_event_audio_observation(text: str, event_type: str | None) -> bool:
    """Return True for broad detector-event audio reads that are not transition grades."""
    raw = str(text or "").strip()
    event = str(event_type or "").strip().upper()
    if event == "SUB_LAYER_ARRIVAL":
        return bool(_SUB_LAYER_AUDIO_OBSERVATION_RE.search(raw)) and not (
            _MULTI_DECK_PHRASE_RE.search(raw)
            or _SINGLE_EVENT_TRANSITION_OUTCOME_RE.search(raw)
        )
    return False


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
    *,
    audio_capture_context: dict[str, object] | None = None,
    audio_delta_items: list[str] | tuple[str, ...] | None = None,
    deck_audio_parts_attached: bool | None = None,
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
        if _supports_grounded_transition_verdict(
            resolved,
            moves,
            audio_capture_context=audio_capture_context,
            audio_delta_items=audio_delta_items,
        ):
            if deck_audio_parts_attached is False:
                return "candidate_not_verdict", "deck_audio_parts_not_attached"
            return "supported_verdict", "two_deck_audio_window_delta_proof"
        return "candidate_not_verdict", None
    return "requires_more_evidence", None


def _supports_grounded_transition_verdict(
    resolved: dict[str, DeckTrack],
    moves: list[str] | tuple[str, ...],
    *,
    audio_capture_context: dict[str, object] | None,
    audio_delta_items: list[str] | tuple[str, ...] | None,
) -> bool:
    """Return True only when a transition verdict has citable Deck A/B proof."""
    if not moves:
        return False
    if not all(side in resolved for side in ("A", "B")):
        return False
    for side in ("A", "B"):
        deck = resolved[side]
        if not deck.track_id:
            return False
        if str(deck.source or "").strip().lower() not in DECK_CONTEXT_TRUSTED_SOURCES:
            return False
    if not _deck_audio_capture_has_two_active(audio_capture_context):
        return False
    features = _deck_audio_feature_values(
        audio_capture_context.get("deck_audio_features")
        if isinstance(audio_capture_context, dict)
        else None
    )
    if not all(features.get(side) for side in ("A", "B")):
        return False
    if not _deck_audio_window_has_two_pre_current_lanes(audio_capture_context):
        return False
    deltas = _deck_audio_delta_values(
        audio_capture_context.get("deck_audio_deltas")
        if isinstance(audio_capture_context, dict)
        else None
    )
    return bool(deltas or audio_delta_items)


def should_defer_live_claim_stream(
    state: MusicState,
    moves: list[str] | tuple[str, ...] = (),
    *,
    audio_capture_context: dict[str, object] | None = None,
    audio_delta_items: list[str] | tuple[str, ...] | None = None,
    deck_audio_parts_attached: bool | None = None,
    event_type: str | None = None,
) -> bool:
    """Return True when the response must be post-checked before TTS flush."""
    policy, _reason = live_claim_policy(
        state,
        moves,
        audio_capture_context=audio_capture_context,
        audio_delta_items=audio_delta_items,
        deck_audio_parts_attached=deck_audio_parts_attached,
    )
    capture_deltas = (
        _deck_audio_delta_values(audio_capture_context.get("deck_audio_deltas"))
        if isinstance(audio_capture_context, dict)
        else {}
    )
    if str(event_type or "").upper() == "MANUAL" and not moves and not getattr(
        state, "audible", False
    ):
        return True
    if not moves and str(event_type or "").upper() == "PHASE":
        return True
    if (
        not moves
        and policy == "requires_more_evidence"
        and str(event_type or "").upper() in _LIVE_CLAIM_DEFER_AUTO_EVENTS
    ):
        return True
    if moves and getattr(state, "audible", False):
        return True
    return policy in {"blocked", "watch_not_claim", "candidate_not_verdict"} or bool(
        moves and (_move_effect_audio_delta_items(state, moves, audio_delta_items) or capture_deltas)
    )


def should_defer_live_claim_text(
    text: str,
    state: MusicState,
    moves: list[str] | tuple[str, ...] = (),
    *,
    audio_capture_context: dict[str, object] | None = None,
    audio_delta_items: list[str] | tuple[str, ...] | None = None,
    deck_audio_parts_attached: bool | None = None,
    judge_evidence_line: str | None = None,
    event_type: str | None = None,
) -> bool:
    """Return True once streamed text matches a claim guard that may strip."""
    if not str(text or "").strip():
        return False
    policy, _reason = live_claim_policy(
        state,
        moves,
        audio_capture_context=audio_capture_context,
        audio_delta_items=audio_delta_items,
        deck_audio_parts_attached=deck_audio_parts_attached,
    )
    event = str(event_type or "").strip().upper()
    return (
        _has_unsupported_harmonic_deck_claim(
            text,
            state,
            moves,
            policy=policy,
            event_type=event_type,
            judge_evidence_line=judge_evidence_line,
        )
        or _has_uncited_track_identity_claim(text, state)
        or _has_unsupported_mixer_low_kill_claim(text, state)
        or (not moves and _has_unsupported_no_move_control_claim(text))
        or (
            _unsupported_audio_source_detail_reason(text, state, event_type=event_type)
            is not None
        )
        or (not moves and event == "PHASE" and _has_unsupported_no_move_coaching_advice(text))
        or (
            policy in {"blocked", "watch_not_claim", "candidate_not_verdict", "requires_more_evidence"}
            and _has_unsupported_transition_coaching_advice(text)
        )
    )


def apply_live_claim_guard(
    text: str,
    state: MusicState,
    moves: list[str] | tuple[str, ...] = (),
    *,
    audio_delta_items: list[str] | tuple[str, ...] | None = None,
    audio_capture_context: dict[str, object] | None = None,
    deck_audio_parts_attached: bool | None = None,
    judge_evidence_line: str | None = None,
    event_type: str | None = None,
) -> LiveClaimGuardResult:
    """Correct unsupported or debuggy live outcome text from live coach text.

    This is a result-boundary guard. The prompt teaches the rule, but this
    catches failures without depending on a specific phrase such as "great
    transition". Public copy should not expose the model's internal proof
    struggle either: the held replies below use a short human-facing reason,
    not raw claim-policy/debug labels.
    """
    policy, reason = live_claim_policy(
        state,
        moves,
        audio_capture_context=audio_capture_context,
        audio_delta_items=audio_delta_items,
        deck_audio_parts_attached=deck_audio_parts_attached,
    )
    effect_deltas = _move_effect_audio_delta_items(state, moves, audio_delta_items)
    capture_effect_deltas = _deck_audio_delta_text_items(audio_capture_context)
    effect_signals = [*effect_deltas, *capture_effect_deltas]

    def _text_claim_flags(raw: str) -> tuple[bool, bool, str | None]:
        return (
            has_multi_deck_outcome_claim(raw),
            bool(_LIVE_PUBLIC_DIAGNOSTIC_RE.search(raw)),
            _unsupported_audio_source_detail_reason(
                raw,
                state,
                event_type=event_type,
            ),
        )

    outcome_claim, public_diagnostic, source_detail_reason = _text_claim_flags(text)
    pending_corrected_policy: str | None = None
    pending_corrected_reason: str | None = None
    pending_corrected_summary = ""

    def _mark_emit_correction(*, policy: str, reason: str | None, summary: str) -> None:
        nonlocal pending_corrected_policy, pending_corrected_reason, pending_corrected_summary
        pending_corrected_policy = policy
        pending_corrected_reason = reason
        pending_corrected_summary = summary

    def _pass_result(
        *,
        policy: str = policy,
        reason: str | None = reason,
        summary: str = "",
    ) -> LiveClaimGuardResult:
        if pending_corrected_policy is not None:
            return LiveClaimGuardResult(
                text=text,
                corrected=True,
                emit_corrected=True,
                policy=pending_corrected_policy,
                reason=pending_corrected_reason,
                summary=pending_corrected_summary,
            )
        return LiveClaimGuardResult(text=text, policy=policy, reason=reason, summary=summary)

    if _has_uncited_track_identity_claim(text, state):
        summary = _live_guard_summary(state, moves)
        stripped = _strip_uncited_track_identity_clause(text, state)
        if stripped:
            text = stripped
            outcome_claim, public_diagnostic, source_detail_reason = _text_claim_flags(text)
            _mark_emit_correction(
                policy="track_identity_not_cited",
                reason="missing_track_citation",
                summary=summary,
            )
        else:
            return LiveClaimGuardResult(
                text=LIVE_TRACK_IDENTITY_HELD_REPLY,
                corrected=True,
                policy="track_identity_not_cited",
                reason="missing_track_citation",
                summary=summary,
            )

    if _has_unsupported_harmonic_deck_claim(
        text,
        state,
        moves,
        policy=policy,
        event_type=event_type,
        judge_evidence_line=judge_evidence_line,
    ):
        summary = _live_guard_summary(state, moves)
        stripped = _strip_unsupported_harmonic_clause(text)
        if stripped:
            text = stripped
            outcome_claim, public_diagnostic, source_detail_reason = _text_claim_flags(text)
            _mark_emit_correction(
                policy="harmonic_claim_not_grounded",
                reason="no_citable_key_clash_evidence",
                summary=summary,
            )
        else:
            return LiveClaimGuardResult(
                text=LIVE_TRANSITION_HELD_REPLY,
                corrected=True,
                policy="harmonic_claim_not_grounded",
                reason="no_citable_key_clash_evidence",
                summary=summary,
            )
    if _has_unsupported_mixer_low_kill_claim(text, state):
        summary = _live_guard_summary(state, moves)
        mixer_summary = _mixer_low_summary(state)
        return LiveClaimGuardResult(
            text=LIVE_MOVE_EFFECT_HELD_REPLY,
            corrected=True,
            policy="mixer_contradiction",
            reason="low_kill_not_in_mixer_state",
            summary=summary + (f"; mixer_lows={mixer_summary}" if mixer_summary else ""),
        )
    if not moves and _has_unsupported_no_move_control_claim(text):
        summary = _live_guard_summary(state, moves)
        stripped = _strip_unsupported_no_move_control_clause(text)
        if stripped:
            text = stripped
            outcome_claim, public_diagnostic, source_detail_reason = _text_claim_flags(text)
            _mark_emit_correction(
                policy="single_deck_control_not_grounded",
                reason="control_causality_without_moves",
                summary=summary,
            )
        else:
            return LiveClaimGuardResult(
                text=LIVE_MOVE_EFFECT_HELD_REPLY,
                corrected=True,
                policy="single_deck_control_not_grounded",
                reason="control_causality_without_moves",
                summary=summary,
            )
    event = str(event_type or "").strip().upper()
    if (
        not moves
        and event == "PHASE"
        and _has_unsupported_no_move_coaching_advice(text)
    ):
        summary = _live_guard_summary(state, moves)
        return LiveClaimGuardResult(
            text=LIVE_COACHING_ADVICE_HELD_REPLY,
            corrected=True,
            policy="coaching_advice_not_grounded",
            reason="advice_without_recent_move_proof",
            summary=summary,
        )
    if (
        policy in {"blocked", "watch_not_claim", "candidate_not_verdict", "requires_more_evidence"}
        and _has_unsupported_transition_coaching_advice(text)
    ):
        summary = _live_guard_summary(state, moves)
        return LiveClaimGuardResult(
            text=LIVE_COACHING_ADVICE_HELD_REPLY,
            corrected=True,
            policy="transition_coaching_not_grounded",
            reason=reason or "transition_advice_without_supported_verdict",
            summary=summary,
        )
    effect_claim = bool(
        moves
        and effect_signals
        and (
            (_MOVE_EFFECT_CONTROL_RE.search(text) and _MOVE_EFFECT_CAUSAL_VERDICT_RE.search(text))
            or _MOVE_EFFECT_CAUSAL_TEXTURE_RE.search(text)
            or _MOVE_EFFECT_BARE_VERDICT_RE.search(text)
        )
    )
    if effect_claim and not _MOVE_EFFECT_DISCLAIMER_RE.search(text):
        causal_control_claim = bool(
            (
                _MOVE_EFFECT_CONTROL_RE.search(text)
                and _MOVE_EFFECT_CAUSAL_VERDICT_RE.search(text)
            )
            or _MOVE_EFFECT_CAUSAL_TEXTURE_RE.search(text)
        )
        texture_direction = _move_effect_texture_claim_direction(text)
        license_ = (
            _licensed_move_effect(
                state,
                moves,
                audio_delta_items=effect_deltas,
                audio_capture_context=audio_capture_context,
            )
            if causal_control_claim and source_detail_reason is None
            else None
        )
        if license_ is not None and (
            texture_direction is None or license_.measured_direction == texture_direction
        ):
            return _pass_result(
                policy="move_effect_supported",
                reason="prediction_and_measured_delta_agree",
                summary=f"{license_.context_token}; evidence={_evidence_key(license_.evidence_key)}",
            )
        summary = _live_guard_summary(state, moves)
        delta_hint = "; ".join(effect_signals[:2])
        log_summary = summary + (
            f"; DSP deltas around the move: {delta_hint}" if delta_hint else ""
        )
        names_observed_control = bool(_MOVE_EFFECT_CONTROL_RE.search(text))
        move_read_supported = _move_read_supported_for_ai_coaching(
            state,
            moves,
            effect_signals,
            audio_capture_context=audio_capture_context,
        )
        if (
            source_detail_reason is None
            and names_observed_control
            and move_read_supported
            and (not causal_control_claim or texture_direction is None)
        ):
            return _pass_result(
                policy="move_effect_ai_coaching_allowed",
                reason="recent_move_ear_read",
                summary=log_summary,
            )
        return LiveClaimGuardResult(
            text=LIVE_MOVE_EFFECT_HELD_REPLY,
            corrected=True,
            policy="move_effect_not_verdict",
            reason="dsp_delta_not_causal_proof",
            summary=log_summary,
        )
    if source_detail_reason is not None:
        summary = _live_guard_summary(state, moves)
        stripped = _strip_unsupported_audio_source_detail_clause(
            text,
            state,
            event_type=event_type,
        )
        if stripped:
            text = stripped
            outcome_claim, public_diagnostic, source_detail_reason = _text_claim_flags(text)
            _mark_emit_correction(
                policy="audio_source_detail_not_proof",
                reason=source_detail_reason or "source_detail_without_grounded_detector",
                summary=summary,
            )
        else:
            return LiveClaimGuardResult(
                text=LIVE_AUDIO_SOURCE_DETAIL_HELD_REPLY,
                corrected=True,
                policy="audio_source_detail_not_proof",
                reason=source_detail_reason,
                summary=summary,
            )
    if public_diagnostic:
        summary = _live_guard_summary(state, moves)
        if policy == "candidate_not_verdict":
            return LiveClaimGuardResult(
                text=LIVE_CANDIDATE_HELD_REPLY,
                corrected=True,
                policy=policy,
                reason=reason,
                summary=summary,
            )
        return LiveClaimGuardResult(
            text=LIVE_TRANSITION_HELD_REPLY,
            corrected=True,
            policy=policy,
            reason=reason,
            summary=summary,
        )
    has_disclaimer = bool(outcome_claim and has_multi_deck_outcome_disclaimer(text))
    if has_disclaimer and not has_unsafe_multi_deck_disclaimer_claim(text):
        if policy == "candidate_not_verdict":
            summary = _live_guard_summary(state, moves)
            return LiveClaimGuardResult(
                text=LIVE_CANDIDATE_HELD_REPLY,
                corrected=True,
                policy=policy,
                reason=reason,
                summary=summary,
            )
        if policy in {"blocked", "watch_not_claim", "requires_more_evidence"}:
            summary = _live_guard_summary(state, moves)
            return LiveClaimGuardResult(
                text=LIVE_TRANSITION_HELD_REPLY,
                corrected=True,
                policy=policy,
                reason=reason,
                summary=summary,
            )
        return _pass_result()
    if policy == "candidate_not_verdict" and outcome_claim and _MULTI_DECK_VERDICT_RE.search(text):
        summary = _live_guard_summary(state, moves)
        return LiveClaimGuardResult(
            text=LIVE_CANDIDATE_HELD_REPLY,
            corrected=True,
            policy=policy,
            reason=reason,
            summary=summary,
        )

    if policy == "supported_verdict" and outcome_claim:
        judge_score = _judge_score_from_evidence_line(judge_evidence_line)
        judge_reason = _judge_overpraise_reason(text, judge_score)
        if judge_reason is not None:
            summary = _live_guard_summary(state, moves)
            summary = f"{summary}; judge_score={judge_score:.2f}"
            return LiveClaimGuardResult(
                text=LIVE_JUDGE_OVERPRAISE_HELD_REPLY,
                corrected=True,
                policy="judge_verdict_not_hype_grade",
                reason=judge_reason,
                summary=summary,
            )

    if (
        policy == "blocked"
        and moves
        and _MOVE_EFFECT_CONTROL_RE.search(text)
        and _has_current_observed_eq_move(state, moves)
        and not _has_unsupported_transition_coaching_advice(text)
    ):
        return _pass_result(
            policy="observed_move_ai_coaching_allowed",
            reason="midi_move_proves_control",
            summary=_live_guard_summary(state, moves),
        )

    if policy not in {"blocked", "watch_not_claim"}:
        return _pass_result()
    if _is_grounded_single_event_audio_observation(text, event_type):
        return _pass_result(
            policy="single_event_audio_observation",
            reason=f"{event.lower()}_detector",
            summary=_live_guard_summary(state, moves),
        )
    if not text.strip() or not outcome_claim:
        return _pass_result()

    summary = _live_guard_summary(state, moves)
    return LiveClaimGuardResult(
        text=LIVE_TRANSITION_HELD_REPLY,
        corrected=True,
        policy=policy,
        reason=reason,
        summary=summary,
    )


def _move_effect_texture_claim_direction(text: str) -> str | None:
    """Return the implied band-energy direction for causal texture words."""
    if _MOVE_EFFECT_TEXTURE_FELL_RE.search(text):
        return "fell"
    if _MOVE_EFFECT_TEXTURE_ROSE_RE.search(text):
        return "rose"
    return None


def _move_read_supported_for_ai_coaching(
    state: MusicState,
    moves: list[str] | tuple[str, ...],
    effect_signals: list[str] | tuple[str, ...],
    *,
    audio_capture_context: dict[str, object] | None = None,
) -> bool:
    """Return True when a real EQ move has same-band audio evidence.

    This is weaker than a causal verdict: direction does not have to match the
    model's prediction. It is only permission for Sven to make an AI ear-read
    about an observed control move, not permission to invent a transition,
    source, deck, or hidden stem claim.
    """
    measured = _measured_band_directions(effect_signals)
    if not measured:
        return False
    sample_rate = _move_effect_sample_rate(state, audio_capture_context)
    labels = [_move_label(item) for item in moves]
    labels = [label for label in labels if label]
    for label in reversed(labels[-3:]):
        canonical = canonical_eq_move(label)
        if canonical is None:
            continue
        if not _eq_move_current_state_supports(state, label, canonical):
            continue
        predicted = predicted_band_gains(canonical, sample_rate)
        for band, predicted_db in predicted.items():
            if abs(float(predicted_db or 0.0)) < _MOVE_EFFECT_MIN_PREDICTED_DB:
                continue
            if band in measured:
                return True
    return False


def _has_current_observed_eq_move(
    state: MusicState,
    moves: list[str] | tuple[str, ...],
) -> bool:
    for raw in moves:
        label = _move_label(raw)
        if not label:
            continue
        canonical = canonical_eq_move(label)
        if canonical is None:
            continue
        if _eq_move_current_state_supports(state, label, canonical):
            return True
    return False


def _judge_score_from_evidence_line(judge_evidence_line: str | None) -> float | None:
    if not judge_evidence_line:
        return None
    match = _JUDGE_BLEND_SCORE_RE.search(judge_evidence_line)
    if match is None:
        return None
    try:
        score = float(match.group(1))
    except ValueError:
        return None
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


def _judge_overpraise_reason(text: str, judge_score: float | None) -> str | None:
    if judge_score is None:
        return None
    if judge_score < 0.76 and _JUDGE_STRONG_PRAISE_RE.search(text):
        return "judge_score_below_strong_praise"
    if judge_score < 0.60 and _JUDGE_POSITIVE_PRAISE_RE.search(text):
        return "judge_score_below_positive_praise"
    return None


def _has_uncited_track_identity_claim(text: str, state: MusicState) -> bool:
    """Return True when live text names a track without a track citation."""
    raw = str(text or "").strip()
    if not raw or _TRACK_CITATION_RE.search(raw):
        return False
    return bool(
        _TRACK_IDENTITY_QUOTED_RE.search(raw)
        or _TRACK_IDENTITY_CALLED_RE.search(raw)
        or _TRACK_IDENTITY_BY_RE.search(raw)
        or _TRACK_IDENTITY_DASHED_RE.search(raw)
        or _mentions_known_track_identity(raw, state)
    )


def _strip_uncited_track_identity_clause(text: str, state: MusicState) -> str:
    """Drop sentence(s) that name tracks without a ``[track:*]`` citation."""
    sentences = re.split(r"(?<=[.?!])\s+", str(text or ""))
    kept = [
        sentence.strip()
        for sentence in sentences
        if sentence.strip() and not _has_uncited_track_identity_claim(sentence, state)
    ]
    return _normalize_salvaged_public_text(kept)


def _mentions_known_track_identity(text: str, state: MusicState) -> bool:
    raw = str(text or "")
    for name in _known_track_identity_names(state):
        pattern = r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])"
        if re.search(pattern, raw, flags=re.IGNORECASE):
            return True
    return False


def _known_track_identity_names(state: MusicState) -> tuple[str, ...]:
    candidates: list[str] = []
    deck_state = getattr(state, "deck_state", None)
    decks = getattr(deck_state, "decks", None) or {}
    if isinstance(decks, dict):
        for deck in decks.values():
            candidates.extend(
                [
                    str(getattr(deck, "title", "") or ""),
                    str(getattr(deck, "track_id", "") or ""),
                ]
            )
    candidates.append(str(getattr(state, "audible_track", "") or ""))
    out: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        name = re.sub(r"\s+", " ", candidate).strip(" '\"\t\r\n")
        if len(name) < 3 or name.lower() in {"unknown", "none", "null", "untitled"}:
            continue
        lowered = name.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        out.append(name)
    return tuple(out)


def _unsupported_audio_source_detail_reason(
    text: str,
    state: MusicState,
    *,
    event_type: str | None = None,
) -> str | None:
    """Return a guard reason for hidden song-part claims audio did not prove."""
    if not text.strip() or _LIVE_AUDIO_SOURCE_DETAIL_BOUNDARY_RE.search(text):
        return None
    has_source_claim = bool(
        _LIVE_AUDIO_SOURCE_DETAIL_NOUN_RE.search(text)
        and _LIVE_AUDIO_SOURCE_DETAIL_CLAIM_RE.search(text)
    )
    has_source_tail = bool(_LIVE_AUDIO_SOURCE_DETAIL_TAIL_RE.search(text))
    has_source_advice = bool(_LIVE_AUDIO_SOURCE_DETAIL_ADVICE_RE.search(text))
    if not (has_source_claim or has_source_tail or has_source_advice):
        return None

    unsupported = [
        _source_detail_noun_key(match.group(1))
        for match in _LIVE_AUDIO_SOURCE_DETAIL_NOUN_RE.finditer(text)
        if not _source_detail_noun_supported(match.group(1), state, event_type=event_type)
    ]
    if not unsupported:
        return None
    return "source_detail_without_grounded_detector"


def _strip_unsupported_audio_source_detail_clause(
    text: str,
    state: MusicState,
    *,
    event_type: str | None = None,
) -> str:
    """Keep broad listener clauses while removing ungrounded source-part claims."""

    sentences = re.split(r"(?<=[.?!])\s+", str(text or ""))
    kept: list[str] = []
    for raw_sentence in sentences:
        sentence = raw_sentence.strip()
        if not sentence:
            continue
        if _unsupported_audio_source_detail_reason(
            sentence,
            state,
            event_type=event_type,
        ) is None:
            kept.append(sentence)
            continue

        clauses = re.split(
            r"\s+(?:and then|then|but|however|and)\s+",
            sentence,
            flags=re.IGNORECASE,
        )
        for clause in clauses:
            candidate = clause.strip(" \t\r\n,;:")
            if not candidate:
                continue
            if _has_unsupported_audio_source_detail_noun(
                candidate,
                state,
                event_type=event_type,
            ):
                candidate = _strip_unsupported_audio_source_detail_phrase(
                    candidate,
                    state,
                    event_type=event_type,
                )
                if not candidate or _has_unsupported_audio_source_detail_noun(
                    candidate,
                    state,
                    event_type=event_type,
                ):
                    continue
            if _unsupported_audio_source_detail_reason(
                candidate,
                state,
                event_type=event_type,
            ) is None:
                kept.append(candidate)

    return _normalize_salvaged_public_text(kept)


def _strip_unsupported_audio_source_detail_phrase(
    text: str,
    state: MusicState,
    *,
    event_type: str | None = None,
) -> str:
    """Remove a source-detail tail while preserving the grounded broad read."""

    def _replace(match: re.Match[str]) -> str:
        noun = match.group(1)
        if _source_detail_noun_supported(noun, state, event_type=event_type):
            return match.group(0)
        return ""

    def _replace_advice(match: re.Match[str]) -> str:
        noun = str(match.group("noun") or "")
        if _source_detail_noun_supported(noun, state, event_type=event_type):
            return match.group(0)
        return ""

    cleaned = _LIVE_AUDIO_SOURCE_DETAIL_TAIL_RE.sub(_replace, str(text or ""))
    cleaned = _LIVE_AUDIO_SOURCE_DETAIL_ADVICE_RE.sub(_replace_advice, cleaned)
    return re.sub(r"\s+", " ", cleaned).strip(" ,;:")


def _normalize_salvaged_public_text(parts: list[str]) -> str:
    cleaned: list[str] = []
    for part in parts:
        text = re.sub(r"\s+", " ", part).strip()
        text = re.sub(r"\s+([,.?!])", r"\1", text)
        text = text.strip(" ,;:")
        if not text:
            continue
        if text[-1] not in ".?!":
            text += "."
        cleaned.append(text)
    return " ".join(cleaned)


def _has_unsupported_audio_source_detail_noun(
    text: str,
    state: MusicState,
    *,
    event_type: str | None = None,
) -> bool:
    return any(
        not _source_detail_noun_supported(match.group(1), state, event_type=event_type)
        for match in _LIVE_AUDIO_SOURCE_DETAIL_NOUN_RE.finditer(str(text or ""))
    )


def has_unsupported_audio_source_detail_claim(
    text: str,
    state: MusicState,
    *,
    event_type: str | None = None,
) -> bool:
    """Return True when broad live audio got promoted into hidden source detail."""
    return _unsupported_audio_source_detail_reason(text, state, event_type=event_type) is not None


def has_unsupported_audio_source_detail_mention(
    text: str,
    state: MusicState,
    *,
    event_type: str | None = None,
) -> bool:
    """Return True for an unsupported source noun before a full claim forms."""
    raw = str(text or "")
    if not raw.strip() or _LIVE_AUDIO_SOURCE_DETAIL_BOUNDARY_RE.search(raw):
        return False
    return any(
        _source_detail_noun_key(match.group(1)) not in _LIVE_AUDIO_KICK_NOUNS
        and not _source_detail_noun_supported(match.group(1), state, event_type=event_type)
        for match in _LIVE_AUDIO_SOURCE_DETAIL_NOUN_RE.finditer(raw)
    )


def has_unsupported_no_move_coaching_advice(text: str) -> bool:
    """Return True when text prescribes a DJ fix without recent move proof."""
    return _has_unsupported_no_move_coaching_advice(text)


def _source_detail_noun_key(noun: str) -> str:
    return " ".join(str(noun or "").lower().replace("-", " ").split())


def _source_detail_noun_supported(
    noun: str,
    state: MusicState,
    *,
    event_type: str | None = None,
) -> bool:
    key = _source_detail_noun_key(noun)
    if key in _LIVE_AUDIO_VOCAL_NOUNS:
        return bool(getattr(state, "vocal_active", False))
    if key in _LIVE_AUDIO_KICK_NOUNS:
        return str(event_type or "").strip().upper() in _LIVE_AUDIO_KICK_EVENT_TYPES
    return False


def _has_unsupported_mixer_low_kill_claim(text: str, state: MusicState) -> bool:
    if not getattr(state, "controller_connected", False):
        return False
    if not _MIXER_LOW_KILL_CLAIM_RE.search(text):
        return False
    if _MIXER_LOW_KILL_NEGATION_RE.search(text):
        return False
    tiers = []
    for side in ("A", "B"):
        raw = _deck_raw(state, side)
        if raw:
            tiers.append(_control_now_tier(raw, "low"))
    return bool(tiers) and not any(tier in {"killed", "deep-cut"} for tier in tiers)


def _mixer_low_summary(state: MusicState) -> str:
    parts = []
    for side in ("A", "B"):
        raw = _deck_raw(state, side)
        if raw:
            parts.append(f"{side}:{_control_now_tier(raw, 'low')}")
    return "+".join(parts)


def _has_unsupported_no_move_control_claim(text: str) -> bool:
    if _MOVE_EFFECT_DISCLAIMER_RE.search(text):
        return False
    return _has_unsupported_no_move_control_text(text)


def _has_unsupported_no_move_control_text(text: str) -> bool:
    return bool(
        _NO_MOVE_CONTROL_ACTION_RE.search(text)
        or _NO_MOVE_CONTROL_NOUN_RE.search(text)
        or _NO_MOVE_CONTROL_INSTRUCTION_RE.search(text)
        or _NO_MOVE_CONTROL_ABSENCE_RE.search(text)
    )


def _has_unsupported_no_move_coaching_advice(text: str) -> bool:
    """Return True when no recent move proof exists for a coaching prescription."""
    raw = str(text or "").strip()
    if not raw:
        return False
    if _LIVE_AUDIO_SOURCE_DETAIL_BOUNDARY_RE.search(raw) or _MOVE_EFFECT_DISCLAIMER_RE.search(raw):
        return False
    return bool(_NO_MOVE_COACHING_ADVICE_RE.search(raw))


def _has_unsupported_transition_coaching_advice(text: str) -> bool:
    """Return True for sync/transition prescriptions that need supported two-deck proof."""
    raw = str(text or "").strip()
    if not raw:
        return False
    if _LIVE_AUDIO_SOURCE_DETAIL_BOUNDARY_RE.search(raw) or _MOVE_EFFECT_DISCLAIMER_RE.search(raw):
        return False
    return bool(_UNSUPPORTED_TRANSITION_COACHING_RE.search(raw))


def _has_unsupported_harmonic_deck_claim(
    text: str,
    state: MusicState,
    moves: list[str] | tuple[str, ...],
    *,
    policy: str,
    event_type: str | None,
    judge_evidence_line: str | None,
) -> bool:
    """Return True when a key/harmonic verdict lacks citable deck-pair proof."""
    raw = str(text or "").strip()
    if not raw or not _HARMONIC_DECK_CLAIM_RE.search(raw):
        return False
    event = str(event_type or "").strip().upper()
    if event in {"KEY_CLASH", "TRANSITION_OPPORTUNITY"}:
        return False
    if policy != "supported_verdict":
        return True
    resolved = _resolved_decks(state.deck_state.decks)
    if not all(
        side in resolved and bool(str(resolved[side].camelot or "").strip())
        for side in ("A", "B")
    ):
        return True
    if judge_evidence_line and _HARMONIC_DECK_CLAIM_RE.search(judge_evidence_line):
        return False
    return True


def _strip_unsupported_no_move_control_clause(text: str) -> str:
    """Keep a sound-only clause when the unsupported control clause is trailing."""
    stripped = text.strip()
    if not stripped:
        return ""
    match = re.search(r"\s+\bwhen\s+you\b", stripped, flags=re.IGNORECASE)
    if match:
        kept = stripped[: match.start()].strip(" ,;:")
        if kept:
            return kept if kept.endswith((".", "!", "?")) else f"{kept}."
    sentences = _split_live_sentences(stripped)
    kept_sentences = [
        sentence.strip()
        for sentence in sentences
        if sentence.strip() and not _has_unsupported_no_move_control_text(sentence)
    ]
    if kept_sentences and len(kept_sentences) < len(sentences):
        out = " ".join(kept_sentences).strip()
        return out if out.endswith((".", "!", "?")) else f"{out}."
    return ""


def _strip_unsupported_harmonic_clause(text: str) -> str:
    """Keep grounded audio-read sentences when a trailing key claim is unsupported."""
    stripped = text.strip()
    if not stripped:
        return ""
    sentences = _split_live_sentences(stripped)
    kept_sentences = [
        sentence.strip()
        for sentence in sentences
        if sentence.strip() and not _HARMONIC_DECK_CLAIM_RE.search(sentence)
    ]
    if kept_sentences and len(kept_sentences) < len(sentences):
        out = " ".join(kept_sentences).strip()
        return out if out.endswith((".", "!", "?")) else f"{out}."
    return ""


def _split_live_sentences(text: str) -> list[str]:
    """Split live prose without cutting inside decimal citation atoms."""
    stripped = text.strip()
    if not stripped:
        return []
    return [part for part in re.split(r"(?<=[.!?])\s+(?=[A-Z])", stripped) if part]


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


def _tempo_bridge_context(resolved: dict[str, DeckTrack]) -> str | None:
    """Return metadata-only BPM gap context for the two active deck identities.

    This is deliberately not a timing or beatgrid verdict. The source is deck
    metadata, so the prompt field carries the rule that it cannot prove live
    beat drift by itself.
    """
    if len(resolved) < 2:
        return None

    sides = [side for side in ("A", "B") if side in resolved]
    if len(sides) < 2:
        sides = sorted(resolved)[:2]
    if len(sides) < 2:
        return None

    left, right = sides[0], sides[1]
    left_bpm = resolved[left].bpm
    right_bpm = resolved[right].bpm
    delta = bpm_folded_delta_pct(left_bpm, right_bpm)
    if delta is None:
        return (
            "tempo_bridge["
            f"decks={left}+{right} "
            "risk=bpm_unknown "
            "rule=metadata_not_live_beatgrid_proof]"
        )

    if delta <= 0.03:
        risk = "matched"
    elif delta <= 0.06:
        risk = "bridge"
    elif delta <= 0.08:
        risk = "tempo_push"
    else:
        risk = "tempo_jump"

    return (
        "tempo_bridge["
        f"decks={left}+{right} "
        f"bpm={left}:{left_bpm:.0f},{right}:{right_bpm:.0f} "
        f"folded_delta={delta * 100:.1f}% "
        f"risk={risk} "
        "rule=metadata_not_live_beatgrid_proof]"
    )


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
    source_status = getattr(getattr(state, "deck_state", None), "source_status", {})
    if not decks and not getattr(state, "controller_connected", False) and not source_status:
        return None
    resolved = _resolved_decks(decks)
    scores = dict(_deck_route_scores(state))
    sides: set[str] = set()
    if (
        getattr(state, "controller_connected", False)
        or source_status
        or any(side in decks for side in ("A", "B"))
    ):
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
    source_status = getattr(getattr(state, "deck_state", None), "source_status", {})
    if not decks and not getattr(state, "controller_connected", False) and not source_status:
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
    source_status = getattr(getattr(state, "deck_state", None), "source_status", {})
    if not decks and not getattr(state, "controller_connected", False) and not source_status:
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


def _capture_channel_map_token(raw: object) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip().replace(" ", "")
    if re.fullmatch(r"\d+(?:,\d+)*", text):
        return text
    token = _evidence_token(text)
    return token or None


def _capture_routing_hint_token(raw: object) -> str | None:
    if raw is None:
        return None
    text = " ".join(str(raw).split())
    if not text.startswith("rekordbox_deck_routing_hint["):
        return None
    match = re.search(r"\bdeck_outputs=([^\]\s]+)", text)
    if not match:
        return None
    outputs = match.group(1).replace(",", "+")
    token = _evidence_token(f"rekordbox_settings_{outputs}")
    return token or None


def _capture_deck_channels(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for side in ("A", "B"):
        value = raw.get(side)
        token = _capture_channel_map_token(value)
        if token:
            out[side] = token
    return out


def _deck_pairs_token(deck_channels: dict[str, str]) -> str:
    parts = [f"{side}:{deck_channels[side]}" for side in ("A", "B") if side in deck_channels]
    return "+".join(parts) if parts else "none"


def _deck_audio_rms_values(raw: object) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, float] = {}
    for side in ("A", "B"):
        value = raw.get(side)
        if value is None or isinstance(value, bool):
            continue
        try:
            rms = float(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if rms == rms and rms >= 0.0:
            out[side] = min(rms, 9.999)
    return out


def _feature_float(raw: object) -> float | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError, OverflowError):
        return None
    if value != value or value < 0.0:
        return None
    return min(value, 99.9)


def _deck_audio_feature_values(raw: object) -> dict[str, dict[str, object]]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, object]] = {}
    for side in ("A", "B"):
        row = raw.get(side)
        if not isinstance(row, dict):
            continue
        clean: dict[str, object] = {}
        activity = str(row.get("activity") or "").strip().lower()
        if activity in {"active", "silent"}:
            clean["activity"] = activity
        for key in ("rms", "peak", "zcr", "flux", "crest"):
            value = _feature_float(row.get(key))
            if value is not None:
                clean[key] = value
        if clean:
            out[side] = clean
    return out


def _deck_audio_delta_values(raw: object) -> dict[str, list[str]]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[str]] = {}
    for side in ("A", "B"):
        values = raw.get(side)
        if not isinstance(values, (list, tuple)):
            continue
        clean: list[str] = []
        for value in values:
            token = _evidence_token(str(value))
            if token:
                clean.append(token)
            if len(clean) >= 4:
                break
        if clean:
            out[side] = clean
    return out


def _deck_audio_window_values(raw: object) -> dict[str, object]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, object] = {}
    for key in ("pre_s", "current_s"):
        span = _window_span_pair(raw.get(key))
        if span is not None:
            out[key] = span
    for side in ("A", "B"):
        row = raw.get(side)
        if not isinstance(row, dict):
            continue
        clean: dict[str, object] = {}
        pre = _deck_audio_window_feature_row(row.get("pre"))
        current = _deck_audio_window_feature_row(row.get("current"))
        delta = _deck_audio_delta_values({side: row.get("delta")}).get(side, [])
        if pre:
            clean["pre"] = pre
        if current:
            clean["current"] = current
        if delta:
            clean["delta"] = delta
        if clean:
            out[side] = clean
    return out


def _deck_audio_window_feature_row(raw: object) -> dict[str, object]:
    if not isinstance(raw, dict):
        return {}
    clean: dict[str, object] = {}
    activity = str(raw.get("activity") or "").strip().lower()
    if activity in {"active", "silent"}:
        clean["activity"] = activity
    for key in ("rms", "peak", "zcr", "flux", "crest"):
        value = _feature_float(raw.get(key))
        if value is not None:
            clean[key] = value
    frames = _capture_int(raw.get("frames"))
    if frames is not None and frames > 0:
        clean["frames"] = min(frames, 10000)
    if "activity" not in clean:
        rms = _feature_float(clean.get("rms"))
        if rms is not None:
            clean["activity"] = "active" if rms >= 0.003 else "silent"
    return clean


def _window_feature_token(row: dict[str, object]) -> str:
    activity = str(row.get("activity") or "unknown")
    parts = [activity if activity in {"active", "silent"} else "unknown"]
    for key in ("rms", "peak", "flux"):
        value = _feature_float(row.get(key))
        if value is not None:
            parts.append(f"{key}_{value:.3f}")
    return "_".join(parts)


def _window_span_pair(raw: object) -> tuple[float, float] | None:
    if not isinstance(raw, (list, tuple)) or len(raw) < 2:
        return None
    try:
        start = float(raw[0])
        end = float(raw[1])
    except (TypeError, ValueError, OverflowError):
        return None
    if start != start or end != end or start > end:
        return None
    return (max(-30.0, min(30.0, start)), max(-30.0, min(30.0, end)))


def _window_span_token(raw: object, *, fallback: str) -> str:
    span = _window_span_pair(raw)
    if span is None:
        return fallback
    return f"{span[0]:.1f}..{span[1]:.1f}"


def _deck_audio_activity_token(raw: object) -> str | None:
    rms = _deck_audio_rms_values(raw)
    if not rms:
        return None
    parts = []
    for side in ("A", "B"):
        value = rms.get(side)
        if value is None:
            continue
        tier = "active" if value >= 0.003 else "silent"
        parts.append(f"{side}_{tier}")
    return "+".join(parts) if parts else None


def _deck_audio_route_diagnosis_token(raw: object) -> str | None:
    if not isinstance(raw, dict):
        return None
    status = _evidence_token(str(raw.get("status") or "unknown"))
    if not status or status == "unknown":
        return None
    parts = [status]
    for key in (
        "inactive_sides",
        "active_sides",
        "configured_pairs",
        "opened_active_pairs",
        "active_unassigned_pairs",
        "likely_cause",
        "next_action",
        "rule",
    ):
        token = _evidence_token(str(raw.get(key) or ""))
        if token:
            parts.append(f"{key}_{token}")
    return "__".join(parts)[:420]


def _deck_audio_capture_evidence_status(capture: dict[str, object] | None) -> str | None:
    if not isinstance(capture, dict) or not bool(capture.get("deck_audio_capture_enabled")):
        return None
    activity = _deck_audio_activity_token(capture.get("deck_audio_rms"))
    if activity:
        return f"deck_audio_capture={activity}"
    return "deck_audio_capture=configured"


def _deck_audio_features_evidence_status(capture: dict[str, object] | None) -> str | None:
    if not isinstance(capture, dict) or not bool(capture.get("deck_audio_capture_enabled")):
        return None
    rows = _deck_audio_feature_values(capture.get("deck_audio_features"))
    if not rows:
        return None
    parts: list[str] = []
    for side in ("A", "B"):
        row = rows.get(side)
        if not row:
            continue
        activity = str(row.get("activity") or "").strip().lower()
        if activity not in {"active", "silent"}:
            rms = _feature_float(row.get("rms")) or 0.0
            activity = "active" if rms >= 0.003 else "silent"
        rms = _feature_float(row.get("rms"))
        if rms is None:
            parts.append(f"{side}_{activity}")
        else:
            parts.append(f"{side}_{activity}_rms_{rms:.3f}")
    return "deck_audio_features=" + "+".join(parts) if parts else None


def _deck_audio_delta_evidence_status(capture: dict[str, object] | None) -> str | None:
    if not isinstance(capture, dict) or not bool(capture.get("deck_audio_capture_enabled")):
        return None
    deltas = _deck_audio_delta_values(capture.get("deck_audio_deltas"))
    if not deltas:
        return None
    parts = [
        f"{side}_{items[0]}" for side in ("A", "B") for items in [deltas.get(side)] if items
    ]
    return "deck_audio_delta=" + "+".join(parts) if parts else None


def _deck_audio_window_evidence_status(capture: dict[str, object] | None) -> str | None:
    if not isinstance(capture, dict) or not bool(capture.get("deck_audio_capture_enabled")):
        return None
    windows = _deck_audio_window_values(capture.get("deck_audio_windows"))
    if not windows:
        return None

    parts: list[str] = []
    for side in ("A", "B"):
        row = windows.get(side)
        if not isinstance(row, dict):
            continue
        pre = row.get("pre")
        current = row.get("current")
        pre_rms = _feature_float(pre.get("rms")) if isinstance(pre, dict) else None
        current_rms = _feature_float(current.get("rms")) if isinstance(current, dict) else None
        activity = "unknown"
        if isinstance(current, dict) and current.get("activity") in {"active", "silent"}:
            activity = str(current["activity"])
        elif isinstance(pre, dict) and pre.get("activity") in {"active", "silent"}:
            activity = str(pre["activity"])

        if pre_rms is not None and current_rms is not None:
            parts.append(f"{side}_{activity}_pre_{pre_rms:.3f}_current_{current_rms:.3f}")
        elif current_rms is not None:
            parts.append(f"{side}_{activity}_current_{current_rms:.3f}")
        elif pre_rms is not None:
            parts.append(f"{side}_{activity}_pre_{pre_rms:.3f}")
        else:
            delta = row.get("delta")
            if isinstance(delta, list) and delta:
                parts.append(f"{side}_{delta[0]}")
    return "deck_audio_window=" + "+".join(parts) if parts else None


def _deck_audio_window_has_two_pre_current_lanes(capture: dict[str, object] | None) -> bool:
    if not isinstance(capture, dict) or not bool(capture.get("deck_audio_capture_enabled")):
        return False
    windows = _deck_audio_window_values(capture.get("deck_audio_windows"))
    if not windows:
        return False
    for side in ("A", "B"):
        row = windows.get(side)
        if not isinstance(row, dict):
            return False
        pre = row.get("pre")
        current = row.get("current")
        if not isinstance(pre, dict) or not isinstance(current, dict):
            return False
        if _feature_float(pre.get("rms")) is None:
            return False
        if _feature_float(current.get("rms")) is None:
            return False
    return True


def _deck_audio_capture_has_two_active(capture: dict[str, object] | None) -> bool:
    if not isinstance(capture, dict) or not bool(capture.get("deck_audio_capture_enabled")):
        return False
    rms = _deck_audio_rms_values(capture.get("deck_audio_rms"))
    return all(rms.get(side, 0.0) >= 0.003 for side in ("A", "B"))


def _capture_sample_rate_token(raw: object) -> str:
    if raw is None or isinstance(raw, bool):
        return "unknown"
    try:
        value = int(float(str(raw)))
    except (TypeError, ValueError, OverflowError):
        return "unknown"
    if value <= 0:
        return "unknown"
    return str(min(value, 384000))


def _bounded_seconds(raw: object, *, default: float, minimum: float, maximum: float) -> float:
    if raw is None or isinstance(raw, bool):
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError, OverflowError):
        return default
    if not math.isfinite(value):
        return default
    return max(minimum, min(maximum, value))


def _bounded_count(raw: object) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError, OverflowError):
        return 0
    return max(0, min(99, value))


def _set_window_energy_arc(state: MusicState) -> str:
    arc = [float(v) for v in getattr(state, "long_arc", []) if isinstance(v, (int, float))]
    if len(arc) < 2:
        return "energy_arc=unknown:0"
    delta = arc[-1] - arc[0]
    if abs(delta) < 0.03:
        direction = "flat"
    else:
        direction = "up" if delta > 0 else "down"
    return f"energy_arc={direction}:{min(len(arc), 99)}"


def _set_window_moves(state: MusicState, cap: int) -> str:
    moves: list[tuple[float, str]] = []
    for raw in getattr(state, "recent_moves", []) or []:
        if not isinstance(raw, (list, tuple)) or len(raw) < 2:
            continue
        try:
            age = max(0.0, float(raw[0]))
        except (TypeError, ValueError):
            continue
        label = _evidence_token(_move_label(raw[1]).replace(":", " "))
        if label:
            moves.append((age, label))
    moves.sort(key=lambda item: item[0])
    if not moves or cap <= 0:
        return "moves=none"
    items = [f"{label}@-{age:.1f}s" for age, label in moves[:cap]]
    return "moves=" + ",".join(items)


def _set_window_events(state: MusicState, cap: int) -> str:
    if cap <= 0:
        return "events=none"
    now = time.time()
    events: list[tuple[float, str]] = []
    for raw in getattr(state, "phase_history", []) or []:
        if not isinstance(raw, (list, tuple)) or len(raw) < 3:
            continue
        age = _history_age(now, raw[0])
        if age is None:
            continue
        label = _evidence_token(f"PHASE_{raw[1]}_to_{raw[2]}")
        if label:
            events.append((age, label))
    for raw in getattr(state, "track_history", []) or []:
        if not isinstance(raw, (list, tuple)) or len(raw) < 2:
            continue
        age = _history_age(now, raw[0])
        if age is None:
            continue
        label = _evidence_token(f"TRACK_{raw[1]}")
        if label:
            events.append((age, label))
    events.sort(key=lambda item: item[0])
    if not events:
        return "events=none"
    items = [f"{label}@-{age:.1f}s" for age, label in events[:cap]]
    return "events=" + ",".join(items)


def _history_age(now: float, raw_ts: object) -> float | None:
    if raw_ts is None or isinstance(raw_ts, bool):
        return None
    try:
        ts = float(raw_ts)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(ts):
        return None
    return max(0.0, now - ts)


def _set_window_decks(state: MusicState) -> str:
    decks = getattr(getattr(state, "deck_state", None), "decks", {}) or {}
    if not decks:
        return "decks=unknown"
    side_alias = {"A": "deck1", "B": "deck2", "C": "deck3", "D": "deck4"}
    parts: list[str] = []
    for side, deck in sorted(decks.items()):
        alias = side_alias.get(str(side), f"deck_{_evidence_token(str(side)) or 'unknown'}")
        track = _evidence_token(str(deck.track_id or deck.title or "unknown")) or "unknown"
        bpm = f"{float(deck.bpm):.0f}" if deck.bpm and deck.bpm > 0 else "unknown"
        camelot = _evidence_token(str(deck.camelot or "unknown")) or "unknown"
        genre = _evidence_token(str(deck.genre or "unknown")) or "unknown"
        parts.append(f"{alias}:{side}({track},{bpm},{camelot},genre={genre},cue_next=unknown)")
    return "decks=" + "+".join(parts)


def _set_window_recent_tracks(state: MusicState) -> str:
    titles: list[str] = []
    for raw in getattr(state, "track_history", [])[-4:] or []:
        if not isinstance(raw, (list, tuple)) or len(raw) < 2:
            continue
        token = _evidence_token(str(raw[1]))
        if token:
            titles.append(token)
    return "recent_tracks=" + ("+".join(titles) if titles else "none")


def _set_window_audio_delta(state: MusicState) -> str:
    items = [
        _evidence_token(str(item))
        for item in (
            list(getattr(state, "move_audio_delta", []) or [])
            + list(getattr(state, "audio_delta", []) or [])
        )
    ]
    items = [item for item in items if item][:6]
    return "audio_delta=" + ("+".join(items) if items else "none")


def _set_window_trajectory(state: MusicState) -> str:
    trajectory = _evidence_token(str(getattr(state, "trajectory_narrative", "") or ""))
    return f"trajectory={trajectory}" if trajectory else "trajectory=none"


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
    genre = _deck_genre_field(deck)
    if genre:
        parts.append(genre)
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
        genre = _deck_genre_field(resolved_deck)
        if genre:
            parts.append(genre)
        parts.append(f"src={resolved_deck.source}")
        parts.append(f"conf={resolved_deck.confidence:.2f}")
    elif deck is not None:
        if deck.source == "last_known":
            parts.append("identity=last_known_unverified")
            if deck.title:
                parts.append(f"last_title={_prompt_quote(deck.title)}")
            if deck.camelot:
                parts.append(f"last_key={deck.camelot}")
            if deck.bpm and deck.bpm > 0:
                parts.append(f"last_bpm={deck.bpm:.0f}")
        else:
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
            genre = _deck_genre_field(resolved_deck)
            if genre:
                fields.append(genre)
            fields.append(f"src={resolved_deck.source}")
            fields.append(f"conf={resolved_deck.confidence:.2f}")
    elif deck is not None:
        identity = "last_known_unverified" if deck.source == "last_known" else "unresolved"
        fields = [f"{alias}={side}", f"identity={identity}", f"src={deck.source}"]
        if deck.source == "last_known" and deck.title:
            fields.append(f"last_title={_prompt_quote(deck.title)}")
        if not compact:
            if deck.source == "last_known":
                if deck.camelot:
                    fields.append(f"last_key={deck.camelot}")
                if deck.bpm and deck.bpm > 0:
                    fields.append(f"last_bpm={deck.bpm:.0f}")
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


def _deck_genre_field(deck: DeckTrack) -> str | None:
    """Return source genre for deck identity packets, or None when absent.

    This is source metadata, not DSP inference. Keeping it next to title/key/BPM
    gives the live prompt a citable genre anchor for the actual loaded song.
    """
    genre = getattr(deck, "genre", None)
    if not genre:
        return None
    return f"genre={_prompt_quote(str(genre), max_len=40)}"


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
