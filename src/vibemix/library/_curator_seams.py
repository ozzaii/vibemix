# SPDX-License-Identifier: Apache-2.0
"""Shared curator seams — the ONE implementation of the lens + taste reads.

IN-01 / WR-01: both Viber backends (``agent.py`` = gemini, ``codex_curate.py``
= codex) need the SAME ``_shared_lens()`` (persona) and ``_taste_hint()``
(profile bias) reads. Before this module the two implementations were
byte-identical copies — so a fix to one (notably the WR-01 consent gate) could
silently skip the other and orphan a backend (the CURATE acid test). Sourcing
both seams here makes the persona/consent contract single-sourced: a change
lands in both backends from one place and cannot diverge.

Both seams lazy-import their cross-package readers INSIDE the function body
(Pattern 1) so importing this module — or either backend — does NOT pull
``vibemix.runtime`` / ``vibemix.profile`` into ``sys.modules`` at import time.
That keeps the memory-storage spine's no-live-path import boundary intact
(tests/memory/test_no_live_path_import.py). Each read is guarded with a bare
``except Exception`` so a malformed config / profile / consent file degrades to
the cold-path default and never breaks curation.
"""

from __future__ import annotations


def shared_lens() -> str:
    """Read the ONE shared lens (LENS-02), defaulting to ``"tutor"`` when unset.

    Per-surface default-when-unset: the curator cold path is byte-identical to
    the ``build_curator_instruction("tutor")`` it shipped with. When the user
    sets a lens once (via the settings bus ``_apply_lens``), that SAME value
    drives both curator backends AND the live co-host. Lazy-imported so the seam
    keeps the import-time no-live-path boundary clean (matrix-seam pattern).

    WR-03: the read is guarded (mirrors the co-host ``_resolve_prompt_cell``
    guard). ``load_config`` already swallows OSError/JSONDecodeError, but any
    OTHER read failure must NOT break curation — fall back to the ``"tutor"``
    cold-path default on any exception so the curator seam degrades gracefully.
    """
    try:
        from vibemix.runtime.config_store import load_config
        from vibemix.runtime.settings import read_shared_lens

        return read_shared_lens(load_config(), default="tutor") or "tutor"
    except Exception:  # pragma: no cover — guard: any read fail = cold default
        return "tutor"


def taste_hint() -> str:
    """SEAM #2 (CURATE-02): compact, privacy-safe taste hint biasing curation
    'for this DJ', shared verbatim by BOTH curator backends.

    WR-01 — the profile read is GATED ON CONSENT, mirroring the canonical
    project pattern in ``runtime/session_loop.py`` (``load_profile() if
    load_consent() else None``). ``load_profile()`` only checks the file exists +
    validates the schema; it does NOT read the consent toggle. So a
    ``profile.json`` that outlives a consent toggle-OFF would otherwise still
    feed the curator — silently bypassing the consent contract and breaking the
    cold-path byte-identity claim. Gating here makes the docstring's "``""`` when
    consent-OFF" promise true: consent-OFF (or no profile) → ``""`` → the cold
    path is byte-identical regardless of a leftover profile file.

    Only the 5 allowlisted coarse fields ever cross (preferred_genre,
    tempo_preference_bin, mix_style_tags, cadences) — NO track titles / paths /
    free-form (T-82-01; the renderer enforces it). Lazy-import keeps the
    no-live-path boundary clean; guarded so any read failure = cold default.

    Recomputed per call (NOT cached behind the lens key) so a profile/consent
    change is reflected without a lens-keyed cache miss; the render is cheap.
    """
    try:
        from vibemix.profile import (
            load_consent,
            load_profile,
            render_profile_for_cache,
        )

        # WR-01 consent gate (mirror session_loop.py): no consent → no profile
        # crosses into the prompt, even when a stale profile.json exists on disk.
        if not load_consent():
            return ""
        return render_profile_for_cache(load_profile())  # "" when profile None
    except Exception:  # pragma: no cover — guard: any read fail = cold default
        return ""


__all__ = ["shared_lens", "taste_hint"]
