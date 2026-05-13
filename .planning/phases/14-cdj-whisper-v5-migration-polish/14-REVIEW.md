---
phase: 14-cdj-whisper-v5-migration-polish
reviewed: 2026-05-13T15:40:00Z
depth: standard
files_reviewed: 41
files_reviewed_list:
  - scripts/check_v5_copy.sh
  - scripts/check_v5_fonts.sh
  - scripts/check_v5_migration.sh
  - src/vibemix/runtime/config_store.py
  - src/vibemix/runtime/session_loop.py
  - src/vibemix/runtime/settings.py
  - src/vibemix/ui_bus/messages.py
  - tauri/ui/LICENSE-3RD-PARTY.md
  - tauri/ui/index.html
  - tauri/ui/mascot.html
  - tauri/ui/src/ipc/messages.schema.json
  - tauri/ui/src/ipc/messages.ts
  - tauri/ui/src/ipc/validator.spec.ts
  - tauri/ui/src/main.ts
  - tauri/ui/src/mascot/chrome.css
  - tauri/ui/src/mascot/index.ts
  - tauri/ui/src/session/SessionLayout.ts
  - tauri/ui/src/session/components/meter.ts
  - tauri/ui/src/session/components/rocker.ts
  - tauri/ui/src/session/components/titlebar.ts
  - tauri/ui/src/session/state.ts
  - tauri/ui/src/session/ws-bridge.ts
  - tauri/ui/src/settings/SettingsDrawer.ts
  - tauri/ui/src/settings/components/confirm-dialog.ts
  - tauri/ui/src/settings/components/hotkey-capture.ts
  - tauri/ui/src/settings/components/mascot-group.ts
  - tauri/ui/src/settings/components/performance-group.ts
  - tauri/ui/src/settings/components/retention-slider.ts
  - tauri/ui/src/tokens.css
  - tauri/ui/src/wizard/components/audio-test-button.ts
  - tauri/ui/src/wizard/components/blackhole-banner.ts
  - tauri/ui/src/wizard/components/button.ts
  - tauri/ui/src/wizard/components/controller-probe.ts
  - tauri/ui/src/wizard/components/dropdown-device.ts
  - tauri/ui/src/wizard/components/permissions-card.ts
  - tauri/ui/src/wizard/components/primary-panel.ts
  - tauri/ui/src/wizard/components/status-bar.ts
  - tauri/ui/src/wizard/components/step-indicator.ts
  - tauri/ui/src/wizard/components/window-picker.ts
  - tauri/ui/src/wizard/smoke-test.ts
  - tauri/ui/src/wizard/step1-permissions.ts
  - tauri/ui/tests/mascot.chrome.test.ts
  - tauri/ui/tests/session.tokens.test.ts
  - tauri/ui/tests/settings.tokens.test.ts
  - tauri/ui/tests/wizard.tokens.test.ts
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: findings_addressed
fixes_applied_at: 2026-05-13T16:00:00Z
fixes_applied_commits:
  WR-01: 77e3b33
  WR-02: 0dc5f9a
  WR-03: e5d1906
  WR-04: 0f0fc25
  IN-01: fe7eae2
  IN-02: 76620ca
  IN-03: 5e7c493
---

# Phase 14: CDJ Whisper v5 Migration — Code Review Report

**Reviewed:** 2026-05-13T15:40:00Z
**Depth:** standard
**Files Reviewed:** 41 (out of 90 modified in commit range `2b608b6..HEAD`)
**Status:** findings_found

## Summary

Phase 14 delivers the v5 visual-contract migration cleanly across all four
shipping surfaces. Objective scripted gates (migration / fonts / copy)
exit 0 repo-wide; the full vitest suite reports 275/275 passing with zero
`describe.skip` and zero `@ts-nocheck` carried into shipping code; the
pre-commit hook lifecycle (wired → fired → removed) verified; the five
legacy WOFF2 files are deleted and four new SHA-256 attestations land in
`LICENSE-3RD-PARTY.md`. POC files (`cohost*.py`, `cohost.streaming.py.bak`,
root `mascot.html`, `mocks/*`) untouched. Phase 13's `renderer.ts` +
`fixMeshyMaterials()` preserved verbatim.

The migration body is correct. The findings below cluster around two
themes that the phase did not catch:

