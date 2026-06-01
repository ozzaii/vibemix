# SPDX-License-Identifier: Apache-2.0
"""Live-stack cost model — composes :mod:`vibemix.library.pricing` rows into the
per-turn / per-session / per-DJ-month / fleet bill for `budget --stack live`.

The cache-blend (``_effective_input_rate``) is the load-bearing insight: with a
high implicit cache-hit rate the input leg collapses. Production speech is local
MOSS, so the default TTS leg is explicit zero-cost rather than a hidden paid
provider. Paid voice rows remain only as what-if sensitivity rows. All money is
USD here; the EUR conversion happens at the CLI boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from vibemix.library.budget import USD_TO_EUR as _DEFAULT_USD_TO_EUR
from vibemix.library.pricing import PriceRow, price_for_model, price_for_path

__all__ = [
    "LegCost",
    "LiveCostBreakdown",
    "LiveStackSpec",
    "SensitivityRow",
    "TurnProfile",
    "UsageProfile",
    "brain_reaction_usd",
    "compute_live_cost",
    "listen_reaction_usd",
    "live_budget_report",
    "sensitivity_rows",
    "tts_reaction_usd",
]

# Gemini/OpenAI audio tokens stream at a fixed 25 tokens/second (ai.google.dev
# pricing: "audio = 25 tok/sec"). Speech runs ~14 chars/sec at a natural pace —
# used only to convert a spoken-seconds estimate to per-character vendor billing.
AUDIO_TOKENS_PER_SECOND = 25.0
CHARS_PER_SECOND = 14.0

# LiveKit Cloud "agent session" rate — the AI-voice-agent cost driver
# (livekit.io/pricing, 2026: $0.01/participant-minute). Self-hosting / the local
# "direct mode" vibemix actually ships eliminates per-minute fees entirely, so
# the default LiveStackSpec.livekit_per_min_usd is 0.0 and this constant is only
# the reference rate for the LiveKit-Cloud what-if (`--livekit-per-min 0.01`).
LIVEKIT_CLOUD_AGENT_PER_MIN_USD = 0.01


def _effective_input_rate(
    input_rate: float | None,
    cached_rate: float | None,
    cache_hit_rate: float,
) -> float:
    """Blend the cached and fresh input rates at ``cache_hit_rate`` (USD/1M tok).

    A model with no cache rate degenerates to "all fresh" (cached == input).
    """
    fresh = input_rate or 0.0
    cached = cached_rate if cached_rate is not None else fresh
    hit = min(max(cache_hit_rate, 0.0), 1.0)
    return hit * cached + (1.0 - hit) * fresh


def brain_reaction_usd(
    row: PriceRow,
    *,
    input_tokens: int,
    output_tokens: int,
    cache_hit_rate: float,
) -> float:
    """USD cost of one live-brain reaction: cache-blended text input + output.

    Audio input (the listening leg) is billed separately — see the STT leg.
    """
    eff_in = _effective_input_rate(
        row.input_per_mtok_usd, row.cached_input_per_mtok_usd, cache_hit_rate
    )
    input_usd = input_tokens * eff_in / 1e6
    output_usd = output_tokens * (row.output_per_mtok_usd or 0.0) / 1e6
    return input_usd + output_usd


def tts_reaction_usd(
    row: PriceRow,
    *,
    speech_seconds: float,
    text_tokens: int = 0,
    chars_per_second: float = CHARS_PER_SECOND,
    audio_tokens_per_second: float = AUDIO_TOKENS_PER_SECOND,
) -> float:
    """USD cost of speaking one reaction, across both TTS billing shapes.

    - local MOSS: verified zero per-provider cost.
    - per-character vendors (ElevenLabs/Hume/OpenAI tts-1): spoken chars × rate.
    - audio-token models (Gemini/gpt-4o-mini-tts): spoken audio tokens × rate,
      plus the small text-input charge for the words spoken.
    """
    if row.tts_per_1m_char_usd is not None:
        chars = speech_seconds * chars_per_second
        return chars * row.tts_per_1m_char_usd / 1e6
    if row.tts_audio_out_per_mtok_usd is not None:
        audio_tok = speech_seconds * audio_tokens_per_second
        audio_usd = audio_tok * row.tts_audio_out_per_mtok_usd / 1e6
        text_usd = text_tokens * (row.input_per_mtok_usd or 0.0) / 1e6
        return audio_usd + text_usd
    raise ValueError(f"TTS row {row.model_id!r} carries no TTS rate")


def listen_reaction_usd(
    *,
    audio_in_seconds: float,
    brain_row: PriceRow,
    stt_row: PriceRow | None = None,
    audio_tokens_per_second: float = AUDIO_TOKENS_PER_SECOND,
) -> float:
    """USD cost of the live-listening leg for one reaction.

    The default fork (``stt_row is None``) is mic→Gemini audio Part: the audio is
    billed as the brain's audio-input tokens (no separate vendor). A dedicated
    STT bills per audio-minute instead.
    """
    if stt_row is None:
        # No SEPARATE audio-in rate (e.g. gemini-3.5-flash) ⇒ audio is still
        # billed as input tokens at the model's standard input rate — never free.
        rate = brain_row.audio_input_per_mtok_usd
        if rate is None:
            rate = brain_row.input_per_mtok_usd or 0.0
        return audio_in_seconds * audio_tokens_per_second * rate / 1e6
    return (audio_in_seconds / 60.0) * (stt_row.stt_per_min_usd or 0.0)


# ─── The composed per-turn → per-session → per-DJ-month → fleet model ──────────


@dataclass(frozen=True, slots=True)
class LiveStackSpec:
    """Which model fills each leg. Defaults = the CURRENT production routes (the
    live brain plus local MOSS voice) so `budget --stack live` shows today's
    bill; flags swap in paid voice vendors or cheaper brain candidates to reveal
    the lever."""

    live_brain_path: str = "live_coach"
    tts_path: str = "moss-local"  # a local/provider model id, or a router what-if
    stt: str = "gemini_part"  # "gemini_part" (mic→Gemini) OR a dedicated STT model id
    viber_model: str = "deepseek-v4-pro"
    # LiveKit runs LOCALLY in direct mode (no Cloud room) ⇒ 0 marginal cost. Set
    # >0 (USD/participant-minute) only for the LiveKit Cloud what-if.
    livekit_per_min_usd: float = 0.0


@dataclass(frozen=True, slots=True)
class TurnProfile:
    """The measured shape of one reaction (anchored on the bench sample:
    ~1900 in / ~40 out tokens, ~12s spoken, ~18s audio window)."""

    input_tokens: int = 1900
    output_tokens: int = 40
    speech_seconds: float = 12.0
    audio_in_seconds: float = 18.0
    cache_hit_rate: float = 0.90


@dataclass(frozen=True, slots=True)
class UsageProfile:
    """How often a DJ reacts + plays + preps. ``sessions_per_month`` defaults to
    20 (a daily-active user, not the legacy hobbyist 4). Viber is a prep-time
    monthly burst, separate from the live per-reaction path."""

    reactions_per_set: int = 80
    sessions_per_month: int = 20
    set_minutes: float = 75.0
    viber_calls_per_month: int = 20
    viber_input_tokens: int = 4000
    viber_output_tokens: int = 1200
    viber_cache_hit_rate: float = 0.90


@dataclass(frozen=True, slots=True)
class LegCost:
    name: str
    per_reaction_eur: float
    per_session_eur: float
    per_dj_month_eur: float
    fleet_month_eur: float


@dataclass(frozen=True, slots=True)
class LiveCostBreakdown:
    legs: tuple[LegCost, ...]
    total_per_session_eur: float
    total_per_dj_month_eur: float
    fleet_month_eur: float
    dominant_leg: str
    dau: int


def _price_any(key: str) -> PriceRow:
    """Resolve a leg key that may be a Gemini router path OR a vendor model id."""
    from vibemix.llm.model_router import RouterPathError

    try:
        return price_for_path(key)
    except (RouterPathError, KeyError):
        return price_for_model(key)


def compute_live_cost(
    spec: LiveStackSpec,
    turn: TurnProfile,
    usage: UsageProfile,
    *,
    dau: int,
    usd_to_eur: float = _DEFAULT_USD_TO_EUR,
) -> LiveCostBreakdown:
    """Compose the four-leg (brain / listen / tts / viber) live-stack bill."""
    brain_row = price_for_path(spec.live_brain_path)
    tts_row = _price_any(spec.tts_path)
    stt_row = None if spec.stt == "gemini_part" else price_for_model(spec.stt)
    viber_row = price_for_model(spec.viber_model)

    brain_pr = brain_reaction_usd(
        brain_row,
        input_tokens=turn.input_tokens,
        output_tokens=turn.output_tokens,
        cache_hit_rate=turn.cache_hit_rate,
    )
    listen_pr = listen_reaction_usd(
        audio_in_seconds=turn.audio_in_seconds, brain_row=brain_row, stt_row=stt_row
    )
    tts_pr = tts_reaction_usd(
        tts_row, speech_seconds=turn.speech_seconds, text_tokens=turn.output_tokens
    )

    # Viber: prep-time monthly burst (a cached DeepSeek LLM call), not per-reaction.
    viber_per_call_usd = brain_reaction_usd(
        viber_row,
        input_tokens=usage.viber_input_tokens,
        output_tokens=usage.viber_output_tokens,
        cache_hit_rate=usage.viber_cache_hit_rate,
    )
    viber_month_eur = viber_per_call_usd * usage.viber_calls_per_month * usd_to_eur

    def _live_leg(name: str, per_reaction_usd: float) -> LegCost:
        pr = per_reaction_usd * usd_to_eur
        ps = pr * usage.reactions_per_set
        pm = ps * usage.sessions_per_month
        return LegCost(name, pr, ps, pm, pm * dau)

    brain_leg = _live_leg("brain", brain_pr)
    listen_leg = _live_leg("listen", listen_pr)
    tts_leg = _live_leg("tts", tts_pr)
    viber_leg = LegCost("viber", 0.0, 0.0, viber_month_eur, viber_month_eur * dau)

    # LiveKit: per-MINUTE of set (not per-reaction). 0 in direct/self-hosted mode.
    lk_per_session = usage.set_minutes * spec.livekit_per_min_usd * usd_to_eur
    lk_per_month = lk_per_session * usage.sessions_per_month
    livekit_leg = LegCost("livekit", 0.0, lk_per_session, lk_per_month, lk_per_month * dau)

    legs = (brain_leg, listen_leg, tts_leg, viber_leg, livekit_leg)
    total_session = (
        brain_leg.per_session_eur
        + listen_leg.per_session_eur
        + tts_leg.per_session_eur
        + livekit_leg.per_session_eur
    )
    total_month = sum(leg.per_dj_month_eur for leg in legs)
    dominant = max(legs, key=lambda leg: leg.per_dj_month_eur).name
    return LiveCostBreakdown(
        legs=legs,
        total_per_session_eur=total_session,
        total_per_dj_month_eur=total_month,
        fleet_month_eur=total_month * dau,
        dominant_leg=dominant,
        dau=dau,
    )


@dataclass(frozen=True, slots=True)
class SensitivityRow:
    """One what-if scenario's fleet bill, with the source's verified flag so an
    UNVERIFIED vendor (Cartesia) is never presented as a confirmed number."""

    axis: str
    label: str
    fleet_month_eur: float
    verified: bool
    note: str = ""


# The candidate set per axis (deliverable #4). Labels avoid the grep-gated model
# literals — descriptive names only; the model ids are resolved via the table.
_TTS_OPTIONS = (
    ("moss-local", "Local MOSS (production)"),
    ("live_coach_tts_fallback", "Gemini value TTS"),
    ("live_coach_tts", "Gemini premium TTS"),
    ("eleven_flash_v2_5", "ElevenLabs Flash v2.5"),
    ("octave-2", "Hume Octave 2"),
    ("sonic-3", "Cartesia Sonic"),
    ("tts-1", "OpenAI tts-1"),
)
_STT_OPTIONS = (
    ("gemini_part", "mic→Gemini Part"),
    ("nova-3-streaming", "Deepgram Nova-3"),
    ("gpt-4o-mini-transcribe", "OpenAI mini-transcribe"),
)
_BRAIN_OPTIONS = (
    ("live_coach", "Premium Flash (current)"),
    ("live_coach_cand_3flash", "3-series Flash (cascade)"),
    ("live_coach_cand_25flash", "Cheapest Flash"),
)
_CACHE_HITS = (0.0, 0.70, 0.90, 0.95)
_VIBER_MULTIPLIERS = ((0.5, "Viber burst x0.5"), (1.0, "Viber burst x1"), (2.0, "Viber burst x2"))


def sensitivity_rows(
    spec: LiveStackSpec,
    turn: TurnProfile,
    usage: UsageProfile,
    *,
    dau: int,
    usd_to_eur: float = _DEFAULT_USD_TO_EUR,
) -> list[SensitivityRow]:
    """The honest what-if table: how the fleet bill moves on each cost axis."""

    def _fleet(
        s: LiveStackSpec = spec, t: TurnProfile = turn, u: UsageProfile = usage
    ) -> float:
        return compute_live_cost(s, t, u, dau=dau, usd_to_eur=usd_to_eur).fleet_month_eur

    rows: list[SensitivityRow] = []
    for key, label in _TTS_OPTIONS:
        row = _price_any(key)
        rows.append(
            SensitivityRow("tts", label, _fleet(s=replace(spec, tts_path=key)), row.verified)
        )
    for key, label in _STT_OPTIONS:
        verified = True if key == "gemini_part" else _price_any(key).verified
        rows.append(
            SensitivityRow("stt", label, _fleet(s=replace(spec, stt=key)), verified)
        )
    for key, label in _BRAIN_OPTIONS:
        rows.append(
            SensitivityRow(
                "brain", label, _fleet(s=replace(spec, live_brain_path=key)), True
            )
        )
    for hit in _CACHE_HITS:
        rows.append(
            SensitivityRow(
                "cache_hit", f"{int(hit * 100)}%", _fleet(t=replace(turn, cache_hit_rate=hit)), True
            )
        )
    for mult, label in _VIBER_MULTIPLIERS:
        calls = int(usage.viber_calls_per_month * mult)
        rows.append(
            SensitivityRow(
                "viber", label, _fleet(u=replace(usage, viber_calls_per_month=calls)), True
            )
        )
    return rows


def live_budget_report(
    spec: LiveStackSpec,
    turn: TurnProfile,
    usage: UsageProfile,
    *,
    dau: int,
    usd_to_eur: float = _DEFAULT_USD_TO_EUR,
) -> dict:
    """A JSON-serializable report: breakdown + sensitivity + echoed assumptions.

    The assumptions block is deliberate — the fleet number is only as honest as
    the per-turn sample it rests on, so the knobs travel WITH the answer.
    """
    bd = compute_live_cost(spec, turn, usage, dau=dau, usd_to_eur=usd_to_eur)
    sens = sensitivity_rows(spec, turn, usage, dau=dau, usd_to_eur=usd_to_eur)
    return {
        "mode": "live_stack",
        "dau": dau,
        "stack": {
            "brain": spec.live_brain_path,
            "tts": spec.tts_path,
            "stt": spec.stt,
            "viber": spec.viber_model,
        },
        "assumptions": {
            "input_tokens": turn.input_tokens,
            "output_tokens": turn.output_tokens,
            "speech_seconds": turn.speech_seconds,
            "audio_in_seconds": turn.audio_in_seconds,
            "cache_hit_rate": turn.cache_hit_rate,
            "reactions_per_set": usage.reactions_per_set,
            "sessions_per_month": usage.sessions_per_month,
            "set_minutes": usage.set_minutes,
            "viber_calls_per_month": usage.viber_calls_per_month,
            "livekit_per_min_usd": spec.livekit_per_min_usd,
            "usd_to_eur": usd_to_eur,
        },
        "legs": [
            {
                "name": leg.name,
                "per_reaction_eur": leg.per_reaction_eur,
                "per_session_eur": leg.per_session_eur,
                "per_dj_month_eur": leg.per_dj_month_eur,
                "fleet_month_eur": leg.fleet_month_eur,
            }
            for leg in bd.legs
        ],
        "totals": {
            "per_session_eur": bd.total_per_session_eur,
            "per_dj_month_eur": bd.total_per_dj_month_eur,
            "fleet_month_eur": bd.fleet_month_eur,
        },
        "dominant_leg": bd.dominant_leg,
        "sensitivity": [
            {
                "axis": r.axis,
                "label": r.label,
                "fleet_month_eur": r.fleet_month_eur,
                "verified": r.verified,
                "note": r.note,
            }
            for r in sens
        ],
    }
