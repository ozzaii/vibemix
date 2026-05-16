# Phase 32: Long-Term DJ Profile (~2KB JSON) - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully)

<domain>
## Phase Boundary

vibemix remembers what kind of DJ the user is across sessions via a tiny content-allowlisted JSON profile that gets cache-side injected into every new live prompt — personalizing coaching without leaking track titles or letting the profile drift generic.

**Mapped REQ-IDs (7):** PROFILE-01 (builder), PROFILE-02 (allowlist + 2KB cap), PROFILE-03 (cache, NOT per-turn prefix), PROFILE-04 (kwargs-only injection), PROFILE-05 (consent screen, default-OFF), PROFILE-06 (≥2 citations rule), PROFILE-07 (Settings → Profile panel).

**In scope:**
- `src/vibemix/profile/builder.py` — post-session regenerator from EvidenceRegistry snapshot + session events; UTF-8 hard cap 2048 bytes (Pitfall P51 size).
- jsonschema with `additionalProperties: false`; allowed fields: `preferred_genre`, `avg_session_duration`, `mix_style_tags` (≤8 items), `tempo_preference_bin`, `event_type_response_preferences`. NO `recent_tracks`, NO `library_titles`, NO free-form strings.
- GeminiContextCache integration — cache-side injection, NOT per-turn prompt prefix (Pitfall P60 — 1024-token floor + 4min refresh preserved).
- `DJCoHostAgent.__init__` 5th kwarg `profile=` (kwargs-only — Pitfall P53). `None` default = v2.0 4-kwarg path byte-identical.
- First-launch wizard: "Build a profile?" toggle, default-OFF, field-set disclosure inline.
- Settings → Profile panel: view + delete + regenerate-now.
- Tendency regeneration rule: each tendency field requires ≥2 EvidenceRegistry citations to regen (drift prevention).

**Out of scope:**
- Cross-user profile sharing.
- Cloud sync of profile (local-only).
- Profile-driven track recommendation (Phase 28 already declared LIBRARY-14 user-ask-only — profile does NOT autosurface tracks).
- Free-form text fields in the profile.
- Profile JSON outside the allowlist (size cap + schema reject).
- Multi-profile support (single user, single profile).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion (locked per gsd-autonomous fully)

Grounded in:
- ROADMAP Phase 32 verbatim success criteria
- REQUIREMENTS.md PROFILE-01..07
- Pitfalls P51 (privacy + allowlist + size cap), P53 (kwargs-only constructor), P60 (cache 1024-token floor)
- v2.0 Phase 25 DEBRIEF data + Phase 10 prompt matrix (shipped)
- Phase 28 library citations (shipped — track citations now flow into reactions)
- STATE.md decision: DJ profile NEVER per-turn prompt prefix; lives in GeminiContextCache.
- Memory `feedback_no_scope_creep_clean_utility` — minimum useful surface.

### Profile builder (PROFILE-01)
- File: `src/vibemix/profile/builder.py`.
- API: `build_profile(prior_profile: dict | None, session_events: list[Event], evidence_snapshot: EvidenceRegistry) -> dict | None`.
- Aggregates across last N sessions (default N=10). Reads `~/.cache/vibemix/profile/history.json` for prior sessions' aggregated counts.
- Generates new profile only if PROFILE-06 ≥2 citation rule satisfied for each tendency field.
- Returns `None` if user opted out (PROFILE-05 consent OFF) or insufficient data.

### Allowlist + schema (PROFILE-02 / P51)
- `src/vibemix/profile/schema.py` — pydantic model:
  - `preferred_genre: Literal["hard_tek", "techno", "house", "unknown"]`
  - `avg_session_duration: float` (minutes, rounded)
  - `mix_style_tags: list[Literal[...]]` (≤8 items, allowed tags: "long_blends", "quick_cuts", "loops", "filter_sweeps", "loud_drops", "subtle_transitions", "vocal_pickups", "bass_riding", "tempo_jumps", "phrase_locked", "off-grid")
  - `tempo_preference_bin: Literal["110-120", "120-128", "128-138", "138-150", "150+"]`
  - `event_type_response_preferences: dict[Literal["TRACK_CHANGE","PHASE","KAAN_SPOKE","MIX_MOVE","DISTORTION_CLIMB","ACID_LINE_ENTRY","HEARTBEAT","LAYER_ARRIVAL"], Literal["always","sometimes","rarely","never"]]`
  - Model config: `extra="forbid"` (rejects unknown fields).
- JSON Schema export to `messages.schema.json` `profile.v1` namespace, Draft-07, `additionalProperties: false`.
- Serializer enforces UTF-8 byte cap: `if len(json.dumps(profile).encode("utf-8")) > 2048: raise ProfileTooLargeError(profile)`.