1. **One real CSS specificity bug** in `SessionLayout.ts` where the
   `z-index 5` descendant promotion rule (added for `.border-anim`
   stacking) silently overrides absolute-positioned ornamental screws,
   collapsing them out of corner placement. The vitest spec passed
   because jsdom does not compute layout.
2. **Production-vs-documentation divergence** in `mascot/index.ts`
   `handleMoodChange()` — the coach mood resolves `--silk-40` through
   `THREE.Color`, which drops the alpha channel and yields the same beige
   RGB as the teacher mood. The slate hex fallback `#3d424c` is only
   exercised in jsdom/test paths. Coach and teacher therefore produce
   visually-identical particle puff colors at runtime, contradicting the
   inline comment "coach → slate".

Plus three lower-severity consistency gaps in the settings IPC + type
surface — leftover from Plan 13-05 that Plan 14-04 only partially
remediated.

No CRITICAL findings. No security regressions. No data-loss risks. No
crash-class bugs.

## Warnings

### WR-01: `.vmx-session > *:not(.border-anim)` overrides screw absolute positioning

**File:** `tauri/ui/src/session/SessionLayout.ts:136-148`
**Issue:** The descendant rule introduced in Plan 14-03 to promote
`.vmx-session` children above the `.border-anim` z=4 sweep has higher CSS
specificity than the screw rule that follows it:

- `.vmx-session > *:not(.border-anim)` → specificity `(0,2,0)` (`.vmx-session` + `:not(.border-anim)` per CSS Selectors L4 — `:not()` arguments count toward specificity)
- `.vmx-session__screw` → specificity `(0,1,0)` (single class)

Result: the screws lose their declared `position: absolute` (overridden
to `relative`) and lose their `z-index: 100` (overridden to `5`). The
corner-anchored `top: 6px; left: 6px;` declarations become inert because
relatively-positioned elements ignore offsets without a containing block
adjustment. The four screw ornaments will render inline at the start of
`.vmx-session` instead of pinned to the four corners. The vitest spec
(`tests/session.tokens.test.ts`) passes because jsdom does not compute
layout — this only surfaces in `npm run tauri dev` or in the real Tauri
webview.

**Fix:**
```css
/* Make the screw rule specifically opt out of the descendant promotion,
 * OR raise screw specificity above (0,2,0). The cleanest fix is to scope
 * the promotion to non-screw direct children: */
.vmx-session > *:not(.border-anim):not(.vmx-session__screw) {
  position: relative;
  z-index: 5;
}
/* Screw rule keeps its absolute positioning + z-index 100 unchanged. */
```
Alternative: add `!important` to the screw `position` + `z-index` (less
desirable). Either way add a render-loop test that asserts
`getComputedStyle(screw).position === 'absolute'`.

---

### WR-02: Coach mood particle puff resolves to same color as teacher (alpha dropped by THREE.Color)

**File:** `tauri/ui/src/mascot/index.ts:480-481`
**Issue:** The coach branch calls `resolveCssColor("--silk-40", "#3d424c")`.
At runtime `getComputedStyle` returns `rgba(214, 207, 199, 0.40)` from
`tokens.css:91`. `new Color("rgba(214,207,199,0.40)")` parses the string
but `THREE.Color` **silently discards the alpha channel** (confirmed via
`THREE.Color: Alpha component of rgba(214, 207, 199, 0.40) will be
ignored.` warning + `getHexString()` returning `d6cfc7`). The result is
the same RGB as the teacher branch's `--silk` (`#d6cfc7`). The slate
fallback `#3d424c` is only reached in jsdom/tests where `getComputedStyle`
returns empty. The inline comment on line 473 ("coach → slate") and the
docstring on line 446 are aspirational, not actual. Production users
toggling hype-man → teacher → coach will see **two distinct particle
puff colors instead of three**.

**Fix:** Either (a) introduce a dedicated `--coach` slate token in
`tokens.css` (e.g. `--coach: #3d424c;`) and use it directly:
```typescript
} else {
  // coach — slate (distinct from teacher's silk)
  color = resolveCssColor("--coach", "#3d424c");
}
```
or (b) keep the v5 audit-gate exception count at 3 but compute the
slate color manually for coach (skip `resolveCssColor` for this branch):
```typescript
} else {
  // coach — slate constant; --silk-40 is alpha-on-silk which THREE.Color
  // would collapse to silk RGB. Hex literal preserved as documented
  // audit-gate exception.
  color = new Color("#3d424c");
}
```
Add a unit test in `mascot/particle-puff.test.ts` that mocks
`document.documentElement` with a real `--silk-40` style and asserts
`color.getHexString() !== "d6cfc7"` for coach.

