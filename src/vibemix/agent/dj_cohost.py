# SPDX-License-Identifier: Apache-2.0
"""DJCoHostAgent — Phase 10 cascade with prompt-matrix dispatch + anti-slop.

Hijacks ``llm_node`` to bypass LiveKit's text-only cascade and call
``google.genai`` directly with the last COACH_AUDIO_SECONDS of audio attached
as a multimodal Part. The LLM literally hears the music.

PHASE 10 ADDITIONS (on top of the Phase 4 v4-port):

1. **Env-var prompt dispatch** — ``__init__`` reads ``VIBEMIX_SKILL_LEVEL``
   and ``VIBEMIX_MODE`` (defaults: ``intermediate`` / ``hype``) and selects the
   right cell from ``vibemix.prompts.matrix.build_system_instruction(...)``.
   Default = HYPE_INTERMEDIATE = byte-identical v4 SYSTEM_INSTRUCTION.

2. **<silence/> short-circuit** — ``llm_node`` accumulates the LLM stream into
   a buffer; if the stripped output is exactly ``<silence/>`` (or starts with
   it), the entire turn is suppressed (no chunks yielded → no TTS → no
   playback) and a ``silence_short_circuit`` event is logged.

3. **Slop filter (post-hoc)** — after silence check, the accumulated text is
   passed through ``filter_for_slop``; if any banned phrase matches, the turn
   is suppressed and a ``slop_suppressed`` event is logged with the matched
   phrases. Otherwise chunks are yielded in their original order.

   Streaming behavior change vs Phase 4: chunks are now buffered until the
   stream completes, then yielded in one batch (after the silence + slop
   gate). Adds ~1 LLM-stream-duration of latency to the TTS path (~1-2s for
   short replies) — acceptable for v1; Phase 14 may revisit with progressive
   streaming if the latency cost shows in Coach feedback.

Other lines remain byte-for-byte v4 — the v4:1502 anti-hallucination comment
stays at its load-bearing position; ``screen_jpeg = None`` deliberate
single-modality gate is preserved.
"""

from __future__ import annotations

import asyncio
import collections
import json
import os
import re
import sys
import time
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

import numpy as np
from google import genai
from google.genai import types
from livekit.agents import Agent, ModelSettings
from livekit.agents import llm as agents_llm
from livekit.agents import tts as agents_tts

from vibemix.agent._streaming_pipe import (
    can_yield_chunks,
    last_balanced_position,
)
from vibemix.agent.cache import GeminiContextCache
from vibemix.agent.config import LLM_MODEL, OPENROUTER_LLM_MODEL
from vibemix.agent.emote_parser import has_emote_tag, strip_emote_tags
from vibemix.agent.language_guard import english_only_violation_matches
from vibemix.agent.playback_sink import _resample_int16_mono_pcm
from vibemix.agent.proxy_client import (
    classify_proxy_error,
    probe_proxy_health,
)
from vibemix.agent.tts_sanitizer import model_text_for_tts
from vibemix.audio import (
    INVOKE_AUDIO_SECONDS,
    MIC_AUDIO_PART_PRESENCE_RMS,
    MIC_AUDIO_PART_RECENCY_S,
    MIC_AUDIO_PART_SECONDS,
    INPUT_SR_NATIVE,
    OUTPUT_SR,
    AudioBuffer,
    VoiceRecorder,
    pcm_to_wav,
    snapshot_wav,
)
from vibemix.coach import CitationLinter, StrippedRateTracker
from vibemix.library.budget import get_session_meter
from vibemix.llm.route_chain import LiveCoachRouteChain, resolve_live_coach_chain
from vibemix.llm.thinking_gate import validate_live_config
from vibemix.prompts import build_parts_description, build_system_instruction, filter_for_slop
from vibemix.runtime.ai_observability import (
    record_session_ai_message,
    snapshot_state_for_ai_message,
)
from vibemix.runtime.debug_flags import debug_log_enabled
from vibemix.runtime.llm_to_tts_delta_meter import LLMToTTSDeltaMeter
from vibemix.runtime.speak_gate import event_speak_fingerprint
from vibemix.runtime.ttft import TTFTMeter
from vibemix.state import AICoach, Event, EvidenceRegistry, MusicState, parse_citations
from vibemix.state.deck_context import (
    GEMINI_AUDIO_TOKENS_PER_SECOND,
    LiveClaimGuardResult,
    apply_live_claim_guard,
    has_unsupported_audio_source_detail_claim,
    has_unsupported_audio_source_detail_mention,
    has_unsupported_no_move_coaching_advice,
    live_claim_policy,
    render_audio_delta_items,
    render_audio_part_context,
    render_audio_window_context,
    render_audio_window_map,
    render_band_env_context,
    render_context_feed_contract,
    render_deck_audio_context,
    render_deck_audio_delta_context,
    render_deck_audio_features_context,
    render_deck_audio_separation_context,
    render_deck_audio_window_context,
    render_deck_change_context,
    render_deck_context,
    render_deck_lane_context,
    render_deck_reference_context,
    render_deck_source_context,
    render_live_evidence_context,
    render_mixer_context,
    render_move_context,
    render_move_effect_context,
    render_set_window_context,
    should_defer_live_claim_stream,
    should_defer_live_claim_text,
)
from vibemix.ui_bus import SessionCohostReaction, SessionOverlayHighlight

if TYPE_CHECKING:  # pragma: no cover — typing-only
    from vibemix.audio.buffers import PlaybackQueue
    from vibemix.audio.lookahead import LookaheadProvider
    from vibemix.library.grounding import Grounding
    from vibemix.memory.retrieval import MemoryRecall
    from vibemix.runtime.ws_bus import IpcBus

# Sentinel suppression-token the LLM emits when nothing's worth reacting to.
# The cascade swallows it. See ``vibemix.prompts.matrix`` for the prompt-side
# instruction.
SILENCE_TOKEN = "<silence/>"

_GROUNDED_RECEIPT_EXTRA_KEYS = (
    "energy_read_voice_line",
    "move_grade_voice_line",
    "next_suggestion_voice_line",
    "transition_verdict_voice_line",
    "set_progress_voice_line",
    "judge_evidence_line",
)
_BAND_INTENSITY_ALIAS_RE: dict[str, re.Pattern[str]] = {
    "sub": re.compile(r"\b(?:sub(?:\s*bass)?|sub-bass)\b", re.IGNORECASE),
    "low": re.compile(r"\b(?:low\s+end|lows?|bass)\b", re.IGNORECASE),
    "mid": re.compile(r"\b(?:mid\s*range|mids?)\b", re.IGNORECASE),
    "high": re.compile(r"\b(?:high\s+end|top\s+end|highs?|treble)\b", re.IGNORECASE),
}
_BAND_ABUNDANCE_RE = re.compile(
    r"\b(?:"
    r"getting\s+busy|busy|heavy|huge|big|full|loud|dominant|dominates?|dominating|"
    r"flood(?:ed|ing)?|stack(?:ed|ing)?|thick|dense|bright|sharp|harsh|piercing|hot|"
    r"prominent|crowded"
    r")\b",
    re.IGNORECASE,
)
_BAND_ABUNDANCE_FLOOR: dict[str, float] = {
    "sub": 0.18,
    "low": 0.18,
    "mid": 0.18,
    "high": 0.12,
}
_BAND_INTENSITY_EVENT_SUPPORT: dict[str, frozenset[str]] = {
    "sub": frozenset({"SUB_LAYER_ARRIVAL", "REENTRY_KICK_LAND", "KICK_SWAP"}),
    "low": frozenset({"BAND_SHIFT_LOW", "SUB_LAYER_ARRIVAL"}),
    "mid": frozenset({"LAYER_ARRIVAL", "BAND_SHIFT_MID"}),
    "high": frozenset({"LAYER_ARRIVAL", "BAND_SHIFT_HIGH"}),
}
_OPTION_SCAFFOLD_PREFIX_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:option(?:\s+[ab])?\b|[ab][).:])",
    re.IGNORECASE,
)
_OPTION_A_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:option\s+a(?:\s*/\s*option\s+b)?\s*[:.)-]|a[).:])\s*(?P<body>.*)",
    re.IGNORECASE | re.DOTALL,
)
_OPTION_B_SPLIT_RE = re.compile(
    r"(?:^|\s)(?:[-*]\s*)?(?:option\s+b\s*[:.)-]|b[).:])\s*",
    re.IGNORECASE,
)
_FINISHED_LINE_META_PREFIX_RE = re.compile(
    r"^\s*(?:"
    r"check\s+constraints\b|"
    r"formulate\b|"
    r"(?:\d+[.)]\s*)?(?:\*+\s*)?final\s+polish\b|"
    r"(?:\d+[.)]\s*)?(?:\*+\s*)?drafting\s+the\s+final\s+response\b|"
    r"(?:[-*]\s*)?\*?\s*draft\s*\d+\b|"
    r"\d+\s*(?:and\s*)?(?:<=|<|>=|>)\s*\d+\s*words?\b|"
    r"\d+\s*,\s*(?:<=|<|>=|>)?\s*\d+\s*words?\b|"
    r"\d+\s*words?\)"
    r")",
    re.IGNORECASE,
)
_PARTIAL_FINISHED_LINE_META_PREFIX_RE = re.compile(
    r"^\s*(?:\d{1,2}\s*(?:$|,|and\b|words?\b|\))|check\s*(?:$|c)|formulate\s*$|"
    r"(?:\d+[.)]\s*)?(?:\*+\s*)?final\s*(?:$|p)|"
    r"(?:\d+[.)]\s*)?(?:\*+\s*)?drafting\s*(?:$|the\b)|"
    r"(?:[-*]\s*)?\*?\s*draft\s*(?:$|\d*))",
    re.IGNORECASE,
)
_QUOTED_FINISHED_LINE_RE = re.compile(r'"(?P<body>[^"\n]{8,220})(?:"|$)')
_ORPHAN_CITATION_TAIL_PREFIX_RE = re.compile(
    r"^\s*(?:[a-z]+:[^\s\]]+|\d+(?:\.\d+)?)\]\s*",
    re.IGNORECASE,
)
_BROKEN_VOICE_FRAGMENT_PREFIX_RE = re.compile(r"^\s*(?:\]|:\*)")
_BROKEN_WORD_COUNT_TAIL_RE = re.compile(r"\(\s*\d+\s+words?\s*$", re.IGNORECASE)
_CHECK_CONSTRAINTS_PREFIX_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*+\s*)?check\s+constraints\s*[:.)*-]*\s*",
    re.IGNORECASE,
)
_FORMULATE_PREFIX_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*+\s*)?formulate\s*[:.)*-]*\s*",
    re.IGNORECASE,
)
_DRAFT_PREFIX_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*+\s*)?draft\s*\d+\s*(?:\*+\s*)?[:.)-]*\s*",
    re.IGNORECASE,
)
_FINAL_POLISH_PREFIX_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\d+[.)]\s*)?(?:\*+\s*)?"
    r"final\s+polish(?:\s*\([^)]*\))?\s*(?:\*+\s*)?[:.)*-]*\s*",
    re.IGNORECASE,
)
_DRAFTING_FINAL_RESPONSE_PREFIX_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\d+[.)]\s*)?(?:\*+\s*)?"
    r"drafting\s+the\s+final\s+response(?:\s*\([^)]*\))?\s*(?:\*+\s*)?[:.)*-]*\s*",
    re.IGNORECASE,
)
_TEXT_PREFIX_RE = re.compile(r"^\s*(?:final\s+)?text\s*[:\n]\s*", re.IGNORECASE)
_WORD_COUNT_PREFIX_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*+\s*)?(?:"
    r"\d+\s*(?:and\s*)?(?:<=|<|>=|>)\s*\d+\s*words?\??|"
    r"\d+\s*,\s*(?:<=|<|>=|>)?\s*\d+\s*words?\)?\??|"
    r"\d+\s*words?\)"
    r")\s*(?:yes\s*\([^)]*\)\.?)?\s*(?:[:.)*-]|\*)*\s*",
    re.IGNORECASE,
)
_SPEAKER_PREFIX_RE = re.compile(r"^\s*(?:sven|you)\s*[:.)-]\s*", re.IGNORECASE)
_META_LINE_RESIDUE_RE = re.compile(
    r"(?:<=|>=|<\s*\d+\s*words|\b\d+\s*words?\b|\bconstraints?\b|\bdraft\b|"
    r"\bword\s+count\b|\bformulate\b|\bfinal\s+polish\b|\brefine\b|"
    r"\boption\s+[ab]\b|\bground\s+citation\b|\bgrounding\s+refs?\b|"
    r"\bexact\s+grounding\b|"
    r"\bdj\s+terminology\b|\bdj-to-dj\b|\bor\s+similar\b|\bdo\s+i\s+have\b|"
    r"\bomit\s+the\s+citation\b|\bprompt\s+mentions\b|\bjson\b|\bshould_speak\b|"
    r"\bfriend_not_narrator\b|"
    r"\bgrounded_not_fabricated\b)",
    re.IGNORECASE,
)
_META_TAIL_RESIDUE_RE = re.compile(r"(?:^|[*.]\s*)\*?\s*check\b", re.IGNORECASE)
_BROKEN_CITATION_TAIL_FRAGMENT_RE = re.compile(
    r"^\s*(?:[.)]?\d+(?:\.\d+)?|[a-z_][a-z0-9_:@.-]*)\]\s*`?",
    re.IGNORECASE,
)
_INCOMPLETE_HEADPHONE_TAIL_RE = re.compile(
    r"\b(?:out\s+of|before\s+you\s+bring|before\s+you\s+layer|that\s+\d+|"
    r"(?:let|bring|lift|open|roll|pull|ride|ease)\s+(?:the\s+)?"
    r"(?:highs?|mids?|lows?|sub|top\s+end|low\s+end|midrange|treble|bass)|"
    r"bring|start|with|into|from|to|for|and|then|the|that|new)$",
    re.IGNORECASE,
)
_PACKET_FRAGMENT_PREFIX_RE = re.compile(
    r"^\s*(?:`?[a-z_][a-z0-9_:-]*=\S+|"
    r"\[(?:ev|aud|midi|track|screen|mix|key|recall|exemplar|cue|judge):[^\]]*$|"
    r"`?[a-z][a-z0-9_]*:[_a-z0-9:@.-]+`?|"
    r"[+-]?\d+(?:\.\d+)?`\s*,\s*`[a-z_][a-z0-9_:-]*=)",
    re.IGNORECASE,
)
_PARTIAL_PACKET_FRAGMENT_PREFIX_RE = re.compile(r"^\s*(?:`|[+-]?\d+\.\d*)")

# Events where the screen Part is ALWAYS skipped, even if a screen frame is
# available. This is independent from the audio window size: MIX_MOVE needs
# the full master-output ear, but screen pixels still over-prime it to invent
# UI/source details.
SCREEN_SKIP_EVENTS: frozenset[str] = frozenset({"MIX_MOVE", "HEARTBEAT"})

# Runtime diet audio window. Keep the short payload only for low-value chatter.
DIET_AUDIO_SECONDS: float = 6.0
# Current direct Gemini credentials accept the exact live prompt/audio shape up
# to 48s and reject the old 60s inline WAV with PERMISSION_DENIED. Keep the
# rolling capture buffer larger, but bound the Part sent to the live brain.
COACH_AUDIO_SECONDS: float = min(INVOKE_AUDIO_SECONDS, 48.0)
RUNTIME_DIET_EVENTS: frozenset[str] = frozenset({"HEARTBEAT"})
DECK_AUDIO_PART_SECONDS_DEFAULT: float = 3.0
DECK_AUDIO_PART_MIN_RMS: float = 0.003
DECK_AUDIO_PART_AUTO_EVENTS: frozenset[str] = frozenset(
    {"MIX_MOVE", "TRANSITION_OPPORTUNITY", "KEY_CLASH", "MANUAL"}
)


_TRUTHY_ENV_VALUES = ("1", "true", "yes", "on")
_FALSEY_ENV_VALUES = ("0", "false", "no", "off")


