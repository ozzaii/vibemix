# SPDX-License-Identifier: Apache-2.0
"""Single source of truth for `(model_id, ServiceTier | None)` per router path.

This is the ONLY file in `src/vibemix/` allowed to carry Gemini model
literals. The CI grep gate (`scripts/release/check_no_hardcoded_model.sh`)
allowlists this path; every other call site in `src/vibemix/` MUST go
through `vibemix.llm.model_router.resolve(path)`.

Future SKU bumps land here as a one-line edit. The `_ROUTES` table is the
foundation Plans 41-02..06 consume — keep it stable.

Tier dispatch follows CONTEXT.md (LAT-07). The ``embedding`` route is retained
only for the legacy Gemini cache/migration helper in ``vibemix.library.embed``;
the product library embedder is local CLAP ONNX via ``embed_factory``.

- live_coach + live_coach_tts (+ fallback) → STANDARD (latency-critical)
- debrief / library auto-tag / embedding  → FLEX     (cost lane)
- live_coach_openrouter / *_tts_openrouter → None     (non-Gemini API surface)
"""

from __future__ import annotations

from typing import Literal

ServiceTierName = Literal["STANDARD", "FLEX"]

# (model_id, tier-or-None). The OpenRouter entry uses None as a sentinel —
# the OpenRouter API is consumed by the LiveKit OpenAI plugin, not by the
# Gemini SDK, so ServiceTier has no semantic meaning there.
_ROUTES: dict[str, tuple[str, ServiceTierName | None]] = {
    # Phase 80 / GROUND-02 — "live_coach" is the Phase-81 BENCH bench-swap
    # alias for the reaction model. Swap the winning model here (one-line edit,
    # no code change); it resolves at agent/config.py:25 via
    # resolve("live_coach") and flows to dj_cohost.py as model=LLM_MODEL.
    "live_coach": ("gemini-3.5-flash", "STANDARD"),
    "live_coach_openrouter": ("google/gemini-3.5-flash", None),
    "live_coach_tts": ("gemini-3.1-flash-tts-preview", "STANDARD"),
    "live_coach_tts_fallback": (
        "gemini-2.5-flash-preview-tts",
        "STANDARD",
    ),
    "live_coach_tts_openrouter": (
        "google/gemini-3.1-flash-tts-preview",
        None,
    ),
    # --- Cost + capability study (2026-05-30) — candidate LIVE-BRAIN aliases.
    # The verified pricing table (``vibemix.library.pricing``) resolves each via
    # ``resolve_model`` so NO Gemini literal escapes this allowlisted file, and
    # the live-brain Gemini-TIER bench (bench ``STUDY_C``) sweeps these aliases.
    # The live co-host brain STAYS Gemini (only Gemini "sees the listener" on the
    # LiveKit pipeline); these are the cheaper tiers the bench proves
    # good-enough-or-not against the current premium ``live_coach``
    # (gemini-3.5-flash). NB: the Viber/set-prep brain (DeepSeek) is deliberately
    # NOT a router entry — it runs through the ``codex_curate`` subprocess lane,
    # and its price is keyed by model-id directly in ``pricing.py`` (deepseek-*
    # is not grep-gated). Keeping this router Gemini-only preserves the
    # ``test_no_non_gemini_models`` invariant.
    "live_coach_cand_25flash": ("gemini-2.5-flash", "STANDARD"),
    "live_coach_cand_3flash": ("gemini-3-flash-preview", "STANDARD"),
    # Phase 92 Plan 92-01 (LESSON-06 — Open Q1 resolution). The Learn module's
    # AI tutor lens. Decoupled from ``live_coach`` so future model swaps don't
    # drag both surfaces — the live co-host (party/coach) and the lesson tutor
    # are independent product surfaces and the planner ratified them keeping
    # separate router entries (see 92-RESEARCH.md §Open Questions Q1). Same
    # model id + tier as ``live_coach`` today; the decoupling is structural,
    # not operational.
    "learn_tutor": ("gemini-3.5-flash", "STANDARD"),
    "debrief": ("gemini-3.5-flash", "FLEX"),
    "library_auto_tag": ("gemini-3.5-flash", "FLEX"),
    # Legacy-only: migration/cache audit path for old Gemini embedding rows.
    # Normal library search/ingest/chat/build-set uses local CLAP ONNX/512.
    "embedding": ("gemini-embedding-2", "FLEX"),
}

# Plan 41-05 LAT-06 — GA-rename probe candidates for the embedding model.
# These literals live here (the only allowlisted file) so the GA-rename
# auto-bump can iterate them at runtime without tripping the grep gate.
# Order MUST be ``GA-renamed first, legacy second`` so we land on the
# canonical id as soon as the rename ships.
EMBEDDING_GA_CANDIDATES: tuple[str, ...] = (
    "gemini-embedding-002",
    "gemini-embedding-2",
)