---

### WR-03: `sendSettingsField()` in SettingsDrawer rejects `boolean` (type drift vs `sendSettings`)

**File:** `tauri/ui/src/settings/SettingsDrawer.ts:671-681`
**Issue:** `sendSettings` in `ws-bridge.ts:203` was widened to
`value: string | number | boolean | null` for Plan 14-04. Its local
wrapper `sendSettingsField` in SettingsDrawer was NOT widened — it stays
`value: string | number | null`. Result: any future drawer-side toggle
that wants to flow through the `sendSettingsField` wrapper for the
shared try/catch convenience cannot pass a boolean without a type
assertion. Today the `PerformanceGroup` works because it calls
`sendSettings` directly (bypassing the wrapper) — but the type drift
will trip up the next contributor adding a boolean setting through the
drawer.

**Fix:**
```typescript
async function sendSettingsField(
  field: SettingsField,
  value: string | number | boolean | null,
): Promise<void> {
  try {
    await sendSettings(field, value);
  } catch (err) {
    console.warn(`[settings] sendSettings(${field}) failed:`, err);
  }
}
```

---

### WR-04: `SETTINGS_FIELDS` in ws-bridge missing `"mood"` and `"click_through"` (drift vs schema enum)

**File:** `tauri/ui/src/session/ws-bridge.ts:122-131`
**Issue:** The IPC schema enum at `messages.schema.json:529` lists 10
fields: `voice, mode, genre, output_device_id, output_profile,
retention_days, push_to_mute_hotkey, mood, click_through, lighter_blur`.
The Python `SettingsSetPayload.field` Literal in
`src/vibemix/ui_bus/messages.py:281-292` lists the same 10. But the TS
runtime allowlist `SETTINGS_FIELDS` in ws-bridge has only 8: it omits
`"mood"` and `"click_through"`. Today this is workable because
`mascot-group.ts:242,263` bypasses `sendSettings` by calling
`emitIpc("ipc.settings.set", { field: "mood", ... })` directly. But the
allowlist drift means any future caller mistakenly using `sendSettings`
for mood or click_through will hit the runtime `unknown field` throw.
This is exactly the drift Plan 14-04's deviation #4 acknowledged on the
Python side; the TS side stayed inconsistent.

**Fix:**
```typescript
const SETTINGS_FIELDS = [
  "voice",
  "mode",
  "genre",
  "output_device_id",
  "output_profile",
  "retention_days",
  "push_to_mute_hotkey",
  "mood",            // Plan 13-05
  "click_through",   // Plan 13-05
  "lighter_blur",    // Plan 14-04
] as const;
```
After widening, the `mascot-group.ts` direct `emitIpc` call sites can be
optionally migrated to `sendSettings` for consistency, but that's not
required by the fix itself.

## Info

### IN-01: `main.ts` boot-read comment promises a subscription it doesn't make

**File:** `tauri/ui/src/main.ts:149-152`
**Issue:** The block comment claims:
> "Independently, the OS-level prefers-reduced-motion media query already
> routes through the same tokens.css cascade — we ALSO subscribe to that
> here so an a11y toggle flips the attribute without a reload."

But the code below is a single-shot `applyBlurPerfPreference(await
readBlurPerfPreference())` — there is no `matchMedia('(prefers-reduced-motion: reduce)').addEventListener(...)` subscription anywhere. The
CSS `@media (prefers-reduced-motion: reduce)` block in tokens.css already
handles live OS-level toggles via the cascade, so the missing subscription
is harmless — but the comment overpromises.

**Fix:** Either remove the misleading "we ALSO subscribe" sentence, or
add an actual `matchMedia` subscription that flips `data-blur-perf`. The
first option is simpler:
```typescript
// Apply boot-time perf-blur preference (CONTEXT Area 3). Reads from
// the existing settings IPC; defaults off if the field is absent.
// OS-level prefers-reduced-motion lives in the tokens.css @media
// cascade independently — no JS subscription needed here.
applyBlurPerfPreference(await readBlurPerfPreference());
```

---

