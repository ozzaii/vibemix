# SPDX-License-Identifier: Apache-2.0
"""vibemix.profile — long-term DJ profile (~2KB JSON, content-allowlisted).

Phase 32 ships a tiny, schema-locked JSON profile that summarizes the user's
DJ tendencies across sessions and gets cache-side injected into Gemini's
context cache (NEVER per-turn — see Pitfall P60). The profile is:

- **Size-capped** at 2048 UTF-8 bytes (Pitfall P51 size).
- **Allowlisted** to five specific fields — NO track titles, NO library
  contents, NO free-form strings (Pitfall P51 privacy).
- **Citation-gated** — each tendency field needs ≥2 distinct EvidenceRegistry
  observations to (re)generate; otherwise the prior value is retained
  (PROFILE-06 drift prevention).
- **Local-only** — stored at ``~/.config/vibemix/profile.json`` with 0o600
  perms. Never uploaded. Default-OFF consent (PROFILE-05) gates creation.

Public API:

- ``build_profile(prior, events, evidence_snapshot, *, consent)`` — regenerate.
- ``serialize_profile(profile)`` → bytes — enforces 2048-byte cap + schema.
- ``validate_profile(profile)`` — raises ``ProfileError`` on schema violation.
- ``render_profile_for_cache(profile)`` → str — compact flat-key form for the
  GeminiContextCache body prefix (P60 cache injection).
- ``load_profile() / save_profile(d) / delete_profile()`` — disk storage.
- ``load_consent() / save_consent(bool)`` — state.json consent toggle.

The grep gate that protects P60 is enforced by
``tests/profile/test_profile_not_in_per_turn_prompt.py``: the substring
``profile`` MUST NOT appear in the per-turn agent path
(``vibemix.agent.dj_cohost.DJCoHostAgent.llm_node``).
"""

from vibemix.profile.builder import (
    MAX_PROFILE_BYTES,
    ProfileError,
    build_profile,
    serialize_profile,
)
from vibemix.profile.cache_render import render_profile_for_cache
from vibemix.profile.schema import PROFILE_SCHEMA, validate_profile
from vibemix.profile.storage import (
    consent_path,
    delete_profile,
    load_consent,
    load_profile,
    profile_path,
    save_consent,
    save_profile,
)

__all__ = [
    "MAX_PROFILE_BYTES",
    "PROFILE_SCHEMA",
    "ProfileError",
    "build_profile",
    "consent_path",
    "delete_profile",
    "load_consent",
    "load_profile",
    "profile_path",
    "render_profile_for_cache",
    "save_consent",
    "save_profile",
    "serialize_profile",
    "validate_profile",
]
