---
phase: 62-floating-pill-ui
reviewed: 2026-05-22T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - tauri/src-tauri/src/pill_window.rs
  - tauri/src-tauri/src/config.rs
  - tauri/src-tauri/src/main.rs
  - tauri/src-tauri/capabilities/default.json
  - src/vibemix/runtime/ws_bus.py
  - tauri/ui/pill.html
  - tauri/ui/src/pill/index.ts
  - tauri/ui/src/pill/state-machine.ts
  - tauri/ui/src/pill/waveform.ts
  - tauri/ui/src/pill/deck-chips.ts
  - tauri/ui/src/pill/ws-client.ts
  - tauri/ui/src/pill/pill.css
  - tests/runtime/test_ws_bus_deck_state.py
findings:
  critical: 2
  warning: 6
  info: 5
  total: 13
status: issues_found
---

# Phase 62: Code Review Report

**Reviewed:** 2026-05-22
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Phase 62 adds a Tauri v2 floating-pill overlay: a Rust window builder cloned from `mascot_window.rs` with an `unsafe` objc2 NSWindow→NSPanel swizzle (gated STRETCH), a tri-state `primary_surface` config, an additive read-only `deck_state` field on the existing ws:8765 frame, and a vanilla-TS pill UI (pure state machine, real-voice waveform, reused citation strip, honest deck chips).

The architecture is sound and the focus areas the phase brief flagged are mostly well-executed: the state machine is genuinely pure (no timers/wall-clock in the reducer), the ws_bus serialization is a true read-only pass-through (single-writer untouched), frame text is rendered via `textContent` (no innerHTML/eval injection path), the citation strip is reused verbatim, no new WS port is opened, and no secrets/credentials appear. The CSS is token-only with no hardcoded hex (frontend-enforcement clean).

However, two BLOCKERS exist. **(1)** The `unsafe` objc2 swizzle in `pill_window.rs` violates the documented `set_class` safety contract on two counts and the doc claim "never panics" is contradicted by the build profile (`panic = "abort"`) — a `msg_send!`/`unwrap_unchecked` failure aborts the whole app rather than degrading to the floor. **(2)** The honest-null contract has a real hole: `DeckTrack.bpm` defaults to `0.0` (not `None`), so an unresolved deck serializes `bpm: 0.0`, and `deck-chips.ts` renders it as a fabricated `"0"` instead of `"unknown"` — exactly the anti-slop leak the phase set out to prevent, and it is untested.

## Critical Issues

### CR-01: objc2 NSWindow→NSPanel swizzle violates `set_class` safety contract and can abort the app under `panic = "abort"`

**File:** `tauri/src-tauri/src/pill_window.rs:402-451` (esp. 416-441), with `tauri/src-tauri/Cargo.toml:85-89` (`panic = "abort"`)

**Issue:** The STRETCH swizzles the live window object's class to `NSPanel` via `AnyObject::set_class`, then sends `setStyleMask:` / `setFloatingPanel:` / `setBecomesKeyOnlyIfNeeded:` / `setHidesOnDeactivate:`. Three problems compound:

1. **Subclass requirement violated.** objc2 0.6.4's `set_class` SAFETY contract (verified in `objc2-0.6.4/src/runtime/mod.rs:1276-1290`) requires "(1) the new class must be a subclass of the object's current class" and "(2) the subclass must not add any instance variables — the instance size of old and new classes must be the same." The object's *current* class is **wry's own `NSWindow` subclass** (e.g. `WryWindow`/`TaoWindow`), not bare `NSWindow`. `NSPanel` is **not** a subclass of wry's window class — it is a cousin (`NSResponder → NSWindow → {WryWindow, NSPanel}`). So requirement (1) is broken. Additionally `NSPanel` historically carries ivars beyond `NSWindow`, breaking (2). The code comment "NSPanel is a direct subclass of NSWindow so the layout/ivars are compatible" is **factually wrong** — it reasons about `NSWindow`, not wry's actual runtime class, and ignores the no-added-ivars rule entirely. This is genuine UB (mis-sized object → potential OOB ivar access in AppKit).