### IN-02: `ConfigStore.from_dict` does not type-coerce `lighter_blur` from disk

**File:** `src/vibemix/runtime/config_store.py:164-186`
**Issue:** `from_dict` validates `retention_days` (special-case int
coercion) but accepts any value for `lighter_blur`. If a config.json on
disk has been corrupted to `"lighter_blur": "yes"` or `"lighter_blur": 1`,
the dataclass field is populated with the non-bool value verbatim. Most
downstream paths handle truthiness fine, but the JSON schema-validated
`SettingsState` emit at `session_loop.py:436` would emit
`lighter_blur: "yes"` which the JSON-schema validator (`"type":
"boolean"`) would then reject, breaking the boot ack. The applier
(`_apply_lighter_blur`) does validate at the trust boundary, so any
*new* write is safe — but the disk-load path skips that gate.

**Fix:** Add bool coercion next to the existing `retention_days` block:
```python
# If lighter_blur came in as something non-bool, fall back to default.
if "lighter_blur" in kwargs and not isinstance(kwargs["lighter_blur"], bool):
    kwargs.pop("lighter_blur", None)
```
Same treatment could be applied to the other Phase 11 bool fields
(`first_run_completed`, `blackhole_install_seen`) if the policy is
"silently drop garbage rather than emit a broken ack".

---

### IN-03: SettingsState schema requires `lighter_blur` but does not declare `mood` / `click_through`

**File:** `tauri/ui/src/ipc/messages.schema.json:557-582`
**Issue:** The `SettingsState` payload has `additionalProperties: false`
+ a 9-field `required` list including the new `lighter_blur`. But `mood`
and `click_through` are still absent from both the properties block and
the required list — meaning a `SettingsState` payload that DID carry
those fields (per Plan 13-05's design intent for mood persistence
restoration) would fail schema validation. The current sidecar at
`session_loop.py:_emit_settings_state` does not include them on emit, so
this is currently dormant — but it means mood + click_through cannot be
round-tripped through a `SettingsState` snapshot on next launch. The
client-side `WireSettingsStatePayload` (`ws-bridge.ts:108-114`) optimistically declares them
as optional, but they would never arrive due to the schema gate.

This is leftover Plan 13-05 debt that Phase 14 had occasion to fix
(extending `SettingsState.required`) and only addressed the lighter_blur
field. Not a Phase 14 regression — pre-existing drift surfaced by the
review.

**Fix:** Add `mood` and `click_through` to `SettingsState.payload`
properties + `required`, mirror the change in
`SettingsStatePayload` (`messages.py:302-311`), and pass the values
through in `session_loop.py:_emit_settings_state`:
```python
state = SettingsState.make(
    ...
    lighter_blur=self.config_store.lighter_blur,
    mood=self.music_state.mood,
    click_through=bool(self.config_store.extra.get("click_through", False)),
)
```
Note: this expands Phase 13-05 scope — flag as a follow-up plan rather
than rolling into Phase 14's already-closed scope.

---

## Out of Scope (Verified Clean)

- POC files (`cohost*.py`, `cohost.streaming.py.bak`, root `mascot.html`,
  `mocks/*`) — `git diff 2b608b6..HEAD` returns nothing for these paths.
- `tauri/ui/src/mascot/renderer.ts` — last touched at commit `2b608b6`
  (Phase 13 Meshy material fix); `fixMeshyMaterials()` still defined at
  `renderer.ts:80` and called from `MascotRenderer` constructor at
  `renderer.ts:176`.
- Hex literals outside `tokens.css` — exactly the 3 documented exceptions
  in `mascot/index.ts:476,478,481` (`#ff8a3d`, `#d6cfc7`, `#3d424c`).
  No other hex hits in `tauri/ui/src/`.
- Legacy shim tokens (`--phosphor*`, `--brushed-*`, `--bezel-*`,
  `--col-mascot`, `--ink-*`, `--rec`, `--crash-grad-*`, `--sp-{xs,sm,md,lg,xl,2xl,3xl}`)
  — all 3 strict gates (`migration` / `fonts` / `copy`) exit 0 repo-wide.
- Pre-commit hook — confirmed absent (`.git/hooks/pre-commit` does not exist).
- Legacy WOFF2 files — confirmed deleted from `tauri/ui/public/fonts/`;
  only the 4 vendored files (Saira variable + JBM 3 weights) remain.