def _env_flag_enabled(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in _TRUTHY_ENV_VALUES:
        return True
    if value in _FALSEY_ENV_VALUES or value == "":
        return False
    return default


def _sven_probe_mode_enabled() -> bool:
    return _env_flag_enabled("VIBEMIX_SVEN_PROBE_MODE") or _env_flag_enabled(
        "VIBEMIX_SVEN_QA_SET"
    )


def _anti_slop_runtime_enabled() -> bool:
    return _env_flag_enabled("VIBEMIX_ANTI_SLOP", default=not _sven_probe_mode_enabled())


def _runtime_coach_audio_seconds() -> float:
    raw = os.environ.get("VIBEMIX_LIVE_COACH_AUDIO_SECONDS", "").strip()
    default = COACH_AUDIO_SECONDS
    if not raw:
        return float(default)
    try:
        seconds = float(raw)
    except (TypeError, ValueError):
        return float(default)
    return float(min(max(seconds, 3.0), COACH_AUDIO_SECONDS))


def _stale_reaction_age_budget_s() -> float:
    """Late-line-blurt freshness budget (Invariant #3 — trust the audio).

    A reaction whose triggering event fired longer than this many seconds ago is
    stale: its moment in the set is gone, so voicing it now blurts an
    out-of-context line. Default 12.0s mirrors coach_loop's in-flight
    stale-clear threshold (runtime/coach.py:776) — if an in-flight generation
    older than 12s is already force-cleared, a reaction whose event fired >12s
    ago is stale enough never to reach TTS. Tuned far above normal Gemini+TTS
    latency (~1-3s) so a timely line is never dropped, and well under the 60s
    COACH_PLAYOUT_TIMEOUT_S. Override: ``VIBEMIX_STALE_REACTION_AGE_BUDGET_S``.
    """
    raw = os.environ.get("VIBEMIX_STALE_REACTION_AGE_BUDGET_S", "").strip()
    if not raw:
        return 12.0
    try:
        return max(1.0, float(raw))
    except (TypeError, ValueError):
        return 12.0


def _has_grounded_receipt_extra(extra: dict[str, Any]) -> bool:
    return any(
        isinstance(extra.get(key), str) and bool(str(extra.get(key)).strip())
        for key in _GROUNDED_RECEIPT_EXTRA_KEYS
    )


def _should_guard_option_scaffold(ev_tag: str, ev_extra: dict[str, Any]) -> bool:
    return ev_tag == "TRACK_CHANGE" and _has_grounded_receipt_extra(ev_extra)


def _unsupported_band_intensity_reason(
    text: str,
    state: MusicState,
    moves: list[str] | tuple[str, ...],
    *,
    event_type: str | None,
) -> str | None:
    """Return a reason when move-less abundance talk contradicts live bands."""

    raw = str(text or "").strip()
    if not raw or moves or not _BAND_ABUNDANCE_RE.search(raw):
        return None
    bands = getattr(state, "bands", {})
    if not isinstance(bands, dict):
        bands = {}
    event = str(event_type or "").strip().upper()
    for band, alias_re in _BAND_INTENSITY_ALIAS_RE.items():
        if not alias_re.search(raw):
            continue
        if event in _BAND_INTENSITY_EVENT_SUPPORT.get(band, frozenset()):
            continue
        try:
            value = float(bands.get(band, 0.0))
        except (TypeError, ValueError):
            value = 0.0
        if value != value:
            value = 0.0
        if value < _BAND_ABUNDANCE_FLOOR[band]:
            return f"{band}_band_below_claim_floor"
    return None


def _band_intensity_guard_summary(state: MusicState, *, event_type: str | None) -> str:
    bands = getattr(state, "bands", {})
    if not isinstance(bands, dict):
        bands = {}
    values: list[str] = []
    for band in ("sub", "low", "mid", "high"):
        try:
            value = float(bands.get(band, 0.0))
        except (TypeError, ValueError):
            value = 0.0
        if value != value:
            value = 0.0
        values.append(f"{band}={value:.2f}")
    event = str(event_type or "").strip().upper() or "UNKNOWN"
    return f"event={event}; bands={','.join(values)}"


def _starts_option_scaffold(text: str) -> bool:
    return bool(_OPTION_SCAFFOLD_PREFIX_RE.match(text or ""))


def _repair_option_scaffold_line(text: str) -> str | None:
    """Return the first model-provided option as one spoken line, or None."""

    if not _starts_option_scaffold(text):
        return None
    joined = " ".join(part.strip() for part in (text or "").splitlines() if part.strip())
    match = _OPTION_A_RE.match(joined)
    if match is None:
        return None
    body = match.group("body").strip()
    body = _OPTION_B_SPLIT_RE.split(body, maxsplit=1)[0].strip()
    body = body.strip(" \"'")
    if not body or _starts_option_scaffold(body):
        return None
    if len(body.split()) < 2:
        return None
    return body


def _starts_finished_line_meta_scaffold(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    if _looks_like_broken_voice_fragment(stripped):
        return True
    without_tail = _strip_orphan_citation_tail(stripped)
    if without_tail != stripped:
        return True
    if _META_LINE_RESIDUE_RE.search(without_tail):
        return True
    return bool(_FINISHED_LINE_META_PREFIX_RE.match(stripped))


def _could_be_finished_line_meta_scaffold(text: str) -> bool:
    if _starts_finished_line_meta_scaffold(text):
        return True
    stripped = (text or "").strip()
    if not stripped:
        return False
    if _looks_like_broken_voice_fragment(stripped):
        return True
    without_tail = _strip_orphan_citation_tail(stripped)
    if without_tail != stripped:
        return True
    lowered = stripped.lower()
    return (
        "check constraints".startswith(lowered)
        or "formulate".startswith(lowered)
        or bool(_PARTIAL_FINISHED_LINE_META_PREFIX_RE.match(without_tail))
    )


def _starts_unspoken_packet_fragment(text: str) -> bool:
    return bool(_PACKET_FRAGMENT_PREFIX_RE.match(text or ""))


def _could_be_unspoken_packet_fragment(text: str) -> bool:
    return _starts_unspoken_packet_fragment(text) or bool(
        _PARTIAL_PACKET_FRAGMENT_PREFIX_RE.match((text or "").strip())
    )


def repair_finished_headphone_line(text: str) -> str | None:
    """Strip model-authored drafting wrappers without inventing a replacement."""

    stripped = (text or "").strip()
    if not stripped:
        return None
    stripped = _strip_orphan_citation_tail(stripped).strip()
    if not stripped:
        return None
    stripped = _TEXT_PREFIX_RE.sub("", stripped, count=1).strip()
    if not stripped:
        return None
    if _looks_like_broken_voice_fragment(stripped):
        return None
    if _starts_unspoken_packet_fragment(stripped):
        return None
    if _starts_option_scaffold(stripped):
        return _repair_option_scaffold_line(stripped)
    if not _starts_finished_line_meta_scaffold(stripped):
        return _strip_headphone_line_edge_quotes(stripped)

    joined = " ".join(part.strip() for part in stripped.splitlines() if part.strip())
    for match in _QUOTED_FINISHED_LINE_RE.finditer(joined):
        if not match.group(0).rstrip().endswith('"'):
            continue
        candidate = _clean_finished_line_candidate(match.group("body"))
        if candidate:
            return candidate

    candidate = joined
    for _ in range(6):
        before = candidate
        candidate = _CHECK_CONSTRAINTS_PREFIX_RE.sub("", candidate, count=1)
        candidate = _FORMULATE_PREFIX_RE.sub("", candidate, count=1)
        candidate = _WORD_COUNT_PREFIX_RE.sub("", candidate, count=1)
        candidate = _DRAFT_PREFIX_RE.sub("", candidate, count=1)
        candidate = _FINAL_POLISH_PREFIX_RE.sub("", candidate, count=1)
        candidate = _DRAFTING_FINAL_RESPONSE_PREFIX_RE.sub("", candidate, count=1)
        if candidate == before:
            break
    return _clean_finished_line_candidate(candidate)


def _line_for_grounded_citation_repair(text: str) -> str | None:
    """Return a clean headphone line eligible for appending an existing cite."""

    candidate_text = text or ""
    if _has_unclosed_bracket_tail(candidate_text):
        candidate_text = candidate_text.rsplit("[", 1)[0].rstrip()
    candidate = repair_finished_headphone_line(candidate_text)
    if not candidate:
        return None
    if parse_citations(candidate):
        return None
    if _META_LINE_RESIDUE_RE.search(candidate) or re.search(
        r"^(?:thought|thinking)\b|^thought(?=[A-Z])|"
        r"\b(?:citation|bracket|grounding_refs?|scratchpad)\b",
        candidate,
        re.IGNORECASE,
    ):
        return None
    if _looks_like_broken_voice_fragment(candidate):
        return None
    if len(candidate.split()) < 4:
        return None
    if candidate[-1] not in ".!?":
        candidate += "."
    return candidate


def _valid_repair_citation_from_texts(
    texts: tuple[object, ...],
    *,
    linter: CitationLinter,
    snapshot: dict[str, dict[str, tuple[float, ...]]] | None,
) -> str | None:
    """Pick the first already-grounded citation atom from trusted prompt text."""

    if not snapshot:
        return None
    for value in texts:
        if not isinstance(value, str) or not value.strip():
            continue
        for source, body in parse_citations(value):
            citation = f"[{source}:{body}]"
            if linter.check(citation, snapshot, mode="live").valid:
                return citation
    return None


def _event_grounding_ref_citation(
    ev: Event | None,
    snapshot: dict[str, dict[str, tuple[float, ...]]] | None,
    *,
    linter: CitationLinter,
) -> str | None:
    if ev is None or not snapshot:
        return None
    observed = snapshot.get("ev", {}).get(ev.type)
    if not observed:
        return None
    try:
        latest = max(float(t) for t in observed)
    except (TypeError, ValueError):
        return None
    citation = f"[ev:{ev.type}@{latest:.1f}]"
    return citation if linter.check(citation, snapshot, mode="live").valid else None


def _repair_missing_live_citation(
    text: str,
    *,
    ev: Event | None,
    ev_extra: dict[str, Any],
    text_prompt: str,
    linter: CitationLinter,
    snapshot: dict[str, dict[str, tuple[float, ...]]] | None,
) -> tuple[str, str] | None:
    """Append one existing grounded citation when the model omitted it.

    This is deliberately narrower than a fallback: it only repairs an otherwise
    clean headphone line and only with a citation already present in the event
    payload, current event registry, or prompt evidence. The linter re-checks
    the repaired text before the caller may use it.
    """

    if parse_citations(text):
        return None
    candidate = _line_for_grounded_citation_repair(text)
    if not candidate:
        return None
    receipt_values = tuple(
        ev_extra.get(key)
        for key in _GROUNDED_RECEIPT_EXTRA_KEYS
        if isinstance(ev_extra.get(key), str)
    )
    citation = _valid_repair_citation_from_texts(
        (*receipt_values, text_prompt),
        linter=linter,
        snapshot=snapshot,
    )
    if citation is None:
        citation = _event_grounding_ref_citation(ev, snapshot, linter=linter)
    if citation is None:
        return None
    repaired = f"{candidate} {citation}"
    if not linter.check(repaired, snapshot, mode="live").valid:
        return None
    return repaired, citation


def _strip_orphan_citation_tail(text: str) -> str:
    """Remove a leading half-citation tail such as ``108.0]``."""

    return _ORPHAN_CITATION_TAIL_PREFIX_RE.sub("", text or "", count=1)


def _looks_like_broken_voice_fragment(text: str) -> bool:
    """Return True for clipped model fragments that should not be repaired."""

    stripped = (text or "").strip()
    return bool(
        _BROKEN_VOICE_FRAGMENT_PREFIX_RE.match(stripped)
        or _BROKEN_WORD_COUNT_TAIL_RE.search(stripped)
        or _INCOMPLETE_HEADPHONE_TAIL_RE.search(stripped)
    )


def _strip_headphone_line_edge_quotes(text: str) -> str | None:
    candidate = (text or "").strip()
    if (
        _BROKEN_CITATION_TAIL_FRAGMENT_RE.match(candidate)
        or _META_LINE_RESIDUE_RE.search(candidate)
        or _META_TAIL_RESIDUE_RE.search(candidate)
        or _INCOMPLETE_HEADPHONE_TAIL_RE.search(candidate)
    ):
        return None
    for quote in ('"', "`"):
        while candidate.startswith(quote):
            candidate = candidate[1:].lstrip()
        while candidate.endswith(quote):
            candidate = candidate[:-1].rstrip()
    if _INCOMPLETE_HEADPHONE_TAIL_RE.search(candidate):
        return None
    return candidate or None


def _has_unclosed_bracket_tail(text: str) -> bool:
    stripped = (text or "").strip()
    return "[" in stripped and last_balanced_position(stripped) < len(stripped)


def _clean_finished_line_candidate(text: str) -> str | None:
    candidate = " ".join(part.strip() for part in (text or "").splitlines() if part.strip())
    candidate = candidate.strip(" \t\r\n-*:_\"'`")
    candidate = _SPEAKER_PREFIX_RE.sub("", candidate).strip(" \t\r\n-*:_\"'`")
    if not candidate:
        return None
    first_sentence = re.split(r"(?<=[.!?])\s+", candidate, maxsplit=1)[0].strip()
    if first_sentence:
        candidate = first_sentence
    candidate = candidate.strip(" \t\r\n-*:_\"'`")
    if not candidate or len(candidate.split()) < 2:
        return None
    if _starts_option_scaffold(candidate) or _starts_finished_line_meta_scaffold(candidate):
        return None
    if re.match(r"^(?:yes|no)\b", candidate, re.IGNORECASE):
        return None
    if _META_LINE_RESIDUE_RE.search(candidate):
        return None
    return candidate

# Env-var names — public contract, surfaced in CLI / Settings UI in Phase 11/12.
ENV_SKILL_LEVEL = "VIBEMIX_SKILL_LEVEL"
ENV_MODE = "VIBEMIX_MODE"
ENV_GEMINI_DECK_AUDIO_PARTS = "VIBEMIX_GEMINI_DECK_AUDIO_PARTS"
ENV_GEMINI_DECK_AUDIO_PART_SECONDS = "VIBEMIX_GEMINI_DECK_AUDIO_PART_SECONDS"
# Phase 13-05 — mood persona env override. Default "hype-man" preserves
# Phase 10 backward compat (the byte-identical-to-v4 invariant) — the
# Coach prompt template renders the mood only for COACH cells.
ENV_MOOD = "VIBEMIX_MOOD"

# Defaults — preserve Phase 4 v4 behavior for callers that don't set env vars.
DEFAULT_SKILL_LEVEL = "intermediate"
DEFAULT_MODE = "hype"
DEFAULT_MOOD = "hype-man"

# Plan 24-02 — overlay-highlight defaults.
# 1300ms = 200ms fade-in + 800ms hold + 300ms fade-out per CDJ Whisper v5
# ring animation timing. Matches the Rust overlay.html CSS keyframe.
OVERLAY_DURATION_MS: int = 1300
OVERLAY_COLOR: str = "amber"

# Plan 41-04 — silence-pad payload pushed to ``PlaybackQueue`` when a
# speculatively-emitted head is invalidated by the post-stream gate
# (slop / citation_failure). 500ms of 24kHz int16 mono zero-fill ==
# 24000 bytes. The pad replaces the audio that would have been the
# trailing slop; the LiveKit OPUS pipeline plays it as ~half a second of
# audible silence — a perceptible "cut" rather than a hard click.
#
# Per Pitfall 8: if the LiveKit TTS path has already committed the head
# audio frames into the OPUS encoder, the silence-pad APPENDS to the
# queue — it does NOT preempt frames already in flight. The realistic
# user experience is "head plays, then a brief silence where the slop
# would have been". The cleaner cancel (mid-utterance cut) is documented
# as a known degrade — see CONTEXT.md Open Q2.
SILENCE_PAD_MS: int = 500
SILENCE_PAD_BYTES: int = 24000 * 2 * SILENCE_PAD_MS // 1000  # 24kHz * 2B * 0.5s = 24000B

# Plan 44-03 / LAUNCH-02 — citation-strip chip cap. The live UI renders a
# small `[<verb> @ <mm:ss>]` chip per cited evidence event below each AI
# reaction; capping at 3 keeps the strip readable when the LLM packs a turn
# with citations. Per CONTEXT.md: "2-3 word evidence tag" — implies a small
# chip count. The cap is enforced at the structured-payload boundary
# (_build_citation_strip), NOT in the renderer — the wire stays clean.
CITATION_STRIP_MAX_CHIPS: int = 3

# Plan 44-03 / LAUNCH-02 — verb word cap. The KEY portion of an `ev:KEY@t`
# citation atom is upper-snake-case (e.g. `KICK_SWAP`, `BAND_SHIFT_HIGH`).
# We split on `_`, lowercase, take the first 1-3 tokens. Multi-token KEYS
# (`BAND_SHIFT_HIGH` → "band shift") get trimmed to keep chip width tight.
CITATION_VERB_MAX_WORDS: int = 3

# Phase 66 (COPILOT-02) — coach-tier recall-callback cooldown. ≥120s
# between any two recall callbacks per the CONTEXT.md Area 1 Q3 decision
# (66-CONTEXT.md: "rare-and-earned"; two recall moves in a single set
# are the ceiling — not a floor). The structural max-1-per-turn cap is
# enforced by the prompt fragment template ("cite [recall:<id>] EXACTLY
# ONCE") + the registry strict-subset invariant + the single-emit-stream-
# per-turn shape; the cooldown is the multi-turn pacing knob.
#
# This is a SEPARATE concern from ``EventDetector._cooldown_ok`` /
# ``audio/constants.py::MIN_EVENT_GAP_PER_TYPE``: that cooldown gates
# whether the EVENT fires at all (so the live reaction still happens);
# this cooldown gates whether the recall-callback prompt fragment is
# threaded for an event that already fired. Mixing them couples two
# concerns — see 66-RESEARCH.md §Anti-Patterns ("Putting the cooldown
# in EventDetector._cooldown_ok").
#
# One-line-tunable contract: a Kaan-ear pass on the real corpus
# (§RECALL-EAR in KAAN-ACTION-LEGAL.md) may re-tune this value via a
# single edit here — no surrounding wiring depends on the literal.
RECALL_CALLBACK_COOLDOWN_S: float = 120.0


def _event_live_move_labels(ev: Event | None, fallback_state: MusicState) -> tuple[str, ...]:
    """Return bounded move labels for live claim gating."""
    if ev is not None:
        raw = ev.extra.get("moves")
        if isinstance(raw, (list, tuple)):
            labels = tuple(str(label) for label in raw if str(label).strip())
            if labels:
                return labels[-3:]
        state = ev.state
    else:
        state = fallback_state

    labels: list[str] = []
    for item in getattr(state, "recent_moves", []) or []:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        age_raw, label = item[0], item[1]
        try:
            age = float(age_raw)
        except (TypeError, ValueError):
            continue
        if age <= 8.0 and str(label).strip():
            labels.append(str(label))
    return tuple(labels[-3:])


def _deck_audio_parts_mode(raw: str | None = None) -> str:
    text = str(raw if raw is not None else os.environ.get(ENV_GEMINI_DECK_AUDIO_PARTS, "auto"))
    mode = text.strip().lower()
    if mode in {"0", "false", "no", "off", "never", "disabled"}:
        return "off"
    if mode in {"1", "true", "yes", "on", "always"}:
        return "always"
    return "auto"


def _deck_audio_part_seconds(raw: object | None = None) -> float:
    value = raw if raw is not None else os.environ.get(ENV_GEMINI_DECK_AUDIO_PART_SECONDS)
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        seconds = DECK_AUDIO_PART_SECONDS_DEFAULT
    return max(1.0, min(6.0, seconds))


def _deck_audio_rms_activity(audio_capture_context: dict[str, object] | None) -> dict[str, str]:
    if not isinstance(audio_capture_context, dict):
        return {}
    raw = audio_capture_context.get("deck_audio_rms")
    if not isinstance(raw, dict):
        return {}
    activity: dict[str, str] = {}
    for side in ("A", "B"):
        value = raw.get(side)
        if value is None or isinstance(value, bool):
            continue
        try:
            rms = float(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if rms == rms and rms >= 0.0:
            activity[side] = "active" if rms >= DECK_AUDIO_PART_MIN_RMS else "silent"
    return activity


def _deck_audio_rms_active(audio_capture_context: dict[str, object] | None) -> bool:
    return any(
        activity == "active"
        for activity in _deck_audio_rms_activity(audio_capture_context).values()
    )


def _deck_audio_pcm_activity(pcm: np.ndarray) -> str:
    if pcm.size == 0:
        return "silent"
    pcm_f = pcm.astype(np.float32) / 32768.0
    rms = float(np.sqrt(np.mean(pcm_f * pcm_f)))
    return "active" if rms >= DECK_AUDIO_PART_MIN_RMS else "silent"


def _state_audio_signal_active(state: MusicState) -> bool:
    try:
        rms = float(getattr(state, "rms", 0.0) or 0.0)
    except (TypeError, ValueError, OverflowError):
        rms = 0.0
    return rms >= DECK_AUDIO_PART_MIN_RMS


def _should_skip_manual_no_evidence_llm(
    event_type: str,
    state: MusicState,
    moves: list[str] | tuple[str, ...] = (),
    *,
    audio_delta_items: list[str] | tuple[str, ...] | None = None,
    audio_capture_context: dict[str, object] | None = None,
    deck_part_activity: dict[str, str] | None = None,
) -> bool:
    """True when a manual trigger has no live evidence worth sending to Gemini."""
    if str(event_type or "").upper() != "MANUAL":
        return False
    if any(str(move).strip() for move in moves):
        return False
    if bool(getattr(state, "audible", False)) or _state_audio_signal_active(state):
        return False
    if audio_delta_items:
        return False
    if _deck_audio_rms_active(audio_capture_context):
        return False
    if any(str(value).strip().lower() == "active" for value in (deck_part_activity or {}).values()):
        return False
    return True


def _deck_audio_part_suffix(parts: list[dict[str, object]]) -> str:
    if not parts:
        return ""
    lines = []
    for part in parts:
        label = str(part.get("label") or "")
        side = str(part.get("side") or "")
        if label and side in {"A", "B"}:
            activity = str(part.get("activity") or "").strip().lower()
            suffix = f" ({activity})" if activity in {"active", "silent"} else ""
            lines.append(f"{label} = captured Deck {side} audio{suffix}")
    if not lines:
        return ""
    joined = "; ".join(lines)
    return (
        "\n\nAdditional attached deck audio: "
        f"{joined}. These Parts are configured deck-pair captures aligned with P1; "
        "use them to map deck A/deck B contribution. P1 remains the audience-truth "
        "master mix, and deck Parts are not a transition quality verdict by themselves."
    )


def _deck_audio_part_contract_labels(
    deck_part_labels: dict[str, str] | None,
    *,
    reserved_labels: tuple[str | None, ...] = (),
) -> dict[str, str]:
    if not isinstance(deck_part_labels, dict):
        return {}
    labels: dict[str, str] = {}
    for side in ("A", "B"):
        label = str(deck_part_labels.get(side) or "").strip().upper()
        if re.fullmatch(r"P[2-9][0-9]?", label):
            labels[side] = label
    if set(labels) != {"A", "B"} or labels["A"] == labels["B"]:
        return {}
    reserved = {
        label
        for label in (str(item or "").strip().upper() for item in reserved_labels)
        if re.fullmatch(r"P[2-9][0-9]?", label)
    }
    if labels["A"] in reserved or labels["B"] in reserved:
        return {}
    return labels


def _build_attached_audio_context_clause(
    state: MusicState,
    moves: list[str] | tuple[str, ...] = (),
    *,
    audio_delta_items: list[str] | tuple[str, ...] | None = None,
    audio_capture_context: dict[str, object] | None = None,
    audio_seconds: float = DIET_AUDIO_SECONDS,
    mic_part_label: str | None = None,
    lookahead_part_label: str | None = None,
    deck_part_labels: dict[str, str] | None = None,
    deck_part_activity: dict[str, str] | None = None,
    deck_part_seconds: float = DECK_AUDIO_PART_SECONDS_DEFAULT,
    lookahead_horizon_s: float = 3.0,
) -> str:
    """Return deck-grounding context adjacent to Gemini's live audio Part.

    ``AICoach.build_prompt`` already carries the full evidence packet. This
    small suffix repeats only the live audio/deck gates immediately before the
    attached P1 audio description so Gemini binds "what I hear" to "which deck
    evidence permits that claim" in the same local context window. It is
    bounded text, not a raw MIDI/screen Part.
    """
    move_items = tuple(str(item) for item in moves if str(item).strip())
    contract_deck_part_labels = _deck_audio_part_contract_labels(
        deck_part_labels,
        reserved_labels=(mic_part_label, lookahead_part_label),
    )
    context_lines: list[str] = []
    for item in (
        render_context_feed_contract(
            state,
            move_items,
            surface="gemini_p1",
            audio_seconds=audio_seconds,
            force=True,
        ),
        render_audio_part_context(
            audio_seconds=audio_seconds,
            mic_part_label=mic_part_label,
            mic_part_seconds=MIC_AUDIO_PART_SECONDS,
            lookahead_part_label=lookahead_part_label,
            deck_part_labels=deck_part_labels,
            deck_part_activity=deck_part_activity,
            deck_part_seconds=deck_part_seconds,
            lookahead_horizon_s=lookahead_horizon_s,
        ),
        render_deck_context(state, compact=True),
        render_deck_lane_context(state, compact=True),
        render_deck_reference_context(state, compact=True),
        render_deck_source_context(state, compact=True),
        render_mixer_context(state),
        render_deck_audio_context(state),
        render_deck_audio_separation_context(audio_capture_context),
        render_deck_audio_features_context(audio_capture_context),
        render_deck_audio_delta_context(audio_capture_context),
        render_deck_audio_window_context(audio_capture_context),
        render_band_env_context(state),
        render_audio_window_context(
            state,
            move_items,
            audio_seconds=audio_seconds,
            mic_part_label=mic_part_label,
            lookahead_part_label=lookahead_part_label,
            deck_part_labels=deck_part_labels,
            deck_part_activity=deck_part_activity,
            deck_part_seconds=deck_part_seconds,
            lookahead_horizon_s=lookahead_horizon_s,
            force=True,
        ),
        render_set_window_context(state, audio_seconds=audio_seconds)
        if audio_seconds >= COACH_AUDIO_SECONDS
        else None,
        _render_audio_window_map_line(
            render_audio_window_map(
                state,
                move_items,
                audio_seconds=audio_seconds,
                mic_part_label=mic_part_label,
                lookahead_part_label=lookahead_part_label,
                deck_part_labels=deck_part_labels,
                deck_part_activity=deck_part_activity,
                deck_part_seconds=deck_part_seconds,
                lookahead_horizon_s=lookahead_horizon_s,
                force=True,
            )
        ),
        render_move_context(state, move_items),
        render_deck_change_context(state, move_items),
        render_move_effect_context(
            state,
            move_items,
            audio_delta_items=audio_delta_items,
            audio_capture_context=audio_capture_context,
        ),
        render_live_evidence_context(
            state,
            move_items,
            audio_delta_items=audio_delta_items,
            audio_capture_context=audio_capture_context,
        ),
    ):
        if item:
            context_lines.append(item)

    policy, reason = live_claim_policy(
        state,
        move_items,
        audio_capture_context=audio_capture_context,
        audio_delta_items=audio_delta_items,
        deck_audio_parts_attached=bool(contract_deck_part_labels),
    )
    policy_fields = [f"policy={policy}"]
    if reason:
        policy_fields.append(f"reason={reason}")
    if policy in {"blocked", "watch_not_claim"}:
        policy_fields.append("rule=do_not_claim_transition_blend_handoff")
    elif policy == "candidate_not_verdict":
        policy_fields.append("rule=candidate_not_quality_verdict")
    elif policy == "supported_verdict":
        policy_fields.append("rule=grounded_verdict_allowed")
    else:
        policy_fields.append("rule=multi_deck_outcome_requires_live_support")
    context_lines.append("claim_policy[" + " ".join(policy_fields) + "]")

    deck_audio_part_contract = "deck_audio_parts=not_attached."
    deck_separation_contract = "structured_text_only"
    if contract_deck_part_labels:
        deck_contract_fields = ["deck_audio_parts=attached_configured_deck_pair_refs"]
        for side in ("A", "B"):
            label = contract_deck_part_labels.get(side, "not_attached")
            activity = str((deck_part_activity or {}).get(side) or "unknown")
            deck_contract_fields.append(f"deck{side}_audio={label}")
            deck_contract_fields.append(f"deck{side}_activity={activity}")
        ordered_parts = [
            "P1",
            *sorted(
                {
                    str(label)
                    for label in (
                        mic_part_label,
                        lookahead_part_label,
                        *contract_deck_part_labels.values(),
                    )
                    if re.fullmatch(r"P[2-9][0-9]?", str(label))
                },
                key=lambda label: int(label[1:]),
            ),
        ]
        deck_contract_fields.append("part_order=" + ",".join(ordered_parts))
        deck_contract_fields.append("deck_parts_rule=reference_not_quality_verdict.")
        deck_audio_part_contract = " ".join(deck_contract_fields)
        deck_separation_contract = "deck_pair_parts"

    return (
        "\n\nAUDIO CONTEXT MAP FOR ATTACHED P1:\n"
        + "\n".join(context_lines)
        + "\nAUDIO PART CONTRACT: P1=live_global_mix isolated_decks=false "
        f"deck_separation={deck_separation_contract} audio_window_context=time_aligned "
        "deck_audio_separation_context=capture_capability "
        f"{deck_audio_part_contract}"
        + "\nAUDIO CLAIM RULE: P1 is the global live mix, not isolated deck stems. "
        "Transition/blend/drop/handoff/bridge claims require deck/live_evidence "
        "support; controller moves plus audio deltas are timing evidence, not "
        "causal or quality proof. Deck audio Parts identify per-deck contribution; "
        "they are not a score by themselves."
    )


def _render_audio_window_map_line(audio_map: dict[str, Any] | None) -> str | None:
    if not audio_map:
        return None
    anchors = audio_map.get("move_anchors")
    if isinstance(anchors, list) and anchors:
        anchor_tokens = []
        for item in anchors[:3]:
            if not isinstance(item, dict):
                continue
            token = str(item.get("token") or "move")[:96]
            relation = str(item.get("relation") or "unknown")[:32]
            age = item.get("age_s")
            if isinstance(age, (int, float)):
                anchor_tokens.append(f"{token}@-{float(age):.1f}s:{relation}")
            else:
                anchor_tokens.append(f"{token}:age_unknown")
        anchor_text = ",".join(anchor_tokens) if anchor_tokens else "none"
    else:
        anchor_text = "none"

    future = audio_map.get("future") if isinstance(audio_map.get("future"), dict) else {}
    future_text = "not_attached"
    if future.get("part") and isinstance(future.get("span_s"), list):
        span = future.get("span_s") or [0.0, 0.0]
        try:
            future_text = f"{future.get('part')}:{float(span[0]):.1f}..+{float(span[1]):.1f}"
        except (TypeError, ValueError, IndexError):
            future_text = str(future.get("part"))

    deck_part_span = audio_map.get("deck_part_span_s")
    deck_span_text = ""
    if isinstance(deck_part_span, list) and len(deck_part_span) >= 2:
        try:
            deck_span_text = f":{float(deck_part_span[0]):.1f}..{float(deck_part_span[1]):.1f}"
        except (TypeError, ValueError):
            deck_span_text = ""

    def _deck_audio_text(key: str) -> str:
        value = str(audio_map.get(key) or "not_attached").strip()
        if value.startswith("P") and value[1:].isdigit():
            return value + deck_span_text
        return value or "not_attached"

    per_deck_audio = str(audio_map.get("per_deck_audio") or "structured_text_only")
    duplicate_audio = str(audio_map.get("duplicate_audio") or "same_master_not_deck_split")

    return (
        "audio_window_map["
        "P1=master_global_mix heard=true old=pre_s current=current_s action=action_s "
        "future="
        + future_text
        + " deckA_audio="
        + _deck_audio_text("deckA_audio")
        + " deckB_audio="
        + _deck_audio_text("deckB_audio")
        + " per_deck_audio="
        + per_deck_audio
        + " duplicate_audio="
        + duplicate_audio
        + " anchors="
        + anchor_text
        + " rule=time_alignment_not_outcome_verdict]"
    )


def _build_recall_query_context(ev: Event) -> str:
    """Return ingest-signature context fields for memory recall queries."""
    state = ev.state
    moves = _event_live_move_labels(ev, state)
    audio_delta_items = render_audio_delta_items(state)
    extra = ev.extra if isinstance(ev.extra, dict) else {}
    maybe_audio_capture_context = extra.get("audio_capture_context")
    audio_capture_context = (
        maybe_audio_capture_context if isinstance(maybe_audio_capture_context, dict) else None
    )
    fields: list[tuple[str, object | None]] = [
        (
            "context_feed",
            render_context_feed_contract(
                state,
                moves,
                surface="gemini_recall_query",
                audio_seconds=DIET_AUDIO_SECONDS,
            ),
        ),
        ("deck_lane", render_deck_lane_context(state)),
        ("deck_ref", render_deck_reference_context(state)),
        ("deck_source", render_deck_source_context(state, compact=True)),
        ("deck_audio", render_deck_audio_context(state)),
        (
            "deck_audio_separation",
            render_deck_audio_separation_context(audio_capture_context),
        ),
        ("deck_audio_features", render_deck_audio_features_context(audio_capture_context)),
        ("deck_audio_delta", render_deck_audio_delta_context(audio_capture_context)),
        ("deck_audio_window", render_deck_audio_window_context(audio_capture_context)),
        ("band_env", render_band_env_context(state)),
        (
            "audio_window",
            render_audio_window_context(
                state,
                moves,
                audio_seconds=DIET_AUDIO_SECONDS,
            ),
        ),
        (
            "live_evidence",
            render_live_evidence_context(
                state,
                moves if moves else None,
                audio_delta_items=audio_delta_items,
                audio_capture_context=audio_capture_context,
            ),
        ),
    ]
    if moves:
        fields.extend(
            [
                ("move", render_move_context(state, moves)),
                (
                    "move_effect",
                    render_move_effect_context(
                        state,
                        moves,
                        audio_delta_items=audio_delta_items,
                        audio_capture_context=audio_capture_context,
                    ),
                ),
            ]
        )
    if audio_delta_items:
        fields.append(("audio_delta", audio_delta_items))

    rendered: list[str] = []
    for name, value in fields:
        if name == "audio_window":
            cap = 480
        elif name == "live_evidence":
            cap = 640
        elif name == "context_feed":
            cap = 420
        else:
            cap = 240
        field = _recall_query_field(value, cap=cap)
        if field != "none":
            rendered.append(f"{name}={field}")
    return " | ".join(rendered)


def _recall_query_field(value: object | None, *, cap: int = 240) -> str:
    if isinstance(value, (list, tuple)):
        raw = "; ".join(str(item) for item in value[:4] if item)
    else:
        raw = str(value) if value else ""
    raw = " ".join(raw.split()).replace("|", "/")
    return raw[:cap] if raw else "none"


def _build_citation_strip(
    *,
    reaction_text: str,
    registry: EvidenceRegistry,
) -> list[dict]:
    """Build the structured chip-strip payload for an AI reaction.

    Plan 44-03 / LAUNCH-02. Parses citation atoms off ``reaction_text``
    using the existing ``parse_citations`` grammar (EvidenceRegistry's
    locked EBNF), looks each atom up in the registry, and returns a list
    of `{event_id, verb, timestamp_s}` dicts ready for the WS broadcast.

    Contract (pinned by tests/agent/test_citation_strip_emit.py):

    * ``event_id`` — the full citation atom prefixed with source, e.g.
      ``"ev:KICK_SWAP@45.2"``. The UI uses this as the click→debrief
      deep-link key (the debrief timeline resolves it back to a region).
    * ``verb`` — 1-3 word lowercase label derived from the KEY portion
      of the atom body (``KICK_SWAP@45.2`` → ``"kick swap"``). Cap at
      3 words to keep chip text terse.
    * ``timestamp_s`` — the recorded session-relative time at which the
      registry observed the event. Sourced from the registry, NOT
      parsed from the citation body (anti-hallucination: the body is
      the LLM's claim; the registry is the truth).

    Cap: at most ``CITATION_STRIP_MAX_CHIPS`` chips per reaction; chips
    beyond the cap are dropped silently (first-in-text-wins).

    Anti-hallucination rule (LAUNCH-02 white-space §6.2): citations that
    do NOT resolve to a registry observation are dropped — NO chip is
    emitted for an invented citation. Empty input → empty list (not
    None) so the WS payload type stays stable across reactions.

    Sources currently supported for chip derivation: ``ev``, ``mix``,
    ``midi``, ``key``. Other sources (``aud``, ``track``, ``screen``)
    parse correctly but do not yield chips — they're either too
    noisy (``aud``) or carry no obvious DJ-action verb (``track``). v2.x
    may widen this set; v1 stays narrow per the "no scope creep" rule.

    ``key`` (Phase 59 / DECK-03) is the deck harmonic source, body
    ``<deck>:<camelot>`` (e.g. ``A:8A``). It is existence-only — the
    registry key is the FULL ``A:8A`` body (NOT a ``KEY@t`` form), so the
    lookup uses the body verbatim and the chip ``timestamp_s`` is sourced
    from the registry observation, NEVER from the citation body (the
    anti-hallucination contract — the body is the LLM's claim, the registry
    is the truth). The verb is a fixed ``"key"`` label (the deck + camelot
    detail lives in ``event_id`` for the click→debrief deep-link).

    Args:
        reaction_text: The full AI reaction text returned by the LLM
            (post-stream-completion, pre-emit). May contain zero or
            many bracketed citation atoms in the locked EBNF grammar.
        registry: The live :class:`EvidenceRegistry` (snapshot is taken
            internally — caller does not need to snapshot first).

    Returns:
        Ordered list (text order) of chip dicts. Empty list when no
        citation atom resolves to a registry observation. Never None.
    """
    snapshot = registry.snapshot()
    chips: list[dict] = []
    for source, body in parse_citations(reaction_text):
        if len(chips) >= CITATION_STRIP_MAX_CHIPS:
            break  # cap reached — drop the rest silently
        # Source allow-list — only sources with a clear "DJ action" verb
        # yield UI chips. Quiet sources (aud/screen) parse but do
        # not surface as user-visible evidence tags.
        #
        # Phase 66 (COPILOT-01) — ``recall`` added as the fifth allow-list
        # entry. The Phase 65 deferral comment that previously sat at this
        # site ("do NOT add `recall`… the recall chip is Phase 66") is
        # discharged here: the recall registration loop at
        # ``llm_node`` line ~770 writes ``("recall", record_id, t_session)``
        # BEFORE the snapshot below, so a grounded ``[recall:<id>]`` resolves
        # like any other source and an unregistered (fabricated) ``[recall:
        # <unregistered>]`` falls through the existing ``if not timestamps:
        # continue`` guard with strip == [] (same final state as the
        # Phase 65 anti-poisoning gate would produce via the linter
        # whole-turn strip — defense in depth at two tiers).
        #
        # Phase 93 (EXEMPLAR-05) — ``exemplar`` added as the sixth allow-list
        # entry (mirrors v6 commit 0bfc8bd0 for [recall:]). The
        # ``ExemplarFinder.find()`` registration writes
        # ``("exemplar", track_id, t_session)`` BEFORE the LLM emits the
        # cite (Plan 93-04 wiring), so a grounded ``[exemplar:<id>]``
        # resolves like any other source and an unregistered (fabricated)
        # ``[exemplar:<bogus>]`` falls through the same ``if not timestamps:
        # continue`` guard with strip == [] (defense in depth at two tiers:
        # the Phase 20 CitationLinter strips the WHOLE turn upstream, and
        # this gate drops the chip downstream).
        # Phase 96 (CURR-3.07) — ``cue`` added as the seventh allow-list
        # entry. state/refresh.py registers ``("cue", anchor_id, t_session)``
        # BEFORE the LLM emits the cite so a grounded ``[cue:<id>]``
        # resolves like any other source and an unregistered (fabricated)
        # ``[cue:<unregistered>]`` falls through the existing
        # ``if not timestamps: continue`` guard with strip == [] (same
        # final state as the linter whole-turn strip — defense in depth
        # at two tiers).
        if source not in ("ev", "mix", "midi", "key", "recall", "exemplar", "cue", "judge"):
            continue
        # Registry lookup uses the body verbatim (KEY@t form). Drop the
        # chip when the registry has no matching observation — closes
        # "invented timestamps" hallucination class. Body is the full
        # body string (e.g. "KICK_SWAP@45.2"), used as the registry key.
        inner = snapshot.get(source, {})
        timestamps = inner.get(body)
        if not timestamps:
            continue  # citation parsed but not grounded → no chip
        # Use the FIRST recorded timestamp for the chip — multiple writes
        # at the same key would arrive from cooldown bypass paths, but
        # the first is the authoritative "when did this event fire".
        timestamp_s = float(timestamps[0])
        # Derive verb from the KEY portion of the body.
        if source == "key":
            # Phase 59 (DECK-03): body is ``<deck>:<camelot>`` (e.g. A:8A),
            # not the ``KEY@t`` shape. The camelot detail (deck + code) lives
            # in event_id for the deep-link; the chip verb is a fixed,
            # letters-only "key" label (keeps the locked verb format
            # `^[a-z]+( [a-z]+){0,2}$` — camelot codes carry digits).
            verb = "key"
        elif source == "recall":
            # Phase 66 (COPILOT-01) — mirrors the ``key`` precedent above for
            # opaque/structured bodies. The ``recall`` body shape is
            # ``<session_id>:<seq>`` (e.g. ``20260520-2200:7``); the full
            # record_id rides in ``event_id`` for the click→debrief deep-link.
            # The chip verb is a fixed letters-only ``"recall"`` label —
            # deriving a verb from a session-date string is meaningless and
            # would leak embedding-internal values to the UI surface
            # (66-RESEARCH.md §Don't Hand-Roll). A single lowercase word
            # trivially matches the locked verb-format regex
            # ``^[a-z]+( [a-z]+){0,2}$`` (pinned by
            # tests/agent/test_citation_strip_emit.py::
            # test_verb_format_is_two_to_three_lowercase_words).
            verb = "recall"
        elif source == "exemplar":
            # Phase 93 (EXEMPLAR-05) — mirrors the ``recall`` and ``key``
            # precedents above for opaque/structured bodies. The ``exemplar``
            # body shape is ``<track_id>`` (e.g. ``library:Marlon Hoffstadt
            # - Atlas`` or ``_packaged:low:track_03``). The full track_id
            # rides in ``event_id`` for the click→tutor-context deep-link.
            # The chip verb is a fixed letters-only ``"exemplar"`` label —
            # deriving a verb from a track-id string is meaningless and
            # would leak embedding-internal values to the UI surface
            # (P93-RESEARCH.md §4-Site Mirror Pattern). A single lowercase
            # word trivially matches the locked verb-format regex
            # ``^[a-z]+( [a-z]+){0,2}$``.
            verb = "exemplar"
        elif source == "cue":
            # Phase 96 (CURR-3.07) — mirrors the ``exemplar`` / ``recall`` /
            # ``key`` precedents above for opaque/structured bodies. The
            # ``cue`` body shape is ``<anchor_id>`` (e.g.
            # ``phrase_boundary@45.2`` or ``drop@180.0``). The full anchor_id
            # rides in ``event_id`` for the click→tutor-context deep-link.
            # The chip verb is a fixed letters-only ``"cue"`` label —
            # deriving a verb from an anchor-id string would leak
            # detector-internal values to the UI surface. A single lowercase
            # word trivially matches the locked verb-format regex
            # ``^[a-z]+( [a-z]+){0,2}$``.
            verb = "cue"
        elif source == "judge":
            # v11.0 (the Vibe Judge) — mirrors the ``cue`` / ``exemplar`` /
            # ``recall`` precedents above for opaque/structured bodies. The
            # ``judge`` body shape is ``<verdict_id>`` (e.g.
            # ``transition@128.4`` or ``8A>9A@128.4``). The full verdict_id
            # rides in ``event_id`` for the click→debrief deep-link. The chip
            # verb is a fixed letters-only ``"judge"`` label — deriving a verb
            # from a verdict-id string would leak engine-internal values to the
            # UI surface. A single lowercase word trivially matches the locked
            # verb-format regex ``^[a-z]+( [a-z]+){0,2}$``.
            verb = "judge"
        elif source == "mix" and body.startswith("next_suggestion="):
            # The next-suggestion body carries an opaque library id
            # (``next_suggestion=folder:<hash>``). Keep that full id in
            # ``event_id`` for the receipt/deep-link, but render a stable
            # human-sized chip label that satisfies the cohost-reaction schema.
            verb = "next suggestion"
        else:
            # Body shape is ``KEY@t`` for ev/aud/midi/mix; partition on "@"
            # so a missing "@" (defensive: future grammar drift) falls back
            # to the full body.
            key, _, _ = body.partition("@")
            verb_tokens = key.lower().split("_")
            verb = " ".join(verb_tokens[:CITATION_VERB_MAX_WORDS])
        chips.append(
            {
                "event_id": f"{source}:{body}",
                "verb": verb,
                "timestamp_s": timestamp_s,
            }
        )
    return chips


def _resolve_prompt_cell(mood: str | None = None, learn_progress: Any | None = None) -> str:
    """Read the env vars and dispatch to the right matrix cell.

    Re-evaluated per ``DJCoHostAgent`` instantiation (no module-level
    caching) so unit tests can monkeypatch and Settings UI can hot-swap
    by re-instantiating the agent (Phase 11/12).

    Args:
        mood: Phase 13-05 mood override. When None (default), reads
            ``VIBEMIX_MOOD`` env var, falling back to ``"hype-man"``. A
            non-None ``mood`` arg wins over the env var (used by Plan
            13-06's agent-rebuild-on-mood-change path).
        learn_progress: Optional already-loaded LearnProgress. When supplied,
            a Competent-not-Mastered skill may add a fixed coach-mode aim
            fragment. The resolver never loads progress from disk by itself;
            callers must pass the session object intentionally.

    Phase 79 LENS-02 (CR-01 fix): when a shared lens is EXPLICITLY set in
    ``ConfigStore.extra["lens"]`` (the ONE selection shared with the curator),
    it resolves ``(mode, mood)`` via ``LENS_TO_MODE_MOOD`` and drives the cell —
    choosing the lens once flows here AND to the curator. The lens is the user's
    EXPLICIT persona choice, so it WINS over the auto-derived live
    ``MusicState.mood`` arg (which is NOT explicit user intent — it defaults to
    ``"hype-man"`` and is the value the production caller always passes). The
    original "lens only when ``mood is None``" guard meant the lens was silently
    dead on the live co-host path (production always passes a non-None mood);
    routing the lens read BEFORE the mood arg fixes that.

    When NO lens is set (unset/empty), the resolution is byte-identical to today
    (cold path): the ``mood`` arg (live ``MusicState.mood`` rebuild path) > env >
    ``DEFAULT_*`` (Pitfall 3: route through the one ``extra["lens"]`` read, NOT
    the orphaned ``VIBEMIX_MODE`` env).

    CR-02 fix: the persisted lens value is VALIDATED against ``LENS_TO_MODE_MOOD``
    before it is subscripted. ``read_shared_lens`` returns any non-empty string
    unvalidated, so a corrupt/foreign/hand-edited ``config.json`` (e.g.
    ``extra["lens"]="coach"`` — a valid mood but NOT a lens key) would previously
    raise an uncaught ``KeyError`` and crash agent construction. An invalid or
    unreadable lens now falls through to the cold path — no ``KeyError`` ever
    escapes.

    Raises ``ValueError`` on unknown skill, mode, or mood (fail loud —
    silent fallback would mask env-var typos).
    """
    skill = os.environ.get(ENV_SKILL_LEVEL, DEFAULT_SKILL_LEVEL)

    # Shared lens read (LENS-02). Lazy + guarded: config_store is import-light
    # but a read failure must NEVER regress the cold path. The lens is the user's
    # EXPLICIT persona axis, so it wins over the auto-derived live mood arg — but
    # ONLY when explicitly set AND valid. When unset/invalid, the cold path below
    # runs byte-identically to today (mood arg > env > DEFAULT_*).
    try:
        from vibemix.runtime.config_store import load_config
        from vibemix.runtime.settings import read_shared_lens

        lens = read_shared_lens(load_config())
    except Exception:  # pragma: no cover — guard: any read fail = cold path
        lens = None

    # One Mind S2 — taste → persona overlay tags. Lazy + guarded exactly like
    # the lens read above: load the consent-gated taste model and project it to
    # prompt-safe style tags. Any failure (no consent, no file, parse error) =
    # empty tuple = cold path with no overlay (byte-identical to today). This
    # runs on EVERY agent (re)build, so a mood-swap rebuild keeps the overlay
    # too. The projection is privacy-validated + allowlisted upstream; matrix's
    # _render_taste_overlay filters again (defense in depth) and maps only fixed
    # phrases (anti-injection). Read-only — never writes MusicState (Inv #1).
    taste_tags: tuple[str, ...] = ()
    try:
        from vibemix.intel.profile_projection import project_profile
        from vibemix.intel.taste_model import load_taste_model
        from vibemix.profile import load_consent as _load_consent
        from vibemix.runtime.config_store import app_data_dir

        _consent = bool(_load_consent())
        if _consent:
            _model = load_taste_model(
                app_data_dir() / "taste_feedback.jsonl", profile_consent=_consent
            )
            taste_tags = tuple(
                project_profile(_model, consent=_consent).get("transition_style_tags", ())
            )
    except Exception:  # pragma: no cover — any read fail = no overlay
        taste_tags = ()

    coaching_aim_skill: str | None = None
    if learn_progress is not None:
        try:
            from vibemix.learn.coaching_aim import resolve_coaching_aim_skill

            coaching_aim_skill = resolve_coaching_aim_skill(learn_progress)
        except Exception:  # pragma: no cover — any read fail = no aim
            coaching_aim_skill = None

    # CR-02: validate the persisted value against the lens enum BEFORE
    # subscripting. An unknown/foreign value (e.g. a stray mood name) falls
    # through to the cold path instead of raising a raw KeyError.
    if lens is not None:
        from vibemix.prompts.matrix import LENS_TO_MODE_MOOD

        if lens in LENS_TO_MODE_MOOD:
            mode, lens_mood = LENS_TO_MODE_MOOD[lens]
            return build_system_instruction(
                skill,
                mode,
                lens_mood,
                include_listening_fallback=False,
                include_tag_dsl=False,
                include_audio_vibe_contract=True,
                include_coach_closing=True,
                taste_persona_tags=taste_tags,
                coaching_aim_skill=coaching_aim_skill,
            )

    mode = os.environ.get(ENV_MODE, DEFAULT_MODE)
    if mood is None:
        mood = os.environ.get(ENV_MOOD, DEFAULT_MOOD)
    return build_system_instruction(
        skill,
        mode,
        mood,
        include_listening_fallback=False,
        include_tag_dsl=False,
        include_audio_vibe_contract=True,
        include_coach_closing=True,
        taste_persona_tags=taste_tags,
        coaching_aim_skill=coaching_aim_skill,
    )


class DJCoHostAgent(Agent):
    """Hijacks llm_node to bypass LiveKit's text-only cascade and call
    google.genai directly with the last 10s of audio + the latest screen
    frame attached as multimodal Parts. The LLM literally hears the music.

    Phase 10: env-var dispatch over the 6-cell prompt matrix +
    ``<silence/>`` short-circuit + post-hoc slop filter.
    """

    def __init__(
        self,
        *,
        genai_client: genai.Client,
        clean_audio_buf: AudioBuffer,
        screen_buf,  # duck-typed: has .latest() -> (bytes | None, (w, h))
        state: MusicState,
        recorder: VoiceRecorder,
        llm_inst: agents_llm.LLM,
        tts_inst: agents_tts.TTS,
        evidence_registry: EvidenceRegistry | None = None,
        cache: GeminiContextCache | None = None,
        ttft_meter: TTFTMeter | None = None,
        # Plan 20-01 — citation-linter chokepoint kwargs. ALL FOUR must be
        # non-None for the wired path; default None preserves Phase 18/19
        # backward-compat (legacy emit-everything-from-buffered-chunks
        # behavior). The all-or-nothing wiring keeps the byte-identity
        # guarantee for the existing tests/agent/test_dj_cohost.py suite.
        citation_linter: CitationLinter | None = None,
        stripped_rate_tracker: StrippedRateTracker | None = None,
        playback: PlaybackQueue | None = None,
        # Plan 24-02 — overlay-highlight publish path. Default None
        # preserves backward compat (no overlay events). When non-None,
        # llm_node publishes ipc.session.overlay-highlight envelopes for
        # every [screen:<element>] citation in an emit-action turn.
        ipc_bus: IpcBus | None = None,
        # Plan 32-03 / PROFILE-04 — long-term DJ profile reference. P53
        # kwargs-only addition; None default keeps v2.0 4-kwarg construction
        # path byte-identical. P60: profile lives in GeminiContextCache
        # (vibemix.agent.cache.GeminiContextCache.profile_section), NEVER
        # in the per-turn prompt. The agent stores the reference only for
        # diagnostics; llm_node must NEVER read it (enforced by
        # tests/profile/test_profile_not_in_per_turn_prompt.py).
        profile: dict | None = None,
        # Plan 40-01 / AUDIO-01 — mic-as-2nd-Gemini-Part ring. None default
        # preserves Phase 4/18/19 backward compat (the existing 1-Part
        # request is byte-identical when mic_audio_buf is None). When non-
        # None, llm_node appends a 2nd ``audio/wav`` Part to ``contents``
        # iff (a) KAAN_SPOKE is recent (within MIC_AUDIO_PART_RECENCY_S)
        # and (b) the ring snapshot has signal (RMS > presence floor).
        # Closes hallucination class "AI invents what Kaan said" by
        # putting Kaan's literal voice in front of Gemini.
        mic_audio_buf: AudioBuffer | None = None,
        # Plan 40-03 / AUDIO-02 + AUDIO-04 — source-file lookahead provider.
        # None default preserves Phase 4/18/19/40-01 backward compat (the
        # 1-Part / 2-Part request shapes are byte-identical when lookahead
        # is None). When non-None, llm_node calls
        # ``self._lookahead.snapshot_wav()`` after the mic Part attach and
        # conditionally appends a 3rd ``audio/wav`` Part containing 18s
        # ending ~3s past the current playhead. The prompt-suffix labels
        # that Part with "NOT YET HEARD BY AUDIENCE" per locked CONTEXT
        # Q2 — closes the "AI claims to predict the future" hallucination
        # class that lookahead introduces.
        lookahead: LookaheadProvider | None = None,
        # ipc.session.snapshot transcript sink. Optional bounded deque the
        # live runtime (``ws_broadcast``) drains per snapshot to light up the
        # cohost transcript panel. None default keeps every other construction
        # path byte-identical. Appended ONLY at the spoken-text points (next
        # to ``_ai_text_history.append``) which live in the cold post-stream
        # logging tail — NEVER in the audio/TTS hot path. Best-effort: any
        # append failure is swallowed so a sink hiccup can't touch a turn.
        transcript_sink: collections.deque | None = None,
        # 2026-05-21 — OpenRouter LLM path. When ``or_client`` is non-None,
        # llm_node streams the brain through OpenRouter (OpenAI-compat,
        # ``or_model``) instead of the direct google.genai client — escapes
        # the free-tier Gemini 503s while keeping inline-audio grounding
        # (verified: OR passes input_audio to Gemini). None default keeps the
        # direct-genai path byte-identical for every existing caller/test.
        or_client: Any = None,
        or_model: str = OPENROUTER_LLM_MODEL,
        # Phase 65 Plan 04 — Memory Retrieval Seam (RECALL-01/02/03/04). The
        # MemoryRecall enrichment service is the off-hot-path retrieval
        # seam: track-aware events pre-dispatch it via run_in_executor +
        # asyncio.wait_for(RECALL_DEADLINE_S); llm_node pulls survivors via
        # ``recall.get_latest()`` (``[]`` if the deadline missed → no
        # block, no TTFT regression). Default ``None`` + ``recall_enabled
        # = False`` keeps EVERY existing dj_cohost construction path
        # BYTE-IDENTICAL (the cold/feature-off path is the v5.0 baseline).
        # The live-relevance veto flip is KAAN-ACTION (Kaan-ear pass on the
        # real corpus); the seam ships wired + tested regardless.
        recall: MemoryRecall | None = None,
        recall_enabled: bool = False,
        # Phase 77 Plan 04 — WIRE-01: the "what's playing" Grounding engine.
        # Built + armed at boot (``__main__.py``) but historically orphaned —
        # never passed downstream. This kwarg wires it in, mirroring the
        # Phase-65 MemoryRecall 4-point seam: track-aware events pre-dispatch
        # ``Grounding.on_event`` OFF the loop (run_in_executor) so the embed
        # never blocks the reaction hot path (TTFT non-regression); llm_node
        # pulls ``get_latest_citation()`` and, when CITED, injects the
        # ``[track:<id>]`` reference into the prompt (it resolves in the
        # EvidenceRegistry because ``register_library`` already seeded every
        # library track id — invariant #2, no linter change); the latch is
        # cleared at turn end alongside the recall clear. Grounding is
        # consulted STRICTLY READ-ONLY — it never writes MusicState
        # (single-writer invariant #1). Default ``None`` → cold path
        # BYTE-IDENTICAL to the v8.0 baseline (``grounding is None`` IS the
        # gate; no separate enabled flag, since the live build already
        # conditions grounding creation on library presence).
        grounding: Grounding | None = None,
        # Phase 80 Plan 02 — GROUND-01: secondary-ear framing flag. Default
        # False keeps the cold path BYTE-IDENTICAL to the v8.0 baseline (the
        # Part-1 audio attach is unconditional regardless; this flag gates ONLY
        # the prompt framing clause built in ``build_parts_description``). When
        # True, the parts_clause names the live audio a *secondary grounding
        # signal* and reaffirms the structured evidence is authoritative.
        # Threaded from a default-OFF ``VIBEMIX_GROUND_SECONDARY_EAR`` env read
        # in ``__main__.py``. The judgment "is the second ear worth it / which
        # model wins" is Phase-81 BENCH + KAAN-ACTION.
        secondary_ear: bool = False,
        # Optional live capture-capability receipt from __main__. This does not
        # attach extra audio by itself; it tells Gemini whether P1 is global-only
        # or the runtime has real deck-pair capture available.
        audio_capture_context: dict[str, object] | None = None,
        # Optional per-deck rings from the multichannel capture path. These only
        # become Gemini Parts when VIBEMIX_GEMINI_DECK_AUDIO_PARTS permits it.
        deck_audio_buffers: dict[str, AudioBuffer] | None = None,
        deck_audio_parts_mode: str | None = None,
        deck_audio_part_seconds: float | None = None,
        learn_progress: Any | None = None,
    ):
        # Resolve which prompt cell to use BEFORE super().__init__ — the
        # parent Agent constructor stores ``instructions`` for LiveKit's
        # text-only fallback path. We pass the matrix-resolved cell here.
        # Phase 13-05: prefer the live MusicState.mood over the env-var
        # default so a mood-swap before agent build is honored. Plan 13-06
        # is responsible for re-instantiating the agent on subsequent swaps.
        # Plan 18-03: prompt_body now includes the citation-grammar block
        # appended via build_system_instruction's default
        # include_citation_grammar=True — Gemini SEES the grammar in the
        # system instruction (GROUND-03 prompt-only seeding).
        live_mood = getattr(state, "mood", None)
        prompt_body = _resolve_prompt_cell(mood=live_mood, learn_progress=learn_progress)
        super().__init__(
            instructions=prompt_body,
            llm=llm_inst,
            tts=tts_inst,
            allow_interruptions=False,
        )
        self._genai_client = genai_client
        self._tts_inst = tts_inst
        # 2026-05-21 — OpenRouter brain path (see kwarg docstring). Store the
        # resolved persona cell too: the OR path passes it as the system
        # message (the direct path carries it in _gen_cfg.system_instruction
        # / the context cache).
        self._or_client = or_client
        self._or_model = or_model
        self._prompt_body = prompt_body
        self._clean_audio_buf = clean_audio_buf
        self._screen_buf = screen_buf
        self._state = state
        self._recorder = recorder
        # Plan 18-03 — evidence registry for per-turn snapshot threading.
        # Default None preserves Phase 4 backward-compat (the agent is the
        # only call site that wires the registry into AICoach.build_prompt;
        # standalone tests + legacy run paths skip the snapshot).
        self._registry: EvidenceRegistry | None = evidence_registry
        # Plan 19-03 — optional context cache. None default preserves Phase 4
        # backward compat (llm_node uses self._gen_cfg with system_instruction
        # inline). When non-None AND cache.current_name() returns a string,
        # llm_node builds a per-call gen_cfg with cached_content set.
        self._cache: GeminiContextCache | None = cache
        # Plan 19-05 — optional TTFT meter. None default preserves backward
        # compat for tests that don't drive the meter. When non-None,
        # set_next_event records the event-fired timestamp and llm_node
        # records the first non-empty stream chunk timestamp; the rolling
        # average is exposed as live latency telemetry. (Historically it also
        # fed AckBank.should_fire(); the ack-bank was retired 2026-05-19 —
        # strip-to-silence replaced pre-canned acks — so this meter is now
        # telemetry-only.)
        self._ttft_meter: TTFTMeter | None = ttft_meter
        # Plan 41-04 / LAT-04 — per-turn (event_fired → first_sentence
        # _yielded) delta meter. Always-on (unlike _ttft_meter which is
        # optional). Records via :meth:`llm_node` at the speculative head
        # emit point; emits ``llm_to_tts_delta_ms`` to events.jsonl when
        # a head was yielded. Skip path (no head emitted — short
        # response / suppression / strip) writes no event.
        self._llm_to_tts_meter: LLMToTTSDeltaMeter = LLMToTTSDeltaMeter()
        # Plan 20-01 — citation linter chokepoint. All four kwargs default
        # None; the wired path runs iff ALL FOUR are non-None. ``_linter_wired``
        # is computed once at __init__ to avoid four None-checks on every
        # turn (the gate runs in the LLM hot-path).
        self._linter: CitationLinter | None = citation_linter
        self._stripped_tracker: StrippedRateTracker | None = stripped_rate_tracker
        self._playback: PlaybackQueue | None = playback
        self._linter_wired: bool = all(
            x is not None for x in (citation_linter, stripped_rate_tracker, playback)
        )
        # Plan 24-02 — overlay-highlight publish path. Wired iff non-None.
        self._ipc_bus: IpcBus | None = ipc_bus
        # Plan 32-03 / PROFILE-04 — stored read-only reference. NEVER
        # accessed inside llm_node (P60 grep gate enforces this). The
        # Settings → Profile panel may read it for diagnostics without
        # re-loading from disk. If you find yourself adding self._profile
        # into the per-turn flow, STOP — that breaks the cache contract.
        self._profile: dict | None = profile
        # Plan 40-01 / AUDIO-01 — mic ring reference. Read-only consumer:
        # llm_node snapshots the ring per turn and conditionally attaches
        # Part 2 to ``contents``. The ring itself is fed by
        # ``__main__._mic_callback_factory`` on the sounddevice audio thread
        # (verbatim port of cohost_v4.py:2278-2296 with AI-talk zero-fill).
        self._mic_audio_buf: AudioBuffer | None = mic_audio_buf
        # Plan 40-03 / AUDIO-02 + AUDIO-04 — lookahead provider reference.
        # Read-only consumer: llm_node calls ``snapshot_wav()`` per turn
        # and conditionally appends Part 3 to ``contents``. The provider
        # is per-session (instantiated in __main__.py next to
        # clean_audio_buf); the title→path cache lives for the whole DJ
        # session per RESEARCH Open Question 3 resolution.
        self._lookahead: LookaheadProvider | None = lookahead
        # Phase 65 Plan 04 — MemoryRecall service + recall_enabled flag.
        # The wired path runs iff BOTH the service is non-None AND the flag
        # is True; the flag is the Kaan-ear veto switch (default-OFF so the
        # engineering close ships wired but never live until Kaan flips it).
        # The recall_enabled flag is checked at the seam (set_next_event +
        # llm_node) — passing only the service is not enough.
        self._recall: MemoryRecall | None = recall
        self._recall_enabled: bool = recall_enabled and recall is not None
        # Phase 77 Plan 04 — WIRE-01: the Grounding service reference + its
        # off-loop pre-dispatch task ref. ``grounding is not None`` is the
        # gate (see __init__ kwarg docstring). The task ref mirrors
        # ``self._recall_task``: ``set_next_event`` creates a cancellable
        # background task per track-aware event; llm_node leaves it alone and
        # pulls ``get_latest_citation()``. Default None → cold path
        # byte-identical (no dispatch, no injection, no clear).
        self._grounding: Grounding | None = grounding
        self._grounding_task: asyncio.Task | None = None
        # Phase 80 Plan 02 — GROUND-01 secondary-ear framing gate. Default
        # False → parts_clause/contents byte-identical to v8.0.
        self._secondary_ear: bool = secondary_ear
        # Keep the shared runtime dict so the audio callback can update deck
        # RMS/activity between turns without needing another model or bus pass.
        self._audio_capture_context = (
            audio_capture_context if isinstance(audio_capture_context, dict) else None
        )
        self._deck_audio_buffers: dict[str, AudioBuffer] = (
            {
                side: buf
                for side, buf in deck_audio_buffers.items()
                if side in {"A", "B"} and isinstance(buf, AudioBuffer)
            }
            if isinstance(deck_audio_buffers, dict)
            else {}
        )
        self._deck_audio_parts_mode = _deck_audio_parts_mode(deck_audio_parts_mode)
        self._deck_audio_part_seconds = _deck_audio_part_seconds(deck_audio_part_seconds)
        # Phase 66 (COPILOT-02) — wall-clock timestamp of the last recall
        # callback that REACHED the audience (the ``await self._ipc_bus.
        # emit(...)`` returned without raising on a turn that emitted a
        # chip with ``event_id.startswith("recall:")``). Read by the
        # cooldown gate in ``llm_node`` to drop ``recall_moments = []``
        # when ``(time.time() - self._last_recall_callback_at) <
        # RECALL_CALLBACK_COOLDOWN_S``. The semantic locked at CONTEXT.md
        # Area 1 Q3 + RESEARCH §Pitfall 2 + §Open Q5 is "REACHED the
        # audience" — a bus-emit failure cannot arm this timestamp (the
        # arm sits on the ``else:`` branch of the bus-emit try/except,
        # success-only).
        #
        # Initialized to ``float("-inf")`` (never-armed sentinel) so the
        # FIRST recall callback always passes the cooldown gate regardless
        # of the wall-clock value — ``(time.time() - -inf) == inf`` which
        # is never ``< 120.0``. The plain ``0.0`` initializer would
        # incorrectly trip the gate when ``time.time()`` is mocked to a
        # small value (the pinned cooldown test mocks ``t=100.0`` on turn
        # N; with ``0.0`` init the gap is 100s < 120s → first callback
        # wrongly suppressed; with ``-inf`` the gate passes on turn N as
        # intended, arms to 100.0, then suppresses turn N+1 at t=180 with
        # gap=80s as the test expects).
        #
        # Wall-clock ``time.time()`` (not session-relative ``t_session``)
        # so a single Kaan-session's pacing is what matters; if Kaan opens
        # a fresh session, the previous session's timestamp is forgotten
        # by virtue of being a per-agent-instance scalar.
        self._last_recall_callback_at: float = float("-inf")
        # The pre-dispatch task ref. set_next_event creates this off-loop
        # background task and llm_node leaves it alone — it either landed
        # survivors in `_recall._latest` (Plan 65-03 contract) or its
        # asyncio.wait_for(RECALL_DEADLINE_S) timed out and the timeout
        # handler called `_recall.clear()` to ensure nothing leaks.
        self._recall_task: asyncio.Task | None = None
        self._pending_event: Event | None = None
        # Late-line-blurt guard (Invariant #3): monotonic stamp of the moment the
        # current pending event fired, written by set_next_event. llm_node reads
        # it to drop a reaction whose generation only resolves after the
        # freshness budget. None = no stamp yet (guard disabled, fail-open).
        self._pending_event_fired_monotonic: float | None = None
        self._ai_text_history: collections.deque = collections.deque(maxlen=10)
        self._recent_speak_fingerprints: collections.deque = collections.deque(maxlen=4)
        # ipc.session.snapshot transcript sink (see __init__ kwarg docstring).
        self._transcript_sink: collections.deque | None = transcript_sink

        # ---- Phase 69 Plan 69-03 (OSS-02) — proxy outage state -----------
        # In proxy mode, when the upstream Bravoh proxy returns 5xx / times
        # out / refuses the connection / returns non-JSON body, the brain
        # refuses to lie (anti-slop): LLM emission skips for the duration,
        # diagnostics land in events.jsonl/route telemetry, and a 60s
        # ``probe_proxy_health`` canary auto-clears the flag when /health
        # returns 200 (or whenever a real LLM call next succeeds — whichever
        # fires first). The transcript sink is reserved for genuinely spoken
        # lines; outage diagnostics must not masquerade as Sven speech.
        #
        # All five attributes default-init to "not armed" so direct mode
        # (BYO) and tests that never touch the proxy path are byte-identical
        # to v5.0 behavior.
        self._proxy_unavailable: bool = False
        self._proxy_unavailable_message_emitted: bool = False
        self._proxy_recovery_message_emitted: bool = False
        # Loud-failure guard — when the LLM call raises an UNCLASSIFIED error
        # (auth 401/403, missing/invalid key, DNS, TLS, connection refused on
        # the DIRECT path, etc.), we surface ONE clear connection_error event
        # to events.jsonl + the UI transcript instead of dying silently. This
        # closes the "events fire but the co-host never speaks and nothing is
        # logged" release blocker. One-shot per error streak so a persistent
        # auth failure doesn't spam the timeline; reset on the next success.
        self._connection_error_emitted: bool = False
        # Phase 69 review WR-02 — never-probed sentinel is ``float("-inf")``,
        # NOT ``0.0``. ``time.monotonic()`` has an unspecified origin; on a
        # freshly booted host it can legitimately read < 60.0, and a ``0.0``
        # init would make the debounce gate (``now - last < 60.0``) swallow
        # the FIRST armed canary tick — the same off-by-one-against-a-real-
        # clock bug class fixed for ``_last_recall_callback_at`` above (whose
        # 30-line comment explains why ``0.0`` is wrong). ``(now - -inf)`` is
        # always ``inf`` so the first armed tick always passes the gate.
        self._last_proxy_health_probe: float = float("-inf")  # monotonic seconds
        # Resolve proxy_base_url from env at construction time; None ⇒ direct
        # mode and the fallback never arms (gate every state transition on
        # ``self._proxy_base_url is not None``).
        _llm_mode = os.environ.get("VIBEMIX_LLM_MODE", "direct").strip().lower()
        self._proxy_base_url: str | None = (
            os.environ.get("VIBEMIX_PROXY_BASE_URL", "https://api.altidus.world").rstrip("/")
            if _llm_mode == "proxy"
            else None
        )
        # ---- end Plan 69-03 state -----------------------------------------
        # Both the LiveKit-side ``instructions`` AND the google.genai-side
        # ``GenerateContentConfig.system_instruction`` use the same cell.
        self._gen_cfg = types.GenerateContentConfig(
            system_instruction=prompt_body,
            thinking_config=types.ThinkingConfig(thinking_level="minimal"),
            temperature=1.0,
            max_output_tokens=1024,  # 2026-05-20 — lifted from 220 for live-coach thinking budget; Kaan: don't cap output
        )
        # Plan 41-03 / LAT-08 — second gate, defense in depth. llm_factory
        # already runs validate_live_config; the agent re-runs it against
        # the actual _gen_cfg used per-turn so any future construction
        # path that bypasses the factory (test fixtures, mood rebuilds)
        # still hits the invariant. Runs ONCE per agent boot — zero
        # per-turn overhead (the per-turn cached_content branch in
        # llm_node uses its own pre-validated thinking_level="minimal"
        # literal, identical to this _gen_cfg, so it inherits the gate).
        validate_live_config(self._gen_cfg)

    async def refresh_coaching_aim(self, learn_progress: Any | None) -> bool:
        """Refresh the prompt prefix after Learn mastery changes.

        The Learn aim is a cached system-instruction frame. When a live demo
        flips a skill to Mastered, recompute the fixed fragment from the same
        progress object and invalidate any remote cache carrying the old body.
        Returns True only when the prompt body changed.
        """

        live_mood = getattr(self._state, "mood", None)
        prompt_body = _resolve_prompt_cell(mood=live_mood, learn_progress=learn_progress)
        if prompt_body == self._prompt_body:
            return False

        self._prompt_body = prompt_body
        self._gen_cfg = types.GenerateContentConfig(
            system_instruction=prompt_body,
            thinking_config=types.ThinkingConfig(thinking_level="minimal"),
            temperature=1.0,
            max_output_tokens=1024,
        )
        validate_live_config(self._gen_cfg)

        if self._cache is not None:
            self._cache.set_system_instruction_body(prompt_body)
            await self._cache.invalidate()
        return True

    def _push_transcript(self, text: str, *, ts: str | None = None) -> None:
        """Best-effort push of a spoken AI line onto the snapshot sink.

        Called next to each ``_ai_text_history.append`` (the spoken-text
        signal). Swallows all errors — a transcript-sink hiccup must never
        perturb a reaction turn.
        """
        if self._transcript_sink is None:
            return
        try:
            if ts:
                self._transcript_sink.append({"text": text, "ts": ts})
            else:
                self._transcript_sink.append(text)
        except Exception:
            pass

    def _live_coach_route_chain(self) -> LiveCoachRouteChain:
        """Return the current brain route chain for telemetry only.

        This is intentionally non-dispatching. Slow TTFT or proxy outage may
        produce an ``operator_decision_required`` hedge signal, but provider
        switching stays a user/runtime setting decision.
        """
        ttft_ms: float | None = None
        if self._ttft_meter is not None:
            try:
                raw_ttft_ms = self._ttft_meter.rolling_avg_ms()
                if isinstance(raw_ttft_ms, (int, float)):
                    ttft_ms = float(raw_ttft_ms)
            except Exception:
                ttft_ms = None
        active_provider = "openrouter" if self._or_client is not None else "gemini"
        active_model = self._or_model if self._or_client is not None else LLM_MODEL
        openrouter_configured = self._or_client is not None or bool(
            os.environ.get("OPENROUTER_API_KEY")
        )
        return resolve_live_coach_chain(
            active_provider=active_provider,
            active_model=active_model,
            llm_mode="proxy" if self._proxy_base_url is not None else "direct",
            proxy_configured=self._proxy_base_url is not None,
            proxy_unavailable=self._proxy_unavailable,
            openrouter_configured=openrouter_configured,
            ttft_ms=ttft_ms,
        )

    def _maybe_emit_proxy_unavailable(self, reason: str) -> None:
        """Arm the proxy-unavailable flag + log a one-shot diagnostic.

        Gates:
        - Only fires when ``self._proxy_base_url is not None`` (proxy mode).
          Direct mode (BYO) never arms — BYO users see their own network
          errors per existing v3.x behavior.
        - The diagnostic emits EXACTLY ONCE per unavailable-streak; subsequent
          ticks while still unavailable do not spam events.jsonl.

        Best-effort: a recorder / transcript-sink hiccup must never perturb
        the LLM turn — every side-effect is wrapped.
        """
        if self._proxy_base_url is None:
            return
        # Arm the flag + reset the recovery one-shot guard (the next recovery
        # is a fresh event).
        if not self._proxy_unavailable:
            self._proxy_unavailable = True
            self._proxy_recovery_message_emitted = False
        if not self._proxy_unavailable_message_emitted:
            self._proxy_unavailable_message_emitted = True
            try:
                self._recorder.log_event(
                    "proxy_unavailable",
                    reason=reason,
                    path="live_coach",
                    **self._live_coach_route_chain().event_fields(),
                )
            except Exception:
                pass

    def _maybe_emit_proxy_recovery(self) -> None:
        """Log one-shot proxy recovery and clear the proxy-unavailable flag.

        Called from two paths:
        1. After a successful LLM call when ``self._proxy_unavailable`` was
           True — the next real LLM success implicitly clears the fallback.
        2. The pre-call 60s ``probe_proxy_health`` canary when /health
           returns 200.

        Best-effort + one-shot: only fires once per recovery; the next
        unavailable-streak resets the guard.
        """
        if self._proxy_base_url is None:
            return
        if not self._proxy_unavailable:
            return
        self._proxy_unavailable = False
        self._proxy_unavailable_message_emitted = False
        if not self._proxy_recovery_message_emitted:
            self._proxy_recovery_message_emitted = True
            try:
                self._recorder.log_event(
                    "proxy_recovered",
                    path="live_coach",
                    **self._live_coach_route_chain().event_fields(),
                )
            except Exception:
                pass

    def _emit_connection_error(self, err: BaseException) -> None:
        """LOUD, never-silent diagnostics for an LLM connect/auth failure.

        Fires from the ``llm_node`` exception handler for ANY error that the
        proxy classifier did NOT already handle. Covers the release-blocker
        case: a direct-mode session whose Gemini key is missing/invalid (or
        whose connection is refused) used to print ``[llm err]`` to stderr
        ONLY — no ``events.jsonl`` line, no UI signal — so the co-host fell
        silent with zero diagnostics. Now we log a ``connection_error`` event
        to ``events.jsonl`` with a coarse, key-free classification so logs never
        leak secrets. The stderr banner remains for operator visibility.

        Deliberately does NOT push a transcript line: ``transcript_delta`` is
        the co-host/spoken surface, and an outage diagnostic that was never
        synthesized must not look like Sven said it. One-shot per error streak
        (``_connection_error_emitted``) so a persistent failure logs once, not
        10×/second. Cleared on the next successful stream (see the ``else``
        branch in ``llm_node``).

        Best-effort: every side-effect is wrapped — surfacing the error must
        never itself crash the turn.
        """
        if self._connection_error_emitted:
            return
        self._connection_error_emitted = True

        msg = str(err)
        low = msg.lower()
        # Coarse, secret-free classification for the log line.
        if any(
            tok in low
            for tok in (
                "401",
                "403",
                "unauthorized",
                "permission",
                "api key",
                "api_key",
                "invalid key",
                "authenticat",
            )
        ):
            kind = "auth"
        elif any(tok in low for tok in ("getaddrinfo", "name resolution", "dns")):
            kind = "dns"
        elif any(
            tok in low
            for tok in ("refused", "connection reset", "ssl", "tls", "timed out", "timeout")
        ):
            kind = "connection"
        else:
            kind = "unknown"

        # 1. events.jsonl — the durable diagnostic that was missing before.
        try:
            self._recorder.log_event(
                "connection_error",
                error_kind=kind,
                error=type(err).__name__,
                # repr() can echo request bodies/headers on some SDK errors;
                # str() is the safer surface and we've already classified.
                detail=msg[:300],
                path="live_coach",
                **self._live_coach_route_chain().event_fields(),
            )
        except Exception:
            pass

        # 2. stderr — keep the human-readable banner the Tauri log captures.
        hint = {
            "auth": "Gemini rejected the credentials — check GEMINI_API_KEY.",
            "dns": "DNS lookup failed — check network connectivity.",
            "connection": "could not connect to Gemini — check network / firewall.",
            "unknown": "the LLM call failed — see detail above.",
        }[kind]
        print(
            f"\n[FATAL-SOFT] co-host connection_error ({kind}): {hint}",
            file=sys.stderr,
            flush=True,
        )

        # No transcript injection here: the transcript_delta channel is the
        # spoken/cohost surface, and diagnostics that were never synthesized
        # must not look like Sven said them. The durable user/developer signal
        # is the connection_error event plus the stderr banner above.

    async def _check_proxy_health_canary(self, now_monotonic: float) -> None:
        """Pre-call gate: if the fallback is armed AND 60s have elapsed since
        the last ``probe_proxy_health`` tick, fire one canary check; on 200
        emit the recovery one-shot line + clear the flag.

        Best-effort: ``probe_proxy_health`` is a 5s-timeout sync GET that NEVER
        raises. If /health is not yet implemented on api.altidus.world (Bravoh
        ops repo work — KAAN-ACTION-LEGAL.md §V7-PROXY) this returns False
        perpetually and the recovery line never fires via the canary — the next
        real LLM success (via _maybe_emit_proxy_recovery) is the fallback.

        Phase 69 review WR-01 — the probe is a SYNCHRONOUS blocking GET. On the
        happy path it returns in milliseconds, but the canary is only ever
        armed when the proxy is DOWN, where the GET hangs to its full 5s
        timeout. Running that directly on the asyncio event loop stalls the
        whole reaction pipeline (audio frame delivery, TTS playback, WS
        broadcast) for up to 5s every 60s for the duration of the outage.
        So we offload the blocking GET to a thread executor — mirroring the
        recall pre-dispatch offload (``set_next_event`` ~line 809) — and the
        debounce timestamp is armed BEFORE the offload so a slow probe cannot
        let a second canary stack up behind it.
        """
        if self._proxy_base_url is None or not self._proxy_unavailable:
            return
        if now_monotonic - self._last_proxy_health_probe < 60.0:
            return
        self._last_proxy_health_probe = now_monotonic
        loop = asyncio.get_running_loop()
        ok = await loop.run_in_executor(None, probe_proxy_health, self._proxy_base_url)
        if ok:
            self._maybe_emit_proxy_recovery()

    def _record_speak_fingerprint(self, ev: Event | None) -> None:
        if ev is None:
            return
        if ev.type == "TRACK_CHANGE":
            self._recent_speak_fingerprints.clear()
        self._recent_speak_fingerprints.append(event_speak_fingerprint(ev))

    def _record_said(
        self,
        text: str,
        set_s_at_event: float | None = None,
        *,
        event: Event | None = None,
    ) -> None:
        """Append a spoken line to the no-repeat memory, prefixed with the
        set-time it was said at ([M:SS]). Lets the model see WHEN it last
        spoke so it doesn't re-react to a moment it already covered or
        re-quote a set-time it already used. Kaan-directed 2026-05-21.

        Stays a deque[str] (timestamp baked into the string) so the
        existing _ai_text_history contract + tests are untouched.

        Phase 66 review WR-04 — accept an optional ``set_s_at_event``
        captured at event-fired time (top of ``llm_node``) so the
        [M:SS] stamp reflects WHEN the event fired rather than WHEN
        ``_record_said`` happens to be called (which is after the
        entire llm_node call — stream consumed, lint gate, bus emit;
        2-3s of drift on a typical reaction turn). Falls back to live
        ``self._state.set_seconds`` for legacy callers that don't yet
        thread the event-fired value, so the existing _ai_text_history
        contract + tests stay untouched.
        """
        if set_s_at_event is not None:
            set_s = float(set_s_at_event)
        else:
            set_s = getattr(self._state, "set_seconds", 0.0) or 0.0
        stamp = f"{int(set_s // 60)}:{int(set_s % 60):02d}"
        self._ai_text_history.append(f"[{stamp}] {text}")
        self._record_speak_fingerprint(event)

    def attach_grounding(self, grounding: Grounding | None) -> None:
        """Post-construction wiring for the WIRE-01 Grounding engine.

        Phase 77 Plan 04. ``main()`` builds the agent BEFORE the Grounding
        engine (the grounding build depends on ``deck_library``, which is
        resolved after the agent). Rather than reorder the build (which would
        be a large, churny diff), the orchestrator constructs the agent with
        ``grounding=None`` and calls this setter once the engine is armed.
        Passing ``None`` (no library → no grounding) leaves the cold path
        byte-identical. Idempotent — safe to call at most once per agent.
        """
        self._grounding = grounding

    def bind_ipc_bus(self, ipc_bus: IpcBus | None) -> None:
        """Post-construction wiring for the UI publish bus (One Mind W1).

        ``main()`` builds the agent (``__main__.py``) BEFORE the live
        ``IpcRouterBus`` exists — the router is created downstream of the
        SessionLoop / ws_broadcast wiring. Rather than reorder the build, the
        orchestrator constructs the agent with ``ipc_bus=None`` and calls this
        setter once the router is armed, mirroring :meth:`attach_grounding`.
        With the bus wired, ``llm_node``'s emit-action turns publish
        ``ipc.session.cohost-reaction`` (the citation-chip "show your receipts"
        strip) + ``ipc.session.overlay-highlight`` envelopes. Before this call
        (or when ``None`` is passed) the cold path is byte-identical: the
        reaction still reaches the audience via TTS — only the chip/overlay
        surfaces stay dark. Idempotent — safe to call at most once per agent.
        """
        self._ipc_bus = ipc_bus

    def _tts_has_cached_text(self, text: str) -> bool:
        """Return True when the live TTS chain can speak ``text`` without generation."""
        wanted = str(text or "").strip()
        if not wanted:
            return False
        seen: set[int] = set()
        stack: list[Any] = [self._tts_inst]
        while stack:
            item = stack.pop()
            if item is None:
                continue
            marker = id(item)
            if marker in seen:
                continue
            seen.add(marker)
            has_cached_text = getattr(item, "has_cached_text", None)
            if callable(has_cached_text):
                try:
                    if bool(has_cached_text(wanted)):
                        return True
                except Exception:
                    pass
            for child in getattr(item, "_tts_instances", ()) or ():
                stack.append(child)
            for attr in ("_tts", "tts"):
                child = getattr(item, attr, None)
                if child is not None:
                    stack.append(child)
        return False

    def _direct_tts_synthesizer(self) -> tuple[Any, Any] | None:
        """Return the first local TTS object with a direct PCM synthesis hook."""
        seen: set[int] = set()
        stack: list[Any] = [self._tts_inst]
        while stack:
            item = stack.pop()
            if item is None:
                continue
            marker = id(item)
            if marker in seen:
                continue
            seen.add(marker)
            synthesize_pcm = getattr(item, "synthesize_pcm", None)
            if callable(synthesize_pcm):
                return item, synthesize_pcm
            for child in getattr(item, "_tts_instances", ()) or ():
                stack.append(child)
            for attr in ("_tts", "tts"):
                child = getattr(item, attr, None)
                if child is not None:
                    stack.append(child)
        return None

    def _probe_direct_voice_enabled(self) -> bool:
        direct_override = os.environ.get("VIBEMIX_SVEN_PROBE_DIRECT_VOICE", "0")
        if direct_override.strip().lower() in ("0", "false", "no", "off"):
            return False
        return _sven_probe_mode_enabled()

    @staticmethod
    def _probe_spoken_text(text: str) -> str:
        """Remove citations/grounding receipts before direct probe playback."""
        spoken = model_text_for_tts(text or "")
        spoken = re.sub(r"\[[^\[\]]+:[^\[\]]+\]", " ", spoken)
        spoken = re.sub(r"\s+", " ", spoken)
        return spoken.strip()

    @staticmethod
    def _probe_playback_speed() -> float:
        raw = os.environ.get("VIBEMIX_SVEN_PROBE_PLAYBACK_SPEED", "1.0")
        try:
            speed = float(raw)
        except (TypeError, ValueError):
            return 1.0
        if speed < 0.75 or speed > 1.5:
            return 1.0
        return speed

    @staticmethod
    def _speed_int16_mono_pcm(pcm: bytes, speed: float) -> bytes:
        if not pcm or abs(speed - 1.0) < 0.01:
            return pcm
        samples = np.frombuffer(pcm, dtype=np.int16)
        if samples.size < 2:
            return pcm
        indexes = np.arange(0, samples.size, speed, dtype=np.float64).astype(np.int64)
        indexes = indexes[indexes < samples.size]
        if indexes.size == 0:
            return pcm
        return samples[indexes].astype(np.int16, copy=False).tobytes()

    def _schedule_probe_direct_voice(
        self,
        text: str,
        *,
        event: str,
        response_id: str,
    ) -> None:
        """Probe-mode rescue path: push local TTS PCM straight to playback.

        This is intentionally gated by ``VIBEMIX_SVEN_PROBE_MODE``. It lets a
        live QA run hear every emitted Sven line even if LiveKit's TTS output
        adapter fails to deliver frames. The normal LiveKit path stays wired
        and remains visible in logs for later cleanup.
        """
        if not self._probe_direct_voice_enabled():
            return
        spoken = self._probe_spoken_text(text)
        if not spoken or self._playback is None:
            return
        synth_pair = self._direct_tts_synthesizer()
        if synth_pair is None:
            self._recorder.log_event(
                "sven_probe_direct_voice_skipped",
                event=event,
                response_id=response_id,
                reason="no_direct_tts_synthesizer",
                chars=len(spoken),
            )
            return
        tts_obj, synthesize_pcm = synth_pair
        ref_path = getattr(tts_obj, "_ref_path", None)
        synth_source = type(tts_obj).__name__

        async def _run() -> None:
            chunks: list[bytes] = []

            def _on_pcm(pcm: bytes) -> None:
                if pcm:
                    chunks.append(pcm)

            start = time.time()
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, lambda: synthesize_pcm(spoken, _on_pcm))
                raw_pcm = b"".join(chunks)
                source_sr = int(getattr(tts_obj, "sample_rate", OUTPUT_SR) or OUTPUT_SR)
                raw_pcm = _resample_int16_mono_pcm(
                    raw_pcm,
                    source_sr=source_sr,
                    target_sr=OUTPUT_SR,
                )
                speed = self._probe_playback_speed()
                out_pcm = self._speed_int16_mono_pcm(raw_pcm, speed)
                if out_pcm:
                    self._playback.clear()
                    self._playback.push(out_pcm)
                    self._recorder.push_voice(out_pcm)
                self._recorder.log_event(
                    "sven_probe_direct_voice",
                    event=event,
                    response_id=response_id,
                    source=synth_source,
                    ref_path=str(ref_path) if ref_path else None,
                    chars=len(spoken),
                    chunks=len(chunks),
                    pcm_bytes=len(out_pcm),
                    source_sr=source_sr,
                    target_sr=OUTPUT_SR,
                    playback_speed=speed,
                    latency_s=round(time.time() - start, 2),
                )
            except Exception as exc:
                self._recorder.log_event(
                    "sven_probe_direct_voice_error",
                    event=event,
                    response_id=response_id,
                    error=repr(exc),
                    chars=len(spoken),
                    latency_s=round(time.time() - start, 2),
                )

        asyncio.create_task(_run())

    def set_next_event(self, ev: Event) -> None:
        self._pending_event = ev
        # Late-line-blurt guard — stamp the event-fired moment so llm_node can
        # measure reaction age and drop a line whose moment has passed. The
        # Event itself carries no monotonic clock, which is exactly why this
        # event-fired boundary (not the Event) is the correct seam to stamp.
        self._pending_event_fired_monotonic = time.monotonic()
        # Plan 19-05 — start the TTFT measurement window. Overwriting an
        # existing pending pointer is intentional (the previous event was
        # preempted via CancelGate or failed via TimeoutError).
        if self._ttft_meter is not None:
            self._ttft_meter.record_event_fired()
        # Plan 41-04 / LAT-04 — arm the LLM→TTS delta meter at the same
        # boundary so its event_fired_at matches the TTFT meter's. Both
        # meters share the (event_fired, first_*_at) baseline; only the
        # measured RHS differs (first_chunk vs first_sentence_yielded).
        self._llm_to_tts_meter.start_turn()
        # Phase 65 Plan 04 — pre-dispatch MemoryRecall.on_event OFF the
        # event loop for track-aware events. We MUST NOT inline-await the
        # embed inside llm_node (TTFT regression — the RECALL-04 static
        # gate); pre-dispatching here lets the embed + query_topk overlap
        # with the audio snapshot + multimodal Part build that llm_node
        # does up to the registry snapshot. Outcome semantics:
        #   * on success within RECALL_DEADLINE_S → survivors latched in
        #     ``recall._latest`` (Plan 65-03 contract); llm_node pulls them
        #     via ``get_latest()``.
        #   * on TimeoutError / Exception → the deadline handler calls
        #     ``recall.clear()`` so a missed retrieval CANNOT bleed into
        #     this turn (or the next) — ``get_latest()`` returns ``[]``,
        #     the evidence_line gate is falsy, no recall block emitted, no
        #     TTFT regression.
        # The flag-OFF / no-service path is byte-identical to today.
        self._maybe_dispatch_recall(ev)
        # Phase 77 Plan 04 — WIRE-01: pre-dispatch Grounding.on_event OFF the
        # event loop for track-aware events, exactly like the recall seam
        # above. The "what's playing" cosine embed is the expensive part; it
        # MUST NOT be inline-awaited in llm_node (TTFT regression — the whole
        # reason the pre-dispatch+latch+pull pattern exists). The grounding=
        # None / no-loop paths are byte-identical to today.
        self._maybe_dispatch_grounding(ev)

    def _maybe_dispatch_grounding(self, ev: Event) -> None:
        """Pre-dispatch ``Grounding.on_event`` off-loop for track-aware events.

        WIRE-01 (Phase 77 Plan 04). Mirrors ``_maybe_dispatch_recall``: a
        no-op when no grounding service is wired / the event is not
        track-aware / no running asyncio loop is available (e.g. agent
        constructed outside a live coach loop, as several unit tests do).
        Best-effort — every step is guarded so a grounding-side failure
        CANNOT perturb a reaction turn; at worst, no citation is injected.

        Schedules an asyncio task wrapping
        ``loop.run_in_executor(None, grounding.on_event, …)`` in
        ``asyncio.wait_for(timeout=RECALL_DEADLINE_S)`` (reuses the proven
        recall deadline constant — both are off-hot-path Gemini embeds). On
        timeout / exception the latch is cleared so a missed/late lookup
        never bleeds into the turn. NEVER inline-awaits the embed in llm_node.
        """
        grounding = self._grounding
        if grounding is None:
            return
        # Lazy import — keeps the track-aware event gate colocated with the
        # grounding module (the single source of TRACK_AWARE_EVENTS) and
        # avoids a top-level agent→library coupling at import time.
        try:
            from vibemix.library.grounding import TRACK_AWARE_EVENTS
        except Exception as _e:  # pragma: no cover — defensive only
            print(f"[grounding dispatch import err] {_e}", file=sys.stderr)
            return
        # Event gate — short-circuit BEFORE any executor / loop work on the
        # high-frequency event classes (HEARTBEAT, etc.). on_event ALSO gates
        # internally (defense in depth), but checking here avoids burning a
        # task + executor slot. (TRACK_AWARE_EVENTS = TRACK_CHANGE /
        # LAYER_ARRIVAL / MIX_MOVE.)
        if ev.type not in TRACK_AWARE_EVENTS:
            return
        # We need a running loop to schedule the task. set_next_event is
        # called from coach_loop (async context) so a loop is normally
        # available; in test contexts that construct the agent without a
        # running loop, fall through silently — the grounding path is opt-in
        # and the no-grounding path is byte-identical.
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        # Snapshot the clean-audio buffer to WAV bytes HERE (synchronous,
        # cheap buffer read) and hand the bytes to the executor. Reuse the
        # same ``self._clean_audio_buf`` snapshot that llm_node feeds Gemini
        # — do NOT add a second capture path (A3). identify_playing tolerates
        # audio_bytes=None → below-threshold Citation, so a snapshot failure
        # degrades to "no citation", never a crash.
        try:
            audio_bytes = snapshot_wav(self._clean_audio_buf, INVOKE_AUDIO_SECONDS)
        except Exception as _e:
            print(f"[grounding snapshot err] {_e}", file=sys.stderr)
            audio_bytes = None
        # Resolve the off-loop deadline. Reuse the recall constant — both are
        # off-hot-path Gemini embeds with the same TTFT budget. Defensive
        # fallback keeps grounding working even if the memory module is
        # unavailable in a stripped build.
        try:
            from vibemix.memory.retrieval import RECALL_DEADLINE_S as _DEADLINE_S
        except Exception:
            _DEADLINE_S = 2.0
        ev_type = ev.type

        async def _run() -> None:
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        grounding.on_event,
                        ev_type,
                        audio_bytes,
                    ),
                    timeout=_DEADLINE_S,
                )
            except asyncio.CancelledError:
                # A new event preempted this dispatch (cancel + replace
                # below). Re-raise without clearing — the new event's own
                # on_event will latch its own fresh citation; clearing here
                # would torpedo the new dispatch. Mirrors the recall seam.
                raise
            except TimeoutError:
                # Late grounding is worse than none — clear so the stale
                # latch from a prior turn cannot bleed into this one.
                grounding.clear()
            except Exception as _e:
                # Any other failure also clears, then swallows — grounding
                # can never break a reaction turn.
                grounding.clear()
                print(f"[grounding dispatch err] {_e}", file=sys.stderr)

        # Overwriting an existing pending pre-dispatch is intentional — the
        # prior event was preempted, so its grounding result is no longer
        # relevant. Cancel + replace.
        prev = self._grounding_task
        if prev is not None and not prev.done():
            prev.cancel()
        self._grounding_task = asyncio.create_task(_run())

    def _maybe_dispatch_recall(self, ev: Event) -> None:
        """Pre-dispatch ``MemoryRecall.on_event`` off-loop for track-aware events.

        No-op when the recall service is None / recall_enabled is False / no
        running asyncio loop is available (e.g. agent constructed outside a
        live coach loop, as several unit tests do). Best-effort wrapper:
        every step is guarded so a recall-side failure CANNOT perturb a
        reaction turn — at worst, the recall block stays empty.

        Schedules an asyncio task that wraps
        ``loop.run_in_executor(None, recall.on_event, …)`` in
        ``asyncio.wait_for(timeout=RECALL_DEADLINE_S)``; the task's done
        callback calls ``recall.clear()`` on TimeoutError / Exception so a
        missed retrieval never bleeds. NEVER inline-awaits the embed in
        llm_node (RECALL-04 TTFT-unchanged static gate).
        """
        if not self._recall_enabled or self._recall is None:
            return
        # Lazy import — keeps the constants colocated with the service and
        # avoids a top-level memory→agent coupling. The static no-live-path
        # gate scans memory/*.py for forbidden imports, so this direction
        # is the safe one (agent → memory, not the reverse).
        try:
            from vibemix.memory.retrieval import (
                RECALL_DEADLINE_S,
                build_recall_query,
                should_recall_event,
            )
        except Exception as _e:  # pragma: no cover — defensive only
            print(f"[recall dispatch import err] {_e}", file=sys.stderr)
            return
        # Event gate — short-circuit BEFORE any executor / loop work. MIX_MOVE
        # only passes when the event has a move label plus audio_delta, so
        # historical knob/fader memory is learned without embedding every
        # controller twitch.
        if not should_recall_event(ev):
            return
        # Build the query text + resolve current_session_id before the
        # executor hop — `build_recall_query` is duck-typed (no live-path
        # import) and `_recorder.session_dir.name` is the canonical
        # session-id basename used by the rest of the runtime.
        try:
            query_text = build_recall_query(ev)
            recall_query_context = _build_recall_query_context(ev)
            if recall_query_context:
                query_text = f"{query_text} | {recall_query_context}"
            current_session_id = self._recorder.session_dir.name
        except Exception as _e:
            print(f"[recall dispatch prep err] {_e}", file=sys.stderr)
            return
        # We need a running loop to schedule the task. set_next_event is
        # called from coach_loop (async context) so a loop is normally
        # available; in test contexts that construct the agent without a
        # running loop, fall through silently — the recall path is
        # opt-in and the no-recall path is byte-identical.
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        recall = self._recall
        assert recall is not None  # narrowed by the early return above

        async def _run() -> None:
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        recall.on_event,
                        ev.type,
                        query_text,
                        current_session_id,
                    ),
                    timeout=RECALL_DEADLINE_S,
                )
            except asyncio.CancelledError:
                # Phase 65 review iter-3 WR-02 — ``prev.cancel()`` below
                # raises ``asyncio.CancelledError`` inside this task, which
                # is NOT a subclass of ``Exception`` (Python 3.8+). Catching
                # only ``Exception`` lets the cancel propagate uncaught
                # through the task wrapper but, more importantly, would
                # SKIP a clear if we tried to handle it generically — and a
                # clear on cancel is WRONG: the cancel was triggered by
                # ``set_next_event`` overwriting the dispatch with a NEW
                # event, whose own ``on_event`` will (a) bump
                # ``_inflight_gen`` (invalidating any still-running
                # executor write from THIS task) and (b) latch its own
                # fresh survivors. So we explicitly catch + re-raise the
                # cancel so it propagates to the task scheduler normally,
                # WITHOUT calling ``recall.clear()`` (which would torpedo
                # the new dispatch's latch).
                raise
            except TimeoutError:
                # Late memory is worse than no memory — clear() ensures the
                # stale latch from a prior turn cannot bleed into this one.
                # This DOES bump ``_inflight_gen`` (default) so the still-
                # running executor's final ``_latest = survivors`` write
                # fails its token check and is discarded (CR-04 race).
                recall.clear()
            except Exception as _e:
                # Any other failure also clears, then swallows — recall
                # can never break a reaction turn. Same generation-bump
                # semantics as the deadline path: invalidate the in-flight
                # write if any.
                recall.clear()
                print(f"[recall dispatch err] {_e}", file=sys.stderr)

        # Overwriting an existing pending pre-dispatch is intentional —
        # the prior event was preempted (CancelGate or in-flight drop),
        # so its recall result is no longer relevant. Cancel + replace.
        prev = self._recall_task
        if prev is not None and not prev.done():
            prev.cancel()
        self._recall_task = asyncio.create_task(_run())

    def _deck_audio_part_snapshots(
        self, ev_type: str, first_part_index: int
    ) -> list[dict[str, object]]:
        """Return short Deck A/B WAV Parts when configured and worth the cost."""
        context = self._audio_capture_context
        if not self._deck_audio_buffers:
            self._recorder.log_event("deck_audio_parts_skipped", reason="no_deck_audio_buffers")
            return []
        if not isinstance(context, dict) or not context.get("deck_audio_capture_enabled"):
            self._recorder.log_event("deck_audio_parts_skipped", reason="capture_not_enabled")
            return []
        mode = self._deck_audio_parts_mode
        if mode == "off":
            self._recorder.log_event("deck_audio_parts_skipped", reason="mode_off")
            return []
        if mode == "auto" and ev_type not in DECK_AUDIO_PART_AUTO_EVENTS:
            self._recorder.log_event(
                "deck_audio_parts_skipped",
                reason="event_not_auto",
                event=ev_type,
            )
            return []
        if mode == "auto" and not _deck_audio_rms_active(context):
            self._recorder.log_event(
                "deck_audio_parts_skipped",
                reason="deck_audio_silent",
                event=ev_type,
            )
            return []

        seconds = self._deck_audio_part_seconds
        parts: list[dict[str, object]] = []
        for offset, side in enumerate(("A", "B")):
            buf = self._deck_audio_buffers.get(side)
            if buf is None:
                self._recorder.log_event(
                    "deck_audio_parts_skipped",
                    reason=f"missing_deck_{side}_buffer",
                    event=ev_type,
                )
                return []
            pcm = buf.snapshot(int(seconds * buf._sr))
            if pcm.size == 0:
                self._recorder.log_event(
                    "deck_audio_parts_skipped",
                    reason=f"empty_deck_{side}_buffer",
                    event=ev_type,
                )
                return []
            wav = pcm_to_wav(pcm, buf._sr)
            parts.append(
                {
                    "side": side,
                    "label": f"P{first_part_index + offset}",
                    "wav": wav,
                    "seconds": seconds,
                    "bytes": len(wav),
                    "activity": _deck_audio_pcm_activity(pcm),
                }
            )

        self._recorder.log_event(
            "deck_audio_parts_attached",
            event=ev_type,
            mode=mode,
            seconds=seconds,
            sides="+".join(str(part["side"]) for part in parts),
            labels="+".join(str(part["label"]) for part in parts),
            activity="+".join(
                f"{part['side']}:{part.get('activity', 'unknown')}" for part in parts
            ),
            bytes=sum(int(part["bytes"]) for part in parts),
        )
        return parts

    async def llm_node(
        self,
        chat_ctx: agents_llm.ChatContext,
        tools: list,
        model_settings: ModelSettings,
    ) -> AsyncGenerator:
        # Phase 65 review WR-03 — capture ``_pending_event`` but defer the
        # ``= None`` clear until AFTER recall pull + registration finish (in
        # the ``finally`` below). Previously the field was cleared on the
        # next line, so if the registration block raised an uncaught
        # exception the registry was in a partial-write state AND
        # ``_pending_event`` was already gone — the agent could never retry
        # this turn but the registry permanently carried the half-registered
        # ids. The ``finally`` keeps the one-event-per-turn semantics intact
        # while guaranteeing the clear runs on both the success and
        # exception paths.
        ev = self._pending_event
        # Phase 66 review WR-04 — capture the event-fired set_seconds NOW,
        # before the LLM dispatch (stream + lint + bus emit, ~2-3s on a
        # typical reaction turn). ``_record_said`` writes a [M:SS] stamp
        # into the no-repeat memory; reading ``self._state.set_seconds`` at
        # write time would carry the END-of-reaction set time, not the
        # EVENT-fired set time, drifting Gemini's "how long ago did I cover
        # that" reasoning by the full turn latency. Threaded through the
        # three _record_said call sites below as ``set_s_at_event=``.
        ev_set_seconds: float | None = (
            float(getattr(ev.state, "set_seconds", 0.0) or 0.0) if ev is not None else None
        )
        # Late-line-blurt freshness guard (Invariant #3 — trust the audio).
        # ``event_fired_monotonic`` is the set_next_event stamp; a generation
        # that only resolves after ``stale_age_budget`` is a now-stale reaction
        # and must not reach TTS. Captured into a local BEFORE the recall-pull
        # ``finally`` nulls the instance attr, so this turn's guard is unaffected
        # by the reset. None (agent built outside a coach loop / no stamp)
        # disables the guard — fail-open, never over-drop a timely line.
        event_fired_monotonic = self._pending_event_fired_monotonic
        stale_age_budget = _stale_reaction_age_budget_s()
        recall_moments: list = []
        try:
            # Phase 65 Plan 04 (RECALL-01/02) — pull the off-loop recall
            # survivors and REGISTER their record_ids in the EvidenceRegistry
            # BEFORE the once-per-turn snapshot below. The order is structural:
            # if survivors are written AFTER the snapshot, the linter's
            # existence-only branch wouldn't see them and a legitimate
            # ``[recall:<id>]`` would strip the turn. If recall is disabled /
            # no service / pre-dispatch hasn't landed, get_latest() returns
            # ``[]`` → no registration, no recall block, byte-identical to the
            # cold/feature-off path.
            if self._recall_enabled and self._recall is not None:
                # Phase 65 review iter-3 BLOCKER — clear the "recall" bucket
                # UNCONDITIONALLY at the top of the recall path (when a
                # registry exists), regardless of whether THIS turn produces
                # survivors. Previously the clear was gated inside
                # ``if recall_moments and self._registry is not None:`` so a
                # turn with empty survivors after a prior turn registered
                # {A, B} would leave {A, B} in the registry — Gemini could
                # then fabricate ``[recall:A]`` on this turn and the linter's
                # existence-only branch would ACCEPT it (the strict-subset
                # invariant collapses across turn boundaries). Moving the
                # clear OUT of the conditional makes every turn rescope its
                # own registrations: snapshot["recall"] at line 736 is always
                # exactly the ids in the current turn's prompt recall block
                # (or ``{}`` when there are none), so a fabricated id that
                # matches a prior turn's registration is now unregistered-
                # by-construction and the whole turn strips.
                #
                # Cross-turn regression test:
                # ``test_fabricated_recall_strips_turn_n_plus_1_with_empty_recall``.
                if self._registry is not None:
                    try:
                        self._registry.clear_source("recall")
                    except Exception as _e:
                        # Defensive — best-effort; if clear fails, the per-turn
                        # subset invariant below still holds because we only
                        # ever append to ``kept`` on successful registration.
                        print(f"[recall registry clear err] {_e}", file=sys.stderr)
                try:
                    recall_moments = self._recall.get_latest()
                except Exception as _e:
                    print(f"[recall pull err] {_e}", file=sys.stderr)
                    recall_moments = []
                    # Phase 65 review WR-01 — defense-in-depth: a failed read
                    # must NOT leave a stale latch on the service. The next
                    # turn's get_latest() would otherwise return the prior
                    # turn's survivors (the "stale latch" failure mode the
                    # design explicitly tries to prevent).
                    #
                    # Phase 65 review iter-3 WR-03 — pass ``bump_generation=
                    # False`` so this reactive clear does NOT invalidate any
                    # concurrent in-flight ``on_event`` dispatch that is
                    # about to land survivors for a FUTURE turn. The
                    # ``_inflight_gen`` bump is only meaningful for the
                    # deadline-miss path in ``_run`` (where the in-flight
                    # dispatch is exactly the one we want to invalidate);
                    # here we just want to drop the stale latched value, not
                    # torpedo a healthy concurrent task.
                    try:
                        self._recall.clear(bump_generation=False)
                    except Exception:
                        pass
                # Phase 65 review iter-3 WR-01 — when ``_recall_enabled`` is
                # True but ``_registry`` is None (test-only construction
                # path; default production wiring threads both together),
                # the recall block would otherwise inject ``[recall:<id>]``
                # tokens into the prompt with NO registry to validate them.
                # The linter would then strip every recall-bearing turn (no
                # registered set → existence-only check fails on every id).
                # Drop the survivors here so the recall block is never
                # injected without a backing registry — the cold/feature-off
                # path is preserved byte-identically and the live LLM is
                # never asked to ground against a state that can never
                # validate. Lower blast radius than a hard assertion (which
                # would break test_recall_pull_called_when_enabled-style
                # smoke tests that wire a service without a registry).
                if self._registry is None:
                    recall_moments = []
                # Phase 66 (COPILOT-02) — coach-tier recall-callback cooldown
                # gate. When ``recall_moments`` is non-empty AND the wall-clock
                # gap since the last callback REACHED the audience is < 120s,
                # drop survivors to ``[]``. Downstream is then byte-identical
                # to the cold/feature-off path: the strict-subset registration
                # loop at :754 short-circuits (its ``recall_moments and ...``
                # guard); the falsy-gate in ``evidence_line`` / the new
                # ``recall_fragment_for_event`` helper both skip the recall
                # block; the linter's existence-only branch sees no recall ids
                # in the snapshot so a fabricated ``[recall:<id>]`` would
                # strip the turn (the Phase 65 anti-poisoning gate still
                # carries forward). The cooldown ARM site is the ``else:``
                # branch of the bus-emit try/except below — strict "REACHED
                # the audience" semantic per CONTEXT.md Area 1 Q3 + RESEARCH
                # §Pitfall 2 + §Open Q5; a bus-emit failure cannot arm. Pinned
                # by ``test_cooldown_suppresses_back_to_back_recalls_COPILOT02``.
                if (
                    recall_moments
                    and (time.time() - self._last_recall_callback_at) < RECALL_CALLBACK_COOLDOWN_S
                ):
                    recall_moments = []
                if recall_moments and self._registry is not None:
                    # Phase 65 review CR-01/CR-02 — the registered set MUST
                    # be a strict subset of what the prompt shows, or
                    # fabricated ``[recall:<id>]`` ids that match an
                    # accumulated registration would pass the linter's
                    # existence-only branch (the headline anti-poisoning
                    # gate). Use an explicit accumulator (``kept``) so we
                    # only register survivors that actually land in
                    # ``recall_moments`` — no in-loop list rebind (CR-02
                    # iterator/rebind interaction), no registered-but-
                    # dropped ids (CR-01 superset leak). The per-turn
                    # rescope (``clear_source("recall")``) ran above
                    # unconditionally — see iter-3 BLOCKER above.
                    t_session = getattr(ev.state, "set_seconds", 0.0) if ev is not None else 0.0
                    kept: list = []
                    for m in recall_moments:
                        try:
                            self._registry.write("recall", m.record_id, float(t_session))
                            kept.append(m)
                        except Exception as _e:
                            # A failed registration is structural — the offending
                            # survivor is omitted from ``kept`` so the linter
                            # cannot see an unregistered token.
                            print(f"[recall register err] {_e}", file=sys.stderr)
                    recall_moments = kept  # strict subset of registered ids
        finally:
            # Phase 65 review WR-03 — clear ``_pending_event`` on BOTH the
            # success and exception paths so the agent's one-event-per-turn
            # model holds even if recall pull/registration raises.
            self._pending_event = None
            # Late-line-blurt guard — clear the event-fired stamp on the same
            # boundary (this turn already captured it into a local above, so
            # the active guard is unaffected). Restores fail-open: a future
            # non-coach_loop generation that fires WITHOUT a fresh stamp can
            # never be muted by a stale leftover age.
            self._pending_event_fired_monotonic = None

        # Phase 77 review WR-03 — wrap the stream/emit body so the
        # turn-end recall + grounding latch clears ALWAYS run, even if
        # an uncaught exception is raised between the inner guarded
        # blocks (or the generator is closed early). Previously the
        # clears sat at the body tail AFTER this region, so a mid-stream
        # raise skipped them and a [track:<id>] / [recall:<id>] latch
        # persisted into the next turn (widening the CR-01 window).
        try:
            # Plan 18-03 — snapshot the EvidenceRegistry FRESH per turn so the
            # AICoach.evidence_line corpus footer reflects observations written
            # by state_refresh_loop + EventDetector since the last invocation.
            # snapshot() is O(N) over total observations and lock-guarded; with
            # the cohost_v4 cooldown gates a 1h DJ session caps at ~500 obs, so
            # this fits well under 1ms per turn (cheap). When _registry is None
            # (default Phase 4 backward-compat path), pass None — AICoach skips
            # the corpus footer and the v4 byte-identical evidence_line is
            # preserved. This is the production-corpus seeding loop:
            #   registry → snapshot → AICoach evidence_corpus footer → Gemini
            # plus the citation-grammar block in the system instruction
            # (Task 1) tells Gemini HOW to cite against that corpus.
            #
            # Phase 65 Plan 04 — recall survivors MUST already be written
            # above so they appear in this snapshot. The linter's existence-
            # only branch reads snapshot["recall"]; missing survivors would
            # strip a legitimate turn.
            snapshot = self._registry.snapshot() if self._registry is not None else None

            # Diet dispatch. Only low-value chatter keeps the 6s audio window.
            # Musically substantive turns (especially MIX_MOVE and LAYER_ARRIVAL)
            # get the full master-output minute so Sven can hear before/after
            # context instead of reacting to an underfed instant.
            ev_type_for_diet = ev.type if ev is not None else "MANUAL"
            diet = ev_type_for_diet in RUNTIME_DIET_EVENTS
            audio_seconds = DIET_AUDIO_SECONDS if diet else _runtime_coach_audio_seconds()
            skip_screen = ev_type_for_diet in SCREEN_SKIP_EVENTS
            ev_extra = ev.extra if ev is not None and isinstance(ev.extra, dict) else {}
            guard_option_scaffold = _should_guard_option_scaffold(ev_type_for_diet, ev_extra)
            judge_evidence_line = ev_extra.get("judge_evidence_line")
            if not isinstance(judge_evidence_line, str):
                judge_evidence_line = None
            ev_audio_capture_context = ev_extra.get("audio_capture_context")
            prompt_audio_capture_context = (
                ev_audio_capture_context
                if isinstance(ev_audio_capture_context, dict)
                else self._audio_capture_context
            )

            # Build grounded text packet (same evidence + task v2 used).
            # Phase 65 Plan 04 — thread ``recall_moments`` ONLY when non-empty
            # so every existing dj_cohost call-shape test stays BYTE-IDENTICAL
            # (the cold/feature-off path is the v5.0 baseline). An empty list
            # and a missing kwarg are semantically identical (the falsy-gate
            # in evidence_line treats None and [] the same), but the existing
            # mocker.assert_called_once_with(..., registry_snapshot=..., diet=)
            # tests pin the EXACT kwargs — so we omit recall_moments when
            # there's nothing to inject. The non-diet path with survivors
            # passes the kwarg. Diet prompts render a compact recall block
            # only when hot, so MIX_MOVE can use historical move->sound memory
            # without expanding to the full prompt.
            _bp_kwargs: dict[str, Any] = {"registry_snapshot": snapshot, "diet": diet}
            if recall_moments:
                _bp_kwargs["recall_moments"] = recall_moments
            if prompt_audio_capture_context is not None:
                _bp_kwargs["audio_capture_context"] = prompt_audio_capture_context
            if ev is not None:
                text_prompt = AICoach.build_prompt(ev, **_bp_kwargs)
            else:
                # No event context (e.g. generate_reply called without prep) — fall back
                text_prompt = AICoach.build_prompt(
                    Event(type="MANUAL", state=self._state, extra={}),
                    **_bp_kwargs,
                )

            # Phase 77 Plan 04 — WIRE-01: pull the latest CITED grounding citation
            # (latched off-loop by _maybe_dispatch_grounding) and inject it as a
            # ``[track:<id>]`` reference into the prompt. The id resolves in the
            # EvidenceRegistry because ``register_library`` already seeded every
            # library track id (invariant #2) — so the CitationLinter keeps the
            # turn with NO linter change. STRICTLY READ-ONLY: we never write
            # MusicState (single-writer invariant #1). The grounding=None path
            # (cold path) skips this entirely → byte-identical. NEVER inline-await
            # the embed here — get_latest_citation() is a cheap lock-guarded read
            # of the already-computed latch (the off-loop dispatch did the work).
            if self._grounding is not None:
                try:
                    cit = self._grounding.get_latest_citation()
                    if cit is not None and cit.is_cited and cit.track_id:
                        text_prompt = f"{text_prompt} [track:{cit.track_id}]"
                except Exception as _e:
                    print(f"[grounding pull err] {_e}", file=sys.stderr)

            audio_wav = snapshot_wav(self._clean_audio_buf, audio_seconds)
            # Per-invocation dump folder — full audit trail for rapid dev.
            invoke_ts = time.strftime("%H%M%S")
            invoke_n = getattr(self, "_invoke_counter", 0) + 1
            self._invoke_counter = invoke_n
            invoke_dir = (
                self._recorder.session_dir
                / "invocations"
                / f"{invoke_n:04d}_{invoke_ts}_{ev.type if ev else 'MANUAL'}"
            )
            try:
                invoke_dir.mkdir(parents=True, exist_ok=True)
                (invoke_dir / "audio.wav").write_bytes(audio_wav)
                # Also keep top-level shortcut to the latest dump.
                (self._recorder.session_dir / "last_gemini_audio.wav").write_bytes(audio_wav)
            except Exception as _e:
                print(f"[dump err] {_e}", file=sys.stderr)
            # Single-modality: audio only. Screen + MIDI metadata caused hallucination.
            # Plan 19-02 pre-wiring: when v2.x re-enables screen capture, the
            # gate becomes ``screen_jpeg = None if skip_screen else
            # self._screen_buf.latest()[0]`` — for v2.0 the line stays None per
            # the v4 anti-hallucination invariant. The screen Part append below
            # gets a ``not skip_screen`` guard so the diet rule is enforced
            # the moment the screen frame becomes non-None.
            screen_jpeg = None

            # Short-term verbal memory — don't repeat or rephrase what you just said
            history_clause = ""
            if self._ai_text_history:
                recent = " | ".join(f'"{t}"' for t in self._ai_text_history)
                history_clause = (
                    f"\n\nRECENT THINGS YOU JUST SAID (each tagged [M:SS] with the set-time you "
                    f"said it — compare against the current set_time in the evidence packet to know "
                    f"how long ago that was). Do NOT repeat, rephrase, or re-react to a moment you "
                    f"already covered, and don't re-quote a set-time you already mentioned. Find a "
                    f"FRESH angle on what's happening NOW: {recent}"
                )

            # Plan 40-01 / AUDIO-01 — mic-as-2nd-Gemini-Part decision. Three
            # gates; all must pass for Part 2 to attach:
            #   1. self._mic_audio_buf is not None
            #   2. now - state.last_kaan_spoke_at <= MIC_AUDIO_PART_RECENCY_S
            #   3. snapshot ring RMS > MIC_AUDIO_PART_PRESENCE_RMS * 32767
            # The snapshot/RMS work runs ONCE; the result + skip-reason feed
            # both the prompt suffix and the structured log line. Plan 40-03
            # will append a 3rd lookahead Part immediately after this block.
            mic_wav: bytes | None = None
            mic_skip_reason: str | None = None
            kaan_spoke_age_s: float | None = None
            mic_rms_int16: float = 0.0
            if self._mic_audio_buf is None:
                mic_skip_reason = "no_mic_audio_buf"
            else:
                kaan_spoke_age_s = time.time() - self._state.last_kaan_spoke_at
                if kaan_spoke_age_s > MIC_AUDIO_PART_RECENCY_S:
                    mic_skip_reason = "kaan_spoke_not_recent"
                else:
                    # Snapshot the ring at the v4-baseline 8s window and check
                    # presence. snapshot_wav already peak-normalizes — read the
                    # raw int16 pcm via buf.snapshot() for an honest RMS gate.
                    import numpy as _np  # local import — keeps top-level clean

                    n = int(MIC_AUDIO_PART_SECONDS * self._mic_audio_buf._sr)
                    pcm = self._mic_audio_buf.snapshot(n)
                    if pcm.size == 0:
                        mic_skip_reason = "mic_ring_empty"
                    else:
                        mic_rms_int16 = float(_np.sqrt(_np.mean(pcm.astype(_np.float32) ** 2)))
                        presence_floor_int16 = MIC_AUDIO_PART_PRESENCE_RMS * 32767.0
                        if mic_rms_int16 < presence_floor_int16:
                            mic_skip_reason = "mic_silent"
                        else:
                            mic_wav = snapshot_wav(self._mic_audio_buf, MIC_AUDIO_PART_SECONDS)

            # Plan 40-03 / AUDIO-02 + AUDIO-04 — source-file lookahead Part 3
            # decision. Belt-and-braces try/except wrapping: the provider's
            # snapshot_wav() already returns ``(None, meta)`` on every observed
            # failure path (T-40-02-* threat register), but the wrapper here
            # guarantees ``llm_node`` cannot crash even if the provider
            # misbehaves (T-40-03-02 mitigation). When self._lookahead is
            # None (Phase 4/40-01 backward-compat default), Part 3 is never
            # attempted and the meta dict carries an explicit "no_lookahead"
            # reason — feeds the lookahead_part_skipped event below.
            lookahead_wav: bytes | None = None
            lookahead_meta: dict = {"ok": False, "reason": "no_lookahead"}
            if self._lookahead is not None:
                try:
                    lookahead_wav, lookahead_meta = self._lookahead.snapshot_wav()
                except Exception as e:
                    print(f"[lookahead err] {e}", file=sys.stderr)
                    lookahead_wav = None
                    lookahead_meta = {"ok": False, "reason": f"exception: {e!r}"}
            mic_attached = mic_wav is not None
            lookahead_attached = lookahead_wav is not None
            ev_tag = ev.type if ev else "MANUAL"
            first_deck_part_index = 2 + int(mic_attached) + int(lookahead_attached)
            deck_audio_parts = self._deck_audio_part_snapshots(
                ev_tag,
                first_part_index=first_deck_part_index,
            )
            deck_part_labels = {
                str(part["side"]): str(part["label"])
                for part in deck_audio_parts
                if str(part.get("side")) in {"A", "B"} and str(part.get("label"))
            }
            deck_part_activity = {
                str(part["side"]): str(part["activity"])
                for part in deck_audio_parts
                if str(part.get("side")) in {"A", "B"}
                and str(part.get("activity")) in {"active", "silent"}
            }

            # Plan 40-03 — Part-aware prompt suffix via build_parts_description.
            # Delegates the 4-way string dispatch (1-Part baseline / mic-only /
            # lookahead-only / 3-Part full) to the locked builder in
            # vibemix.prompts.matrix. The builder encodes CONTEXT.md Q2:
            # lookahead-present variants carry "NOT YET HEARD BY AUDIENCE" +
            # anti-prediction guard language.
            parts_clause = build_parts_description(
                audio_seconds=float(audio_seconds),
                has_mic_part=mic_attached,
                has_lookahead_part=lookahead_attached,
                # Phase 80 / GROUND-01 — gated framing only; the Part-1 audio
                # attach below stays UNCONDITIONAL (gating it breaks byte-
                # identity). Shared by both the genai + OpenRouter brain paths
                # via contents[0] — no path-specific branch.
                secondary_ear=self._secondary_ear,
            )
            parts_clause += _deck_audio_part_suffix(deck_audio_parts)

            if mic_attached:
                self._recorder.log_event(
                    "mic_part_attached",
                    duration_s=MIC_AUDIO_PART_SECONDS,
                    rms_int16=mic_rms_int16,
                    kaan_spoke_age_s=kaan_spoke_age_s,
                    bytes=len(mic_wav),
                )
            else:
                self._recorder.log_event(
                    "mic_part_skipped",
                    reason=mic_skip_reason or "unknown",
                    kaan_spoke_age_s=kaan_spoke_age_s,
                    rms_int16=mic_rms_int16,
                )
            # Plan 40-03 — Part 3 (lookahead) attach + structured event. The
            # mic_part_* / lookahead_part_* pair forms a uniform diagnostic
            # surface for coach-loop tails + Settings → Diagnostics; per-turn
            # both events fire (one of each pair from each side). The lookahead
            # event carries the provider's full meta dict so events.jsonl
            # consumers see title / file / seek / duration / reason.
            if lookahead_attached:
                self._recorder.log_event(
                    "lookahead_part_attached",
                    bytes=len(lookahead_wav),
                    **{k: v for k, v in lookahead_meta.items() if k != "bytes"},
                )
            else:
                self._recorder.log_event(
                    "lookahead_part_skipped",
                    **lookahead_meta,
                )
            live_claim_state = ev.state if ev is not None else self._state
            live_claim_moves = _event_live_move_labels(ev, self._state)
            live_claim_audio_delta = render_audio_delta_items(live_claim_state)
            observability_state = (
                snapshot_state_for_ai_message(live_claim_state) or live_claim_state
            )
            lookahead_part_label = (
                "P3"
                if lookahead_attached and mic_attached
                else "P2"
                if lookahead_attached
                else None
            )
            deck_audio_parts_attached = bool(
                _deck_audio_part_contract_labels(
                    deck_part_labels or None,
                    reserved_labels=("P2" if mic_attached else None, lookahead_part_label),
                )
            )
            try:
                lookahead_horizon_s = float(lookahead_meta.get("delta_sec") or 3.0)
            except (TypeError, ValueError):
                lookahead_horizon_s = 3.0
            audio_tokens_est = round(float(audio_seconds) * GEMINI_AUDIO_TOKENS_PER_SECOND)
            if mic_attached:
                audio_tokens_est += round(MIC_AUDIO_PART_SECONDS * GEMINI_AUDIO_TOKENS_PER_SECOND)
            if lookahead_attached:
                audio_tokens_est += round(
                    max(0.1, min(12.0, lookahead_horizon_s)) * GEMINI_AUDIO_TOKENS_PER_SECOND
                )
            for deck_part in deck_audio_parts:
                try:
                    deck_seconds = float(deck_part.get("seconds") or self._deck_audio_part_seconds)
                except (TypeError, ValueError):
                    deck_seconds = self._deck_audio_part_seconds
                audio_tokens_est += round(
                    max(1.0, min(6.0, deck_seconds)) * GEMINI_AUDIO_TOKENS_PER_SECOND
                )
            audio_context_clause = _build_attached_audio_context_clause(
                live_claim_state,
                live_claim_moves,
                audio_delta_items=live_claim_audio_delta,
                audio_capture_context=prompt_audio_capture_context,
                audio_seconds=float(audio_seconds),
                mic_part_label="P2" if mic_attached else None,
                lookahead_part_label=lookahead_part_label,
                deck_part_labels=deck_part_labels or None,
                deck_part_activity=deck_part_activity or None,
                deck_part_seconds=self._deck_audio_part_seconds,
                lookahead_horizon_s=lookahead_horizon_s,
            )
            full_text_prompt = text_prompt + history_clause + audio_context_clause + parts_clause

            contents: list = [
                full_text_prompt,
                types.Part.from_bytes(data=audio_wav, mime_type="audio/wav"),
            ]
            if mic_attached:
                contents.append(types.Part.from_bytes(data=mic_wav, mime_type="audio/wav"))
            if lookahead_attached:
                contents.append(types.Part.from_bytes(data=lookahead_wav, mime_type="audio/wav"))
            for deck_part in deck_audio_parts:
                contents.append(types.Part.from_bytes(data=deck_part["wav"], mime_type="audio/wav"))
            if screen_jpeg and not skip_screen:
                contents.append(types.Part.from_bytes(data=screen_jpeg, mime_type="image/jpeg"))

            full_prompt = contents[0] if contents else text_prompt
            prompt_path = invoke_dir / "prompt.txt"
            try:
                prompt_path.write_text(full_prompt)
            except Exception:
                pass

            ai_provider = "openrouter" if self._or_client is not None else "gemini"
            ai_model = self._or_model if self._or_client is not None else LLM_MODEL
            route_chain = self._live_coach_route_chain()
            manual_no_evidence_skip = _should_skip_manual_no_evidence_llm(
                ev_tag,
                live_claim_state,
                live_claim_moves,
                audio_delta_items=live_claim_audio_delta,
                audio_capture_context=prompt_audio_capture_context,
                deck_part_activity=deck_part_activity,
            )
            if manual_no_evidence_skip:
                response_id = f"{invoke_n:04d}_{invoke_ts}"
                response_path = invoke_dir / "response.txt"
                meta_path = invoke_dir / "meta.json"
                meta_payload = {
                    "event": ev_tag,
                    "ts": invoke_ts,
                    "invoke_n": invoke_n,
                    "response_id": response_id,
                    "provider": ai_provider,
                    "model": ai_model,
                    "audible": bool(getattr(observability_state, "audible", False)),
                    "deck": getattr(observability_state, "audible_deck", "none"),
                    "track": getattr(observability_state, "audible_track", None),
                    "track_confidence": round(
                        float(
                            getattr(
                                observability_state,
                                "audible_track_confidence",
                                0.0,
                            )
                            or 0.0
                        ),
                        2,
                    ),
                    "phase": getattr(observability_state, "phase", ""),
                    "rms": round(float(getattr(observability_state, "rms", 0.0) or 0.0), 4),
                    "bpm": round(float(getattr(observability_state, "bpm", 0.0) or 0.0), 1),
                    "audio_bytes": len(audio_wav),
                    "audio_seconds": audio_seconds,
                    "diet": diet,
                    "llm_latency_s": 0.0,
                    "llm_error": None,
                    "response_chars": 0,
                    "suppression": "manual_no_evidence",
                    "slop_matches": [],
                    "citation_lint_valid": None,
                    "citation_lint_reason": "manual_no_live_evidence",
                    "citation_lint_missing": None,
                    "citation_action": "skip",
                    "head_yielded": False,
                    "pre_llm_short_circuit": True,
                    "avoided_audio_tokens_est": audio_tokens_est,
                    **route_chain.event_fields(),
                }
                try:
                    response_path.write_text("")
                    meta_path.write_text(json.dumps(meta_payload, indent=2, ensure_ascii=False))
                except Exception:
                    pass
                try:
                    self._recorder.log_event(
                        "manual_silence_short_circuit",
                        event=ev_tag,
                        reason="manual_no_live_evidence",
                        audible=bool(getattr(observability_state, "audible", False)),
                        deck=getattr(observability_state, "audible_deck", "none"),
                        phase=getattr(observability_state, "phase", ""),
                        rms=round(float(getattr(observability_state, "rms", 0.0) or 0.0), 4),
                        audio_bytes=len(audio_wav),
                        avoided_audio_tokens_est=audio_tokens_est,
                        deck_audio_parts=len(deck_audio_parts),
                        invoke_dir=str(invoke_dir),
                    )
                except Exception:
                    pass
                print("[ai_text] <manual silence: no live evidence>", flush=True)
                record_session_ai_message(
                    self._recorder,
                    engine="live_coach",
                    surface="session",
                    direction="assistant",
                    text="",
                    response_id=response_id,
                    event=ev_tag,
                    provider=ai_provider,
                    model=ai_model,
                    stop_reason="manual_no_live_evidence",
                    latency_s=0.0,
                    prompt_chars=len(full_prompt),
                    response_chars=0,
                    prompt=full_prompt,
                    response="",
                    citation_count=0,
                    citation_action="skip",
                    citation_valid=None,
                    citation_reason="manual_no_live_evidence",
                    suppression="manual_no_evidence",
                    state=observability_state,
                    event_obj=ev,
                    artifacts={
                        "invoke_dir": str(invoke_dir),
                        "prompt_path": str(prompt_path),
                        "response_path": str(response_path),
                        "meta_path": str(meta_path),
                        "audio_path": str(invoke_dir / "audio.wav"),
                    },
                    extra={
                        "head_yielded": False,
                        "diet": diet,
                        "cache_state": "skipped",
                        "audio_tokens_est": 0,
                        "avoided_audio_tokens_est": audio_tokens_est,
                        "deck_audio_parts": len(deck_audio_parts),
                        "live_claim_defer_stream": True,
                        "pre_llm_short_circuit": True,
                        "raw_response_chars": 0,
                        "spoken_response_chars": 0,
                    },
                )
                return

            # ---- Plan 19-03 — context-cache dispatch ----
            # Three branches:
            #   1. cache is None at construction → cache_state="disabled", reuse
            #      self._gen_cfg by reference (Phase 4 byte-identical path).
            #   2. cache non-None but current_name()=None (warm-up window OR
            #      post-invalidate gap) → cache_state="cold", same fallback as
            #      disabled (system_instruction in self._gen_cfg drives the call).
            #   3. cache non-None AND current_name() returns a string → cache_
            #      state="warm", build a per-call gen_cfg with cached_content set
            #      and system_instruction OMITTED (Gemini rejects passing both).
            #      thinking_config + temperature + max_output_tokens preserved.
            if self._cache is None:
                gen_cfg = self._gen_cfg
                cache_state = "disabled"
            else:
                cache_name = self._cache.current_name()
                if cache_name is None:
                    gen_cfg = self._gen_cfg
                    cache_state = "cold"
                else:
                    gen_cfg = types.GenerateContentConfig(
                        cached_content=cache_name,
                        thinking_config=types.ThinkingConfig(thinking_level="minimal"),
                        temperature=1.0,
                        max_output_tokens=1024,  # 2026-05-20 — lifted from 220 for live-coach thinking budget; Kaan: don't cap output
                    )
                    cache_state = "warm"

            direct_grounded_response: str | None = None
            if self._linter_wired:
                raw_direct = ev_extra.get("next_suggestion_fast_response")
                if isinstance(raw_direct, str) and raw_direct.strip():
                    direct_grounded_response = raw_direct.strip()
                    ai_provider = "local"
                    ai_model = "grounded-next-suggestion"
                    cache_state = "direct_grounded_receipt"

            if direct_grounded_response is None:
                self._recorder.log_event(
                    "llm_invoke",
                    event=ev_tag,
                    audible=bool(getattr(observability_state, "audible", False)),
                    deck=getattr(observability_state, "audible_deck", "none"),
                    track=getattr(observability_state, "audible_track", None),
                    phase=getattr(observability_state, "phase", ""),
                    audio_bytes=len(audio_wav),
                    audio_tokens_est=audio_tokens_est,
                    deck_audio_parts=len(deck_audio_parts),
                    has_screen=bool(screen_jpeg),
                    audio_seconds=int(audio_seconds),
                    diet=diet,
                    cache_state=cache_state,
                    provider=ai_provider,
                    model=ai_model,
                    **route_chain.event_fields(),
                    prompt=text_prompt,
                    invoke_dir=str(invoke_dir),
                )
            else:
                self._recorder.log_event(
                    "direct_grounded_receipt",
                    event=ev_tag,
                    audible=bool(getattr(observability_state, "audible", False)),
                    deck=getattr(observability_state, "audible_deck", "none"),
                    track=getattr(observability_state, "audible_track", None),
                    response_chars=len(direct_grounded_response),
                    avoided_audio_tokens_est=audio_tokens_est,
                    deck_audio_parts=len(deck_audio_parts),
                    provider=ai_provider,
                    model=ai_model,
                    reason="next_suggestion_fast_response",
                    invoke_dir=str(invoke_dir),
                )
            # Plan 20-01: surface the linter wiring state in the per-turn
            # log line so coach-loop tails show the gate decision next to
            # cache state. Actual gate decision (valid|invalid|skip) is
            # logged after the stream — see the meta.json dump below.
            linter_state = "wired" if self._linter_wired else "skip"
            if direct_grounded_response is None:
                print(
                    f"\n[llm {ev_tag} #{invoke_n:04d}] audio={len(audio_wav) // 1024}KB"
                    f"({int(audio_seconds)}s) diet={diet} cache={cache_state} "
                    f"linter={linter_state} "
                    f"screen={'yes' if screen_jpeg else 'no'} dump={invoke_dir.name}"
                )
            else:
                print(
                    f"\n[direct {ev_tag} #{invoke_n:04d}] grounded next-suggestion "
                    f"linter={linter_state} dump={invoke_dir.name}"
                )
            anti_slop_runtime_enabled = _anti_slop_runtime_enabled()
            live_claim_defer_stream = (
                should_defer_live_claim_stream(
                    live_claim_state,
                    live_claim_moves,
                    audio_capture_context=prompt_audio_capture_context,
                    audio_delta_items=live_claim_audio_delta,
                    deck_audio_parts_attached=deck_audio_parts_attached,
                    event_type=ev_tag,
                )
                if anti_slop_runtime_enabled
                else False
            )

            # === Chunk-by-chunk streaming pipe-through ===
            # Yields each chunk to TTS as the LLM emits it (no
            # sentence-boundary buffer). The single guard is
            # ``can_yield_chunks(full_text)`` — it blocks yielding only
            # while the accumulated text-so-far either matches a banned
            # opener (silence-token or slop prefix) OR could still grow
            # into one. Once it clears, ``buffered_chunks`` is flushed
            # in one shot and every subsequent chunk passes through
            # verbatim. This eliminates the old sentence-boundary wait
            # (~500ms-2s) AND the end-of-stream defer that left
            # single-sentence responses stuck in the post-stream batched
            # emit path.
            #
            # ``buffered_chunks`` stays alive — the post-stream
            # silence/slop/citation gates are the authority on the FULL
            # response. When the gate never clears (banned-opener
            # locked), the post-stream gate fires the appropriate
            # suppression and nothing is re-yielded. In linter-wired
            # live mode, all chunks are held until citation validation
            # passes, so uncitable text never reaches TTS. In legacy /
            # non-linter paths, chunks may still be flushed mid-stream;
            # if a later post-stream gate fails, a silence-pad frame
            # cancels remaining audio (``streaming_cancel`` event).
            #
            # Streaming pipe state:
            #   buffered_chunks   — every chunk text in arrival order
            #                       (post-stream gate consumes this when
            #                       head_yielded is False).
            #   head_yielded      — True iff the gate cleared and the
            #                       first flush happened. Drives
            #                       post-stream branching (cancel-with-
            #                       silence-pad vs re-yield-from-buffer).
            full_text = ""
            buffered_chunks: list[str] = []
            head_yielded = False
            # When the citation linter is wired, do not stream speculative
            # audio before the full response has passed the evidence gate.
            # A silence-pad can mask trailing audio, but it cannot guarantee
            # the already-yielded head was never heard. Buffering wired turns
            # keeps the product contract binary: cited lines speak; uncitable
            # lines never enter TTS.
            citation_lint_defer_stream = self._linter_wired
            language_defer_stream = False
            # Latches once the reaction ages past the freshness budget before
            # the head commits; holds the head and drives the post-stream
            # "stale" suppression.
            freshness_expired = False
            language_matches: tuple[str, ...] = ()
            tts_yielded_any = False
            tts_yielded_ends_space = False
            direct_voice_skip_reason: str | None = None

            def _prepare_tts_segment(segment: str) -> str:
                nonlocal tts_yielded_any, tts_yielded_ends_space
                tts_segment = model_text_for_tts(segment, normalize=False)
                if tts_yielded_ends_space or not tts_yielded_any:
                    tts_segment = tts_segment.lstrip()
                if tts_segment:
                    tts_yielded_any = True
                    tts_yielded_ends_space = tts_segment[-1].isspace()
                return tts_segment

            # Tracks the highest position in ``full_text`` we have
            # already yielded. Combined with ``last_balanced_position``
            # this keeps mid-stream yields clipped at the last closed
            # citation so TTS never receives a bare ``"[ev:"`` fragment.
            yielded_pos = 0
            t_start = time.time()
            llm_err: str | None = None
            # Plan 19-05 — record first-chunk arrival exactly once per turn for
            # the TTFT meter. Skipped when no meter wired (Phase 4 backward-compat).
            first_chunk_recorded = False
            # ---- Plan 41-02 telemetry — Plan 41-04 may refactor this loop further ----
            # Surface Gemini's UsageMetadata.cached_content_token_count to
            # events.jsonl on every chunk that reports a non-zero hit. The
            # SDK emits the same usage_metadata snapshot on multiple chunks
            # within one stream, so dedupe per-turn against the LAST emitted
            # value to keep the log line count proportional to interesting
            # state-changes, not chunk arrivals.
            last_cache_hit_emitted: int = 0
            # ---- end Plan 41-02 telemetry block ----
            # ---- quick task 260525-fuv — per-session cost meter -----------------
            # usage_metadata repeats across chunks; only the final chunk carries
            # authoritative totals. Capture the last-seen usage here and record()
            # ONCE after the stream completes (the `else` branch below) to avoid
            # double-billing — mirrors the last_cache_hit_emitted dedup intent.
            last_usage = None
            # ---- end quick task 260525-fuv -------------------------------------
            # ---- Plan 69-03 (OSS-02) — pre-call 60s /health canary -----------
            # If the proxy fallback is armed, fire a single canary GET against
            # /health every 60s. On 200, the recovery diagnostic event lands
            # and the flag clears. NEVER raises (probe is best-effort).
            # Phase 69 review WR-01 — the blocking ``probe_proxy_health`` GET is
            # offloaded to a thread executor inside the (now async) canary so the
            # reaction path NEVER stalls on the 5s timeout while the proxy is down
            # (the exact state in which the canary is armed). Mirrors the recall
            # pre-dispatch offload pattern (``set_next_event`` ~line 809).
            if direct_grounded_response is None:
                await self._check_proxy_health_canary(time.monotonic())
            # ---- end Plan 69-03 canary ---------------------------------------
            try:
                if direct_grounded_response is not None:

                    async def _direct_stream(text: str) -> AsyncGenerator:
                        yield type("Chunk", (), {"text": text})()

                    stream = _direct_stream(direct_grounded_response)
                elif self._or_client is not None:
                    # 2026-05-21 — OpenRouter brain. Same ``contents`` (text +
                    # inline-audio Parts) converted to OpenAI-compat messages by
                    # the adapter; system instruction passed explicitly (no
                    # Gemini context cache on this path). Yields genai-shaped
                    # chunks so the downstream loop is byte-identical.
                    from vibemix.agent.openrouter_llm import stream_or

                    stream = stream_or(
                        self._or_client,
                        model=self._or_model,
                        system_instruction=self._prompt_body,
                        contents=contents,
                        temperature=1.0,
                    )
                else:
                    stream = await self._genai_client.aio.models.generate_content_stream(
                        model=LLM_MODEL,
                        contents=contents,
                        config=gen_cfg,
                    )
                async for chunk in stream:
                    txt = getattr(chunk, "text", None) or ""
                    # ---- Plan 41-02 cache_hit telemetry ---------------------
                    # Inspect usage_metadata BEFORE the empty-text continue —
                    # the chunk that carries the final UsageMetadata may have
                    # no text payload but still reports the cache-hit token
                    # count for the whole stream.
                    usage = getattr(chunk, "usage_metadata", None)
                    if usage is not None:
                        # quick task 260525-fuv — keep the last-seen usage; the
                        # final chunk's totals are authoritative. Recorded ONCE
                        # post-stream (see the `else` branch) to avoid double-bill.
                        last_usage = usage
                        cached_tokens = getattr(usage, "cached_content_token_count", None) or 0
                        if cached_tokens > 0 and cached_tokens != last_cache_hit_emitted:
                            try:
                                self._recorder.log_event(
                                    "cache_hit",
                                    cached_tokens=cached_tokens,
                                    model=LLM_MODEL,
                                    path="live_coach",
                                    cache_state=cache_state,
                                )
                            except Exception:
                                # best-effort; never let telemetry write
                                # failures break the LLM stream consumer
                                pass
                            last_cache_hit_emitted = cached_tokens
                    # ---- end Plan 41-02 cache_hit telemetry -----------------
                    if not txt:
                        continue
                    if not first_chunk_recorded and self._ttft_meter is not None:
                        self._ttft_meter.record_first_chunk()
                        first_chunk_recorded = True
                    print(txt, end="", flush=True)
                    full_text += txt
                    buffered_chunks.append(txt)
                    source_detail_risky = (
                        anti_slop_runtime_enabled
                        and (
                            has_unsupported_audio_source_detail_claim(
                                full_text, live_claim_state, event_type=ev_tag
                            )
                            or (
                                not head_yielded
                                and has_unsupported_audio_source_detail_mention(
                                    full_text,
                                    live_claim_state,
                                    event_type=ev_tag,
                                )
                            )
                        )
                    )
                    advice_risky = (
                        anti_slop_runtime_enabled
                        and not live_claim_moves
                        and has_unsupported_no_move_coaching_advice(full_text)
                    )
                    band_intensity_risky = (
                        anti_slop_runtime_enabled
                        and (
                        _unsupported_band_intensity_reason(
                            full_text,
                            live_claim_state,
                            live_claim_moves,
                            event_type=ev_tag,
                        )
                        is not None
                        )
                    )
                    claim_guard_risky = (
                        anti_slop_runtime_enabled
                        and should_defer_live_claim_text(
                            full_text,
                            live_claim_state,
                            live_claim_moves,
                            audio_capture_context=prompt_audio_capture_context,
                            audio_delta_items=live_claim_audio_delta,
                            deck_audio_parts_attached=deck_audio_parts_attached,
                            judge_evidence_line=judge_evidence_line,
                            event_type=ev_tag,
                        )
                    )
                    if (
                        source_detail_risky
                        or advice_risky
                        or band_intensity_risky
                        or claim_guard_risky
                    ):
                        live_claim_defer_stream = True
                    spoken_so_far, _ = strip_emote_tags(full_text, normalize=False)
                    language_matches = english_only_violation_matches(spoken_so_far)
                    if language_matches:
                        language_defer_stream = True
                    if guard_option_scaffold and _starts_option_scaffold(full_text):
                        continue
                    if _could_be_finished_line_meta_scaffold(full_text):
                        continue
                    if _could_be_unspoken_packet_fragment(full_text):
                        continue
                    if live_claim_defer_stream:
                        continue
                    if language_defer_stream:
                        continue
                    if citation_lint_defer_stream:
                        continue
                    # Late-line-blurt guard (Invariant #3 — trust the audio):
                    # once this reaction is older than the freshness budget,
                    # hold the head so stale audio never reaches TTS. Latches;
                    # the post-stream gate logs + suppresses. Arms ONLY before
                    # the head commits (``not head_yielded``) — a line already
                    # speaking on time finishes rather than being cut.
                    if (
                        not head_yielded
                        and not freshness_expired
                        and event_fired_monotonic is not None
                        and time.monotonic() - event_fired_monotonic > stale_age_budget
                    ):
                        freshness_expired = True
                    if freshness_expired:
                        continue
                    # Chunk-by-chunk yield with bracket-balance clipping.
                    # Before the speed-gate clears we hold every chunk
                    # in ``buffered_chunks`` so a banned opener cannot
                    # leak to TTS. After it clears, yields are clipped
                    # at ``last_balanced_position(full_text)`` so an
                    # unclosed citation never reaches the synth (Pitfall
                    # 1 — a bare ``"[ev:kick@2.5"`` would be spoken as
                    # bracket-noise if it reached TTS).
                    if not head_yielded:
                        if can_yield_chunks(full_text):
                            safe_pos = last_balanced_position(full_text)
                            if safe_pos > yielded_pos:
                                segment = full_text[yielded_pos:safe_pos]
                                tts_segment = _prepare_tts_segment(segment)
                                yielded_pos = safe_pos
                                if tts_segment:
                                    head_yielded = True
                                    self._llm_to_tts_meter.record_first_sentence()
                                    yield tts_segment
                            # else: every char is inside an open bracket
                            # (e.g. the entire first chunk is the start
                            # of one big citation). Defer; the next
                            # chunk presumably closes the bracket.
                        # else: gate still blocking — either locked on a
                        # banned opener (post-stream gate will suppress)
                        # or still disambiguating (next chunk may clear).
                    else:
                        # Gate already cleared — extend the safe yield
                        # frontier as more brackets close. If the new
                        # chunk lands entirely inside an open bracket,
                        # ``safe_pos`` won't move and we just defer.
                        safe_pos = last_balanced_position(full_text)
                        if safe_pos > yielded_pos:
                            segment = full_text[yielded_pos:safe_pos]
                            tts_segment = _prepare_tts_segment(segment)
                            yielded_pos = safe_pos
                            if tts_segment:
                                yield tts_segment
            except Exception as e:
                # ---- Plan 69-03 (OSS-02) — proxy unavailable classification ---
                # Classify the exception against the 4 documented trigger classes
                # (5xx / timeout / connection_refused / bad_body). On match, arm
                # the unavailable flag + emit the one-shot diagnostic event;
                # the LLM-turn skip is implicit
                # (full_text stays "" → downstream silence-short-circuit fires
                # naturally → no TTS, no playback). 4xx / 429 / programming
                # errors fall through to the original [llm err] path so the
                # existing per-error messaging surfaces unchanged.
                _unavail = classify_proxy_error(e)
                if _unavail is not None:
                    if self._proxy_base_url is not None:
                        self._maybe_emit_proxy_unavailable(_unavail.reason)
                    else:
                        # Direct Gemini mode has no proxy fallback flag to arm.
                        # Still surface the outage loudly; otherwise 5xx/timeouts
                        # become stderr-only and the UI looks merely "listening".
                        self._emit_connection_error(e)
                else:
                    # NOT a proxy-classified transient (5xx/timeout/refused/bad
                    # body). This is the silent-death class: a direct-mode auth
                    # failure (bad/missing GEMINI_API_KEY → 401/403), a DNS/TLS
                    # error, or any other connect failure on either path. Surface
                    # it LOUDLY — events.jsonl + UI transcript — instead of dying
                    # to stderr-only as before (the release blocker).
                    self._emit_connection_error(e)
                # ---- end Plan 69-03 classification ----------------------------
                llm_err = repr(e)
                print(f"\n[llm err] {e}", file=sys.stderr)
            else:
                if direct_grounded_response is None:
                    # ---- quick task 260525-fuv — once-per-stream cost record -------
                    # The stream completed without raising. Bill the live_coach usage
                    # ONCE here using the last-seen authoritative totals. The
                    # OpenRouter brain path yields chunks with usage_metadata=None →
                    # last_usage stays None → count the generation as untracked (no
                    # fabricated tokens). Best-effort: a meter write must NEVER break
                    # the stream consumer (T-fuv-01).
                    try:
                        if last_usage is not None:
                            get_session_meter().record(
                                "live_coach",
                                prompt=getattr(last_usage, "prompt_token_count", 0) or 0,
                                cached=getattr(last_usage, "cached_content_token_count", 0) or 0,
                                output=getattr(last_usage, "candidates_token_count", 0) or 0,
                            )
                        elif self._or_client is not None:
                            get_session_meter().record_untracked()
                    except Exception:
                        pass
                    # ---- end quick task 260525-fuv ---------------------------------
                    # ---- Plan 69-03 (OSS-02) — implicit recovery on next success --
                    # When the stream completed without raising AND the proxy
                    # fallback flag is currently armed, this is the "next real LLM
                    # call succeeded" recovery path (the second of two recovery
                    # triggers; the other is the 60s /health canary). One-shot
                    # guard means a duplicate emission is impossible.
                    if self._proxy_unavailable:
                        self._maybe_emit_proxy_recovery()
                    # ---- end Plan 69-03 recovery ----------------------------------
                    # Reset the loud connection-error one-shot — the next failure in a
                    # fresh streak should log again. A successful stream means the
                    # connection/auth is healthy now.
                    if self._connection_error_emitted:
                        self._connection_error_emitted = False
                        try:
                            self._recorder.log_event("connection_recovered", path="live_coach")
                        except Exception:
                            pass
                        # No transcript injection for diagnostics. A recovered
                        # connection is observable via events/status; only actual
                        # spoken model output enters transcript_delta.
            # === end Plan 41-04 streaming pipe-through ===

            print()
            elapsed = time.time() - t_start
            stripped = full_text.strip()
            option_scaffold_suppressed = False
            line_scaffold_suppressed = False
            packet_fragment_suppressed = False
            if guard_option_scaffold and _starts_option_scaffold(full_text):
                repaired = _repair_option_scaffold_line(full_text)
                if repaired:
                    raw_option_scaffold_text = full_text
                    full_text = repaired
                    buffered_chunks = [full_text]
                    stripped = full_text.strip()
                    try:
                        self._recorder.log_event(
                            "option_scaffold_repaired",
                            event=ev_tag,
                            raw_text=raw_option_scaffold_text,
                            repaired_text=full_text,
                            latency_s=round(elapsed, 2),
                        )
                    except Exception:
                        pass
                else:
                    option_scaffold_suppressed = True
            elif _starts_finished_line_meta_scaffold(full_text):
                repaired = repair_finished_headphone_line(full_text)
                if repaired:
                    raw_line_scaffold_text = full_text
                    full_text = repaired
                    buffered_chunks = [full_text]
                    stripped = full_text.strip()
                    try:
                        self._recorder.log_event(
                            "line_scaffold_repaired",
                            event=ev_tag,
                            raw_text=raw_line_scaffold_text,
                            repaired_text=full_text,
                            latency_s=round(elapsed, 2),
                        )
                    except Exception:
                        pass
                else:
                    line_scaffold_suppressed = True
            elif _starts_unspoken_packet_fragment(full_text):
                packet_fragment_suppressed = True

            if (
                self._linter_wired
                and self._linter is not None
                and not option_scaffold_suppressed
                and not line_scaffold_suppressed
                and not packet_fragment_suppressed
            ):
                repaired_citation = _repair_missing_live_citation(
                    full_text,
                    ev=ev,
                    ev_extra=ev_extra,
                    text_prompt=text_prompt,
                    linter=self._linter,
                    snapshot=snapshot,
                )
                if repaired_citation is not None:
                    raw_citation_repair_text = full_text
                    full_text, citation_repair_atom = repaired_citation
                    buffered_chunks = [full_text]
                    stripped = full_text.strip()
                    try:
                        self._recorder.log_event(
                            "citation_repair",
                            event=ev_tag,
                            raw_text=raw_citation_repair_text,
                            repaired_text=full_text,
                            citation=citation_repair_atom,
                            latency_s=round(elapsed, 2),
                        )
                    except Exception:
                        pass

            # ---- Plan 18-04: citation-count telemetry ----
            # Count citations in the FULL response text BEFORE the suppression
            # gate. Even silence/slop suppressed turns get their emissions
            # counted — Phase 16 ear-test reads ``registry.citation_telemetry()``
            # as Gemini's TRUE emission rate (not the post-suppression rate)
            # to gate Phase 20 enforcement readiness.
            #
            # response_id format ``f"{invoke_n:04d}_{invoke_ts}"`` matches the
            # per-invocation dump folder name pattern (line ~202) so the
            # events.jsonl line cross-references the dump folder trivially.
            # The recorder.log_event auto-injects ``t = time.time() -
            # self.start_time`` (recorder.py:303) — DO NOT pass ``t`` manually.
            #
            # Best-effort: every step is wrapped in try/except: pass — a
            # parser failure or recorder write failure MUST NOT break the LLM
            # response path (matches v4 anti-pattern parity, threat T-18-04-03).
            try:
                citation_pairs = parse_citations(full_text)
                citation_count = len(citation_pairs)
            except Exception:
                citation_count = 0

            response_id = f"{invoke_n:04d}_{invoke_ts}"
            try:
                self._recorder.log_event(
                    "citation_count",
                    count=citation_count,
                    response_id=response_id,
                )
            except Exception:
                pass  # best-effort; recorder write failure must not block LLM path

            if self._registry is not None:
                try:
                    self._registry.record_citation_count(citation_count)
                except Exception:
                    pass  # best-effort; registry update failure must not block LLM path

            # ---- Silence + slop gate (Phase 10) ----
            suppression: str | None = None
            slop_matches: list[str] = []
            if anti_slop_runtime_enabled:
                if option_scaffold_suppressed:
                    suppression = "option_scaffold"
                elif line_scaffold_suppressed:
                    suppression = "line_scaffold"
                elif packet_fragment_suppressed:
                    suppression = "packet_fragment"
                elif stripped == SILENCE_TOKEN or stripped.startswith(SILENCE_TOKEN):
                    suppression = "silence"
                else:
                    # Run filter_for_slop on the FULL accumulated text; suppress turn
                    # if any banned phrase matches.
                    _filtered, slop_matches = filter_for_slop(full_text)
                    if slop_matches:
                        suppression = "slop"
            elif stripped == SILENCE_TOKEN or stripped.startswith(SILENCE_TOKEN):
                original_text = full_text
                full_text = re.sub(rf"^\s*{re.escape(SILENCE_TOKEN)}\s*", "", full_text).strip()
                if not full_text:
                    full_text = "I am listening."
                stripped = full_text.strip()
                try:
                    self._recorder.log_event(
                        "silence_bypassed",
                        event=ev_tag,
                        original_text=original_text,
                        replacement=full_text,
                    )
                except Exception:
                    pass

            # Late-line-blurt guard — post-stream authority (commit-aware).
            # Re-checks age so the wired/citation-buffered path AND short
            # single-chunk responses (which never reach the mid-stream head
            # gate) are still dropped when stale. Arms ONLY while
            # ``not head_yielded`` — a line already speaking on time finishes
            # rather than being cut mid-delivery (the 'spoke-then-cut' artifact
            # is worse than a clean drop). Independent of the anti-slop flag:
            # this is timing, not content — a stale reaction is suppressed
            # regardless of what it says.
            if (
                not head_yielded
                and event_fired_monotonic is not None
                and time.monotonic() - event_fired_monotonic > stale_age_budget
            ):
                freshness_expired = True
                suppression = "stale"

            # Plan 20-01 meta.json fields — initialized here so the dump
            # path at the bottom can reference them regardless of which
            # branch ran. "skip" means the wired path was not taken (legacy
            # path or suppression beat the linter to it).
            citation_action: str = "skip"
            citation_lint_valid: bool | None = None
            citation_lint_reason: str | None = None
            citation_lint_missing_payload: list[list[str]] | None = None
            pending_transcript_text: str | None = None

            # Plan 41-04 — cancel-with-silence-pad on speculative-emit failure.
            # When ``head_yielded`` is True AND the post-stream gate fails
            # (silence / slop / citation_failure), push a 500ms zero-fill
            # frame into the playback queue (when wired) and emit a
            # ``streaming_cancel`` event. This is the Open Q2 auto-
            # resolution; the LiveKit cancel-race fallback (Pitfall 8) is
            # documented in the module — head may play through to completion
            # if frames are already in the OPUS encoder when we push the pad.
            def _push_silence_pad_and_cancel(reason: str) -> None:
                try:
                    if self._playback is not None:
                        self._playback.push(b"\x00" * SILENCE_PAD_BYTES)
                except Exception as _e:
                    print(f"[silence-pad err] {_e}", file=sys.stderr)
                try:
                    self._recorder.log_event(
                        "streaming_cancel",
                        reason=reason,
                        head_yielded=True,
                        response_chars=len(full_text),
                        latency_s=round(elapsed, 2),
                    )
                except Exception:
                    pass

            live_claim_guard = None
            raw_live_claim_text: str | None = None
            if suppression is None and anti_slop_runtime_enabled:
                try:
                    live_claim_guard = apply_live_claim_guard(
                        full_text,
                        live_claim_state,
                        live_claim_moves,
                        audio_delta_items=live_claim_audio_delta,
                        audio_capture_context=prompt_audio_capture_context,
                        deck_audio_parts_attached=deck_audio_parts_attached,
                        judge_evidence_line=judge_evidence_line,
                        event_type=ev_tag,
                    )
                    band_intensity_reason = _unsupported_band_intensity_reason(
                        live_claim_guard.text if live_claim_guard.corrected else full_text,
                        live_claim_state,
                        live_claim_moves,
                        event_type=ev_tag,
                    )
                    if band_intensity_reason is not None:
                        live_claim_guard = LiveClaimGuardResult(
                            text="",
                            corrected=True,
                            policy="band_intensity_not_grounded",
                            reason=band_intensity_reason,
                            summary=_band_intensity_guard_summary(
                                live_claim_state,
                                event_type=ev_tag,
                            ),
                        )
                except Exception as _e:
                    live_claim_guard = None
                    print(f"[live-claim guard err] {_e}", file=sys.stderr)
                if live_claim_guard is not None and live_claim_guard.corrected:
                    raw_live_claim_text = full_text
                    full_text = live_claim_guard.text
                    stripped = full_text.strip()
                    if _sven_probe_mode_enabled() and full_text:
                        live_claim_guard = LiveClaimGuardResult(
                            text=full_text,
                            corrected=True,
                            emit_corrected=True,
                            policy=live_claim_guard.policy,
                            reason=live_claim_guard.reason,
                            summary=live_claim_guard.summary,
                        )
                    if live_claim_guard.emit_corrected and not re.search(
                        r"[A-Za-z0-9]",
                        model_text_for_tts(full_text),
                    ):
                        live_claim_guard = LiveClaimGuardResult(
                            text=full_text,
                            corrected=True,
                            emit_corrected=False,
                            policy=live_claim_guard.policy,
                            reason="corrected_text_not_speakable",
                            summary=live_claim_guard.summary,
                        )
                    buffered_chunks = [full_text] if full_text else []
                    guard_action = "emit_corrected" if live_claim_guard.emit_corrected else "strip"
                    try:
                        self._recorder.log_event(
                            "live_claim_guard",
                            event=ev_tag,
                            policy=live_claim_guard.policy,
                            reason=live_claim_guard.reason,
                            summary=live_claim_guard.summary,
                            raw_text=raw_live_claim_text,
                            corrected_text=full_text,
                            action=guard_action,
                            latency_s=round(elapsed, 2),
                        )
                    except Exception:
                        pass
                    if head_yielded and not live_claim_guard.emit_corrected:
                        _push_silence_pad_and_cancel("live_claim_guard")

            spoken_text, emote_intents = strip_emote_tags(full_text)
            audience_text = model_text_for_tts(full_text)
            audience_stripped = audience_text.strip()
            if direct_grounded_response is not None and audience_stripped:
                if not self._tts_has_cached_text(audience_text):
                    direct_voice_skip_reason = "chatterbox_cache_miss"
                    try:
                        self._recorder.log_event(
                            "voice_playback_skipped",
                            event=ev_tag,
                            response_id=response_id,
                            reason=direct_voice_skip_reason,
                            cache_state="direct_grounded_receipt",
                            chars=len(audience_text),
                        )
                    except Exception:
                        pass
            if has_emote_tag(full_text):
                # Post-stream re-yield paths consume buffered_chunks only when
                # nothing has reached TTS yet. Collapse to the spoken response
                # so bracketed control/citation tags never leak to audio.
                buffered_chunks = [audience_text] if audience_text else []
            if suppression is None and not (
                live_claim_guard is not None
                and live_claim_guard.corrected
                and not live_claim_guard.emit_corrected
            ):
                language_matches = english_only_violation_matches(audience_text)
                if language_matches:
                    suppression = "non_english"

            if suppression == "silence":
                self._recorder.log_event(
                    "silence_short_circuit",
                    event=ev_tag,
                    response_chars=len(full_text),
                    latency_s=round(elapsed, 2),
                )
                print("[ai_text] <silence/> (suppressed)", flush=True)
                if head_yielded:
                    _push_silence_pad_and_cancel("silence")
            elif suppression == "stale":
                # Late-line-blurt suppression — the reaction's moment has passed.
                # By construction the commit-aware gates only set "stale" while
                # the head was NEVER yielded, so there is nothing in TTS to cancel
                # (no silence-pad needed); the line is simply dropped.
                self._recorder.log_event(
                    "stale_suppressed",
                    event=ev_tag,
                    age_s=(
                        round(time.monotonic() - event_fired_monotonic, 2)
                        if event_fired_monotonic is not None
                        else None
                    ),
                    budget_s=stale_age_budget,
                    response_chars=len(full_text),
                    latency_s=round(elapsed, 2),
                )
                print("[ai_text] <stale reaction suppressed>", flush=True)
            elif suppression == "slop":
                self._recorder.log_event(
                    "slop_suppressed",
                    event=ev_tag,
                    matches=slop_matches,
                    response_chars=len(full_text),
                    latency_s=round(elapsed, 2),
                )
                print(f"[ai_text] <slop suppressed: {slop_matches}>", flush=True)
                if head_yielded:
                    _push_silence_pad_and_cancel("slop")
            elif suppression == "option_scaffold":
                self._recorder.log_event(
                    "option_scaffold_suppressed",
                    event=ev_tag,
                    response_chars=len(full_text),
                    latency_s=round(elapsed, 2),
                )
                print("[ai_text] <option scaffold suppressed>", flush=True)
                if head_yielded:
                    _push_silence_pad_and_cancel("option_scaffold")
            elif suppression == "line_scaffold":
                self._recorder.log_event(
                    "line_scaffold_suppressed",
                    event=ev_tag,
                    response_chars=len(full_text),
                    latency_s=round(elapsed, 2),
                )
                print("[ai_text] <line scaffold suppressed>", flush=True)
                if head_yielded:
                    _push_silence_pad_and_cancel("line_scaffold")
            elif suppression == "packet_fragment":
                self._recorder.log_event(
                    "packet_fragment_suppressed",
                    event=ev_tag,
                    response_chars=len(full_text),
                    latency_s=round(elapsed, 2),
                )
                print("[ai_text] <packet fragment suppressed>", flush=True)
                if head_yielded:
                    _push_silence_pad_and_cancel("packet_fragment")
            elif suppression == "non_english":
                self._recorder.log_event(
                    "non_english_suppressed",
                    event=ev_tag,
                    matches=list(language_matches),
                    response_chars=len(full_text),
                    latency_s=round(elapsed, 2),
                )
                print(
                    f"[ai_text] <non-English suppressed: {list(language_matches)}>",
                    flush=True,
                )
                if head_yielded:
                    _push_silence_pad_and_cancel("non_english")
                buffered_chunks = []
                spoken_text = ""
                audience_text = ""
                audience_stripped = ""
            elif (
                live_claim_guard is not None
                and live_claim_guard.corrected
                and not live_claim_guard.emit_corrected
            ):
                # A live-claim guard hit means the model tried to say something
                # we cannot ground. Do not convert that failure into a spoken
                # canned line; leave the correction in artifacts/repair queues
                # and keep the user's audio path silent.
                citation_action = "strip"
                if head_yielded:
                    _push_silence_pad_and_cancel("live_claim_guard")
                if self._stripped_tracker is not None:
                    self._stripped_tracker.record(
                        True,
                        unverified_text=raw_live_claim_text or full_text,
                    )
                print(
                    f"[ai_text:live-claim-stripped] policy={live_claim_guard.policy}",
                    flush=True,
                )
                buffered_chunks = []
                spoken_text = ""
                audience_text = ""
                audience_stripped = ""
            else:
                # Plan 20-01 — citation linter chokepoint runs HERE, after the
                # silence/slop gate, before yielding chunks. The wired path
                # (all 4 kwargs non-None) runs the binary response-level linter
                # against the same registry snapshot already taken at line ~216
                # (REUSE — never call self._registry.snapshot() twice per turn,
                # races would be possible). The legacy path emits unchanged.
                #
                # Decision ladder (when wired AND suppression is None):
                #   1. valid -> emit + tracker.record(False) + ai_text log.
                #   2. invalid -> DO NOT yield + record(True) + citation_strip
                #      log. Silence beats invented or uncitable speech.
                #      The old one-shot bypass remains a tracker diagnostic
                #      primitive, but live cohost speech no longer consumes it.
                #      (The pre-recorded ack-bank substitution was retired;
                #      see the strip block below.)
                if self._linter_wired and self._linter is not None:
                    lint_result = self._linter.check(full_text, snapshot, mode="live")
                    citation_lint_valid = lint_result.valid
                    citation_lint_reason = lint_result.reason
                    citation_lint_missing_payload = [list(t) for t in lint_result.missing]

                    sven_probe_speak_uncited = _sven_probe_mode_enabled()
                    if lint_result.valid or sven_probe_speak_uncited:
                        citation_action = "emit" if lint_result.valid else "emit_probe_uncited"
                        if sven_probe_speak_uncited and not lint_result.valid:
                            try:
                                self._recorder.log_event(
                                    "citation_bypass",
                                    response_id=response_id,
                                    raw_text=full_text,
                                    missing=citation_lint_missing_payload,
                                    reason=lint_result.reason,
                                    mode="sven_probe",
                                    latency_s=round(elapsed, 2),
                                )
                            except Exception:
                                pass
                        # Plan 41-04 — head_yielded means the streaming pipe
                        # already emitted the head + trailing chunks
                        # in-flight; the legacy re-yield from buffered_chunks
                        # would duplicate audio. Skip it.
                        probe_direct_voice = (
                            self._probe_direct_voice_enabled()
                            and self._playback is not None
                            and self._direct_tts_synthesizer() is not None
                        )
                        if probe_direct_voice:
                            print("[ai_voice:probe-direct] suppress streaming TTS", flush=True)
                        elif direct_voice_skip_reason is not None:
                            print(
                                f"[ai_voice:skipped] reason={direct_voice_skip_reason}",
                                flush=True,
                            )
                        elif not head_yielded:
                            if citation_lint_defer_stream:
                                tts_txt = _prepare_tts_segment(audience_text)
                                if tts_txt:
                                    yield tts_txt
                            else:
                                for txt in buffered_chunks:
                                    tts_txt = _prepare_tts_segment(txt)
                                    if tts_txt:
                                        yield tts_txt
                        if self._stripped_tracker is not None:
                            self._stripped_tracker.record(False)
                        if audience_stripped:
                            print(f"[ai_text] {audience_stripped!r}", flush=True)
                            if self._stripped_tracker is not None:
                                self._stripped_tracker.clear_last_unverified()
                            self._recorder.log_event(
                                "ai_text",
                                text=audience_text,
                                latency_s=round(elapsed, 2),
                            )
                            self._schedule_probe_direct_voice(
                                audience_text,
                                event=ev_tag,
                                response_id=response_id,
                            )
                            # WR-04 — stamp from event-fired set_seconds, not the
                            # post-stream/lint/bus set_seconds (multi-second drift).
                            self._record_said(
                                audience_stripped[:140],
                                set_s_at_event=ev_set_seconds,
                                event=ev,
                            )
                            pending_transcript_text = audience_stripped[:140]
                        else:
                            print("[ai_text] <empty> (skip TTS)", flush=True)
                    else:
                        # Strip path — no chunks yielded. Pre-recorded
                        # ack substitution is retired (English placeholder
                        # clips fought the anti-slop thesis and the
                        # Turkish persona). Linter-wired live mode
                        # defers chunks until validation, so this is
                        # normally pre-TTS silence. The head_yielded
                        # branch remains a defensive legacy-path mask
                        # for any already-in-flight speculative head.
                        citation_action = "strip"
                        if head_yielded:
                            _push_silence_pad_and_cancel("citation_failure")
                        # Plan 55-03 — surface the raw reply as the
                        # last-unverified text: this is the line the user did
                        # NOT hear, but the diagnostics strip should show what
                        # got silenced. Mirrors the raw_text= log field below.
                        if self._stripped_tracker is not None:
                            self._stripped_tracker.record(True, unverified_text=full_text)
                        self._recorder.log_event(
                            "citation_strip",
                            response_id=response_id,
                            raw_text=full_text,
                            missing=citation_lint_missing_payload,
                            reason=lint_result.reason,
                            latency_s=round(elapsed, 2),
                        )
                        print(
                            f"[ai_text:stripped] reason={lint_result.reason}",
                            flush=True,
                        )
                        # History NOT appended — nothing was emitted.
                else:
                    # Legacy Phase 18/19 path — clean turn, yield buffered chunks
                    # in their original order and run the v4 ai_text logging
                    # path (history append + log event). Byte-identical to the
                    # pre-Plan-20 behavior (locked by
                    # tests/agent/test_dj_cohost.py + test_dj_cohost_silence_*).
                    # Plan 41-04 — when ``head_yielded`` is True the streaming
                    # path already emitted the chunks in-flight; skip the
                    # buffer re-yield to avoid duplicate audio.
                    probe_direct_voice = (
                        self._probe_direct_voice_enabled()
                        and self._playback is not None
                        and self._direct_tts_synthesizer() is not None
                    )
                    if probe_direct_voice:
                        print("[ai_voice:probe-direct] suppress streaming TTS", flush=True)
                    elif not head_yielded:
                        replay_chunks = (
                            [audience_text]
                            if live_claim_defer_stream or language_defer_stream
                            else buffered_chunks
                        )
                        for txt in replay_chunks:
                            tts_txt = _prepare_tts_segment(txt)
                            if tts_txt:
                                yield tts_txt
                    if audience_stripped:
                        print(f"[ai_text] {audience_stripped!r}", flush=True)
                        if self._stripped_tracker is not None:
                            self._stripped_tracker.clear_last_unverified()
                        self._recorder.log_event(
                            "ai_text", text=audience_text, latency_s=round(elapsed, 2)
                        )
                        self._schedule_probe_direct_voice(
                            audience_text,
                            event=ev_tag,
                            response_id=response_id,
                        )
                        # WR-04 — stamp from event-fired set_seconds.
                        self._record_said(
                            audience_stripped[:140],
                            set_s_at_event=ev_set_seconds,
                            event=ev,
                        )
                        pending_transcript_text = audience_stripped[:140]
                    else:
                        print("[ai_text] <empty> (skip TTS)", flush=True)
                    # Legacy path = no linter wired; treat as if citation_action
                    # were "emit" for the overlay publish (the user heard the
                    # text). Plan 20-01 wired-path callers set citation_action
                    # explicitly in the branches above.
                    if citation_action == "skip":
                        citation_action = "emit"

            # ---- v8.0 LOG-02 — consolidated per-turn evidence + gate decision ----
            # When the debug-log switch is on (``vibemix --debug-log`` /
            # VIBEMIX_DEBUG_LOG=1), append ONE auditable ``reaction_evidence`` event
            # per turn: a compact digest of the evidence packet the linter checked
            # against (sources → atom count, never the payload) + the citation-gate
            # decision. Runs for EVERY turn — suppressed, emit, strip,
            # legacy. Default-OFF so events.jsonl is byte-identical in normal runs
            # (the discrete citation_count/strip/ai_text events already cover
            # the default case). Best-effort: never breaks the LLM response path.
            if debug_log_enabled():
                try:
                    ev_digest: dict[str, int] = {}
                    if isinstance(snapshot, dict):
                        for _src, _keys in snapshot.items():
                            try:
                                ev_digest[str(_src)] = (
                                    len(_keys) if hasattr(_keys, "__len__") else 0
                                )
                            except Exception:
                                continue
                    self._recorder.log_event(
                        "reaction_evidence",
                        response_id=response_id,
                        event=ev_tag,
                        evidence_sources=ev_digest,
                        citation_count=citation_count,
                        citation_action=citation_action,
                        citation_valid=citation_lint_valid,
                        citation_reason=citation_lint_reason,
                        citation_missing=citation_lint_missing_payload,
                        suppression=suppression,
                        latency_s=round(elapsed, 2),
                    )
                except Exception:
                    pass

            if citation_action == "emit" and emote_intents and audience_stripped:
                reaction_intent = emote_intents[-1]
                try:
                    self._state.last_reaction_intent = reaction_intent
                    self._state.last_reaction_intent_seq = (
                        int(getattr(self._state, "last_reaction_intent_seq", 0) or 0) + 1
                    )
                    self._recorder.log_event(
                        "mascot_reaction_intent",
                        intent=reaction_intent,
                        seq=self._state.last_reaction_intent_seq,
                        response_id=response_id,
                    )
                except Exception:
                    pass

            reaction_msg_dict: dict[str, Any] | None = None
            reaction_msg_ts: str | None = None
            reaction_strip: list[dict] = []
            if self._ipc_bus is not None and citation_action == "emit":
                try:
                    reaction_strip = (
                        _build_citation_strip(
                            reaction_text=spoken_text,
                            registry=self._registry,
                        )
                        if self._registry is not None
                        else []
                    )
                    reaction_msg = SessionCohostReaction.make(
                        text=audience_text,
                        event_id=ev_tag,
                        citation_strip=reaction_strip,
                    )
                    reaction_msg_dict = reaction_msg.to_dict()
                    reaction_msg_ts = str(reaction_msg_dict.get("ts") or "") or None
                except Exception as e:
                    print(f"\n[cohost-reaction build err] {e}", file=sys.stderr)

            # ---- Plan 24-02 — overlay-highlight publish ----
            # Fire once per [screen:<element>] citation IFF:
            #   1. ipc_bus is wired (sidecar publish path enabled).
            #   2. citation_action is "emit" (user heard verified text).
            #      "strip" and "skip"-from-suppression do NOT publish: a ring
            #      without audio is ghost-firing.
            # Best-effort: every step wrapped in try/except so a malformed
            # element_id, schema validation error, or bus emit failure
            # cannot break the LLM response path (T-18-04-03-style mitigation).
            if self._ipc_bus is not None and citation_action == "emit":
                try:
                    for source, body in parse_citations(full_text):
                        if source != "screen":
                            continue
                        # The body of a [screen:<key>] atom is the element_id
                        # verbatim — no @t suffix per evidence_registry grammar.
                        element_id = body.strip()
                        if not element_id:
                            continue
                        msg = SessionOverlayHighlight.make(
                            element_id=element_id,
                            color=OVERLAY_COLOR,
                            duration_ms=OVERLAY_DURATION_MS,
                        )
                        await self._ipc_bus.emit(msg.to_dict())
                except Exception as e:
                    print(f"\n[overlay publish err] {e}", file=sys.stderr)

            # ---- Plan 44-03 / LAUNCH-02 — cohost-reaction broadcast ----
            # Same guard as overlay-highlight: fire only when the user actually
            # heard the reaction (citation_action == emit). When the
            # linter stripped the text or suppression beat the linter to it,
            # no chips fire — chips below a silent reaction would be ghost UI.
            # When the registry is None (Phase 4 backward-compat path) or has
            # no matching observations, `citation_strip` is an empty list and
            # the message still fires — the UI then renders the transcript
            # line without a chip strip beneath it (correct behavior, not a
            # missed broadcast).
            # Best-effort: any exception in chip building OR the bus emit is
            # logged + swallowed; the LLM response path must NEVER crash on
            # the launch-marketing surface (T-18-04-03-style mitigation).
            if self._ipc_bus is not None and citation_action == "emit":
                if reaction_msg_dict is not None:
                    try:
                        await self._ipc_bus.emit(reaction_msg_dict)
                    except Exception as e:
                        print(f"\n[cohost-reaction publish err] {e}", file=sys.stderr)
                    else:
                        # Arm recall cooldown only when the chip reached the UI.
                        try:
                            if any(
                                chip.get("event_id", "").startswith("recall:")
                                for chip in reaction_strip
                            ):
                                self._last_recall_callback_at = time.time()
                        except Exception as _e:
                            print(f"\n[recall cooldown arm err] {_e}", file=sys.stderr)
            elif self._ipc_bus is None and citation_action == "emit":
                # Phase 66 (COPILOT-02) — bus-less arm path. When ``_ipc_bus`` is
                # None (test contexts that don't wire the UI broadcast surface,
                # or production agents that skip the IPC bus) the chip surface
                # never publishes, but the AUDIO surface still delivered the
                # reaction to the audience via the TTS chunks (citation_action
                # emit). Reuse the same grounded-strip lens as the bus
                # path so fabricated recall atoms never arm cooldown.
                if self._recall_enabled and self._registry is not None:
                    try:
                        strip = _build_citation_strip(
                            reaction_text=spoken_text,
                            registry=self._registry,
                        )
                        if any(chip.get("event_id", "").startswith("recall:") for chip in strip):
                            self._last_recall_callback_at = time.time()
                    except Exception as _e:
                        print(f"\n[recall cooldown arm err] {_e}", file=sys.stderr)

            if pending_transcript_text:
                self._push_transcript(pending_transcript_text, ts=reaction_msg_ts)

            # ---- Per-invocation dump (always written, even on suppression) ----
            response_path = invoke_dir / "response.txt"
            meta_path = invoke_dir / "meta.json"
            prompt_path = invoke_dir / "prompt.txt"
            meta_payload = {
                "event": ev_tag,
                "ts": invoke_ts,
                "invoke_n": invoke_n,
                "response_id": response_id,
                "provider": ai_provider,
                "model": ai_model,
                "audible": bool(getattr(observability_state, "audible", False)),
                "deck": getattr(observability_state, "audible_deck", "none"),
                "track": getattr(observability_state, "audible_track", None),
                "track_confidence": round(
                    float(getattr(observability_state, "audible_track_confidence", 0.0) or 0.0),
                    2,
                ),
                "phase": getattr(observability_state, "phase", ""),
                "rms": round(float(getattr(observability_state, "rms", 0.0) or 0.0), 4),
                "bpm": round(float(getattr(observability_state, "bpm", 0.0) or 0.0), 1),
                "audio_bytes": len(audio_wav),
                "audio_seconds": audio_seconds,
                "diet": diet,
                "llm_latency_s": round(elapsed, 2),
                "llm_error": llm_err,
                "response_chars": len(full_text),
                "suppression": suppression,
                "slop_matches": slop_matches,
                "language_matches": list(language_matches),
                # Plan 20-01 — citation linter chokepoint outcome. When wired
                # is False, all four are None (skip path).
                "citation_lint_valid": citation_lint_valid,
                "citation_lint_reason": citation_lint_reason,
                "citation_lint_missing": citation_lint_missing_payload,
                "citation_action": citation_action,
                # Plan 41-04 — streaming-pipe outcome. True iff the
                # speculative head was emitted before stream completion; False
                # on suppression/short-response.
                "head_yielded": head_yielded,
                "pre_llm_fast_path": direct_grounded_response is not None,
                "direct_voice_skip_reason": direct_voice_skip_reason,
                "avoided_audio_tokens_est": audio_tokens_est
                if direct_grounded_response is not None
                else 0,
            }
            try:
                response_path.write_text(full_text)
                meta_path.write_text(json.dumps(meta_payload, indent=2, ensure_ascii=False))
            except Exception:
                pass

            record_session_ai_message(
                self._recorder,
                engine="live_coach",
                surface="session",
                direction="assistant",
                text=audience_text,
                response_id=response_id,
                event=ev_tag,
                provider=ai_provider,
                model=ai_model,
                stop_reason=llm_err
                or suppression
                or (
                    "direct_grounded_receipt"
                    if direct_grounded_response is not None and citation_action == "emit"
                    else citation_action
                ),
                latency_s=round(elapsed, 2),
                prompt_chars=len(full_prompt),
                response_chars=len(full_text),
                prompt=full_prompt,
                response=full_text,
                citation_count=citation_count,
                citation_action=citation_action,
                citation_valid=citation_lint_valid,
                citation_reason=citation_lint_reason,
                suppression=suppression,
                state=observability_state,
                event_obj=ev,
                artifacts={
                    "invoke_dir": str(invoke_dir),
                    "prompt_path": str(prompt_path),
                    "response_path": str(response_path),
                    "meta_path": str(meta_path),
                    "audio_path": str(invoke_dir / "audio.wav"),
                },
                extra={
                    "head_yielded": head_yielded,
                    "diet": diet,
                    "cache_state": cache_state,
                    "audio_tokens_est": audio_tokens_est,
                    "deck_audio_parts": len(deck_audio_parts),
                    "live_claim_defer_stream": live_claim_defer_stream,
                    "pre_llm_fast_path": direct_grounded_response is not None,
                    "direct_voice_skip_reason": direct_voice_skip_reason,
                    "avoided_audio_tokens_est": audio_tokens_est
                    if direct_grounded_response is not None
                    else 0,
                    "language_defer_stream": language_defer_stream,
                    "language_matches": list(language_matches),
                    "raw_response_chars": len(full_text),
                    "spoken_response_chars": len(audience_text),
                },
            )

            # Plan 41-04 — emit llm_to_tts_delta_ms event (skip when no head
            # was yielded — keeps the per-turn metric stream tight).
            try:
                self._llm_to_tts_meter.log_turn(
                    self._recorder,
                    extra={
                        "event": ev_tag,
                        "response_id": response_id,
                        "head_yielded": head_yielded,
                    },
                )
            except Exception as _e:
                print(f"[delta-meter err] {_e}", file=sys.stderr)
        finally:
            self._clear_turn_latches()

    def _clear_turn_latches(self) -> None:
        """Phase 77 review WR-03 — clear the recall + grounding turn-end
        latches, called from the ``finally`` that wraps the ``llm_node``
        stream/emit body so the clears ALWAYS run regardless of how the turn
        exits (normal completion, a mid-stream exception between the inner
        guarded blocks, or generator close).

        Previously these clears sat at the function-body tail AFTER the
        ``finally`` at the recall-pull block, so any uncaught exception in
        the streaming/lint/emit phase skipped them and a ``[track:<id>]`` /
        ``[recall:<id>]`` latch persisted into the next turn — widening the
        CR-01 stale-citation window. Moving them into a wrapping ``finally``
        guarantees the latch is cleared on every exit path. Both clears are
        best-effort: a clear() failure cannot perturb the turn that already
        completed.

        Phase 65 Plan 04 / Phase 77 Plan 04 — clear reasons unchanged:
        (1) the next HEARTBEAT turn never retrieves/grounds, so a stale latch
        must NOT be re-injected; (2) the next track-aware event overwrites
        ``_latest`` cleanly via its own on_event dispatch. The cold/feature-
        off paths (recall disabled / grounding=None) skip → byte-identical.
        """
        if self._recall_enabled and self._recall is not None:
            try:
                self._recall.clear()
            except Exception as _e:  # pragma: no cover — defensive only
                print(f"[recall clear err] {_e}", file=sys.stderr)
        if self._grounding is not None:
            try:
                self._grounding.clear()
            except Exception as _e:  # pragma: no cover — defensive only
                print(f"[grounding clear err] {_e}", file=sys.stderr)

    async def invalidate_cache(self) -> None:
        """Invalidate the context cache — Plan 19-03 cancel-aware chokepoint.

        Called by the cancel-and-refire path in Plan 19-01 (CancelGate
        telemetry callback) to ensure the refire starts with a fresh cache
        rather than one that may carry context from the cancelled in-flight
        turn. No-op when the agent was constructed without a cache (the
        Phase 4 backward-compat default).

        This is the single public agent-side surface for cache invalidation —
        downstream code (Plan 19-04 ack-bank wiring, future Settings UI)
        SHOULD call this method, NOT reach into self._cache directly."""
        if self._cache is not None:
            await self._cache.invalidate()