2. **"Never panics" is false under this build profile.** The module doc (lines 50-53, 382, 398-399) and the `with_webview` `match res` arms (445-450) assume any failure surfaces as `Err` and degrades to the floor. But `with_webview` only returns `Err` when the *webview is absent* — it does **not** catch a panic inside the closure. Inside the `unsafe` block, `set_class` ends with `ptr.as_ref().unwrap_unchecked()` and the `msg_send!` macro performs runtime nil/selector checks that can panic. With `[profile.release] panic = "abort"`, any such panic is an immediate `SIGABRT` of the entire process — the exact opposite of the documented "degrade to floor, main UI still comes up" discipline (T-62-05).

3. **`AnyClass::get(c"NSPanel")` is the only guarded failure mode.** Every other obj-c send is unguarded; there is no verification that `_old` (the returned previous class) is what was expected, which objc2's own docs explicitly recommend ("verify that the returned class is what you would expect, and if not, panic" — line 1293-1295), and no try-style isolation.

**Fix:** Either drop the STRETCH and ship only the Accessory-policy floor (the brief allows this — "Accept for v1; surface as KAAN-ACTION"), or make the swizzle genuinely safe and non-aborting:

```rust
// 1. Verify the runtime class is what we expect BEFORE swizzling, and bail
//    (to floor) if wry's window class is not a clean NSWindow subclass that
//    NSPanel can legally replace. Do NOT assume.
// 2. Isolate from panic = "abort": wrap the unsafe block in
//    std::panic::catch_unwind so a selector/dispatch failure cannot abort
//    the app — and confirm catch_unwind actually unwinds (it does NOT under
//    panic="abort"; you must either set panic="unwind" for this TU, or move
//    the swizzle behind the no-op floor entirely).
let safe = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| unsafe {
    // ... swizzle ...
}));
if safe.is_err() {
    tracing::warn!("pill: NSPanel swizzle panicked; Accessory floor in effect");
}
```

Note `catch_unwind` is a no-op under `panic = "abort"`; the cleanest correct path for v1 is to **not swizzle** and rely on the floor, since the brief explicitly sanctions that. If the swizzle ships, the "never panics" / "no UB beyond the documented swizzle" claims in the module doc must be corrected — the UB here is NOT documented-and-bounded, it is contract-violating.

### CR-02: Unresolved deck serializes `bpm: 0.0` and renders a fabricated `"0"` instead of `unknown` — honest-null hole

**File:** `src/vibemix/runtime/ws_bus.py:103` (`"bpm": dt.bpm`), `tauri/ui/src/pill/deck-chips.ts:116,129` (`d.bpm != null`)

**Issue:** The phase's central anti-slop guarantee is honest-null: an unresolved deck must never render a fabricated value. `camelot`/`key` honor this (both default `None` → JSON `null` → rendered `unknown`). But `DeckTrack.bpm` defaults to **`0.0`, not `None`** (confirmed `src/vibemix/state/deck_state.py:39` — "typed-empties-on-absence" shape). So a present-but-unresolved deck (e.g. screen-vision detected a deck is loaded but no metadata resolved) serializes `bpm: 0.0`. On the UI side both `deckChipText` (line 116) and `buildDeckChip` (line 129) gate on `d.bpm != null` — `0.0 != null` is `true` — so they render `Math.round(0.0)` = **`"0"`**. The chip reads `a · unknown · 0`, presenting a fabricated "0 BPM" for a track whose BPM is genuinely unknown. This is precisely the anti-slop class the phase exists to close, and it is **untested**: every test in `test_ws_bus_deck_state.py` sets `bpm` explicitly (128.0 / 124.0), so the `0.0`-default path never runs.