- LICENSE-3RD-PARTY.md — 4 SHA-256 attestations match
  `14-01-FONT-ATTESTATION.md` byte-for-byte (`d5f1ee1c…` Saira,
  `14425ba9…` JBM-Regular, `cb182fee…` JBM-Medium, `400c6bfd…` JBM-SemiBold).
- IPC schema parity — `python3 scripts/check_ipc_schema.py` →
  `27 dataclasses validate against schema` + `count parity — 27 oneOf
  entries == 27 wrapper dataclasses`. Note: scope memo expected 26
  wrappers; actual is 27 — no new family added in Phase 14, the count
  reflects all phases through 14.
- vitest full suite — 22 files / 275 passing / 0 skipped.
- `mascot.html` (`tauri/ui/mascot.html`) — links `/src/tokens.css`,
  enforces transparent body + disables `body::before` film-grain layer
  with `!important` (Phase 13 invariant preserved), `.border-anim slow rev`
  is the first child of `.mascot-window`.

---

## Fixes Applied

Applied 2026-05-13T16:00:00Z by gsd-code-fixer. All 7 findings addressed
with atomic per-finding commits. Verification gates re-run after the
final commit: all green.

| ID    | Title (abbreviated)                                                              | Commit    |
| ----- | -------------------------------------------------------------------------------- | --------- |
| WR-01 | exclude `.vmx-session__screw` from descendant z-index promotion                  | `77e3b33` |
| WR-02 | coach mood uses flat slate hex (`new Color("#3d424c")`) — THREE.Color drops alpha | `0dc5f9a` |
| WR-03 | widen `sendSettingsField` value union to include `boolean`                       | `e5d1906` |
| WR-04 | add `mood` + `click_through` to `SETTINGS_FIELDS` allowlist                      | `0f0fc25` |
| IN-01 | correct misleading boot-read comment in `main.ts`                                | `fe7eae2` |
| IN-02 | coerce/drop non-bool `lighter_blur` (+ Phase 11 bools) from disk                 | `76620ca` |
| IN-03 | add optional `mood` + `click_through` to `SettingsState`                         | `5e7c493` |

### Verification gates re-run after final fix commit

- `bash scripts/check_v5_migration.sh --strict` → PASS (0 hits)
- `bash scripts/check_v5_fonts.sh --strict` → PASS (0 hits)
- `bash scripts/check_v5_copy.sh --strict` → PASS (0 hits)
- `python3 scripts/check_ipc_schema.py` → 27 dataclasses validate; 27 == 27 oneOf parity
- `cd tauri/ui && npm run check:ipc` → codegen idempotent, `tsc --noEmit` zero errors
- `cd tauri/ui && npm run test -- --run` → 22 files / 275 passing / 0 skipped
- `python -m pytest -q tests/runtime/ tests/ui_bus/ tests/ipc/` → 173 passed

### Deviations from REVIEW.md fix suggestions

- **WR-02** — followed option (b) (direct `new Color("#3d424c")` for coach) over option (a) (new `--coach` token in tokens.css). Option (b) keeps the audit-gate exception count at 3 as the review noted; the `tokens.css` token surface stays untouched. The corresponding regex assertion in `tauri/ui/tests/mascot.chrome.test.ts` was relaxed (`--silk-40` removed from the required-token list, since the coach branch no longer calls `resolveCssColor` for it).
- **IN-02** — extended the bool-coercion drop to `first_run_completed` and `blackhole_install_seen` in addition to `lighter_blur` per the review's "same treatment could be applied" suggestion. Policy unified: silently drop non-bool garbage from disk for all bool dataclass fields.
- **IN-03** — added `mood` + `click_through` to `SettingsState.payload.properties` and the Python `SettingsStatePayload` + `SettingsState.make()` factory, but kept them OUT of `required`. The review suggested adding to `required`; doing so would have broken `tests/ui_bus/test_messages_schema.py` and `tests/ipc/test_session_messages.py` which both construct `SettingsState.make()` calls without these fields. Optional-with-`anyOf null` is consistent with how `output_device_id` is modeled and how the TS client `WireSettingsStatePayload` already declares them. The factory uses default `None`, matching `lighter_blur: bool = False`.

---

_Reviewed: 2026-05-13T15:40:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Fixes applied: 2026-05-13T16:00:00Z by gsd-code-fixer_
