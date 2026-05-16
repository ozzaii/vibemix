# Phase 32 Research — Long-Term DJ Profile (~2KB JSON)

**Date:** 2026-05-15
**Source artifacts read:**
- `CLAUDE.md`, `.planning/PROJECT.md`, `.planning/STATE.md`
- `.planning/research/v2-1/PITFALLS.md` (P51, P53, P60)
- `src/vibemix/agent/dj_cohost.py` (DJCoHostAgent constructor)
- `src/vibemix/agent/cache.py` (GeminiContextCache lifecycle)
- `src/vibemix/agent/persona.py` (SYSTEM_INSTRUCTION)
- `src/vibemix/state/evidence_registry.py` (snapshot shape)
- `src/vibemix/state/event.py` (Event dataclass)
- `src/vibemix/ui_bus/messages.py` (IPC dataclass conventions)
- `src/vibemix/ui_bus/schemas/library.py` (subpackage payload pattern)
- `src/vibemix/runtime/session_loop.py` (handler registration)
- `tauri/ui/src/ipc/messages.schema.json` (RecordingsList/Delete reference shape)
- `tauri/ui/src/settings/SettingsDrawer.ts` (group composition pattern)
- `tauri/ui/src/settings/components/library-panel.ts` (async-mounted settings panel)
- `tauri/ui/src/wizard/router.ts`, `step0-intro.ts` (wizard step pattern)
- `tests/agent/test_dj_cohost.py` (constructor fixture style)

## Hard pins anchoring this phase

### DJCoHostAgent constructor (P53)
Already kwargs-only (`*` separator on `dj_cohost.py:140`). 12 existing kwargs:
`genai_client, clean_audio_buf, screen_buf, state, recorder, llm_inst, tts_inst,
evidence_registry=None, cache=None, ttft_meter=None, citation_linter=None,
stripped_rate_tracker=None, ack_bank=None, playback=None, ipc_bus=None`.

P53-language ("5th kwarg `profile=` AFTER `*` separator", "v2.0 4-kwarg path
byte-identical") describes the policy. The literal-5th-position framing
predates v2.0 Phase 19 (cache/ttft) and v2.0 Phase 20 (linter/tracker/ack/
playback). Translation: `profile=` is added as **another** None-default
kwargs-only argument; the byte-identical test compares constructor behavior
with `profile=None` (omitted) vs v2.0 shape, NOT a literal "5 args only" check.

**One call site to update:** `src/vibemix/__main__.py:644-659`. Default is
`profile=None` so __main__'s call without `profile=` keeps byte-identical
behavior. Plan adds `profile=` after Phase 28 wiring.

### GeminiContextCache injection (P60)
The cache constructor takes `system_instruction_body: str`. Profile must be
serialized into the body BEFORE `cache.create()` is called. The body =
`SYSTEM_INSTRUCTION + "\n\n" + profile_section` (or empty if profile is None).
`padded_body()` floor + 4min refresh contract preserved automatically since
profile inflates body (still well under floor — SYSTEM_INSTRUCTION is already
~5KB).

**Per-turn grep gate:** the agent's hot path is `DJCoHostAgent.llm_node`. Search
must show no `profile` field referenced there.

### EvidenceRegistry snapshot shape (PROFILE-06)
`snapshot()` returns `dict[source, dict[key, tuple[float, ...]]]`. Sources
seen in v2.0: `event` (keys = event-type strings like `TRACK_CHANGE`, `PHASE`,
`MIX_MOVE`), `track` (keys = track IDs), `screen`, `mic`. A "citation" for
the ≥2-rule is `(source, key)` × distinct timestamps. We require ≥2 distinct
timestamps per inferred tendency-field source.

### IPC schema additions
Pattern: shell→sidecar request + sidecar→shell response (+ optional ack).
Use `_VALIDATOR.validate(d)` via `_serialize`. Three new IPC types planned:
- `ipc.profile.view` (shell→sidecar) + `ipc.profile.view_result` (sidecar→shell)
- `ipc.profile.regenerate` (shell→sidecar) + `ipc.profile.regenerate_result`
- `ipc.profile.delete` (shell→sidecar) + `ipc.profile.delete_ack`

Plus consent persistence: `ipc.profile.set_consent` + `ipc.profile.consent_state`.

### Wizard insertion point
Profile consent is a NEW step BEFORE smoke-test (so user sees field-set before
the cascade greeting). Insertion: after `controller`, before `smoke-test`.
`STEP_ORDER` in `router.ts:116` is `["permissions", "audio", "controller",
"smoke-test"]`. New: `["permissions", "audio", "controller", "profile-consent",
"smoke-test"]`.

Alternative (lighter): mount profile-consent as a **non-blocking checkbox** on
the existing smoke-test step. Decision: separate step is overscope; instead,
add the consent toggle to a NEW "PROFILE" sub-card on the smoke-test surface
OR ship a minimal `profile-consent.ts` step. Final pick → minimal new step
since (a) UI-SPEC fits cleanly, (b) field-set disclosure needs room, (c) the
"build a profile?" question is a discrete decision moment. STEP_ORDER grows
by one entry.

### Settings panel insertion
After PERSONA / OUTPUT / HOTKEY / RECORDING / LIBRARY / CALIBRATION / MASCOT /
PERFORMANCE / HELP. New PROFILE group lands between LIBRARY and CALIBRATION
(both are user-data groups; PROFILE is the more sensitive one so it sits
adjacent to LIBRARY for findability).

## Pitfalls re-confirmed

- **P51 size + privacy:** ≤2048 UTF-8 bytes via `len(json.dumps(profile).encode("utf-8"))`. Allowlist enforced by `additionalProperties: false` + `Literal[...]` enum unions in the python `TypedDict`-style validator (jsonschema only — no pydantic per project convention).
- **P53 kwargs-only:** add `profile: dict | None = None` to `DJCoHostAgent.__init__`, kwargs-only (the `*` is already there), None default = byte-identical.
- **P60 cache-side:** profile baked into `GeminiContextCache(system_instruction_body=...)` at construction in `__main__.py`. No reference in `prompt_builder` or `dj_cohost.llm_node`.

## Open questions resolved

1. **Where does the profile file live?** `~/.config/vibemix/profile.json` (matches `state.json` location from wizard completion).
2. **Where does prior history live?** `~/.cache/vibemix/profile/history.json` (separate from profile — kept across regenerations for the ≥10-session aggregation).
3. **What schema lib does the builder use?** `jsonschema` (already in repo; pydantic banned by D-Area-4.4).
4. **Where does the profile string get rendered into the cache body?** Helper in `profile.cache_render` — flat key:value lines (P60 prevents JSON literal injection).
5. **What does the regenerator return if consent OFF?** `None` — caller skips the persistence write + cache rebuild.

## Plan decomposition

- **32-01** — `src/vibemix/profile/{builder.py,schema.py,cache_render.py}` + 6 tests. Pure-Python, no IPC.
- **32-02** — `GeminiContextCache` profile-section integration in `__main__.py`; profile loaded at boot, injected into cache body. Grep gate test.
- **32-03** — `DJCoHostAgent.__init__` `profile=` kwarg + byte-identical fixture test.
- **32-04** — Wizard consent toggle step (TS) + `ipc.profile.set_consent` schema + handler.
- **32-05** — Settings → Profile panel TS + `ipc.profile.view`/`delete`/`regenerate` schemas + handlers.
- **32-06** — Codegen + E2E smoke (`npm run check:ipc` + python schema-parity test).
