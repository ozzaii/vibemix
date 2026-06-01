# SPDX-License-Identifier: Apache-2.0
"""Source-audited live-stack model pricing for `budget --stack live`.

Every Gemini row is keyed by an id resolved through ``model_router`` at import
time, so NO Gemini model literal is ever typed in this file (the CI grep gate in
``scripts/release/check_no_hardcoded_model.sh`` only allowlists
``_router_config.py``). Non-Gemini ids (DeepSeek, the premium TTS vendors,
dedicated STT) are not grep-gated, so they are keyed by their literal id.

Each :class:`PriceRow` carries ``source_url`` + ``source_date`` + ``verified`` so
an UNVERIFIED price (a vendor page that does not publish a confirmable rate) can
never masquerade as fact — it is flagged, never invented (the Cartesia row is the
worked example).

All money is USD. Token rates are USD per 1,000,000 tokens; TTS per-character
rates are USD per 1,000,000 characters; STT rates are USD per minute of audio.
The EUR conversion + the per-turn/per-session/fleet cost model live in
``vibemix.library.cost`` and consume this table — this module is data only.

Sources (rechecked 2026-05-31):
- Gemini:   https://ai.google.dev/gemini-api/docs/pricing
- DeepSeek: https://api-docs.deepseek.com/quick_start/pricing
- MOSS:     local on-device TTS; no per-call provider bill
- ElevenLabs: https://elevenlabs.io/pricing/api
- Hume:     https://www.hume.ai/pricing
- Cartesia: https://www.cartesia.ai/pricing   (UNVERIFIED — credits/minutes only)
- OpenAI:   https://developers.openai.com/api/docs/pricing
- Deepgram: https://deepgram.com/pricing
"""

from __future__ import annotations

from dataclasses import dataclass

from vibemix.llm.model_router import resolve_model

__all__ = [
    "MODEL_PRICING",
    "PriceRow",
    "UnknownModelError",
    "price_for_model",
    "price_for_path",
]

_GEMINI = "https://ai.google.dev/gemini-api/docs/pricing"
_DEEPSEEK = "https://api-docs.deepseek.com/quick_start/pricing"
_GEMINI_DATE = "2026-05-31"
_DEEPSEEK_DATE = "2026-05-31"


class UnknownModelError(KeyError):
    """Raised when a model id / router path has no row in :data:`MODEL_PRICING`."""


@dataclass(frozen=True, slots=True)
class PriceRow:
    """One model's verified cost facts. Unset legs stay ``None`` (not 0.0) so a
    missing rate is distinguishable from a genuine free leg."""

    model_id: str
    kind: str  # "llm" | "tts" | "stt"
    source_url: str
    source_date: str
    verified: bool
    notes: str = ""
    # LLM (USD per 1M tokens)
    input_per_mtok_usd: float | None = None
    output_per_mtok_usd: float | None = None
    cached_input_per_mtok_usd: float | None = None
    audio_input_per_mtok_usd: float | None = None
    # TTS — two billing shapes: per-character (vendors) OR per audio-token (Gemini/OpenAI)
    tts_per_1m_char_usd: float | None = None
    tts_audio_out_per_mtok_usd: float | None = None
    # STT (USD per minute of audio)
    stt_per_min_usd: float | None = None


def _gemini_row(alias: str, **kw: object) -> tuple[str, PriceRow]:
    """Build a (model_id, PriceRow) for a Gemini route — the literal id is
    produced by ``resolve_model`` at runtime, never typed (grep-gate clean)."""
    mid = resolve_model(alias)
    return mid, PriceRow(model_id=mid, source_url=_GEMINI, source_date=_GEMINI_DATE, **kw)  # type: ignore[arg-type]


