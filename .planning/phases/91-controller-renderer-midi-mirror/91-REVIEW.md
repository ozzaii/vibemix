---
phase: 91-controller-renderer-midi-mirror
reviewed: 2026-05-28T00:00:00Z
depth: standard
files_reviewed: 40
files_reviewed_list:
  - src/vibemix/learn/__init__.py
  - src/vibemix/learn/midi_mirror.py
  - src/vibemix/ui_bus/learn_messages.py
  - src/vibemix/ui_bus/__init__.py
  - src/vibemix/runtime/ws_bus.py
  - src/vibemix/__main__.py
  - scripts/check_ipc_schema.py
  - tauri/src-tauri/src/learn_window.rs
  - tauri/src-tauri/src/main.rs
  - tauri/src-tauri/capabilities/default.json
  - tauri/ui/src/ipc/messages.schema.json
  - tauri/ui/src/ipc/messages.ts
  - tauri/ui/src/ipc/validator.generated.mjs
  - tauri/ui/src/learn/learn-window.ts
  - tauri/ui/src/learn/ws-client.ts
  - tauri/ui/src/learn/components/controller-stage.ts
  - tauri/ui/src/learn/components/titlebar.ts
  - tauri/ui/src/learn/components/empty-state.ts
  - tauri/ui/src/learn/components/status-bar.ts
  - tauri/ui/src/learn/components/unplugged-toast.ts
  - tauri/ui/src/learn/controllers/_aria-labels.ts
  - tauri/ui/src/learn/controllers/_generic.svg.ts
  - tauri/ui/src/learn/controllers/pioneer_ddj_flx4.svg.ts
  - tauri/ui/src/learn/controllers/pioneer_ddj_flx6.svg.ts
  - tauri/ui/src/learn/controllers/pioneer_ddj_400.svg.ts
  - tauri/ui/src/learn/controllers/pioneer_ddj_flx10.svg.ts
  - tauri/ui/src/learn/controllers/pioneer_ddj_1000.svg.ts
  - tauri/ui/src/learn/controllers/pioneer_ddj_sx3.svg.ts
  - tauri/ui/src/learn/controllers/pioneer_xdj_rx3.svg.ts
  - tauri/ui/src/learn/controllers/numark_party_mix_live.svg.ts
  - tauri/ui/src/learn/controllers/hercules_inpulse_300.svg.ts
  - tauri/ui/src/learn/controllers/hercules_inpulse_500.svg.ts
  - tauri/ui/src/learn/styles/learn.css
  - tauri/ui/vite.config.ts
  - tauri/ui/learn.html
findings:
  blocker: 3
  warning: 6
  info: 4
  total: 13
status: partial
fixed_at: 2026-05-28T02:15:00Z
fixed_summary:
  blocker_fixed: 3   # CR-01 CR-02 CR-03
  warning_fixed: 6   # WR-01 WR-02 WR-03 WR-04 WR-05 WR-06
  info_fixed: 2      # IN-01 IN-03 (IN-04 absorbed into CR-03 inline)
  info_deferred: 1   # IN-02 (Tauri mutex / state-mgmt — non-trivial, theoretical race)
  total_fixed: 11
  total_deferred: 1  # plus IN-04 absorbed into CR-03
fixed_commits:
  - d2dec059 fix(91): CR-01 drop double MIDI listener thread; WR-04 use current_profile()
  - e8a16d05 fix(91): CR-02 stop rotating faders; classify by control-id prefix
  - fb96bf4d fix(91): CR-03 filter ws-client to ipc.learn.* before warn/validate
  - c0bf5ba7 fix(91): WR-01 wire pendingControllerId guard into the rAF drainer
  - 320564cc fix(91): WR-02 pin ARIA_LABELS as the source of truth via parity test
  - 16c7b15b fix(91): WR-03 wire titlebar/status dispose + rAF stopped flag on beforeunload
  - c6719f57 fix(91): WR-05 implement controller_detected mount-time RENDER-01 contract
  - 9aa5ea73 fix(91): WR-06 type the midi_mirror kwarg via a Protocol
  - 59c3a626 fix(91): IN-01 drop <g> prefix from FLX4 SVG pattern comment
  - 979d85b3 fix(91): IN-03 store unplugged-toast timer handles in a WeakMap