### GeminiContextCache injection (PROFILE-03 / P60)
- File: `src/vibemix/agent/context_cache.py` — wrapper around Gemini SDK cache builder.
- Profile dict serialized to a SystemInstruction-style cache block, injected once at session start.
- NEVER appended to per-turn prompt. Test: grep `prompt_builder.py` for `profile` field → must NOT appear in per-turn path.
- 1024-token floor preserved: profile is ~500-800 tokens, fits comfortably in cache.
- 4min refresh contract preserved: cache TTL unaffected.

### DJCoHostAgent kwargs-only injection (PROFILE-04 / P53)
- Edit `DJCoHostAgent.__init__` signature: add `profile: dict | None = None` AFTER existing 4 kwargs, AS kwargs-only (separator `*,` already in place per P53).
- `None` default = v2.0 4-kwarg constructor call path byte-identical.
- Test: `test_djcohost_init_kwargs_only_byte_identical_path` — assert v2.0-style call with 4 args raises NO warning and produces equivalent agent state.

### Consent screen (PROFILE-05)
- First-launch wizard step: "Build a profile to personalize coaching?" toggle.
- Default-OFF. Surfaces field-set inline (list each allowed field with one-line description).
- Persist to `~/.config/vibemix/state.json` under `profile_consent: bool`.
- Vanilla TS class: `tauri/ui/src/wizard/components/profile-consent.ts`.

### Settings → Profile panel (PROFILE-07)
- Tab `Profile` (new) — view current profile JSON (formatted), "Delete profile" button (confirms), "Regenerate now" button.
- Visual: CDJ Whisper restraint. Amber-2 accents only.
- IPC: 3 new schemas `profile.view`, `profile.delete`, `profile.regenerate`.

### Tendency drift prevention (PROFILE-06)
- Each tendency field in the profile schema carries `_citations: list[str]` (event IDs) at build-time (stripped before serialization to keep ≤2KB).
- Builder requires ≥2 distinct citations per field. If a tendency has <2 citations, retain prior value (or `None` if new).
- Test: `test_tendency_requires_2_citations` — synthetic session with 1 citation → tendency preserved/null, not regenerated.

### Frontend convention
- Vanilla TS, no React.
- IPC codegen via `npm run check:ipc`.

### Privacy posture
- Profile is local-only. No cloud sync.
- DELETE button truly deletes — file unlink + cache invalidate.
- No telemetry of profile contents.

### Test discipline
- Pydantic validation tests for every allowed field.
- Size cap test with synthetic over-budget profile.
- `additionalProperties: false` rejection tests.
- Cache injection vs per-turn prompt grep test.
- kwargs-only byte-identical test (P53).
- ≥2-citation test (P51 drift prevention).
- Consent default-OFF test.

</decisions>

<code_context>
## Existing Code Insights

- **v2.0 Phase 25 (shipped)** — DEBRIEF data infrastructure. EvidenceRegistry snapshots per session.
- **v2.0 Phase 10 (shipped)** — prompt matrix in `src/vibemix/agent/prompt_builder.py`.
- **Phase 28 (shipped)** — library citations flow into reactions; profile may reference allowlist tags but NEVER track titles.
- **Phase 29 (shipped)** — `<session_dir>/evidence_registry.json` snapshot persists per session (added in Phase 29 recorder change).
- **GeminiContextCache** — v2.0 Phase 10 owns cache lifecycle.
- **DJCoHostAgent** — v2.0; constructor has `*` separator already in place per P53.
- **Wizard** — v2.0 Phase 11; vanilla TS, CDJ Whisper visual.
- **Settings panel** — v2.0 + Phase 28/29 extensions.

Codebase maps under `.planning/codebase/` feed plan-phase research.

</code_context>

<specifics>
## Specific Ideas

- **2048-byte cap is HARD** — empirically tested for token-cache cost. Over = serializer raises.
- **Default-OFF consent is non-negotiable** (P51 privacy).
- **No track titles in profile** — tags only (e.g., "long_blends", not "Adam Beyer - Greyhound").
- **≥2 citations rule** prevents one-off-session-derived tendencies from polluting the profile.
- **Cache-side, not per-turn** — preserves Gemini API cost efficiency (P60).
- **Profile is local-only** — never uploaded.

</specifics>

<deferred>
## Deferred Ideas

- **Cloud sync of profile** — out of scope, single-machine.
- **Multi-profile (multiple DJs sharing app)** — out of scope; single user.
- **Profile-driven track recommendation** — explicitly NOT (LIBRARY-14 anti-feature).
- **Free-form text fields ("personality", "notes")** — rejected (privacy + drift).
- **Cross-session learning models** — out of scope, rule-based aggregation only.
- **Profile A/B in eval harness** — v2.2 stretch.
- **Profile export / import** — v2.2.

</deferred>