MODEL_PRICING: dict[str, PriceRow] = dict(
    [
        # ─── LIVE-BRAIN candidates (Gemini, LLM) ──────────────────────────────
        # Current live_coach — the premium Flash tier. The wrong cost tier for a
        # live co-host (5x the text-output of the cheap tier); the bench exists to
        # prove a cheaper tier is good-enough so this becomes a one-line swap.
        _gemini_row(
            "live_coach", kind="llm", verified=True,
            input_per_mtok_usd=1.50, output_per_mtok_usd=9.00,
            cached_input_per_mtok_usd=0.15,
            notes="Premium Flash; no broken-out audio-input rate on the page.",
        ),
        # Cheapest standard Flash — the leading good-enough candidate.
        _gemini_row(
            "live_coach_cand_25flash", kind="llm", verified=True,
            input_per_mtok_usd=0.30, output_per_mtok_usd=2.50,
            cached_input_per_mtok_usd=0.03, audio_input_per_mtok_usd=1.00,
            notes="Cheapest text input of the Flash family; $1.00/1M audio in.",
        ),
        _gemini_row(
            "live_coach_cand_3flash", kind="llm", verified=True,
            input_per_mtok_usd=0.50, output_per_mtok_usd=3.00,
            cached_input_per_mtok_usd=0.05, audio_input_per_mtok_usd=1.00,
            notes="Current-gen standard Flash (cascade); $1.00/1M audio in.",
        ),
        # ─── TTS (production local MOSS + paid what-if vendors) ───────────────
        (
            "moss-local",
            PriceRow(
                model_id="moss-local", kind="tts", verified=True,
                source_url="local:vibemix.agent.local_tts", source_date="2026-06-01",
                tts_per_1m_char_usd=0.0,
                notes="Production voice path: on-device MOSS-TTS-Nano. No per-call "
                "provider bill; packaging/model distribution is tracked separately.",
            ),
        ),
        # Historical Gemini TTS rows remain as explicit what-if comparison rows.
        _gemini_row(
            "live_coach_tts", kind="tts", verified=True,
            input_per_mtok_usd=1.00, tts_audio_out_per_mtok_usd=20.00,
            notes="Historical paid Gemini Flash TTS comparison row; production "
            "speech is local MOSS.",
        ),
        _gemini_row(
            "live_coach_tts_fallback", kind="tts", verified=True,
            input_per_mtok_usd=0.50, tts_audio_out_per_mtok_usd=10.00,
            notes="Historical paid Gemini Flash TTS comparison row; production "
            "speech is local MOSS.",
        ),
        # ─── VIBER / set-prep brain (DeepSeek, LLM — not grep-gated) ───────────
        (
            "deepseek-v4-pro",
            PriceRow(
                model_id="deepseek-v4-pro", kind="llm", verified=True,
                source_url=_DEEPSEEK, source_date=_DEEPSEEK_DATE,
                input_per_mtok_usd=0.435, output_per_mtok_usd=0.87,
                cached_input_per_mtok_usd=0.003625,
                notes="V4 flagship. Official page says the 75% promo becomes an "
                "official 1/4-price adjustment after 2026-05-31 15:59 UTC; "
                "cache-hit input is ~120x cheaper.",
            ),
        ),
        (
            "deepseek-v4-flash",
            PriceRow(
                model_id="deepseek-v4-flash", kind="llm", verified=True,
                source_url=_DEEPSEEK, source_date=_DEEPSEEK_DATE,
                input_per_mtok_usd=0.14, output_per_mtok_usd=0.28,
                cached_input_per_mtok_usd=0.0028,
                notes="Smaller/faster V4 tier; legacy deepseek-chat/reasoner now alias this.",
            ),
        ),
        # ─── Premium TTS vendors (per-character; not grep-gated) ───────────────
        (
            "eleven_flash_v2_5",
            PriceRow(
                model_id="eleven_flash_v2_5", kind="tts", verified=True,
                source_url="https://elevenlabs.io/pricing/api", source_date="2026-05",
                tts_per_1m_char_usd=50.0,
                notes="$0.05/1k char = $50/1M char. Flash v2.5 = low-latency tier "
                "(0.5 credit/char, half of Multilingual v2).",
            ),
        ),
        (
            "octave-2",
            PriceRow(
                model_id="octave-2", kind="tts", verified=True,
                source_url="https://www.hume.ai/pricing", source_date="2026-05-31",
                tts_per_1m_char_usd=50.0,
                notes="Hume Octave, per character. Business-tier usage-based overage "
                "$0.05/1k = $50/1M; lower tiers cost more ($0.10-$0.15/1k, "
                "Pro currently $0.12/1k).",
            ),
        ),
        (
            "sonic-3",
            PriceRow(
                model_id="sonic-3", kind="tts", verified=False,
                source_url="https://www.cartesia.ai/pricing", source_date="2026-05-31",
                tts_per_1m_char_usd=29.9,
                notes="LEGACY_DERIVED from the previous self-serve credit table, not a "
                "quoted per-character SKU. Current public page lists Sonic-3.5 minutes "
                "and plan prices but no exact per-character conversion; keep this row "
                "unverified until account billing confirms the current effective rate. "
                "Live primary voice (Gemini TTS is mute live); router id sonic-3.",
            ),
        ),
        (
            "tts-1",
            PriceRow(
                model_id="tts-1", kind="tts", verified=True,
                source_url="https://developers.openai.com/api/docs/models/tts-1",
                source_date="2026-05", tts_per_1m_char_usd=15.0,
                notes="OpenAI standard TTS, per character. tts-1-hd is $30/1M char.",
            ),
        ),
        (
            "gpt-4o-mini-tts",
            PriceRow(
                model_id="gpt-4o-mini-tts", kind="tts", verified=True,
                source_url="https://developers.openai.com/api/docs/models/gpt-4o-mini-tts",
                source_date="2026-05", input_per_mtok_usd=0.60,
                tts_audio_out_per_mtok_usd=12.00,
                notes="Token-billed: $0.60/1M text in + $12/1M audio out. No official "
                "per-char/per-min rate.",
            ),
        ),
        # ─── Dedicated STT (the mic→dedicated-STT fork; not grep-gated) ────────
        (
            "nova-3-streaming",
            PriceRow(
                model_id="nova-3-streaming", kind="stt", verified=True,
                source_url="https://deepgram.com/pricing", source_date="2026-05",
                stt_per_min_usd=0.0048,
                notes="Deepgram Nova-3 streaming PAYG, monolingual. Multilingual $0.0058/min.",
            ),
        ),
        (
            "gpt-4o-mini-transcribe",
            PriceRow(
                model_id="gpt-4o-mini-transcribe", kind="stt", verified=True,
                source_url="https://developers.openai.com/api/docs/pricing",
                source_date="2026-05", stt_per_min_usd=0.003,
                notes="OpenAI's own published 'estimated cost $0.003/min'. Cheapest dedicated STT.",
            ),
        ),
        (
            "whisper-1",
            PriceRow(
                model_id="whisper-1", kind="stt", verified=True,
                source_url="https://developers.openai.com/api/docs/models/whisper-1",
                source_date="2026-05", stt_per_min_usd=0.006,
                notes="OpenAI Whisper transcription, $0.006/min.",
            ),
        ),
    ]
)


def price_for_model(model_id: str) -> PriceRow:
    """Return the :class:`PriceRow` for ``model_id`` or raise :class:`UnknownModelError`."""
    try:
        return MODEL_PRICING[model_id]
    except KeyError:
        known = ", ".join(sorted(MODEL_PRICING))
        raise UnknownModelError(
            f"no pricing row for model {model_id!r}; priced models: {known}"
        ) from None


def price_for_path(path: str) -> PriceRow:
    """Return the :class:`PriceRow` for a ``model_router`` path (Gemini routes)."""
    return price_for_model(resolve_model(path))