---

# Phase 91: Code Review Report

**Reviewed:** 2026-05-28T00:00:00Z
**Depth:** standard
**Files Reviewed:** 40
**Status:** issues_found

## Summary

Phase 91 ships the Learn controller renderer + 30 Hz MIDI mirror — 11 hand-authored SVG schematics, a delta-coalesced Python producer, a Rust window, and the IPC schema/codegen pipeline. The plumbing is wired correctly: the schema parity gate is solid, the brand-safety contract holds (no `#FF7F00`, no `Pioneer DJ` wordmarks, currentColor throughout), the single-socket invariant is preserved, and the threading discipline inside `MidiMirror` is correct.

But three issues survive the existing test suite and break the standalone-verifiable artifact bar:

1. **`__main__.py` spawns a second MIDI listener thread on every hot-plug** because the P91 callback layer constructs a fresh `ListenerHolder` with `bound_port=None` instead of inheriting the holder `MidiMacOS` previously owned. The static listener at `__main__.py:1365` and the new port-watcher-spawned listener both call `controller_state.handle_msg(msg)` for every incoming MIDI message → doubled events, leaked thread on shutdown.
2. **Every fader (vol/xfader/tempo) carries `data-cx`/`data-cy`** so `controller-stage.ts::applyPositionFrame` rotates the whole fader group instead of translating the thumb. A user moving the FLX4 pitch slider will see the on-screen fader *rotate* — the exact "doesn't feel grounded" anti-pattern the milestone is built to prevent.
3. **The Learn ws-client logs `[learn:ws] envelope missing type; dropping` on every 30 Hz mascot frame** because `ws_broadcast` emits the legacy flat mascot frame (no `type` field) on the same socket. At 30 Hz that's 30 warnings per second to the console — performance noise plus the dev-experience regression the existing tests cannot see (jsdom test fixtures bypass live 8765 traffic).

The latency, parity, and brand-safety gates pass cleanly. The bugs above are pre-Kaan-ear-pass; none would be caught by re-running the existing suite.

## Structural Findings (fallow)

No `<structural_findings>` block was provided. The findings below are all narrative.

## Narrative Findings (AI reviewer)

## Blocker Issues

### CR-01: `__main__.py` spawns a second MIDI listener — every MIDI event doubled

**File:** `src/vibemix/__main__.py:1390-1429`
**Issue:** Pre-P91, `midi_macos.start_port_watcher(midi_watcher_stop)` was called with no callback. The default branch in `_midi_macos.py::start_port_watcher` (lines 196-209) built its OWN `ListenerHolder` seeded from `self.controller_state` and used it for `handle_port_change_single_state`. That holder shared lifecycle with the static listener spawned at `__main__.py:1365` (`midi_macos.start_listener_thread(midi_stop)`).

P91 introduces `_on_midi_port_change` and passes it as `on_change=`. This bypasses the default holder construction, so the only `ListenerHolder` in scope is the fresh `_midi_holder` declared at lines 1390-1396 with `bound_port=None`. On port-watcher sweep #1 (always emits a `connected` event for every input present), `handle_port_change_single_state` sees `bound_port=None != port_name` and runs the "stop existing listener + spawn fresh" branch (`_midi_common.py:298-313`). Result: a second `spawn_listener` runs, calls `mido.open_input(port_name)` on the same port, and starts feeding `controller_state.handle_msg(msg)` from a second daemon thread. The static listener from line 1365 is *still running*.

Both threads now call `handle_msg` for every incoming MIDI message → `_record_move()` ring gets every event twice, `_handle_cc` mutates `self.deck[d][field]` twice (same value, idempotent), button toggles flip twice → toggles cancel each other. Particularly visible for `play:A`: pressing the FLX4 play button enqueues two `note_on` messages in fast succession, both invert `self.deck[deck]["play"]` → play state ends up unchanged. The hot-plug fix that landed pre-P91 (single-state in-place mutation) is silently broken.

Additionally, the second listener's stop event (`_midi_holder.listener_stop`) is set only inside `handle_port_change_single_state` and is never reachable from the `finally` block at `__main__.py:1597-1601`. Cleanup only signals `midi_stop` (the static listener's event). The new daemon thread leaks until process exit. Daemon=True keeps shutdown clean, but the thread runs unbounded during the session and on a Mac whose `mido.open_input` returns a real CoreMIDI port it holds the resource open.