**Fix:** Treat a non-positive bpm as unknown on render (mirror the snapshot's own `bpm = raw if raw > 0 else None` pattern at `ws_bus.py:166-167`):

```ts
// deck-chips.ts — both deckChipText and buildDeckChip:
const bpmText = (d.bpm != null && d.bpm > 0) ? String(Math.round(d.bpm)) : UNKNOWN;
```

Or normalize at the serialize edge so the wire carries honest null:

```python
# ws_bus.py _serialize_deck_state:
"bpm": dt.bpm if dt.bpm and dt.bpm > 0.0 else None,
```

Add a test: a `DeckTrack(title="x")` with all-defaults (`bpm=0.0`, `camelot=None`) must serialize `bpm: null` (or render `unknown`), never `0`.

## Warnings

### WR-01: `set_activation_policy(Accessory)` is a process-global side effect fired from the default surface, mutating the whole app's Dock/menubar behavior

**File:** `tauri/src-tauri/src/pill_window.rs:391`

**Issue:** `apply_nonactivating` is called from `create_pill_window`, which runs by default (`primary_surface = Pill` is the default). `app.set_activation_policy(Accessory)` is **not** pill-window-scoped — it changes the activation policy of the entire application: no Dock icon, no menubar takeover, app reads as a background agent. This is a deliberate design choice per the doc, but (a) it is a surprising global mutation triggered by what reads as a per-window builder, (b) the `Mascot` and `None` surface branches do NOT set it, so the app's Dock/activation behavior silently differs depending on which surface the user picked, and (c) for a user who relies on Cmd-Tab / Dock to reach the main session window, Accessory policy removes those affordances. The mascot path (Phase 13) never set Accessory, so this is a behavior change for existing users who flip to the pill default.

**Fix:** Move the activation-policy decision out of the window builder to an explicit, surface-independent setup step (or document loudly that selecting the pill surface intentionally makes vibemix a background-agent app and confirm the main window is still reachable via the tray). At minimum, surface the Dock-disappears consequence as a KAAN-ACTION live-confirm item alongside the focus/drag items.

### WR-02: Geometry listener captures position/size by re-querying the window, not from the event payload — stale-geometry race

**File:** `tauri/src-tauri/src/pill_window.rs:299-304`

**Issue:** Inside the `Moved`/`Resized` handler the code ignores the event's payload and instead calls `window_position(&app)` / `window_size(&app)` (lines 299-304), which re-`get_webview_window` and re-query live geometry. During a fast drag, many `Moved` events queue; each handler invocation reads *current* geometry, not the geometry at the moment that specific event fired. Combined with the 200ms debounce + compare-and-skip, the persisted value is whatever the window happened to be at when the *winning* timer's closure was constructed — usually fine, but the capture happens on the OS event thread synchronously (line 298 comment says so) yet the value used is a fresh query that can race a concurrent move. The mascot original is cloned verbatim, so this is pre-existing, but it's worth flagging: prefer the event payload (`WindowEvent::Moved(pos)`) over re-querying.

**Fix:** Read geometry from the event itself where available:

```rust
if let WindowEvent::Moved(pos) = event { /* use *pos */ }
```

This eliminates the re-query race and the `WebviewNotFound` early-return path (lines 299-301) that silently drops a save if the window is mid-teardown.

### WR-03: `deck_state` view ref persists last-seen map forever — stale deck context after a track unload

**File:** `tauri/ui/src/pill/index.ts:303-304`

**Issue:** `readDeckState` returns `null` when a frame carries no `deck_state` key, and the caller only overwrites `view.deckState` when the result is non-null (lines 303-304), "so we keep deck context across frames that omit it." But `_serialize_deck_state` always emits a `deck_state` key (it returns `{}` when empty, never omits it — `ws_bus.py:337`). So in practice every live frame carries `deck_state` and `readDeckState` returns `{}` (an object, non-null) → `view.deckState = {}` → the chips correctly fall back to `decks · unknown`. The "hold last seen" branch is therefore effectively dead for the real producer. The risk is the inverse: if a bridged snapshot frame (which does NOT carry `deck_state`) is interleaved, `readDeckState` returns `null` and the pill keeps showing the previous deck's resolved key/bpm even though decks have since cleared — presenting stale (and now possibly fabricated-feeling) deck context. The honest behavior on "no fresh deck info" is debatable but holding a resolved key indefinitely risks anti-slop.

**Fix:** Either document that the flat producer always emits `deck_state` (so the persist branch is intentional belt-and-braces only), or distinguish "frame omits deck_state" (keep) from "frame carries empty deck_state" (clear) — the current code already does this correctly via `{}` vs `null`, so the main action is a test pinning that an empty `{}` frame clears the resolved chip back to `unknown`.

### WR-04: `confidence` rides the wire and is asserted in tests but never consumed by the UI — dead contract / unmet "dim a low-confidence chip" promise

**File:** `src/vibemix/runtime/ws_bus.py:104`, `tauri/ui/src/pill/deck-chips.ts:42-48,122-151`, `tests/runtime/test_ws_bus_deck_state.py:143-144`

**Issue:** `_serialize_deck_state` emits `confidence` (line 104), the test asserts it rides the wire with the comment "the consumer can dim a low-confidence chip" (test lines 143-144), and `DeckWire` declares `confidence: number | null` (deck-chips.ts:47). But `renderDeckChips`/`buildDeckChip` never read `confidence` — a deck resolved at confidence 0.3 renders an identical full-amber resolved key glyph as one at 0.95. The "dim a low-confidence chip" behavior is promised in three places and implemented in none. For an anti-slop surface this matters: a low-confidence camelot ("we think it's 8A") is rendered with the same authority as a high-confidence registry hit. Combined with `_serialize_deck_state` passing `camelot` through whenever it is non-null regardless of confidence, the pill can show an amber-authoritative key the system is barely sure of.

**Fix:** Either honor the contract (render the resolved key glyph dimmed/non-amber below a confidence floor, e.g. reuse the `<0.6` `(unsure)` threshold the v2 `derive_audible_track` already uses), or remove the `confidence` field from the wire/type/test so the contract isn't half-stated. Honoring it is the on-brand choice.

### WR-05: `lastChipsKey` / `lastDeckKey` are module-level mutable globals — cross-instance leakage and weak change detection

**File:** `tauri/ui/src/pill/index.ts:183,206`

**Issue:** `lastChipsKey` (line 183) and `lastDeckKey` (line 206) are module-scoped `let` globals used as render-memo keys. (a) They persist across the lifetime of the module, so a vitest suite that mounts the pill twice (or any future second pill instance) shares them, causing the second instance's first render to be skipped because the key matches the first instance's last value — a real test-flake / multi-window hazard. (b) The deck change-key (line 219-222) only hashes `side:camelot:bpm` — it omits `key`, `title`, and `confidence`. If a deck's raw `key` resolves while `camelot` and `bpm` stay constant (or `confidence` changes — relevant if WR-04 is fixed), the DOM will not rebuild. The `childElementCount > 0` guard (line 224) partially mitigates but does not cover the in-place value change.

**Fix:** Hold the memo keys on the `PillView` object (or a closure local in `boot`) instead of module globals, and include every field the chip renders in the change key (`side:camelot:key:bpm:confidence`).

### WR-06: Citation chips from the wire are cast `as CitationChip[]` with no per-element shape validation

**File:** `tauri/ui/src/pill/index.ts:68-71`, consumed by `citation-strip.ts:151-158`

**Issue:** `toPillFrame` does `Array.isArray(m.citation_strip) ? (m.citation_strip as CitationChip[]) : []` — it validates that the value is an array but does not validate that each element has the `{event_id, verb, timestamp_s}` shape. `renderCitationStrip` then reads `chip.event_id`, `chip.verb`, `chip.timestamp_s` directly (citation-strip.ts:155-158). A malformed frame (`citation_strip: [42, null, {}]`) produces chips with `undefined`/`NaN` text (e.g. `[undefined @ 0:00]`). Not an injection vector (all rendered via `textContent`, and `formatMmSs` defends against NaN → `0:00`), but it weakens the "verbatim, contract-tested" claim and can render slop text. The bus is described as a dumb wire, but the pill is the trust boundary for what it paints.

**Fix:** Filter to well-shaped chips before passing to the renderer:

```ts
const chips = Array.isArray(m.citation_strip)
  ? (m.citation_strip as unknown[]).filter(
      (c): c is CitationChip =>
        c != null && typeof c === "object" &&
        typeof (c as any).event_id === "string" &&
        typeof (c as any).verb === "string" &&
        typeof (c as any).timestamp_s === "number",
    )
  : [];
```

## Info

### IN-01: `_serialize_deck_state` drops several DeckTrack fields the wire/UI may want (`track_id`, `open_key`, `energy`, `source`)

**File:** `src/vibemix/runtime/ws_bus.py:98-107`

**Issue:** The serializer carries only `{title, camelot, key, bpm, confidence}`. `DeckTrack` also exposes `track_id` (feeds `[track:<id>]` citations), `open_key` ("for honesty/UI" per the dataclass doc), `energy`, and `source`. Not a bug for v1 (the chips only render deck/key/bpm), but `open_key` is explicitly documented as a UI-honesty field and `source` would let the UI distinguish a registry hit from a vision guess (relevant to WR-04). Worth noting the deliberate narrowing.

**Fix:** None required for v1; consider `source`/`open_key` when implementing confidence-aware rendering.

### IN-02: `STATE_LABEL.expand = ""` is never read because `render` always passes `baseLabel`

**File:** `tauri/ui/src/pill/index.ts:155-163,319-323`

**Issue:** `STATE_LABEL` maps `expand → ""` with a comment explaining the collapsed label keeps the base caption. But `render` (line 169) always sets `view.label.textContent = baseLabel`, and `baseLabel` for the expand mode is computed via `labelForStatus(state.cohostStatus)` (line 320-322), never via `STATE_LABEL["expand"]`. The `expand: ""` entry is dead. Minor; harmless.

**Fix:** Drop the `expand` entry from `STATE_LABEL` (or document it as unreachable) to reduce confusion.

### IN-03: `save_primary_surface` is dead code (no v1 caller), correctly `#[allow(dead_code)]`

**File:** `tauri/src-tauri/src/config.rs:221-233`

**Issue:** The writer has no caller in v1 (the Settings flip command is deferred) and is correctly annotated `#[allow(dead_code)]` with a clear comment. Flagged only for the record — this is acceptable forward-scaffolding, not a defect.

**Fix:** None. Remove the `#[allow]` when the Settings toggle ships.

### IN-04: `capabilities/default.json` description is stale vs. the actual registered command list

**File:** `tauri/src-tauri/capabilities/default.json:4`

**Issue:** The description enumerates 14 app commands but `main.rs:75-96` registers more (e.g. `debrief_window::open_debrief_window`, `wizard_cmds::run_companion_fetch`, `run_audio_config`, `open_audio_settings`). The window scope correctly includes `"pill"` (line 5) and the security posture is correct (pill gets no shell/fs/process perms — least privilege, as claimed). Only the human-readable description has drifted. Not a security issue (Tauri auto-allows registered commands regardless of the description string).

**Fix:** Refresh the description's command count/list, or trim it to avoid maintenance drift.

### IN-05: `peak` is read off the wire and threaded through the waveform API but never rendered

**File:** `tauri/ui/src/pill/index.ts:84-87,333`, `tauri/ui/src/pill/waveform.ts:101`

**Issue:** `toPillFrame` resolves `voicePeak` (flat `peak` or nested `meters.voice.peak`), the state machine carries it, `index.ts` passes it to `setWaveform`, and `setWaveform` accepts `_peak` — but the underscore param is intentionally unused ("the compact pill bars don't render a separate peak needle"). This is deliberate API-parity-with-meter.ts, not a bug. Flagged so a future reader doesn't mistake the threaded-but-unused peak for an oversight. Note the producer's snapshot sets `peak = rms` for all meters (`ws_bus.py:152-156`), so peak carries no extra signal anyway.

**Fix:** None required. Optionally drop the peak plumbing if the needle is never planned.

---

_Reviewed: 2026-05-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
