# Phase 32 Summary — Long-Term DJ Profile (~2KB JSON)

**Status:** SHIPPED 2026-05-15
**Mode:** gsd-autonomous fully
**Plans:** 6/6 (32-01 through 32-06)
**REQ-IDs satisfied:** PROFILE-01..07

## What shipped

| Plan | Surface | REQ |
|------|---------|-----|
| 32-01 | `src/vibemix/profile/` — builder + schema + serializer + cache_render | PROFILE-01, 02, 06 |
| 32-02 | `GeminiContextCache.profile_section` + `storage.{load,save,delete}_profile` + `__main__` wiring | PROFILE-03 |
| 32-03 | `DJCoHostAgent.__init__(*, profile=None)` kwargs-only kwarg | PROFILE-04 |
| 32-04 | Wizard consent step (default-OFF) + 8 `ipc.profile.*` schemas + WizardLoop handler | PROFILE-05 |
| 32-05 | Settings → Profile panel + SessionLoop 4 handlers (view / regenerate / delete / set_consent) | PROFILE-07 |
| 32-06 | E2E lifecycle test + IPC count parity bump 55 → 63 | cross-cutting |

## Privacy / discipline gate evidence

| Gate | Verification |
|------|--------------|
| P51 — 2048-byte hard cap | `serialize_profile` raises `ProfileError` on overflow; `test_profile_size_cap_2048_bytes` + `test_profile_serialize_compact_within_cap` |
| P51 — `additionalProperties: false` | `test_profile_additional_properties_false_rejects_recent_tracks` + same for `library_titles` / `personality` |
| P51 — no track titles | jsonschema enum-only fields; `grep -rE 'track_title\|library_titles' src/vibemix/profile/` only finds rejection docstrings |
| P53 — kwargs-only byte-identical | `test_djcohost_kwargs_only_byte_identical_path` + `test_djcohost_profile_kwargs_only_rejects_positional` |
| P60 — profile NEVER in per-turn prompt | `test_profile_substring_absent_from_dj_cohost_llm_node` + `test_profile_substring_absent_from_ai_coach_build_prompt` + `test_profile_not_in_per_turn_llm_node_path` (E2E grep gate) |
| PROFILE-06 — ≥2 citations rule | `test_tendency_requires_2_citations` + handler-level `insufficient_evidence` gate when no evidence AND no prior |
| PROFILE-05 — default-OFF consent | `test_consent_default_is_false` + `test_profile_set_consent_default_off_path` + wizard `DEFAULT_STATE.profileConsent.consent = false` |

## Test results

- **Python (Phase 32 scope + adjacent):** 404 passed (`tests/profile/ tests/wizard/ tests/ipc/ tests/agent/test_cache* tests/agent/test_dj_cohost* tests/runtime/test_session_loop.py tests/ui_bus/`)
- **TS (vitest profile-panel.spec.ts):** 6 passed (jsdom env added to vitest.config.ts)
- **IPC parity:** 63 oneOf == 63 wrapper dataclasses (`scripts/check_ipc_schema.py`)
- **TS typecheck:** `npm run check:ipc` clean (codegen + tsc --noEmit)

## Pre-existing failures (NOT introduced by Phase 32, verified via `git stash`)

- `tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4` — persona drift, unrelated
- `tests/test_main_smoke.py` × 3 — smoke harness, unrelated
- `tests/test_main_debrief_flag.py` × 2 — debrief CLI mock, unrelated
- `tests/test_phase05_verification.py::test_g5_poc_files_untouched` — uncommitted POC files (cohost_v3/v4/v4_tr.py + run scripts), unrelated
- `tauri/ui src/ipc/validator.spec.ts` — `ipc.recordings.delete_ack` validator, unrelated
- `tauri/ui tests/settings/drawer.spec.ts` × 2 — Tauri transformCallback mock, unrelated

## Files committed (chronological)

```
c2ae0a9 src/vibemix/profile/{__init__.py,builder.py,cache_render.py,schema.py}
        tests/profile/{__init__.py,test_builder.py,test_cache_render.py,test_schema.py}
4fd072e src/vibemix/agent/cache.py (profile_section kwarg)
        src/vibemix/profile/storage.py
        src/vibemix/__main__.py (load_profile + render_profile_for_cache + cache wiring)
        tests/agent/test_cache_profile_section.py
        tests/profile/test_storage.py
        tests/profile/test_profile_not_in_per_turn_prompt.py
4f2977e src/vibemix/agent/dj_cohost.py (profile= kwarg, P53)
        src/vibemix/__main__.py (DJCoHostAgent call passes profile=profile_dict)
        tests/agent/test_dj_cohost_profile_kwarg.py
7e77f02 tauri/ui/src/wizard/{components/profile-consent.ts,step-profile-consent.ts,router.ts}
        tauri/ui/src/ipc/{messages.schema.json,messages.ts,validator.generated.mjs}
        src/vibemix/ui_bus/{schemas/profile.py,messages.py,__init__.py}
        src/vibemix/runtime/wizard.py (consent handler)
        scripts/check_ipc_schema.py (8 new examples)
        tests/wizard/{test_profile_consent_handler.py,test_wizard_loop_ipc.py}
db5aedc tauri/ui/src/settings/{SettingsDrawer.ts,components/profile-panel.ts,components/profile-panel.spec.ts}
        tauri/ui/vitest.config.ts (jsdom for profile-panel)
        src/vibemix/runtime/session_loop.py (4 handlers + evidence_registry kwarg)
        tests/profile/test_profile_ipc.py
da95094 tests/profile/test_e2e.py
10aa491 tests/ui_bus/{test_messages_schema.py,test_mood_change_envelope.py,test_recordings_messages.py}
        (count parity 55 → 63)
```

## Deferred (per CONTEXT.md `<deferred>`)

- Cloud sync of profile — out of scope.
- Multi-profile support — out of scope.
- Profile-driven track recommendation — explicitly NOT (LIBRARY-14 anti-feature).
- Free-form text fields — rejected (privacy + drift).
- Profile A/B in eval harness — v2.2 stretch.
- Profile export / import — v2.2.

## What stays loaded going forward

- `profile_consent: bool` persists in `~/.config/vibemix/state.json`.
- `~/.config/vibemix/profile.json` (0o600) holds the on-disk profile when consent is ON and the builder has produced one.
- `~/.cache/vibemix/profile/history.json` reserved for the ≥10-session aggregation across regenerations (Plan 32-01 reads/writes per current implementation).
- `GeminiContextCache.profile_section` carries the rendered profile (~300 tokens max) into the cache body alongside SYSTEM_INSTRUCTION; pad block fires if the combined body is below the 1024-token floor.