**Fix:** Either reuse the MidiMacOS-owned holder (preferred — keeps single-state ownership) or skip step 1 in `_on_midi_port_change` entirely (the static listener already handles the connect/disconnect lifecycle; P91 only needs the bind_profile + envelope-enqueue layer).

```python
# Option A — let MidiMacOS own the holder, and seed _midi_holder from it:
def _on_midi_port_change(event: tuple) -> None:
    # Step 1: delegate to MidiMacOS' owned holder (created lazily inside
    # start_port_watcher when on_change is None — but we override
    # on_change, so reach in and reuse what MidiMacOS already manages).
    # Best path: don't override on_change; instead wrap inside MidiMacOS
    # so the default holder is preserved.
    ...

# Option B — drop the duplicate listener-thread restart entirely:
def _on_midi_port_change(event: tuple) -> None:
    # The static listener (start_listener_thread above) already detects
    # plug/unplug via its inner retry loop. P91 only needs the envelope
    # layer; the legacy listener-restart path is dead weight here.
    kind = event[0]
    if kind == "connected":
        _, port_name, profile = event
        midi_mirror.bind_profile(profile)
        midi_mirror.queue_controller_detected(
            connected=True, profile=profile, port_name=port_name,
        )
    elif kind == "disconnected":
        _, port_name = event
        last_profile = midi_mirror.current_profile()  # new public accessor
        if last_profile is not None:
            midi_mirror.queue_controller_detected(
                connected=False, profile=last_profile, port_name=port_name,
            )
        midi_mirror.unbind()
```

Add a regression test exercising both `start_listener_thread` AND `start_port_watcher` against the same fake mido emitting a port, asserting `controller_state._moves` count equals 1× the events delivered (not 2×).

### CR-02: Fader rotation — `vol:*`, `xfader`, `tempo:*` SVG groups visibly rotate instead of translating

**File:** `tauri/ui/src/learn/components/controller-stage.ts:174-184` + every `*.svg.ts` fader group
**Issue:** Every fader hit-region across all 11 SVGs (e.g. `pioneer_ddj_flx4.svg.ts:132-143, 239-273, 343-...`) carries `data-cx` + `data-cy`. The renderer:

```ts
const cx = group.dataset.cx;
const cy = group.dataset.cy;
if (cx !== undefined && cy !== undefined) {
  // Knob / fader-thumb-with-pivot — rotate.
  const degrees = (value / 127) * 270 - 135;
  group.setAttribute(
    "transform",
    `rotate(${degrees} ${Number(cx)} ${Number(cy)})`,
  );
}
```

…rotates the whole `<g>` group around (cx, cy). For a knob this is correct (the circle is centered at cx/cy so it appears stationary while the index marker line rotates). For a fader the `<g>` contains both the vertical track rect and the thumb rect — at `value=0` the rotation is -135° about the fader's center, visibly tilting the entire slider.

A user moving the FLX4 pitch slider from value=64 (straight) to value=127 (top) will see the on-screen fader *rotate from straight to +135°*. From value=64 to value=0 (bottom) → fader tilts to -135°. The motion is uniformly wrong across all 5+ fader controls per controller and all 11 controllers.

The latency CI gate (`tauri/ui/tests/learn/highlight-latency.test.ts`) only exercises the `eq_hi:A` knob path (lines 76, 110-114), so the bug is invisible to existing tests. No fader/xfader/tempo unit test exists. A Kaan ear-pass with a real FLX4 surfaces this in seconds — fails the milestone success bar.

**Fix:** Distinguish fader thumbs from knob bodies. Two viable patterns:

```ts
// Pattern A — add data-axis="vertical|horizontal" to faders + structure
// the thumb as a child <rect class="thumb"> within the group. Renderer:
const axis = group.dataset.axis;
if (axis) {
  const thumb = group.querySelector<SVGRectElement>(".thumb");
  if (!thumb) continue;
  // Translate thumb along axis; bounds from data-* attrs.
  const range = Number(group.dataset.range ?? 0);
  const offset = ((value / 127) - 0.5) * range; // bipolar example
  thumb.setAttribute(
    "transform",
    axis === "vertical" ? `translate(0 ${-offset})` : `translate(${offset} 0)`
  );
} else if (cx !== undefined && cy !== undefined) {
  // Knob — rotate as today.
}

// Pattern B — drop data-cx/data-cy from fader groups entirely; add
// data-axis instead. Renderer dispatches on attribute presence.
```

Then update every fader group across 11 SVGs + a vitest case covering `vol:A` and `xfader` translation.

### CR-03: ws-client.ts spams `[learn:ws] envelope missing type` 30×/sec on the mascot bus

**File:** `tauri/ui/src/learn/ws-client.ts:104-118`
**Issue:** The Learn webview opens a ws client on `127.0.0.1:8765` — the SAME socket `ws_broadcast` uses for the 30 Hz mascot frame. The mascot frame is a flat dict (no `type` field; see `src/vibemix/runtime/ws_bus.py:496-529`):

```python
mascot_frame = {
    **levels.snapshot(),
    "audible": state.audible,
    "deck": state.audible_deck,
    ...
}
```

When this frame arrives at `LearnWsClient.onMessage`, line 114-117 fires:

```ts
if (typeof envelope?.type !== "string") {
  console.warn("[learn:ws] envelope missing type; dropping");
  return;
}
```

At 30 Hz that's 30 console.warn calls per second to the Learn webview's devtools console. Over a 60-minute teaching session that's 108,000 warnings. DevTools console + perf overhead become unusable; the warning makes diagnosing real schema drift impossible.

Same applies to `ipc.session.snapshot` (~15 Hz), `ipc.status.tick` (~1 Hz), `ipc.mascot.mood_change` events — all valid envelopes the Learn webview doesn't care about but successfully dispatches as window events, doing wasted work.

**Fix:** Filter to `ipc.learn.*` types BEFORE validation, drop everything else silently (or at log-level=debug only).

```ts
private onMessage(raw: unknown): void {
  if (typeof raw !== "string") return;
  let envelope: { type?: string; payload?: unknown };
  try {
    envelope = JSON.parse(raw) as { type?: string; payload?: unknown };
  } catch (e) {
    console.warn("[learn:ws] parse failed; dropping frame", e);
    return;
  }
  // Drop frames that don't target the Learn surface BEFORE logging.
  // ws:8765 is shared with the mascot + status + session-snapshot
  // producers; only `ipc.learn.*` types are this webview's concern.
  const t = envelope?.type;
  if (typeof t !== "string" || !t.startsWith("ipc.learn.")) return;
  const ok = validate(envelope);
  if (!ok) {
    console.warn(`[learn:ws] validate failed for ${t}; dropping`);
    return;
  }
  window.dispatchEvent(new CustomEvent(t, { detail: envelope.payload }));
}
```

Add a vitest case that synthesizes a mascot frame (no `type`) + a status tick + a learn envelope on the same client and asserts only the learn envelope reaches `window.addEventListener("ipc.learn.*", ...)` without any console output for the others.

## Warnings

### WR-01: `pendingControllerId` is dead code; documented swap-race not actually guarded

**File:** `tauri/ui/src/learn/learn-window.ts:82, 138, 147`
**Issue:** The comment block at lines 79-83 says `pendingControllerId` exists so the rAF drainer doesn't apply a frame to the wrong SVG on a same-tick controller swap. It IS set (line 147) and cleared (line 138), but the drainer at lines 164-178 never reads it — it only checks `stage.currentControllerId !== null`. If `controller_detected{A}` lands, then `midi_position{B}` lands before the next rAF tick, then `controller_detected{B}` lands, the drainer paints A's positions onto B's SVG (most `<g data-control-id>` keys overlap across SKUs — `vol:A`, `eq_hi:A` etc. — so the silent miscolor goes unnoticed but is wrong).

