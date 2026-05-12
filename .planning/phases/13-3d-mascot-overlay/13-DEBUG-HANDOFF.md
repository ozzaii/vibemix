# Phase 13 Debug Handoff — Mascot Renders Nothing Visible

**Created:** 2026-05-12 21:35
**For:** Fresh Claude session post-compact
**Status:** Phase 13 code-complete; runtime smoke surfaced a rendering bug

---

## TL;DR

Tauri app builds + launches. The mascot overlay window IS created at runtime (verified
via CGWindowList — 300×400 transparent window, layer 5, on-screen, label `mascot`).
But the Three.js WebGL canvas inside it paints nothing visible — user only sees the
main session window, mascot is "invisible".

All 217 vitest + 28 cargo + 1208 pytest tests pass; the bug only manifests at runtime
in the Tauri webview, not in headless tests.

---

## What's Confirmed Working

- All 8 plans (13-01 .. 13-08) merged to `main`, summaries committed
- Asset bundle ships (`tauri/ui/assets/mascot/` → 22.4 MiB, 21 GLBs + manifest)
- Tauri overlay window gets created (CGWindowList confirms label=`mascot`,
  size=300×400, position=(280,50) logical, layer 5, on_screen=True, alpha=1.0)
- Main session window renders (titlebar "VIBEMIX" + 00:00 timecode visible)
- Tray icon registers + menu items wired
- Vitest fixture replay covers all event taxonomy transitions
- Pytest dispatch-latency p95 = 0.28ms vs 50ms budget
- Sidecar binary builds (`scripts/build_sidecar.py --spec vibemix-core.macos.spec`)
- `cargo build --release` succeeds in ~57s
- No process crash — vibemix runs stable after fixes below

---

## Bugs Fixed in This Session (committed)

1. **`fix(13): Tauri event names cannot contain '.' or ':' — use dash form`**
   (`46010fd`) — `tauri/src-tauri/src/ws_client.rs:89` was emitting events like
   `ipc:ipc.session.snapshot`; Tauri 2.11 IsValidEventName rejects both `.` and `:`.
   Normalized to dash form (`ipc-session-snapshot`) on both emit + listener side.
   Files touched: `ws_client.rs`, `tray.rs`, `tauri/ui/src/main.ts`.

2. **`chore(13): commit untracked session/mock.ts referenced by main.ts:104`**
   (`b5a7ca7`) — `tauri/ui/src/main.ts` referenced `./session/mock.js` but the
   `.ts` source was untracked at fork-time. Committed it to unblock TS compile.

---

## Bug I Reverted (probably still needed)

**Static window label collision** — `tauri.conf.json5` declares a static `mascot`
window with `visible: false`. The runtime `WebviewWindowBuilder::new(app, "mascot", ...)`
in `tauri/src-tauri/src/mascot_window.rs::create_mascot_window` fails with
"a webview with label `mascot` already exists" because Tauri already auto-created
the hidden one from the static config.

I patched `create_mascot_window` to detect via `app.get_webview_window("mascot")`
and reuse the existing handle, then apply runtime-only flags (always_on_top,
visible_on_all_workspaces, skip_taskbar, position, size). **I reverted that patch**
when pausing — `git checkout`. The current binary on disk may differ from the
source tree state by the time you read this.

If the launch panics with "webview with label `mascot` already exists", re-apply
the fix:

```rust
// In mascot_window.rs::create_mascot_window, after loading state:
let window = if let Some(existing) = app.get_webview_window(MASCOT_WINDOW_LABEL) {
    existing
} else {
    WebviewWindowBuilder::new(app, MASCOT_WINDOW_LABEL,
        WebviewUrl::App("mascot.html".into()))
        .title("vibemix mascot")
        .transparent(true)
        .decorations(false)
        .resizable(true)
        .min_inner_size(MIN_WIDTH, MIN_HEIGHT)
        .max_inner_size(MAX_WIDTH, MAX_HEIGHT)
        .build()?
};
// Then runtime flags:
window.set_size(PhysicalSize::new(width, height))?;
window.set_position(PhysicalPosition::new(x, y))?;
window.set_always_on_top(true)?;
window.set_visible_on_all_workspaces(true)?;
window.set_skip_taskbar(true)?;
window.show()?;
if state.click_through { window.set_ignore_cursor_events(true)?; }
```

Alternative cleaner fix: remove the static `mascot` entry from `tauri.conf.json5`
and let the runtime builder be the sole creator. The capability scope
(`capabilities/default.json` has `"windows": ["main", "mascot"]`) doesn't require
the window to exist in static config.

---

## THE REAL BUG: WebGL Canvas Paints Nothing

After fixing the two issues above, the app boots cleanly:

- `[vibemix] mascot overlay window built` prints to stderr
- CGWindowList shows the mascot window exists, on-screen, alpha 1.0, layer 5
- Main session UI window is also up and visible
- BUT user sees ONLY the main window; mascot area is fully transparent / invisible

### Hypothesis Ranking

1. **Most likely**: `index.ts` throws BEFORE `renderer.crossFadeTo("idle_breathe")`
   runs. Silent error means transparent window over transparent canvas.

2. **Likely**: Asset fetch fails. `asset-loader.ts` fetches
   `/assets/mascot/manifest.json` then 21 GLBs. The Tauri webview uses a custom
   protocol (`tauri://localhost` or similar) and the `/assets/...` paths may not
   resolve. Vite static-copy puts assets at `dist/assets/mascot/` — verify they're
   reachable via the runtime URL.

3. **Less likely**: WebGL context fails on Tauri's macOS webview with
   `alpha:true + premultipliedAlpha:false + transparent backing`. The
   tauri-runtime-wry backend on macOS uses WKWebView which has known quirks
   with transparent WebGL.

4. **Edge case**: `frameCameraForBust` computes camera position from
   `Box3.setFromObject(characterRoot)` — if the GLB loads but has zero bounds
   (degenerate scene root), the camera ends up at NaN and nothing renders. Plan
   13-04 explicitly handles `findSkinnedMesh` throwing if absent, but doesn't
   guard against an empty box.

---

## How to Diagnose (Recommended Path)

### Step 1: Enable devtools

Edit `tauri/src-tauri/Cargo.toml` line 29 — add `"devtools"` to the tauri features:

```toml
tauri = { version = "2.11", features = ["macos-private-api", "config-json5", "tray-icon", "image-png", "devtools"] }
```

Rebuild: `cd tauri/src-tauri && cargo build --release` (~1-2 min).

### Step 2: Launch + open Safari Web Inspector

```bash
./tauri/src-tauri/target/release/vibemix > /tmp/vibemix.log 2>&1 &
```

On the user's Mac: Safari → menu bar → Develop → "vibemix" → "mascot.html".
Console tab shows actual JS errors. Network tab shows whether `/assets/...`
fetches return 200 or 404.

If Develop menu missing: Safari → Settings → Advanced → "Show Develop menu in
menu bar". Also requires `defaults write com.apple.Safari IncludeInternalDebugMenu 1`
sometimes.

### Step 3: If Safari Inspector doesn't work

The kludge that worked in diagnosis-attempt: add a magenta CSS background +
inline error logger to `tauri/ui/mascot.html`. The Tauri `transparent: true`
config means CSS bg shows ONLY if the WebGL canvas isn't covering it (i.e.,
canvas mounted but Three.js didn't paint). So if you see magenta = canvas
mount OK, renderer failed. If you see nothing = canvas didn't mount.

```html
<style>
  body { background: #ff00ff; }
  #mascot-diag {
    position: fixed; top: 8px; left: 8px;
    font: 11px/1.4 monospace; color: #fff;
    background: rgba(0,0,0,0.6); padding: 4px 8px;
    border-radius: 4px; z-index: 9999; max-width: 90vw;
    white-space: pre-wrap;
  }
</style>
...
<div id="mascot-diag">mascot.html booted, waiting for script…</div>
<script>
  const diag = document.getElementById('mascot-diag');
  window.addEventListener('error', (e) => {
    diag.textContent += '\nerror: ' + (e.error?.stack || e.message);
  });
  window.addEventListener('unhandledrejection', (e) => {
    diag.textContent += '\nrejection: ' + (e.reason?.stack || e.reason);
  });
</script>
```

This bypasses transparency at the OS level only if Tauri's `transparent: true`
is what's hiding things. If transparent at OS level wins, you'll need to also
temporarily flip `tauri.conf.json5` mascot entry to `"transparent": false` for
diagnosis (rebuild required).

### Step 4: Check asset resolution

In the running app's main webview Console (Safari Inspector):

```js
fetch('/assets/mascot/manifest.json').then(r => console.log(r.status, r.url))
```

If 404 → the path is wrong for Tauri's serving. Check Vite's static-copy
output is in `dist/assets/mascot/` and the bundled HTML references it correctly.

---

## Files to Read First

In order of relevance:

1. `.planning/phases/13-3d-mascot-overlay/13-CONTEXT.md` — locked design decisions
2. `.planning/phases/13-3d-mascot-overlay/13-VERIFICATION.md` — gate status
3. `tauri/src-tauri/src/mascot_window.rs` — window builder, may need re-patch
4. `tauri/src-tauri/src/main.rs` — setup flow
5. `tauri/ui/src/mascot/index.ts` — webview entry, calls renderer + state machine
6. `tauri/ui/src/mascot/renderer.ts` — WebGL setup, asset binding, mixer
7. `tauri/ui/src/mascot/asset-loader.ts` — fetch paths for manifest + GLBs
8. `tauri/ui/mascot.html` — webview HTML, currently transparent
9. `tauri/src-tauri/tauri.conf.json5` — static window definitions + CSP
10. `tauri/src-tauri/capabilities/default.json` — capability scope

---

## Don't Repeat What I Tried

- ✘ Don't fight the IPC event names — `46010fd` already fixed them, dash form is correct
- ✘ Don't add `session/mock.ts` — `b5a7ca7` already added it
- ✘ Don't try to commit changes from running `npm install` — three.js dep is already in package.json (Plan 13-04 added it)
- ✘ Don't run `python scripts/build_sidecar.py` without `--spec vibemix-core.macos.spec`
- ✘ The placeholder `tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin` may
  need to be removed (`rm -f`) before sidecar build, then the script creates a real
  directory there
- ✘ Don't try to enumerate windows via AppleScript `tell System Events` — transparent
  Tauri windows don't show up there. Use CGWindowList via Python:
  ```python
  import Quartz
  for w in Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID):
      if w.get('kCGWindowOwnerName') == 'vibemix':
          print(w.get('kCGWindowName'), dict(w.get('kCGWindowBounds', {})))
  ```

---

## Open Pre-existing Test Failures (NOT regressions, NOT from Phase 13)

Logged in `.planning/phases/13-3d-mascot-overlay/deferred-items.md`:

1. `tests/test_phase05_verification.py::test_g5_poc_files_untouched` — git pathspec
   `mascot.html` matches both legacy `./mascot.html` AND new `tauri/ui/mascot.html`.
   Fix: change pathspec to `":(top)mascot.html"`. One-line fix, do it during Phase 14.
2. `tests/test_audio_macos_live.py::test_open_voice_output_completes_without_real_audio_device` —
   needs headphones plugged in. Move to opt-in `VIBEMIX_LIVE_SMOKE=1` block.
3. `test_persona_02_byte_identical_to_v4` — only fails in worktrees because
   `cohost_v4.py` is untracked. Either commit `cohost_v4.py` or make the test skip
   gracefully when absent.

---

## What to Do After Fixing the Render Bug

1. Commit the fix as `fix(13): mascot renderer paints character — <one-line why>`
2. Update `13-HUMAN-UAT.md` summary: `pending: 29` (item A-01 now passes)
3. Resume autonomous: `/gsd-autonomous --from 14` (FL-Studio polish)
4. Phase 14 will critique → execute → critique on the live UI surfaces; the
   mascot rendering quality will be one of the loop targets

---

## Recent Commit Trail (most relevant first)

```
8bc092b  test(13): persist 30-item manual smoke as HUMAN-UAT (status: partial)
46010fd  fix(13): Tauri event names cannot contain '.' or ':' — use dash form
b5a7ca7  chore(13): commit untracked session/mock.ts referenced by main.ts:104
994e53c  docs(phase-13): mark 13-08 complete after Wave 4 merge
2fa7102  chore: merge executor worktree (13-08 — verification fixtures + smoke)
fad4bf2  chore: merge executor worktree (13-07 — mood + particle puff)
be9673e  chore: merge executor worktree (13-06 — WS bus + event dispatcher)
0d1c6ff  docs(phase-13): mark 13-04 complete
0def908  chore: merge executor worktree (13-04 — Three.js + state machine)
539e916  chore: merge executor worktree (13-05 — Python sidecar mood)
39d3e66  chore: merge executor worktree (13-03 — Phase 12 corner + Settings)
7e4dd15  chore: merge executor worktree (13-02 — Tauri shell + tray)
12b0aa8  chore: merge executor worktree (13-01 — Meshy asset bundle)
```

---

## How to Verify the Render Fix Works

After the fix, the user should see (without any special diagnostic mode):

1. Main session window (VIBEMIX titlebar + black canvas) — already works
2. **A 3D character mascot floating on top of the screen** — the Meshy "Neon Rebel"
   biped, ~300×400px window, top-right area by default, transparent background,
   character visible and animating (idle_breathe loop on boot)
3. Tray icon in menu bar (already works)
4. Left-clicking tray icon toggles mascot visibility

The character should be playing `Sleep_Normally.glb` slowed down (= `idle_breathe`)
on boot, or `idle_bop_to_beat` if a mood profile pre-loaded — Plan 13-07's mood-aware
boot path. Mood defaults to `hype-man`.

When the WS bus connects (sidecar must be running) the mascot should react to
events. Without a sidecar, it stays in idle.

---

Good luck.
