# SPDX-License-Identifier: Apache-2.0
"""DJCoHostAgent — Phase 10 cascade with prompt-matrix dispatch + anti-slop.

Hijacks ``llm_node`` to bypass LiveKit's text-only cascade and call
``google.genai`` directly with the last INVOKE_AUDIO_SECONDS of audio attached
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
import sys
import time
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from google import genai
from google.genai import types
from livekit.agents import Agent, ModelSettings
from livekit.agents import llm as agents_llm
from livekit.agents import tts as agents_tts

from vibemix.agent._streaming_pipe import (
    can_yield_chunks,
    find_sentence_end,
    last_balanced_position,
    passes_head_gate,
)
from vibemix.agent.cache import GeminiContextCache
from vibemix.agent.config import LLM_MODEL, OPENROUTER_LLM_MODEL
from vibemix.agent.proxy_client import (
    classify_proxy_error,
    probe_proxy_health,
)
from vibemix.audio import (
    INVOKE_AUDIO_SECONDS,
    MIC_AUDIO_PART_PRESENCE_RMS,
    MIC_AUDIO_PART_RECENCY_S,
    MIC_AUDIO_PART_SECONDS,
    AudioBuffer,
    VoiceRecorder,
    snapshot_wav,
)
from vibemix.coach import CitationLinter, StrippedRateTracker
from vibemix.library.budget import get_session_meter
from vibemix.llm.thinking_gate import validate_live_config
from vibemix.prompts import build_parts_description, build_system_instruction, filter_for_slop
from vibemix.runtime.debug_flags import debug_log_enabled
from vibemix.runtime.llm_to_tts_delta_meter import LLMToTTSDeltaMeter
from vibemix.runtime.ttft import TTFTMeter
from vibemix.state import AICoach, Event, EvidenceRegistry, MusicState, parse_citations
from vibemix.state.coach import ACK_ELIGIBLE_EVENTS
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

# Plan 19-02 — events where the screen Part is ALWAYS skipped, even if a
# screen frame is available. CONTEXT D-08 rule: MIX_MOVE + HEARTBEAT keep the
# diet payload tight (text + 6s audio only). Pre-wires the v2.x re-enable
# path with the diet rule already enforced — for v2.0 the screen Part is
# always None (v4 anti-hallucination invariant), so this guard is a no-op
# today; it becomes load-bearing the day the screen Part comes back.
SCREEN_SKIP_EVENTS: frozenset[str] = frozenset({"MIX_MOVE", "HEARTBEAT"})

# Plan 19-02 — diet audio window for ack-eligible events. Trims from the
# default 18s INVOKE_AUDIO_SECONDS to 6s — saves ≥500ms TTFT (CONTEXT D-08
# Pitfall 9) by reducing the multimodal payload size.
DIET_AUDIO_SECONDS: float = 6.0

# Env-var names — public contract, surfaced in CLI / Settings UI in Phase 11/12.
ENV_SKILL_LEVEL = "VIBEMIX_SKILL_LEVEL"
ENV_MODE = "VIBEMIX_MODE"
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
    ``midi``, ``key``. Other sources (``aud``, ``track``, ``screen``,
    ``tend``) parse correctly but do not yield chips — they're either too
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
        # yield UI chips. Quiet sources (aud/screen/tend) parse but do
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
        if source not in ("ev", "mix", "midi", "key", "recall", "exemplar", "cue"):
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


def _resolve_prompt_cell(mood: str | None = None) -> str:
    """Read the env vars and dispatch to the right matrix cell.

    Re-evaluated per ``DJCoHostAgent`` instantiation (no module-level
    caching) so unit tests can monkeypatch and Settings UI can hot-swap
    by re-instantiating the agent (Phase 11/12).

    Args:
        mood: Phase 13-05 mood override. When None (default), reads
            ``VIBEMIX_MOOD`` env var, falling back to ``"hype-man"``. A
            non-None ``mood`` arg wins over the env var (used by Plan
            13-06's agent-rebuild-on-mood-change path).

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
                project_profile(_model, consent=_consent).get(
                    "transition_style_tags", ()
                )
            )
    except Exception:  # pragma: no cover — any read fail = no overlay
        taste_tags = ()

    # CR-02: validate the persisted value against the lens enum BEFORE
    # subscripting. An unknown/foreign value (e.g. a stray mood name) falls
    # through to the cold path instead of raising a raw KeyError.
    if lens is not None:
        from vibemix.prompts.matrix import LENS_TO_MODE_MOOD

        if lens in LENS_TO_MODE_MOOD:
            mode, lens_mood = LENS_TO_MODE_MOOD[lens]
            return build_system_instruction(
                skill, mode, lens_mood, taste_persona_tags=taste_tags
            )

    mode = os.environ.get(ENV_MODE, DEFAULT_MODE)
    if mood is None:
        mood = os.environ.get(ENV_MOOD, DEFAULT_MOOD)
    return build_system_instruction(
        skill, mode, mood, taste_persona_tags=taste_tags
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
        prompt_body = _resolve_prompt_cell(mood=live_mood)
        super().__init__(
            instructions=prompt_body,
            llm=llm_inst,
            tts=tts_inst,
            allow_interruptions=False,
        )
        self._genai_client = genai_client
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
            x is not None
            for x in (citation_linter, stripped_rate_tracker, playback)
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
        self._ai_text_history: collections.deque = collections.deque(maxlen=10)
        # ipc.session.snapshot transcript sink (see __init__ kwarg docstring).
        self._transcript_sink: collections.deque | None = transcript_sink

        # ---- Phase 69 Plan 69-03 (OSS-02) — proxy fallback state ----------
        # In proxy mode, when the upstream Bravoh proxy returns 5xx / times
        # out / refuses the connection / returns non-JSON body, the brain
        # refuses to lie (anti-slop): a one-shot "Co-host unavailable this
        # session" transcript line lands, LLM emission skips for the
        # duration, and a 60s ``probe_proxy_health`` canary auto-clears the
        # flag when /health returns 200 (or whenever a real LLM call next
        # succeeds — whichever fires first).
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
            os.environ.get(
                "VIBEMIX_PROXY_BASE_URL", "https://api.altidus.world"
            ).rstrip("/")
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

    def _push_transcript(self, text: str) -> None:
        """Best-effort push of a spoken AI line onto the snapshot sink.

        Called next to each ``_ai_text_history.append`` (the spoken-text
        signal). Swallows all errors — a transcript-sink hiccup must never
        perturb a reaction turn.
        """
        if self._transcript_sink is None:
            return
        try:
            self._transcript_sink.append(text)
        except Exception:
            pass

    def _maybe_emit_proxy_unavailable(self, reason: str) -> None:
        """Arm the proxy-unavailable fallback flag + emit the one-shot
        "Co-host unavailable this session" transcript line (Plan 69-03 / OSS-02).

        Gates:
        - Only fires when ``self._proxy_base_url is not None`` (proxy mode).
          Direct mode (BYO) never arms — BYO users see their own network
          errors per existing v3.x behavior.
        - The transcript line emits EXACTLY ONCE per unavailable-streak;
          subsequent ticks while still unavailable do not spam the transcript.

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
            self._push_transcript("Co-host unavailable this session")
            try:
                self._recorder.log_event(
                    "proxy_unavailable", reason=reason, path="live_coach"
                )
            except Exception:
                pass

    def _maybe_emit_proxy_recovery(self) -> None:
        """Emit the one-shot "Co-host back online" transcript line and clear
        the proxy-unavailable flag (Plan 69-03 / OSS-02).

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
            self._push_transcript("Co-host back online")
            try:
                self._recorder.log_event("proxy_recovered", path="live_coach")
            except Exception:
                pass

    def _emit_connection_error(self, err: BaseException) -> None:
        """LOUD, never-silent surfacing of an LLM connect/auth failure.

        Fires from the ``llm_node`` exception handler for ANY error that the
        proxy classifier did NOT already handle. Covers the release-blocker
        case: a direct-mode session whose Gemini key is missing/invalid (or
        whose connection is refused) used to print ``[llm err]`` to stderr
        ONLY — no ``events.jsonl`` line, no UI signal — so the co-host fell
        silent with zero diagnostics. Now we:

          1. log a ``connection_error`` event to ``events.jsonl`` (with a
             coarse, key-free classification so logs never leak secrets), and
          2. push a one-shot ``"Co-host can't reach Gemini — check API key /
             connection"`` line onto the UI transcript sink.

        One-shot per error streak (``_connection_error_emitted``) so a
        persistent failure logs once, not 10×/second. Cleared on the next
        successful stream (see the ``else`` branch in ``llm_node``).

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
            for tok in ("401", "403", "unauthorized", "permission", "api key", "api_key", "invalid key", "authenticat")
        ):
            kind = "auth"
        elif any(tok in low for tok in ("getaddrinfo", "name resolution", "dns")):
            kind = "dns"
        elif any(tok in low for tok in ("refused", "connection reset", "ssl", "tls", "timed out", "timeout")):
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

        # 3. UI transcript sink — the user-visible "it's broken" signal.
        try:
            self._push_transcript("Co-host can't reach Gemini — check API key / connection")
        except Exception:
            pass

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
        ok = await loop.run_in_executor(
            None, probe_proxy_health, self._proxy_base_url
        )
        if ok:
            self._maybe_emit_proxy_recovery()

    def _record_said(self, text: str, set_s_at_event: float | None = None) -> None:
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

    def set_next_event(self, ev: Event) -> None:
        self._pending_event = ev
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
                RECALL_EVENT_GATE,
                build_recall_query,
            )
        except Exception as _e:  # pragma: no cover — defensive only
            print(f"[recall dispatch import err] {_e}", file=sys.stderr)
            return
        # Event gate — short-circuit BEFORE any executor / loop work on
        # the high-frequency event classes (HEARTBEAT, MIX_MOVE, etc.).
        # MemoryRecall.on_event ALSO gates internally (defense in depth),
        # but checking here avoids burning a task + executor slot.
        if ev.type not in RECALL_EVENT_GATE:
            return
        # Build the query text + resolve current_session_id before the
        # executor hop — `build_recall_query` is duck-typed (no live-path
        # import) and `_recorder.session_dir.name` is the canonical
        # session-id basename used by the rest of the runtime.
        try:
            query_text = build_recall_query(ev)
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
            float(getattr(ev.state, "set_seconds", 0.0) or 0.0)
            if ev is not None
            else None
        )
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
                if recall_moments and (
                    time.time() - self._last_recall_callback_at
                ) < RECALL_CALLBACK_COOLDOWN_S:
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

            # Plan 19-02 — diet dispatch. Ack-eligible events (HEARTBEAT,
            # MIX_MOVE, LAYER_ARRIVAL, KAAN_SPOKE) shrink to a 6s audio window
            # + the compact 5-field evidence_line; non-ack events keep the full
            # 18s window + full evidence_line + corpus footer. An unknown
            # ev.type defaults safely to diet=False (full payload) — erring
            # toward correctness over latency (T-19-02-02 mitigation).
            ev_type_for_diet = ev.type if ev is not None else "MANUAL"
            diet = ev_type_for_diet in ACK_ELIGIBLE_EVENTS
            audio_seconds = DIET_AUDIO_SECONDS if diet else INVOKE_AUDIO_SECONDS
            skip_screen = ev_type_for_diet in SCREEN_SKIP_EVENTS

            # Build grounded text packet (same evidence + task v2 used).
            # Phase 65 Plan 04 — thread ``recall_moments`` ONLY when non-empty
            # so every existing dj_cohost call-shape test stays BYTE-IDENTICAL
            # (the cold/feature-off path is the v5.0 baseline). An empty list
            # and a missing kwarg are semantically identical (the falsy-gate
            # in evidence_line treats None and [] the same), but the existing
            # mocker.assert_called_once_with(..., registry_snapshot=..., diet=)
            # tests pin the EXACT kwargs — so we omit recall_moments when
            # there's nothing to inject. The non-diet path with survivors
            # passes the kwarg; the diet path NEVER receives it (diet =
            # ACK_ELIGIBLE_EVENTS, never a retrieval event).
            _bp_kwargs: dict[str, Any] = {"registry_snapshot": snapshot, "diet": diet}
            if recall_moments and not diet:
                _bp_kwargs["recall_moments"] = recall_moments
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
                        mic_rms_int16 = float(
                            _np.sqrt(_np.mean(pcm.astype(_np.float32) ** 2))
                        )
                        presence_floor_int16 = MIC_AUDIO_PART_PRESENCE_RMS * 32767.0
                        if mic_rms_int16 < presence_floor_int16:
                            mic_skip_reason = "mic_silent"
                        else:
                            mic_wav = snapshot_wav(
                                self._mic_audio_buf, MIC_AUDIO_PART_SECONDS
                            )

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

            contents: list = [
                text_prompt + parts_clause + history_clause,
                types.Part.from_bytes(data=audio_wav, mime_type="audio/wav"),
            ]
            if mic_attached:
                contents.append(types.Part.from_bytes(data=mic_wav, mime_type="audio/wav"))
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
                contents.append(
                    types.Part.from_bytes(data=lookahead_wav, mime_type="audio/wav")
                )
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
            if screen_jpeg and not skip_screen:
                contents.append(types.Part.from_bytes(data=screen_jpeg, mime_type="image/jpeg"))

            ev_tag = ev.type if ev else "MANUAL"
            full_prompt = contents[0] if contents else text_prompt
            try:
                (invoke_dir / "prompt.txt").write_text(full_prompt)
            except Exception:
                pass

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

            self._recorder.log_event(
                "llm_invoke",
                event=ev_tag,
                audible=self._state.audible,
                deck=self._state.audible_deck,
                track=self._state.audible_track,
                phase=self._state.phase,
                audio_bytes=len(audio_wav),
                has_screen=bool(screen_jpeg),
                audio_seconds=int(audio_seconds),
                diet=diet,
                cache_state=cache_state,
                prompt=text_prompt,
                invoke_dir=str(invoke_dir),
            )
            # Plan 20-01: surface the linter wiring state in the per-turn
            # log line so coach-loop tails show the gate decision next to
            # cache state. Actual gate decision (valid|invalid|skip) is
            # logged after the stream — see the meta.json dump below.
            linter_state = "wired" if self._linter_wired else "skip"
            print(
                f"\n[llm {ev_tag} #{invoke_n:04d}] audio={len(audio_wav) // 1024}KB"
                f"({int(audio_seconds)}s) diet={diet} cache={cache_state} "
                f"linter={linter_state} "
                f"screen={'yes' if screen_jpeg else 'no'} dump={invoke_dir.name}"
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
            # suppression and nothing is re-yielded. When chunks WERE
            # flushed mid-stream and the post-stream gate fails (slop in
            # trailing text, missing citation), a silence-pad frame
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
            # /health every 60s. On 200, the recovery one-shot transcript line
            # lands and the flag clears. NEVER raises (probe is best-effort).
            # Phase 69 review WR-01 — the blocking ``probe_proxy_health`` GET is
            # offloaded to a thread executor inside the (now async) canary so the
            # reaction path NEVER stalls on the 5s timeout while the proxy is down
            # (the exact state in which the canary is armed). Mirrors the recall
            # pre-dispatch offload pattern (``set_next_event`` ~line 809).
            await self._check_proxy_health_canary(time.monotonic())
            # ---- end Plan 69-03 canary ---------------------------------------
            try:
                if self._or_client is not None:
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
                        cached_tokens = (
                            getattr(usage, "cached_content_token_count", None) or 0
                        )
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
                            if safe_pos > 0:
                                head_yielded = True
                                self._llm_to_tts_meter.record_first_sentence()
                                yield full_text[:safe_pos]
                                yielded_pos = safe_pos
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
                            yield full_text[yielded_pos:safe_pos]
                            yielded_pos = safe_pos
            except Exception as e:
                # ---- Plan 69-03 (OSS-02) — proxy unavailable classification ---
                # Classify the exception against the 4 documented trigger classes
                # (5xx / timeout / connection_refused / bad_body). On match, arm
                # the fallback flag + emit the one-shot "Co-host unavailable
                # this session" transcript line; the LLM-turn skip is implicit
                # (full_text stays "" → downstream silence-short-circuit fires
                # naturally → no TTS, no playback). 4xx / 429 / programming
                # errors fall through to the original [llm err] path so the
                # existing per-error messaging surfaces unchanged.
                _unavail = classify_proxy_error(e)
                if _unavail is not None:
                    self._maybe_emit_proxy_unavailable(_unavail.reason)
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
                            cached=getattr(last_usage, "cached_content_token_count", 0)
                            or 0,
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
                    try:
                        self._push_transcript("Co-host reconnected")
                    except Exception:
                        pass
            # === end Plan 41-04 streaming pipe-through ===

            print()
            elapsed = time.time() - t_start
            stripped = full_text.strip()

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
            if stripped == SILENCE_TOKEN or stripped.startswith(SILENCE_TOKEN):
                suppression = "silence"
            else:
                # Run filter_for_slop on the FULL accumulated text; suppress turn
                # if any banned phrase matches.
                _filtered, slop_matches = filter_for_slop(full_text)
                if slop_matches:
                    suppression = "slop"

            # Plan 20-01 meta.json fields — initialized here so the dump
            # path at the bottom can reference them regardless of which
            # branch ran. "skip" means the wired path was not taken (legacy
            # path or suppression beat the linter to it).
            citation_action: str = "skip"
            citation_lint_valid: bool | None = None
            citation_lint_reason: str | None = None
            citation_lint_missing_payload: list[list[str]] | None = None

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
            else:
                # Plan 20-01 — citation linter chokepoint runs HERE, after the
                # silence/slop gate, before yielding chunks. The wired path
                # (all 4 kwargs non-None) runs the binary response-level linter
                # against the same registry snapshot already taken at line ~216
                # (REUSE — never call self._registry.snapshot() twice per turn,
                # races would be possible). The legacy path emits unchanged.
                #
                # Decision ladder (when wired AND suppression is None):
                #   1. valid → emit + tracker.record(False) + ai_text log.
                #   2. invalid + bypass → emit anyway + record(False) +
                #      citation_bypass log + "[ai_text:unverified]" stdout.
                #      Bypass is one-shot per breach window (T-20-01-02).
                #   3. invalid + strip → DO NOT yield + record(True) +
                #      citation_strip log. silence > invented citation.
                #      (The pre-recorded ack-bank substitution was retired —
                #      see the strip block below.)
                if self._linter_wired and self._linter is not None:
                    lint_result = self._linter.check(
                        full_text, snapshot, mode="live"
                    )
                    citation_lint_valid = lint_result.valid
                    citation_lint_reason = lint_result.reason
                    citation_lint_missing_payload = [list(t) for t in lint_result.missing]

                    if lint_result.valid:
                        citation_action = "emit"
                        # Plan 41-04 — head_yielded means the streaming pipe
                        # already emitted the head + trailing chunks
                        # in-flight; the legacy re-yield from buffered_chunks
                        # would duplicate audio. Skip it.
                        if not head_yielded:
                            for txt in buffered_chunks:
                                yield txt
                        if self._stripped_tracker is not None:
                            self._stripped_tracker.record(False)
                        if stripped:
                            print(f"[ai_text] {stripped!r}", flush=True)
                            self._recorder.log_event(
                                "ai_text",
                                text=full_text,
                                latency_s=round(elapsed, 2),
                            )
                            # WR-04 — stamp from event-fired set_seconds, not the
                            # post-stream/lint/bus set_seconds (multi-second drift).
                            self._record_said(stripped[:140], set_s_at_event=ev_set_seconds)
                            self._push_transcript(stripped[:140])
                        else:
                            print("[ai_text] <empty> (skip TTS)", flush=True)
                    else:
                        # Invalid — consult the one-shot bypass before stripping.
                        bypass_active = (
                            self._stripped_tracker.should_bypass()
                            if self._stripped_tracker is not None
                            else False
                        )
                        if bypass_active:
                            citation_action = "bypass"
                            # Plan 41-04 — same head_yielded guard as the
                            # valid path: chunks already in-flight, no
                            # re-yield from buffer.
                            if not head_yielded:
                                for txt in buffered_chunks:
                                    yield txt
                            # Bypass means we did NOT strip — tracker records
                            # the actual outcome (False = "we let it through").
                            # Plan 55-03 — surface the raw reply as the
                            # last-unverified text: the user HEARD this unverified
                            # line, so the diagnostics strip must show it.
                            if self._stripped_tracker is not None:
                                self._stripped_tracker.record(
                                    False, unverified_text=full_text
                                )
                            self._recorder.log_event(
                                "citation_bypass",
                                response_id=response_id,
                                raw_text=full_text,
                                missing=citation_lint_missing_payload,
                                reason=lint_result.reason,
                                latency_s=round(elapsed, 2),
                            )
                            print(
                                f"[ai_text:unverified] {stripped!r}", flush=True
                            )
                            # History appended on bypass — the user heard the
                            # text, so the no-repeat memory must reflect it.
                            if stripped:
                                # WR-04 — stamp from event-fired set_seconds.
                                self._record_said(stripped[:140], set_s_at_event=ev_set_seconds)
                                self._push_transcript(stripped[:140])
                        else:
                            # Strip path — no chunks yielded. Pre-recorded
                            # ack substitution is retired (English placeholder
                            # clips fought the anti-slop thesis and the
                            # Turkish persona). On head_yielded turns the
                            # speculative head is already in flight, so we
                            # cancel with a silence pad to mask the
                            # mid-utterance cut. Otherwise this strip is
                            # exactly the persona's "say NOTHING" path.
                            citation_action = "strip"
                            if head_yielded:
                                _push_silence_pad_and_cancel("citation_failure")
                            # Plan 55-03 — surface the raw reply as the
                            # last-unverified text: this is the line the user did
                            # NOT hear, but the diagnostics strip should show what
                            # got silenced. Mirrors the raw_text= log field below.
                            if self._stripped_tracker is not None:
                                self._stripped_tracker.record(
                                    True, unverified_text=full_text
                                )
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
                    if not head_yielded:
                        for txt in buffered_chunks:
                            yield txt
                    if stripped:
                        print(f"[ai_text] {stripped!r}", flush=True)
                        self._recorder.log_event(
                            "ai_text", text=full_text, latency_s=round(elapsed, 2)
                        )
                        # WR-04 — stamp from event-fired set_seconds.
                        self._record_said(stripped[:140], set_s_at_event=ev_set_seconds)
                        self._push_transcript(stripped[:140])
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
            # decision. Runs for EVERY turn — suppressed, emit, bypass, strip,
            # legacy. Default-OFF so events.jsonl is byte-identical in normal runs
            # (the discrete citation_count/strip/bypass/ai_text events already cover
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

            # ---- Plan 24-02 — overlay-highlight publish ----
            # Fire once per [screen:<element>] citation IFF:
            #   1. ipc_bus is wired (sidecar publish path enabled).
            #   2. citation_action is a "user-heard-the-text" action — "emit"
            #      (normal flow) or "bypass" (unverified-but-spoken via the
            #      one-shot bypass guard). "strip" and "skip"-from-suppression
            #      do NOT publish: a ring without audio is ghost-firing.
            # Best-effort: every step wrapped in try/except so a malformed
            # element_id, schema validation error, or bus emit failure
            # cannot break the LLM response path (T-18-04-03-style mitigation).
            if self._ipc_bus is not None and citation_action in ("emit", "bypass"):
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
            # heard the reaction (citation_action in {emit, bypass}). When the
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
            if self._ipc_bus is not None and citation_action in ("emit", "bypass"):
                try:
                    strip = (
                        _build_citation_strip(
                            reaction_text=full_text,
                            registry=self._registry,
                        )
                        if self._registry is not None
                        else []
                    )
                    reaction_msg = SessionCohostReaction.make(
                        text=full_text,
                        event_id=ev_tag,
                        citation_strip=strip,
                    )
                    await self._ipc_bus.emit(reaction_msg.to_dict())
                except Exception as e:
                    print(f"\n[cohost-reaction publish err] {e}", file=sys.stderr)
                else:
                    # Phase 66 (COPILOT-02) — arm the recall-callback cooldown
                    # ONLY when the chip reached the audience. The ``else:``
                    # branch runs iff the try body completed without raising —
                    # i.e. ``_ipc_bus.emit(...)`` returned cleanly. A bus-emit
                    # failure jumps to the except above and this arm never runs;
                    # this is the strict semantic locked in CONTEXT.md Area 1
                    # Q3 + RESEARCH §Pitfall 2 + §Open Q5: cooldown reflects
                    # "a recall callback REACHED the audience", not "a recall
                    # callback was MERELY ATTEMPTED". One-way (arm only); no
                    # reset path — the wall-clock progression naturally drains
                    # the 120s window. Inner narrow try/except is defense in
                    # depth: a fault in ``chip.get`` (e.g. a future wire-format
                    # change) must not propagate and crash the turn — the
                    # outer ``else:`` placement already guarantees this code
                    # only runs on a clean bus emit, but the inner wrapper
                    # matches the project idiom (Pattern B in 66-PATTERNS.md).
                    try:
                        if any(
                            chip.get("event_id", "").startswith("recall:")
                            for chip in strip
                        ):
                            self._last_recall_callback_at = time.time()
                    except Exception as _e:
                        print(f"\n[recall cooldown arm err] {_e}", file=sys.stderr)
            elif self._ipc_bus is None and citation_action in ("emit", "bypass"):
                # Phase 66 (COPILOT-02) — bus-less arm path. When ``_ipc_bus`` is
                # None (test contexts that don't wire the UI broadcast surface,
                # or production agents that skip the IPC bus) the chip surface
                # never publishes, but the AUDIO surface still delivered the
                # reaction to the audience via the TTS chunks (citation_action
                # in {emit, bypass} = "user heard the text"). The strict
                # "REACHED the audience" semantic locked in CONTEXT.md Area 1
                # Q3 still applies here: the audience heard the recall callback
                # via audio even though no chip was broadcast.
                #
                # Phase 66 review CR-01 — mirror the bus path's STRUCTURAL filter.
                # Previously this arm used ``parse_citations(full_text)`` raw,
                # which arms on ANY ``("recall", <body>)`` atom found — INCLUDING
                # a FABRICATED ``[recall:<unregistered>]`` that the one-shot
                # bypass let through after the linter said invalid. The bus
                # path correctly uses ``_build_citation_strip`` which ONLY counts
                # atoms that resolve in the registry, so a fabricated recall id
                # under bypass NEVER reaches the audience as a registered chip
                # and never arms there. The two paths MUST yield the same
                # arm/no-arm decision per the "REACHED the audience" semantic.
                # Reuse the same lens here. The flag-OFF guard up-front (recall
                # disabled or no registry) closes a secondary leak: today the
                # outer condition only checks ``citation_action`` + bus-None, so
                # if a future flag-OFF code path ever emitted a ``[recall:...]``
                # atom this arm would fire with no recall service in play. The
                # explicit ``_recall_enabled`` / ``_registry is None`` guards
                # make the arm spec-correct under every state.
                # Best-effort try/except so a parse failure cannot crash the
                # turn (project Pattern B).
                if not self._recall_enabled or self._registry is None:
                    pass  # feature OFF or no registry — never arm without backing state
                else:
                    try:
                        strip = _build_citation_strip(
                            reaction_text=full_text,
                            registry=self._registry,
                        )
                        if any(
                            chip.get("event_id", "").startswith("recall:")
                            for chip in strip
                        ):
                            self._last_recall_callback_at = time.time()
                    except Exception as _e:
                        print(f"\n[recall cooldown arm err] {_e}", file=sys.stderr)

            # ---- Per-invocation dump (always written, even on suppression) ----
            try:
                (invoke_dir / "response.txt").write_text(full_text)
                (invoke_dir / "meta.json").write_text(
                    json.dumps(
                        {
                            "event": ev_tag,
                            "ts": invoke_ts,
                            "invoke_n": invoke_n,
                            "audible": self._state.audible,
                            "deck": self._state.audible_deck,
                            "track": self._state.audible_track,
                            "track_confidence": round(self._state.audible_track_confidence, 2),
                            "phase": self._state.phase,
                            "rms": round(self._state.rms, 4),
                            "bpm": round(self._state.bpm, 1),
                            "audio_bytes": len(audio_wav),
                            "audio_seconds": audio_seconds,
                            "diet": diet,
                            "llm_latency_s": round(elapsed, 2),
                            "llm_error": llm_err,
                            "response_chars": len(full_text),
                            "suppression": suppression,
                            "slop_matches": slop_matches,
                            # Plan 20-01 — citation linter chokepoint outcome.
                            # When wired==False, all four are None (skip path).
                            "citation_lint_valid": citation_lint_valid,
                            "citation_lint_reason": citation_lint_reason,
                            "citation_lint_missing": citation_lint_missing_payload,
                            "citation_action": citation_action,
                            # Plan 41-04 — streaming-pipe outcome. True iff
                            # the speculative head was emitted before stream
                            # completion; False on suppression/short-response.
                            "head_yielded": head_yielded,
                        },
                        indent=2,
                        ensure_ascii=False,
                    )
                )
            except Exception:
                pass

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