**Fix:** Either read `pendingControllerId` in the drainer (skip when it doesn't match `stage.currentControllerId`) or delete the dead variable + its tracking comment.

```ts
function drainFrame(): void {
  if (
    pendingPositions !== null &&
    pendingControllerId !== null &&
    stage.currentControllerId === pendingControllerId
  ) {
    stage.applyPositionFrame(pendingPositions);
    if (pendingEmitTs !== null) {
      status.pushLatency(performance.now() - pendingEmitTs);
    }
  }
  pendingPositions = null;
  pendingEmitTs = null;
  requestAnimationFrame(drainFrame);
}
```

### WR-02: `ARIA_LABELS` exported but never imported — drift risk

**File:** `tauri/ui/src/learn/controllers/_aria-labels.ts`
**Issue:** The 101-line table maps `<field>:<deck>` keys to human-readable labels and the file docstring claims it's the "single source of truth" for SVG `aria-label` attributes. But no SVG file imports it; each of the 11 SVGs hardcodes its own `aria-label="..."` strings. A grep across `tauri/ui/src/learn/` confirms zero importers.

A future SKU adding a control or renaming a deck would update one side only; nothing fails the build. The author intended a parity test (`test_aria_labels_present.spec.ts` does check labels are present, but doesn't compare against `ARIA_LABELS`).

**Fix:** Either (a) delete the file if the SVG-internal labels are the source of truth, or (b) write a parity test:

```ts
// tauri/ui/tests/learn/test_aria_labels_match_table.spec.ts
import { ARIA_LABELS } from "../../src/learn/controllers/_aria-labels";
// For each SVG, parse <g data-control-id>, read its aria-label,
// assert label === ARIA_LABELS[control-id].
```

### WR-03: `LearnTitlebar` / `StatusBar` setInterval timers never disposed

**File:** `tauri/ui/src/learn/components/titlebar.ts:42` + `status-bar.ts:81` + `learn-window.ts`
**Issue:** Both components register `setInterval(...)` in their constructors and expose `dispose()` methods, but `learn-window.ts::mountLearnWindow` never calls them. On window close the page tears down and GC reclaims the closures, so production impact is zero — but if `mountLearnWindow` is called twice in the same page (e.g. a future test fixture or HMR reload), timers stack up.

Same applies to the unbounded `requestAnimationFrame(drainFrame)` loop at `learn-window.ts:181` — never stopped.

**Fix:** Wire `window.addEventListener("beforeunload", () => { titlebar.dispose(); status.dispose(); ws.close(); })` in mountLearnWindow, and add a `stopped` flag the drainer checks before re-scheduling.

### WR-04: `_on_midi_port_change` reads `midi_mirror._profile` private attr

**File:** `src/vibemix/__main__.py:1418`
**Issue:** `_last_profile = getattr(midi_mirror, "_profile", None)` couples `__main__.py` to MidiMirror's private attribute. Any future internal refactor (e.g. renaming `_profile` to `_active_profile`) silently changes the disconnect envelope's payload to use `None` and skip the disconnect emit entirely (because of the `if _last_profile is not None:` guard) — the webview would never see the `connected: false` event.

**Fix:** Expose a public accessor on `MidiMirror`:

```python
# src/vibemix/learn/midi_mirror.py
def current_profile(self) -> ControllerProfile | None:
    """The currently-bound profile, or None when no controller is bound."""
    return self._profile
```

Update `__main__.py`:
```python
last_profile = midi_mirror.current_profile()
```

### WR-05: `test_controller_detected_mounts_svg.test.ts` is a TODO stub asserting `expect(real).toBe(true)`

**File:** `tauri/ui/tests/learn/test_controller_detected_mounts_svg.test.ts:42-58`
**Issue:** The test body is a sketched-out comment; the only assertion is `expect(real).toBe(true)` — i.e., "is the real renderer present in source?". Steps 1-6 (mount the window, dispatch a synthetic envelope, await the dynamic-import settle, assert the SVG element exists, assert elapsed ≤ 2000 ms) are all comments. The 2-second mount-time RENDER-01 contract is NOT under test.

CI green is misleading: the assertion can't detect a regression in `mountLearnWindow` or `loadControllerSvg`. Compounded with CR-02 (fader rotation), the entire RENDER-01 + RENDER-02 happy path lacks meaningful coverage at the integration level.

**Fix:** Implement the steps in the TODO sketch. Use vitest's fake timers + jsdom; dispatch the synthetic event; await `setTimeout(50)` for dynamic-import settle; assert `document.querySelector('[data-control-id="eq_hi:A"]') !== null`.

### WR-06: `ws_broadcast` accepts `midi_mirror: Any | None` — no type discipline

**File:** `src/vibemix/runtime/ws_bus.py:348`
**Issue:** The new kwarg is typed `Any | None`. The function calls `midi_mirror.drain_pending_detected()` and `midi_mirror.snapshot()` (lines 594, 608). A typo or stale caller passing the wrong object would only surface at runtime via the existing try/except wrappers — and the resulting `[learn drain err]` / `[learn snapshot err]` messages don't indicate root cause.

The rest of the function uses `Any | None` consistently (`controller_state`, `suggestion_holder`, `tracer`) — so the precedent isn't bad in this file — but Phase 91 had an opportunity to introduce a `Protocol` or import `MidiMirror` directly (now that it lives in `vibemix.learn`).

**Fix:**
```python
# vibemix/runtime/ws_bus.py
from vibemix.learn import MidiMirror  # circular-safe — learn imports from ui_bus, not runtime

async def ws_broadcast(
    ...
    midi_mirror: MidiMirror | None = None,
) -> None:
```

Or, if circular-import risk is real, use TYPE_CHECKING import and a `Protocol`:
```python
from typing import TYPE_CHECKING, Protocol

class _MidiMirrorProtocol(Protocol):
    def drain_pending_detected(self) -> list[dict]: ...
    def snapshot(self) -> dict | None: ...
```

## Info

### IN-01: FLX4 SVG file docstring claims "25 hit-regions" — grep shows 26 hits including the pattern in the comment

**File:** `tauri/ui/src/learn/controllers/pioneer_ddj_flx4.svg.ts:38, 28`
**Issue:** Cosmetic. The docstring at line 38 says "The 25-entry set is:" — accurate (25 actual `<g data-control-id>` groups, the parity test confirms). The grep count of 26 in the file-list summary includes line 28's pattern comment `<g data-control-id="<field>:<deck>"`. Not a code bug — just a flag for future readers that the count `grep -c data-control-id` returns 26 vs the actual hit-region count of 25.

**Fix:** None needed; leave the docstring count accurate. If desired, change line 28 to `g data-control-id` (drop the leading `<`) so grep counts cleanly.

### IN-02: `open_learn_window` window-build race is theoretical but unguarded

**File:** `tauri/src-tauri/src/learn_window.rs:64-86`
**Issue:** Two concurrent invocations (rare; Tauri serializes commands per webview but two webviews could in principle invoke simultaneously) would both pass the `get_webview_window` check before either calls `build()`, then one `build()` would fail with a duplicate-label error. The error propagates correctly through `Result<(), String>` so no crash — just a confusing user-facing error message.

**Fix:** Use Tauri's `Mutex` state-managed lock around the open path, OR catch the duplicate-label error class specifically and treat it as success (the other invocation won the race).

### IN-03: `unplugged-toast` dataset-as-string timer-handle storage is fragile in non-browser

**File:** `tauri/ui/src/learn/components/unplugged-toast.ts:34-35, 44-45`
**Issue:** `setTimeout` returns `number` in browser and `Timeout` object in node/jsdom. `String(timeoutObject)` may yield `"[object Object]"`; `Number("[object Object]")` is `NaN`; `clearTimeout(NaN)` is a silent no-op. Production works because Tauri webviews use the browser `setTimeout`. In a jsdom test that mocks timers differently, the auto-dismiss restart on duplicate toasts could leak the old timer.

**Fix:** Store the handle in a module-scoped `Map<HTMLElement, ReturnType<typeof setTimeout>>` instead of round-tripping through a dataset string.

### IN-04: ws-client `await` keyword present but no awaitable in the function body

**File:** `tauri/ui/src/learn/ws-client.ts:120-123` (comment) + the surrounding method
**Issue:** The comment says "the `await` keyword on this method exists for parity with the earlier dynamic-import path" — but `onMessage` is NOT declared `async`, has no `await`, and validate() returns synchronously. The comment is stale (likely a vestige of an earlier draft that did `await import("...")`).

**Fix:** Delete the misleading comment block (lines 119-123).

---

_Reviewed: 2026-05-28_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
